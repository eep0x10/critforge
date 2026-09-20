import http.client
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import asset_validation
import common
import mesh
import meshy
import preview
import workflow


def triangle():
    return b'fixture'.ljust(80, b' ') + struct.pack('<I12fH', 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); workflow.init(self.root)

    def state(self):
        state = common.load(self.root)
        files = {'final-stl': ('model.stl', triangle())}
        for name, (filename, data) in files.items():
            path = self.root / filename; path.write_bytes(data)
            state['artifacts'][name] = {'path': filename, 'sha256': common.sha256(path)}
        evidence = self.root / 'review.txt'; evidence.write_text('Synthetic review evidence')
        for stage in common.STAGES:
            state['checks'][stage] = {'status': 'passed', 'note': 'test',
                'evidence': {'path': 'review.txt', 'sha256': common.sha256(evidence)},
                'artifact_hashes': {k: v['sha256'] for k, v in state['artifacts'].items()}}
        return state

    def test_manual_delivery_requires_real_stl_and_bound_reviews(self):
        state = self.state()
        self.assertTrue(workflow.report(self.root, state)['delivery_ready'])
        state['artifacts'].clear()
        result = workflow.report(self.root, state)
        self.assertFalse(result['delivery_ready']); self.assertIn('missing:final-stl', result['pending'])

    def test_empty_corrupt_or_wrong_extension_not_deliverable(self):
        for content in (b'', b'solid corrupt'):
            state = self.state(); path = self.root / 'model.stl'; path.write_bytes(content)
            state['artifacts']['final-stl']['sha256'] = common.sha256(path)
            self.assertIn('invalid:final-stl', workflow.report(self.root, state)['pending'])

    def test_height_over_45mm_blocks_delivery(self):
        state = self.state()
        path = self.root / 'model.stl'
        path.write_bytes(b'fixture'.ljust(80, b' ') + struct.pack(
            '<I12fH', 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 46, 0))
        state['artifacts']['final-stl']['sha256'] = common.sha256(path)
        self.assertIn('height-over-45mm:final-stl', workflow.report(self.root, state)['pending'])

    def test_terminal_and_unknown_tasks_do_not_watch(self):
        state = self.state()
        for status in ('FAILED', 'EXPIRED', 'CANCELED', 'CANCELLED', 'UNKNOWN'):
            state['task'] = {'status': status}
            self.assertNotEqual(workflow.next_step(state), 'watch-existing-task')
            with patch('meshy.refresh', return_value={'status': status}) as refresh, patch('meshy.time.sleep') as sleep:
                meshy.watch(self.root, 60, 5)
                refresh.assert_called_once(); sleep.assert_not_called()

    def test_valid_binary_and_ascii_stl(self):
        path = self.root / 'model.stl'; path.write_bytes(triangle())
        details = asset_validation.validate_asset(path)
        self.assertEqual(details['triangles'], 1)
        self.assertEqual(details['dimensions_units'], [1.0, 1.0, 0.0])
        path.write_text('solid test\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\nendloop\nendfacet\nendsolid test\n')
        self.assertEqual(asset_validation.validate_asset(path)['format'], 'ascii-stl')

    def test_corrupt_truncated_and_nonfinite_stl_rejected(self):
        path = self.root / 'model.stl'
        invalid = [triangle()[:-1], b'solid invalid\nendsolid\n', triangle() + b'extra',
                   triangle()[:84] + struct.pack('<12fH', *([float('nan')] + [0] * 11), 0)]
        for content in invalid:
            path.write_bytes(content)
            with self.assertRaises(common.WorkflowError):
                asset_validation.validate_asset(path)

    def test_glb_chunks_and_length(self):
        path = self.root / 'model.glb'
        payload = json.dumps({'asset': {'version': '2.0'}}).encode()
        payload += b' ' * (-len(payload) % 4)
        data = struct.pack('<4sIII4s', b'glTF', 2, 20 + len(payload), len(payload), b'JSON') + payload
        path.write_bytes(data)
        self.assertEqual(asset_validation.validate_asset(path)['format'], 'glb2')
        for content in (data[:-1], data + b'extra', b'glTF' + b'\0' * 100):
            path.write_bytes(content)
            with self.assertRaises(common.WorkflowError):
                asset_validation.validate_asset(path)

    def test_interrupted_download_cleans_partial_and_can_retry(self):
        target = self.root / 'download.stl'
        response = MagicMock(); response.__enter__.return_value = response
        response.headers = {}; response.read.side_effect = [b'partial', http.client.IncompleteRead(b'private')]
        opener = MagicMock(); opener.open.return_value = response
        with patch('meshy.urllib.request.build_opener', return_value=opener), patch('meshy.api') as api:
            with self.assertRaises(common.WorkflowError) as caught:
                meshy.fetch_asset('https://assets.meshy.ai/model.stl', target)
            self.assertNotIn('private', str(caught.exception))
            self.assertFalse(target.exists()); self.assertFalse(target.with_suffix('.stl.partial').exists())
            response.read.side_effect = [triangle(), b'']
            meshy.fetch_asset('https://assets.meshy.ai/model.stl', target)
            self.assertEqual(target.read_bytes(), triangle()); api.assert_not_called()

    def test_short_content_length_and_corruption_not_published(self):
        for content, expected in ((triangle(), '9999'), (b'solid broken' * 10, None)):
            response = MagicMock(); response.__enter__.return_value = response
            response.headers = {'Content-Length': expected} if expected else {}
            response.read.side_effect = [content, b'']
            opener = MagicMock(); opener.open.return_value = response
            with patch('meshy.urllib.request.build_opener', return_value=opener):
                with self.assertRaises(common.WorkflowError):
                    meshy.fetch_asset('https://assets.meshy.ai/model.stl', self.root / 'download.stl')
            self.assertFalse((self.root / 'download.stl').exists())

    def test_preview_rejects_invalid_face_and_dimensions_before_launch(self):
        with patch('preview.subprocess.run') as launch:
            for face in ((0, 0, 0, -1), (0, 0, float('nan'), 1)):
                with self.assertRaises(common.WorkflowError):
                    preview.render(self.root / 'a.stl', self.root / 'views', face=face)
            with self.assertRaises(common.WorkflowError):
                preview.render(self.root / 'a.stl', self.root / 'views', size=0)
            launch.assert_not_called()

    def test_compare_detects_open_repair_regression(self):
        import trimesh
        before = trimesh.creation.box()
        after = before.copy(); after.update_faces([True] * 11 + [False])
        a, b = self.root / 'a.stl', self.root / 'b.stl'
        before.export(a); after.export(b)
        result = mesh.compare(a, b, self.root / 'compare.json')
        self.assertIn('regression:watertight', result['warnings'])
        self.assertIsNone(result['volume_delta_percent'])
        self.assertFalse(result['repair_accepted_automatically'])

    def test_compare_detects_lost_components_and_rescaling(self):
        import trimesh
        a, b = self.root / 'a.stl', self.root / 'b.stl'
        box = trimesh.creation.box(); other = box.copy(); other.apply_translation([3, 0, 0])
        trimesh.util.concatenate([box, other]).export(a)
        box.apply_scale(2); box.export(b)
        result = mesh.compare(a, b, self.root / 'compare.json')
        self.assertIn('components-changed-review-small-details', result['warnings'])
        self.assertIn('dimensions-changed-beyond-tolerance', result['warnings'])
        self.assertIn('volume-changed-beyond-tolerance', result['warnings'])


if __name__ == '__main__':
    unittest.main()
