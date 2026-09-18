"""Read-only mesh checks and explicit uniform scaling. No automatic repair/cuts."""
import argparse
import importlib.metadata
import json
import math
from pathlib import Path
from common import WorkflowError, atomic_json, emit, run, sha256

VERSION = 1


def dependencies():
    try:
        import numpy as np
        import trimesh
        return np, trimesh
    except ImportError:
        raise WorkflowError('Install requirements-mesh.txt for mesh operations.') from None


def read_mesh(path):
    np, trimesh = dependencies()
    if Path(path).suffix.lower() not in ('.stl', '.ply'):
        raise WorkflowError('Use STL or PLY with known orientation and units.')
    mesh = trimesh.load_mesh(path, process=True)
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
        raise WorkflowError('Expected a nonempty triangle mesh.')
    if not np.isfinite(mesh.vertices).all():
        raise WorkflowError('Mesh contains nonfinite coordinates.')
    return mesh


def inspect(path, out, intersections=False, base_mm=None, foot_band_mm=2):
    path, out = Path(path), Path(out)
    if path.resolve() == out.resolve():
        raise WorkflowError('Report must not overwrite the input mesh.')
    if base_mm is not None and (not math.isfinite(base_mm) or base_mm <= 0):
        raise WorkflowError('Base diameter must be positive.')
    if not math.isfinite(foot_band_mm) or foot_band_mm <= 0:
        raise WorkflowError('Foot band must be positive.')
    np, trimesh = dependencies()
    versions = {'trimesh': trimesh.__version__, 'numpy': np.__version__}
    if intersections:
        try:
            import pymeshlab
            versions['pymeshlab'] = importlib.metadata.version('pymeshlab')
        except ImportError:
            raise WorkflowError('Install optional pymeshlab to check intersections.') from None
    key = {'sha256': sha256(path), 'checker': VERSION, 'versions': versions,
           'intersections': intersections, 'base_mm': base_mm, 'foot_band_mm': foot_band_mm}
    if out.exists():
        old = json.loads(out.read_text(encoding='utf-8'))
        if old.get('cache_key') == key:
            return {'cached': True, 'summary': old['summary']}
    mesh = read_mesh(path)
    groups = trimesh.graph.connected_components(mesh.face_adjacency,
                    nodes=np.arange(len(mesh.faces)), min_len=1, engine='scipy')
    counts = sorted((len(g) for g in groups), reverse=True)
    summary = {'faces': len(mesh.faces), 'vertices': len(mesh.vertices),
               'watertight': bool(mesh.is_watertight),
               'winding_consistent': bool(mesh.is_winding_consistent),
               'components': len(counts), 'dimensions_units': mesh.extents.tolist(),
               'signed_volume_units3': float(mesh.volume), 'units_confirmed': False,
               'self_intersecting_faces': None}
    if intersections:
        ms = pymeshlab.MeshSet(); ms.load_new_mesh(str(path))
        ms.compute_selection_by_self_intersections_per_face()
        summary['self_intersecting_faces'] = ms.current_mesh().selected_face_number()
    fit = None
    if base_mm is not None:
        points = mesh.vertices[mesh.vertices[:, 2] <= mesh.bounds[0, 2] + foot_band_mm, :2]
        center = (points.min(axis=0) + points.max(axis=0)) / 2
        diameter = float(2 * np.linalg.norm(points - center, axis=1).max())
        fit = {'assuming_input_mm_and_z_up': True, 'base_mm': base_mm,
               'foot_band_mm': foot_band_mm, 'center_xy': center.tolist(),
               'conservative_circle_diameter_mm': diameter, 'fits': diameter <= base_mm,
               'flat_contact_verified': False}
    atomic_json(out, {'cache_key': key, 'summary': summary, 'component_face_counts': counts,
                     'bounds_units': mesh.bounds.tolist(), 'base_fit': fit,
                     'not_checked': ['artistic_fidelity', 'wall_thickness', 'resin_traps',
                                     'suction_cups', 'support_coverage', 'physical_strength']})
    return {'cached': False, 'summary': summary}


def scale(source, target, height_mm):
    source, target = Path(source), Path(target)
    if target.exists() or target.with_suffix('.scale.json').exists():
        raise WorkflowError('Output exists; use a new revision filename.')
    if target.suffix.lower() != '.stl' or source.resolve() == target.resolve():
        raise WorkflowError('Use a separate STL output.')
    if not math.isfinite(height_mm) or height_mm <= 0:
        raise WorkflowError('Height must be positive.')
    mesh = read_mesh(source)
    if mesh.extents[2] <= 0:
        raise WorkflowError('No Z height to scale.')
    before = mesh.extents.tolist()
    factor = height_mm / mesh.extents[2]
    mesh.apply_scale(factor)
    mesh.apply_translation([-mesh.bounds.mean(axis=0)[0], -mesh.bounds.mean(axis=0)[1], -mesh.bounds[0, 2]])
    target.parent.mkdir(parents=True, exist_ok=True)
    data = mesh.export(file_type='stl')
    with target.open('xb') as stream:
        stream.write(data)
    result = {'input_sha256': sha256(source), 'output_sha256': sha256(target),
              'assumed_z_up': True, 'before_units': before, 'factor': float(factor),
              'dimensions_mm': mesh.extents.tolist(), 'repair_performed': False}
    atomic_json(target.with_suffix('.scale.json'), result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('inspect'); p.add_argument('input'); p.add_argument('--out', required=True)
    p.add_argument('--intersections', action='store_true'); p.add_argument('--base-mm', type=float)
    p.add_argument('--foot-band-mm', type=float, default=2)
    p = sub.add_parser('scale'); p.add_argument('input'); p.add_argument('output')
    p.add_argument('--height-mm', type=float, required=True)
    args = parser.parse_args()
    if args.command == 'inspect':
        emit(inspect(args.input, args.out, args.intersections, args.base_mm, args.foot_band_mm))
    else:
        emit(scale(args.input, args.output, args.height_mm))


if __name__ == '__main__':
    run(main)
