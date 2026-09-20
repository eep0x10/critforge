"""Meshy client with resumable state and no automatic POST retries."""
import argparse
import base64
import json
import http.client
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from common import (WorkflowError, atomic_json, emit, inside, load, lock,
                    project_root, run, save, sha256, validate_task_id)
from asset_validation import validate_asset

ENDPOINTS = {
    'image-4k': 'https://api.meshy.ai/openapi/v1/image-to-3d',
    'multi-image-2k': 'https://api.meshy.ai/openapi/v1/multi-image-to-3d',
}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api(method, task_id=None, body=None, mode='image-4k'):
    key = os.environ.get('MESHY_API_KEY')
    if not key:
        raise WorkflowError('Set MESHY_API_KEY in the environment; never pass it as an argument.')
    if mode not in ENDPOINTS:
        raise WorkflowError('Unknown Meshy generation mode.')
    url = ENDPOINTS[mode] + ('/' + validate_task_id(task_id) if task_id else '')
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, method=method,
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=90) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise WorkflowError(f'Meshy HTTP {exc.code}. Response omitted to protect private data.') from None
    except (urllib.error.URLError, TimeoutError):
        raise WorkflowError('Network result uncertain. Inspect/recover the existing task; do not repeat POST.') from None


def image_data(root, entry):
    path = inside(root, entry['path'])
    if sha256(path) != entry['sha256']:
        raise WorkflowError('Approved image changed. Review and approve again.')
    if path.stat().st_size > 20 * 1024 * 1024:
        raise WorkflowError('Image exceeds the local 20 MiB input limit.')
    mime = 'image/png' if path.suffix.lower() == '.png' else 'image/jpeg'
    return 'data:' + mime + ';base64,' + base64.b64encode(path.read_bytes()).decode()


def submit(root, mode='image-4k'):
    with lock(root):
        state = load(root)
        if state['task']:
            return {'reused_existing_task': True, 'task': state['task']}
        marker = root / '.submit-intent.json'
        if marker.exists():
            raise WorkflowError('Previous submission may have succeeded. Recover its task ID; POST blocked.')
        if set(state['images']) != {'front', 'back', 'face'}:
            raise WorkflowError('Explicit approval for all three views must be recorded first.')
        if not os.environ.get('MESHY_API_KEY'):
            raise WorkflowError('Set MESHY_API_KEY before submitting.')
        if mode == 'image-4k':
            body = {'image_url': image_data(root, state['images']['front']),
                    'ai_model': 'meshy-7.1', 'geometry_resolution': '4k',
                    'should_texture': False, 'should_remesh': False,
                    'image_enhancement': False, 'target_formats': ['stl', 'glb'],
                    'multi_view_thumbnails': True, 'auto_size': False}
            generation = {'mode': mode, 'geometry_resolution': '4k',
                          'geometry_source': 'front', 'qa_views': ['back', 'face']}
        elif mode == 'multi-image-2k':
            body = {'image_urls': [image_data(root, state['images'][role])
                                   for role in ('front', 'back', 'face')],
                    'ai_model': 'meshy-7.1', 'geometry_resolution': '2k',
                    'should_texture': False, 'should_remesh': False,
                    'image_enhancement': False, 'target_formats': ['stl', 'glb'],
                    'multi_view_thumbnails': True, 'auto_size': False}
            generation = {'mode': mode, 'geometry_resolution': '2k',
                          'geometry_source': 'front-back-face', 'qa_views': []}
        else:
            raise WorkflowError('Unknown Meshy generation mode.')
        atomic_json(marker, {'state': 'submission-intent', 'images': state['images'],
                             'generation': generation})
        result = api('POST', body=body, mode=mode)
        task_id = validate_task_id(result['result'])
        state['task'] = {'id': task_id, 'status': 'PENDING', 'progress': 0,
                         'generation': generation}
        save(root, state)
        return {'task': state['task']}


def refresh(root):
    with lock(root):
        state = load(root)
        if not state['task']:
            raise WorkflowError('No task recorded. Submit once or recover an existing task.')
        generation = state['task'].get('generation', {'mode': 'multi-image-2k'})
        result = api('GET', state['task']['id'], mode=generation['mode'])
        state['task'] = {'id': state['task']['id'], 'status': result.get('status', 'UNKNOWN'),
                         'progress': result.get('progress', 0),
                         'consumed_credits': result.get('consumed_credits'),
                         'generation': generation}
        # Signed URLs, API errors and arbitrary provider fields are intentionally not saved.
        save(root, state)
        return state['task']


