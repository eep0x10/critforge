from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import mesh
import common
import trimesh


class MeshTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'box.stl'
        trimesh.creation.box(extents=(10, 10, 20)).export(self.source)

    def test_scale_preserves_original_and_targets_height(self):
        before = common.sha256(self.source)
        target = self.root / 'scaled.stl'
        result = mesh.scale(self.source, target, 36)
        self.assertEqual(before, common.sha256(self.source))
        self.assertAlmostEqual(result['dimensions_mm'][2], 36)
        self.assertAlmostEqual(trimesh.load_mesh(target).bounds[0, 2], 0)
        with self.assertRaises(common.WorkflowError):
            mesh.scale(self.source, target, 36)

    def test_cache_invalidation_on_geometry_and_options(self):
        out = self.root / 'report.json'
        self.assertFalse(mesh.inspect(self.source, out)['cached'])
        self.assertTrue(mesh.inspect(self.source, out)['cached'])
        self.assertFalse(mesh.inspect(self.source, out, base_mm=32)['cached'])
        trimesh.creation.box(extents=(15, 10, 20)).export(self.source)
        self.assertFalse(mesh.inspect(self.source, out, base_mm=32)['cached'])

    def test_disconnected_components_not_silently_removed(self):
        a = trimesh.creation.box(); b = a.copy(); b.apply_translation((3, 0, 0))
        trimesh.util.concatenate([a, b]).export(self.source)
        before = common.sha256(self.source)
        result = mesh.inspect(self.source, self.root / 'report.json')
        self.assertEqual(result['summary']['components'], 2)
        self.assertEqual(common.sha256(self.source), before)

    def test_invalid_height_is_rejected(self):
        for value in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(common.WorkflowError):
                mesh.scale(self.source, self.root / 'invalid.stl', value)


if __name__ == '__main__':
    unittest.main()
