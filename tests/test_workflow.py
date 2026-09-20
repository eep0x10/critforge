import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import subprocess
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import common
import workflow
import meshy
import public_audit


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        workflow.init(self.root)

    def approve(self):
        # Synthetic signatures: network calls are mocked, no artwork is published.
        images = {}
        for role in ('front', 'back', 'face'):
            path = self.root / (role + '.png')
            path.write_bytes(b'\x89PNG\r\n\x1a\n' + role.encode())
            images[role] = path
        workflow.approve(self.root, images)

    def test_init_preserves_state(self):
        state = common.load(self.root); state['custom'] = 'preserved'; common.save(self.root, state)
        self.assertEqual(workflow.init(self.root)['custom'], 'preserved')

    def test_path_escape_rejected(self):
        with self.assertRaises(common.WorkflowError):
            common.inside(self.root, '../outside')

    def test_lock_is_exclusive(self):
        with common.lock(self.root):
            with self.assertRaises(common.WorkflowError):
                with common.lock(self.root):
                    pass

    @patch.dict(os.environ, {'MESHY_API_KEY': 'synthetic-key'})
    @patch('meshy.api')
    def test_duplicate_submit_never_posts_twice(self, api):
        self.approve(); api.return_value = {'result': 'synthetic-task-0001'}
        meshy.submit(self.root); result = meshy.submit(self.root)
        self.assertTrue(result['reused_existing_task']); self.assertEqual(api.call_count, 1)

    @patch.dict(os.environ, {'MESHY_API_KEY': 'synthetic-key'})
    @patch('meshy.api')
    def test_4k_and_multiview_requests_use_supported_modes(self, api):
        self.approve(); api.return_value = {'result': 'synthetic-task-0001'}
        meshy.submit(self.root, 'image-4k')
        body = api.call_args.kwargs['body']
        self.assertEqual(api.call_args.kwargs['mode'], 'image-4k')
        self.assertEqual(body['geometry_resolution'], '4k')
        self.assertIn('image_url', body); self.assertNotIn('image_urls', body)

        other = self.root / 'revision'; workflow.init(other)
        images = {role: self.root / (role + '.png') for role in ('front', 'back', 'face')}
        workflow.approve(other, images)
        api.return_value = {'result': 'synthetic-task-0002'}
        meshy.submit(other, 'multi-image-2k')
        body = api.call_args.kwargs['body']
        self.assertEqual(api.call_args.kwargs['mode'], 'multi-image-2k')
        self.assertEqual(body['geometry_resolution'], '2k')
        self.assertEqual(len(body['image_urls']), 3)

    @patch.dict(os.environ, {'MESHY_API_KEY': 'synthetic-key'})
    @patch('meshy.api', side_effect=common.WorkflowError('Network result uncertain.'))
    def test_uncertain_submit_blocks_retry(self, api):
        self.approve()
        with self.assertRaises(common.WorkflowError):
            meshy.submit(self.root)
        with self.assertRaises(common.WorkflowError):
            meshy.submit(self.root)
        self.assertEqual(api.call_count, 1)

    @patch.dict(os.environ, {'MESHY_API_KEY': 'synthetic-key'})
    @patch('meshy.api')
    def test_modified_image_invalidates_approval(self, api):
        self.approve()
        path = common.inside(self.root, common.load(self.root)['images']['front']['path'])
        path.write_bytes(b'changed')
        with self.assertRaises(common.WorkflowError):
            meshy.submit(self.root)
        api.assert_not_called()

    @patch('meshy.api')
    def test_status_does_not_store_urls_or_errors(self, api):
        state = common.load(self.root); state['task'] = {'id': 'synthetic-task-0001'}; common.save(self.root, state)
        api.return_value = {'status': 'IN_PROGRESS', 'progress': 50,
                            'model_urls': {'stl': 'https://example.invalid/private'},
                            'task_error': {'message': 'private response'}}
        meshy.refresh(self.root)
        text = (self.root / 'project.json').read_text()
        self.assertNotIn('private', text); self.assertNotIn('model_urls', text)

    @patch('meshy.api')
    @patch('meshy.fetch_asset')
    def test_download_resume_enters_review(self, fetch, api):
        state = common.load(self.root); state['task'] = {'id': 'synthetic-task-0001'}; common.save(self.root, state)
        api.return_value = {'status': 'SUCCEEDED', 'consumed_credits': 20,
                            'model_urls': {'stl': 'https://assets.meshy.ai/model.stl',
                                           'glb': 'https://assets.meshy.ai/model.glb'}}
        fetch.side_effect = lambda url, path: path.write_bytes(b'synthetic-model')
        meshy.download(self.root); meshy.download(self.root)
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(workflow.next_step(common.load(self.root)), 'review-repair-scale-and-deliver-stl')

    def test_asset_domain_restrictions(self):
        for url in ('http://assets.meshy.ai/a', 'https://localhost/a',
                    'https://meshy.ai.attacker.invalid/a', 'https://user' + '@' + 'meshy.ai/a'):
            with self.assertRaises(common.WorkflowError):
                meshy.asset_url(url)
        self.assertEqual(meshy.asset_url('https://assets.meshy.ai/a'), 'https://assets.meshy.ai/a')

    def test_stale_evidence_returns_pending(self):
        path = self.root / '06-verificacao/evidence.txt'; path.write_text('before')
        state = common.load(self.root)
        state['checks']['mesh'] = {'status': 'passed', 'note': 'review',
                                  'evidence': {'path': '06-verificacao/evidence.txt', 'sha256': common.sha256(path)}}
        path.write_text('after')
        self.assertIn('mesh', workflow.report(self.root, state)['pending'])

    def test_secret_scanner_does_not_echo_secret(self):
        secret = 'msy' + '_' + 'A' * 32
        result = public_audit.findings(secret.encode())
        self.assertIn('meshy-token', result); self.assertNotIn(secret, json.dumps(result))
        personal_path = 'C:' + '/' + 'Users' + '/' + 'private-person' + '/model.stl'
        self.assertIn('windows-user-path', public_audit.findings(personal_path.encode()))

    def test_audit_rejects_unlisted_file(self):
        (self.root / 'PUBLIC_FILES.txt').write_text('PUBLIC_FILES.txt\n')
        self.assertFalse(public_audit.audit(self.root)['passed'])

    def test_new_artifact_does_not_invalidate_but_replacement_does(self):
        evidence = self.root / '06-verificacao/evidence.txt'; evidence.write_text('review')
        state = common.load(self.root)
        state['checks']['mesh'] = {'status': 'passed', 'note': 'review',
            'evidence': {'path': '06-verificacao/evidence.txt', 'sha256': common.sha256(evidence)},
            'artifact_hashes': {'model': 'hash-one', 'final-stl': 'hash-final'}}
        state['artifacts']['final-stl'] = {'path': '06-verificacao/evidence.txt', 'sha256': 'hash-final'}
        state['artifacts']['model'] = {'path': '06-verificacao/evidence.txt', 'sha256': 'hash-one'}
        state['artifacts']['new'] = {'path': '06-verificacao/evidence.txt', 'sha256': common.sha256(evidence)}
        self.assertNotIn('mesh', workflow.report(self.root, state)['pending'])
        state['artifacts']['model']['sha256'] = 'hash-two'
        self.assertIn('mesh', workflow.report(self.root, state)['pending'])