def recover(root, task_id, mode):
    validate_task_id(task_id)
    with lock(root):
        state = load(root)
        if state['task'] and state['task']['id'] != task_id:
            raise WorkflowError('A different task is already recorded; refusing replacement.')
        result = api('GET', task_id, mode=mode)
        if result.get('id') != task_id:
            raise WorkflowError('Provider task ID mismatch.')
        resolution = '4k' if mode == 'image-4k' else '2k'
        source = 'front' if mode == 'image-4k' else 'front-back-face'
        state['task'] = {'id': task_id, 'status': result['status'], 'progress': result.get('progress', 0),
                         'generation': {'mode': mode, 'geometry_resolution': resolution,
                                        'geometry_source': source,
                                        'qa_views': ['back', 'face'] if mode == 'image-4k' else []}}
        save(root, state)
        return {'recovered': True, 'task': state['task']}


def asset_url(url):
    parsed = urllib.parse.urlsplit(url)
    host = (parsed.hostname or '').lower()
    if (parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None, 443)
            or not (host == 'meshy.ai' or host.endswith('.meshy.ai'))):
        raise WorkflowError('Asset host is outside the expected Meshy HTTPS domain; review provider changes.')
    return url


class AssetRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        asset_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_asset(url, target):
    asset_url(url)
    if target.exists():
        raise WorkflowError('Asset already exists; refusing replacement.')
    partial = target.with_suffix(target.suffix + '.partial')
    try:
        # This request never receives the API Authorization header.
        with urllib.request.build_opener(AssetRedirect).open(url, timeout=90) as response, partial.open('wb') as stream:
            expected = response.headers.get('Content-Length')
            total = 0
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > 1024 * 1024 * 1024:
                    raise WorkflowError('Download exceeds the local 1 GiB limit.')
                stream.write(block)
        if expected is not None and total != int(expected):
            raise WorkflowError('Incomplete asset download; retry download, not generation.')
        validate_asset(partial, target.suffix)
        os.replace(partial, target)
    except (urllib.error.URLError, TimeoutError, http.client.HTTPException, ConnectionError):
        raise WorkflowError('Asset download failed; retry download, not generation.') from None
    finally:
        partial.unlink(missing_ok=True)


def download(root):
    with lock(root):
        state = load(root)
        if not state['task']:
            raise WorkflowError('No task recorded.')
        generation = state['task'].get('generation', {'mode': 'multi-image-2k'})
        result = api('GET', state['task']['id'], mode=generation['mode'])
        if result.get('status') != 'SUCCEEDED':
            raise WorkflowError('Task has not succeeded yet.')
        for fmt in ('stl', 'glb'):
            name = 'original.' + fmt
            relative = '02-meshy-original/' + name
            target = inside(root, relative)
            known = state['artifacts'].get(name)
            if known and target.is_file() and sha256(target) == known['sha256']:
                continue
            if target.exists():
                raise WorkflowError('Unverified asset already exists; preserve and inspect it before retrying.')
            url = result.get('model_urls', {}).get(fmt)
            if not url:
                raise WorkflowError('Requested format unavailable from provider.')
            fetch_asset(url, target)
            state['artifacts'][name] = {'path': relative, 'sha256': sha256(target), 'bytes': target.stat().st_size}
            save(root, state)
        state['task'].update(status='SUCCEEDED', progress=100, consumed_credits=result.get('consumed_credits'))
        save(root, state)
        return {'downloaded': ['original.stl', 'original.glb'],
                'generation': generation, 'next': 'review-repair-scale-and-deliver-stl'}


def watch(root, seconds, interval):
    if not 0 <= seconds <= 3600 or not 5 <= interval <= 60:
        raise WorkflowError('Use seconds 0..3600 and interval 5..60.')
    deadline = time.monotonic() + seconds
    previous = None
    while True:
        state = refresh(root)
        if state != previous:
            emit(state); previous = state
        if state['status'] not in ('PENDING', 'IN_PROGRESS'):
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            emit({'waiting': True, 'resume': 'watch existing task'}); return
        time.sleep(min(interval, remaining))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('submit'); p.add_argument('project')
    p.add_argument('--mode', choices=tuple(ENDPOINTS), default='image-4k')
    for name in ('status', 'download'):
        sub.add_parser(name).add_argument('project')
    p = sub.add_parser('recover'); p.add_argument('project'); p.add_argument('task_id')
    p.add_argument('--mode', choices=tuple(ENDPOINTS), required=True)
    p = sub.add_parser('watch'); p.add_argument('project')
    p.add_argument('--seconds', type=int, default=45); p.add_argument('--interval', type=int, default=15)
    args = parser.parse_args(); root = project_root(args.project)
    if args.command == 'watch':
        watch(root, args.seconds, args.interval)
    elif args.command == 'recover':
        emit(recover(root, args.task_id, args.mode))
    elif args.command == 'submit':
        emit(submit(root, args.mode))
    else:
        emit({'status': refresh, 'download': download}[args.command](root))


if __name__ == '__main__':
    run(main)
