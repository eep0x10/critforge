"""Project shortcuts and evidence ledger; records decisions, does not grant consent."""
import argparse
import importlib.util
import math
from pathlib import Path
import shutil
from common import (FOLDERS, STAGES, WorkflowError, atomic_json, emit, inside,
                    load, lock, project_root, run, save, sha256)
from asset_validation import validate_asset


def init(root):
    root.mkdir(parents=True, exist_ok=True)
    with lock(root):
        if (root / 'project.json').exists():
            return load(root)
        for folder in FOLDERS:
            (root / folder).mkdir(exist_ok=True)
        state = {'schema': 1, 'images': {}, 'task': None, 'checks': {}, 'artifacts': {},
                 'limits': {'max_height_mm': 45.0, 'base_mm': 32.0}}
        save(root, state)
        return state


def approve(root, images):
    with lock(root):
        state = load(root)
        if state.get('task') or (root / '.submit-intent.json').exists():
            raise WorkflowError('Generation already started. Use a separate revision project for new images.')
        entries = {}
        for role, source in images.items():
            source = Path(source)
            suffix = source.suffix.lower()
            if suffix not in ('.png', '.jpg', '.jpeg') or not source.is_file():
                raise WorkflowError('Provide PNG/JPEG files for all three approved views.')
            if source.stat().st_size > 20 * 1024 * 1024:
                raise WorkflowError('Image exceeds the local 20 MiB input limit.')
            with source.open('rb') as stream:
                signature = stream.read(8)
            if not (signature.startswith(b'\x89PNG\r\n\x1a\n') or signature.startswith(b'\xff\xd8\xff')):
                raise WorkflowError('Image signature is not PNG/JPEG.')
            digest = sha256(source)
            relative = f'01-imagens/{role}-{digest[:16]}{suffix}'
            target = inside(root, relative)
            if not target.exists():
                shutil.copyfile(source, target)
            if sha256(target) != digest:
                raise WorkflowError('Image copy verification failed.')
            entries[role] = {'path': relative, 'sha256': digest}
        state['images'] = entries
        save(root, state)
        return {'approved_views': list(entries), 'next': 'submit'}


def next_step(state):
    if not state['images'] and not state['task']:
        return 'generate-review-approve-images'
    if not state['task']:
        return 'submit-or-recover-existing-task'
    status = state['task'].get('status')
    if status in ('FAILED', 'EXPIRED', 'CANCELED', 'CANCELLED'):
        return 'review-terminal-failure-before-authorizing-new-generation'
    if status not in ('PENDING', 'IN_PROGRESS', 'SUCCEEDED'):
        return 'inspect-unknown-task-status'
    if status != 'SUCCEEDED':
        return 'watch-existing-task'
    if 'original.stl' not in state['artifacts']:
        return 'download'
    return 'review-repair-scale-and-deliver-stl'


