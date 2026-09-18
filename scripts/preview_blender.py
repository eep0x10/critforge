"""Blender worker: original triangles, orthographic cameras, no decimation/repair."""
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector


def main():
    config = json.loads(Path(sys.argv[sys.argv.index('--') + 1]).read_text(encoding='utf-8'))
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    meshes = []
    paths = [('before', config['reference']), ('after', config['source'])] if config['reference'] else [('model', config['source'])]
    for label, path in paths:
        if Path(path).suffix.lower() == '.stl':
            bpy.ops.wm.stl_import(filepath=path)
        else:
            bpy.ops.wm.ply_import(filepath=path)
        obj = bpy.context.object
        if obj is None or obj.type != 'MESH' or not len(obj.data.polygons):
            raise RuntimeError('Empty imported mesh')
        meshes.append((label, obj))
    points = [obj.matrix_world @ Vector(corner) for _, obj in meshes for corner in obj.bound_box]
    low = Vector(tuple(min(v[i] for v in points) for i in range(3)))
    high = Vector(tuple(max(v[i] for v in points) for i in range(3)))
    center = (low + high) / 2
    extent = high - low
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x = scene.render.resolution_y = config['size']
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    shading = scene.display.shading
    shading.light = 'STUDIO'; shading.color_type = 'SINGLE'
    shading.single_color = (0.52, 0.52, 0.52)
    shading.show_shadows = True; shading.show_cavity = True
    shading.cavity_type = 'BOTH'; shading.background_type = 'WORLD'
    scene.world.color = (0.8, 0.8, 0.8)
    camera = bpy.data.objects.new('ReviewCamera', bpy.data.cameras.new('ReviewCamera'))
    scene.collection.objects.link(camera); scene.camera = camera
    camera.data.type = 'ORTHO'
    span = max(extent)
    camera.data.clip_start = max(span / 10000, 0.00001)
    camera.data.clip_end = max(span * 100, 100)
    face = config['face']
    detail_center = Vector(face[:3]) if face else Vector((center.x, center.y, high.z - extent.z * 0.15))
    directions = {'front': (0, -1, 0), 'back': (0, 1, 0), 'left': (-1, 0, 0),
                  'right': (1, 0, 0), 'isometric': (1, -1, 0.7), 'detail': (0, -1, 0)}
    for label, obj in meshes:
        for _, other in meshes:
            other.hide_render = other != obj
        for view, direction in directions.items():
            target = detail_center if view == 'detail' else center
            camera.location = target + Vector(direction).normalized() * max(span * 4, 1)
            camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
            # Same bounds and camera settings for both revisions; framing preserves scale changes.
            rotation = camera.rotation_euler.to_matrix().transposed()
            projected = [rotation @ (p - center) for p in points]
            camera.data.ortho_scale = max(max(p[i] for p in projected) - min(p[i] for p in projected)
                                          for i in (0, 1)) * 1.12
            if view == 'detail':
                camera.data.ortho_scale = face[3] if face else max(extent.z * 0.35, span * 0.15)
            scene.render.filepath = str(Path(config['output']) / f'{label}-{view}.png')
            bpy.ops.render.render(write_still=True)
    metadata = {'blender_version': bpy.app.version_string, 'shared_bounds': [list(low), list(high)],
                'assumed_axes': 'Z up, front viewed from negative Y',
                'meshes': {label: {'vertices': len(obj.data.vertices), 'faces': len(obj.data.polygons)}
                           for label, obj in meshes}}
    (Path(config['output']) / 'geometry.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