class HistoryAuditTests(unittest.TestCase):
    def test_retired_files_are_allowed_only_in_history(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'PUBLIC_FILES.txt').write_text('PUBLIC_FILES.txt\nPUBLIC_RETIRED_FILES.txt\n')
            (root / 'PUBLIC_RETIRED_FILES.txt').write_text('removed.txt\n')
            self.assertTrue(public_audit.audit(root)['passed'])

    def test_reviewed_asset_requires_exact_bytes_and_does_not_allow_other_binaries(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            name = 'docs/assets/banner.png'
            (root / 'docs/assets').mkdir(parents=True)
            data = b'\x89PNG\r\n\x1a\n' + b'synthetic-reviewed-bytes'
            (root / name).write_bytes(data)
            (root / 'PUBLIC_FILES.txt').write_text('PUBLIC_FILES.txt\nPUBLIC_ASSETS.json\n' + name + '\n')
            (root / 'PUBLIC_ASSETS.json').write_text(json.dumps({name: [hashlib.sha256(data).hexdigest()]}))
            self.assertTrue(public_audit.audit(root)['passed'])
            (root / name).write_bytes(data + b'changed')
            result = public_audit.audit(root)
            self.assertFalse(result['passed'])
            self.assertTrue(any(i['reason'] == 'unapproved-public-asset' for i in result['issues']))
            self.assertIn('binary-or-oversized-file', public_audit.file_findings('private.stl', b'\0', {name: []}))

    def test_asset_registry_cannot_exempt_private_models(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'PUBLIC_FILES.txt').write_text('PUBLIC_FILES.txt\nPUBLIC_ASSETS.json\nmodel.stl\n')
            (root / 'model.stl').write_bytes(b'\0')
            (root / 'PUBLIC_ASSETS.json').write_text(json.dumps({'model.stl': ['a' * 64]}))
            result = public_audit.audit(root)
            self.assertFalse(result['passed'])
            self.assertTrue(any(i['reason'] == 'invalid-asset-registry' for i in result['issues']))

    def test_removed_secret_remains_detectable_in_history(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            def git(*args):
                subprocess.run(['git', '-C', temp, *args], check=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            git('init')
            git('config', 'user.name', 'Synthetic Test')
            git('config', 'user.email', 'test' + '@users.noreply.github.com')
            (root / 'PUBLIC_FILES.txt').write_text('PUBLIC_FILES.txt\nexample.txt\n')
            (root / 'example.txt').write_text('msy' + '_' + 'B' * 32)
            git('add', 'PUBLIC_FILES.txt', 'example.txt'); git('commit', '-m', 'Synthetic fixture')
            (root / 'example.txt').write_text('clean')
            git('add', 'example.txt'); git('commit', '-m', 'Remove synthetic fixture')
            self.assertTrue(public_audit.audit(root)['passed'])
            result = public_audit.audit(root, with_git=True)
            self.assertFalse(result['passed'])
            self.assertTrue(any(i['reason'] == 'meshy-token' for i in result['issues']))


if __name__ == '__main__':
    unittest.main()