def report(root, state):
    expected = list(STAGES)
    pending = []
    required = {'final-stl': ('.stl',)}
    for name, extensions in required.items():
        item = state['artifacts'].get(name)
        if not item:
            pending.append('missing:' + name)
            continue
        path = inside(root, item['path'])
        if path.suffix.lower() not in extensions or not path.is_file() or path.stat().st_size == 0:
            pending.append('invalid:' + name)
        elif name == 'final-stl':
            try:
                details = validate_asset(path)
                maximum = state.get('limits', {}).get('max_height_mm', 45.0)
                if details['dimensions_units'][2] > maximum:
                    pending.append(f'height-over-{maximum:g}mm:final-stl')
            except WorkflowError:
                pending.append('invalid:' + name)
    lines = ['# Project review', '',
             'This evidence ledger covers the reviewed STL, not slicing or a physical print.', '']
    for name in expected:
        check = state['checks'].get(name, {})
        status = check.get('status', 'pending')
        valid = status == 'passed'
        evidence = check.get('evidence')
        if evidence:
            path = inside(root, evidence['path'])
            valid = valid and path.is_file() and sha256(path) == evidence['sha256']
            if not valid and status in ('passed', 'not-applicable'):
                status = 'stale-evidence'
        else:
            valid = False
        if any(state['artifacts'].get(k, {}).get('sha256') != digest
               for k, digest in check.get('artifact_hashes', {}).items()):
            valid = False
            status = 'stale-artifact-set'
        bound = ('final-stl',)
        if any(not state['artifacts'].get(k) or
               check.get('artifact_hashes', {}).get(k) != state['artifacts'][k]['sha256']
               for k in bound):
            valid = False
            status = 'final-artifact-not-reviewed'
        if not valid:
            pending.append(name)
        lines.append(f"- {name}: {status}. {check.get('note', '')}")
    lines.extend(['', '## Artifacts', ''])
    for name, item in state['artifacts'].items():
        path = inside(root, item['path'])
        valid = path.is_file() and sha256(path) == item['sha256']
        lines.append(f"- {name}: {item['path']} — hash {'verified' if valid else 'MISMATCH'}")
        if not valid:
            pending.append('artifact:' + name)
    lines.extend(['', 'Pending: ' + (', '.join(pending) or 'none in the recorded checks'),
                  '', 'Slicing and physical printing are outside this workflow.', ''])
    (root / '00-documentacao/report.md').write_text('\n'.join(lines), encoding='utf-8')
    return {'report': '00-documentacao/report.md', 'pending': pending,
            'delivery_ready': not pending,
            'automatic_print_certification': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('init', 'status', 'report'):
        sub.add_parser(name).add_argument('project')
    sub.add_parser('doctor')
    p = sub.add_parser('approve-images', help='Record an explicit user approval of these exact images')
    p.add_argument('project')
    for role in ('front', 'back', 'face'):
        p.add_argument('--' + role, required=True)
    p = sub.add_parser('record')
    p.add_argument('project'); p.add_argument('stage', choices=STAGES)
    p.add_argument('status', choices=('passed', 'not-applicable', 'failed', 'pending'))
    p.add_argument('--note', required=True)
    p.add_argument('--evidence', help='Project-relative file with review evidence')
    p = sub.add_parser('artifact', help='Register a produced artifact and its current hash')
    p.add_argument('project'); p.add_argument('name'); p.add_argument('path', help='Project-relative file')
    p = sub.add_parser('limits', help='Set explicit project scale limits')
    p.add_argument('project'); p.add_argument('--max-height-mm', type=float, required=True)
    p.add_argument('--base-mm', type=float, required=True)
    args = parser.parse_args()
    if args.command == 'doctor':
        emit({'optional_modules': {n: importlib.util.find_spec(n) is not None
                                  for n in ('trimesh', 'numpy', 'pymeshlab')},
              'blender_on_path': shutil.which('blender') is not None,
              'meshy_key_configured': bool(__import__('os').environ.get('MESHY_API_KEY'))})
        return
    root = project_root(args.project)
    if args.command == 'init':
        init(root); emit({'initialized': True}); return
    if args.command == 'approve-images':
        emit(approve(root, {r: getattr(args, r) for r in ('front', 'back', 'face')})); return
    with lock(root):
        state = load(root)
        if args.command == 'record':
            if args.status == 'not-applicable':
                raise WorkflowError('Visual and mesh checks must pass or fail explicitly.')
            if args.status in ('passed', 'not-applicable') and not args.evidence:
                raise WorkflowError('Completed checks require an evidence file.')
            item = {'status': args.status, 'note': args.note,
                    'artifact_hashes': {k: v['sha256'] for k, v in state['artifacts'].items()}}
            if args.evidence:
                path = inside(root, args.evidence)
                item['evidence'] = {'path': path.relative_to(root).as_posix(), 'sha256': sha256(path)}
            state['checks'][args.stage] = item; save(root, state)
        elif args.command == 'limits':
            if any(not math.isfinite(value) or value <= 0
                   for value in (args.max_height_mm, args.base_mm)):
                raise WorkflowError('Scale limits must be positive finite millimeters.')
            state['limits'] = {'max_height_mm': args.max_height_mm, 'base_mm': args.base_mm}
            save(root, state)
        elif args.command == 'artifact':
            if args.name in ('original.stl', 'original.glb'):
                raise WorkflowError('Original asset records are managed by the Meshy download command.')
            path = inside(root, args.path)
            state['artifacts'][args.name] = {'path': path.relative_to(root).as_posix(),
                                            'sha256': sha256(path), 'bytes': path.stat().st_size}
            save(root, state)
        if args.command == 'report':
            emit(report(root, state))
        else:
            emit({'task': state['task'], 'limits': state.get('limits', {'max_height_mm': 45.0,
                                                                        'base_mm': 32.0}),
                  'next': next_step(state),
                  'checks': {k: v['status'] for k, v in state['checks'].items()}})


if __name__ == '__main__':
    run(main)
