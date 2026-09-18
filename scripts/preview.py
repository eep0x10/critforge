"""Render real mesh views with Blender; optional before/after uses identical cameras."""
import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
from common import WorkflowError, atomic_json, emit, project_root, run, sha256
from asset_validation import validate_asset

VIEWS = ('front', 'back', 'left', 'right', 'isometric', 'detail')


def render(source, output, blender=None, reference=None, face=None, size=768):
    source, output = Path(source).resolve(), project_root(output)
    reference = Path(reference).resolve() if reference else None
    if size < 128 or size > 2048:
        raise WorkflowError('Preview size must be 128..2048 pixels.')
    if face and (len(face) != 4 or not all(math.isfinite(v) for v in face) or face[3] <= 0):
        raise WorkflowError('Face framing requires center X Y Z and a positive view width in mesh units.')
    for path in (source, reference):
        if path:
            if path.suffix.lower() not in ('.stl', '.ply'):
                raise WorkflowError('Preview supports STL/PLY only.')
            if path.suffix.lower() == '.stl':
                validate_asset(path)
    executable = shutil.which(blender or 'blender')
    if not executable:
        raise WorkflowError('Blender unavailable: pass --blender with its executable path.')
    worker = Path(__file__).with_name('preview_blender.py')
    key = {'source': sha256(source), 'reference': sha256(reference) if reference else None,
           'face': list(face) if face else None, 'size': size, 'worker': sha256(worker),
           'renderer': sha256(Path(__file__)), 'blender_binary': sha256(executable)}
    manifest = output / 'preview.json'
    if manifest.is_file():
        try:
            old = json.loads(manifest.read_text(encoding='utf-8'))
            if old.get('cache_key') == key and old.get('files') and all(
                Path(name).name == name and (output / name).is_file() and sha256(output / name) == digest
                for name, digest in old['files'].items()):
                return {'cached': True, 'contact_sheet': str(output / 'contact-sheet.png')}
        except (ValueError, KeyError):
            pass
    if output.exists() and any(output.iterdir()):
        raise WorkflowError('Preview directory is nonempty or cache changed; use a new revision directory.')
    from PIL import Image, ImageDraw
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.preview-') as temp:
        temp = Path(temp)
        config = {'source': str(source), 'reference': str(reference) if reference else None,
                  'output': str(temp), 'size': size, 'face': face}
        atomic_json(temp / 'config.json', config)
        with (temp / 'render.log').open('wb') as log:
            try:
                result = subprocess.run([executable, '--background', '--factory-startup', '-t', '4',
                    '--python-exit-code', '2', '--python', str(worker), '--', str(temp / 'config.json')],
                    stdout=log, stderr=subprocess.STDOUT, timeout=600)
            except subprocess.TimeoutExpired:
                raise WorkflowError('Preview timed out. Use a smaller revision or inspect locally.') from None
        if result.returncode:
            raise WorkflowError('Blender rendering failed; no completed preview was published.')
        if sha256(source) != key['source'] or (reference and sha256(reference) != key['reference']):
            raise WorkflowError('Input changed during rendering; use a stable revision and render again.')
        labels = ('before', 'after') if reference else ('model',)
        sheet = Image.new('RGB', (size * 3, (size + 32) * 2 * len(labels)), '#eeeeee')
        draw = ImageDraw.Draw(sheet)
        for row, label in enumerate(labels):
            for index, view in enumerate(VIEWS):
                name = f'{label}-{view}.png'
                with Image.open(temp / name) as frame:
                    frame.load()
                    if frame.size != (size, size):
                        raise WorkflowError('Unexpected rendered frame dimensions.')
                    x, y = (index % 3) * size, (row * 2 + index // 3) * (size + 32)
                    sheet.paste(frame.convert('RGB'), (x, y + 32))
                    caption = label + ' / ' + view
                    if view == 'detail' and not face:
                        caption += ' (automatic upper crop; verify face)'
                    draw.text((x + 8, y + 8), caption, fill='black')
        sheet.save(temp / 'contact-sheet.png')
        metadata = json.loads((temp / 'geometry.json').read_text(encoding='utf-8'))
        files = {p.name: sha256(p) for p in temp.glob('*.png')}
        files['geometry.json'] = sha256(temp / 'geometry.json')
        atomic_json(temp / 'preview.json', {'cache_key': key, 'files': files,
                    'geometry': metadata, 'face_crop_explicit': bool(face),
                    'artistic_review_required': True, 'geometry_modified': False})
        output.mkdir(exist_ok=True)
        for name in (*files, 'preview.json'):
            shutil.move(str(temp / name), output / name)
    return {'cached': False, 'contact_sheet': str(output / 'contact-sheet.png'),
            'face_crop_explicit': bool(face), 'same_cameras_for_comparison': bool(reference)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input'); parser.add_argument('--out-dir', required=True)
    parser.add_argument('--blender'); parser.add_argument('--reference', help='Before mesh; input is after')
    parser.add_argument('--face', type=float, nargs=4, metavar=('X', 'Y', 'Z', 'WIDTH'))
    parser.add_argument('--size', type=int, default=768)
    args = parser.parse_args()
    emit(render(args.input, args.out_dir, args.blender, args.reference, args.face, args.size))


if __name__ == '__main__':
    run(main)
