"""Allowlist and secret/path checks. Findings never echo matched values."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    'meshy-token': re.compile(r'\bmsy_[A-Za-z0-9]{16,}'),
    'github-token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})'),
    'api-secret': re.compile(r'\bsk-[A-Za-z0-9_-]{20,}'),
    'private-key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'windows-user-path': re.compile(r'[A-Za-z]:[\\/]+Users[\\/]+[^\s<>"\']+', re.I),
    'unix-user-path': re.compile(r'/(?:home|Users)/[A-Za-z0-9_.-]+/'),
    'signed-url': re.compile(r'(?:X-Amz-Signature|X-Goog-Signature|Signature)=[A-Za-z0-9%+/]{16,}', re.I),
    'bearer-literal': re.compile(r'Bearer\s+[A-Za-z0-9_.-]{20,}'),
    'email': re.compile(r'\b[A-Za-z0-9_.+%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'),
}


def findings(data):
    if len(data) > 300_000 or b'\x00' in data:
        return ['binary-or-oversized-file']
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        return ['non-utf8-file']
    result = []
    for name, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            if name == 'email' and match.group().endswith('@users.noreply.github.com'):
                continue
            result.append(name); break
    return result


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def reviewed_assets(root, allowed):
    registry = root / 'PUBLIC_ASSETS.json'
    if not registry.exists():
        return {}
    value = json.loads(registry.read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError('Invalid asset registry')
    for name, hashes in value.items():
        path = Path(name)
        if (name not in allowed or not name.startswith('docs/assets/') or path.suffix != '.png'
                or '..' in path.parts or not isinstance(hashes, list) or not hashes
                or any(not isinstance(h, str) or not re.fullmatch('[0-9a-f]{64}', h) for h in hashes)):
            raise ValueError('Invalid asset registry')
    return value


def file_findings(name, data, assets):
    if name not in assets:
        return findings(data)
    # Only visually reviewed bytes are exempt from the text-only policy, including in Git history.
    if (len(data) > 5 * 1024 * 1024 or not data.startswith(b'\x89PNG\r\n\x1a\n')
            or hashlib.sha256(data).hexdigest() not in assets[name]):
        return ['unapproved-public-asset']
    return []


def audit(root, with_git=False):
    root = Path(root).resolve()
    manifest = root / 'PUBLIC_FILES.txt'
    allowed = set(manifest.read_text(encoding='utf-8').splitlines())
    retired_manifest = root / 'PUBLIC_RETIRED_FILES.txt'
    retired_lines = retired_manifest.read_text(encoding='utf-8').splitlines() if retired_manifest.is_file() else []
    retired = set(retired_lines)
    history_allowed = allowed | retired
    issues = []
    try:
        assets = reviewed_assets(root, allowed)
    except (ValueError, OSError):
        assets = {}
        issues.append({'file': 'PUBLIC_ASSETS.json', 'reason': 'invalid-asset-registry'})
    if len(allowed) != len(manifest.read_text(encoding='utf-8').splitlines()):
        issues.append({'file': 'PUBLIC_FILES.txt', 'reason': 'duplicate-entry'})
    if ('' in retired or len(retired) != len(retired_lines)
            or any(Path(name).is_absolute() or '..' in Path(name).parts for name in retired)):
        issues.append({'file': 'PUBLIC_RETIRED_FILES.txt', 'reason': 'invalid-retired-entry'})
    for name in sorted(allowed):
        path = root / name
        if path.is_symlink() or root not in path.resolve().parents:
            issues.append({'file': name, 'reason': 'unsafe-manifest-path'}); continue
        if not path.is_file():
            issues.append({'file': name, 'reason': 'missing-file'}); continue
        issues.extend({'file': name, 'reason': reason} for reason in file_findings(name, path.read_bytes(), assets))
    ignored_parts = {'.git', '__pycache__', '.venv'}
    for path in root.rglob('*'):
        relative = path.relative_to(root)
        if any(part in ignored_parts for part in relative.parts):
            continue
        if path.is_file() and relative.as_posix() not in allowed:
            issues.append({'file': relative.as_posix(), 'reason': 'not-in-public-manifest'})
    blobs = 0
    if with_git:
        tracked = git(root, 'ls-files', '-z').decode().split('\0')
        for name in filter(None, tracked):
            if name not in allowed:
                issues.append({'file': name, 'reason': 'tracked-outside-manifest'})
        # Every reachable commit and tree is checked, not just the working tree.
        commits = git(root, 'rev-list', '--all').decode().splitlines()
        seen = set()
        for commit in commits:
            issues.extend({'file': 'commit:' + commit[:12], 'reason': reason}
                          for reason in findings(git(root, 'cat-file', 'commit', commit)))
            for entry in git(root, 'ls-tree', '-r', '-z', commit).split(b'\0'):
                if not entry:
                    continue
                meta, raw_name = entry.split(b'\t', 1)
                mode, kind, oid = meta.decode().split()
                name = raw_name.decode()
                if name not in history_allowed or mode not in ('100644', '100755') or kind != 'blob':
                    issues.append({'file': name, 'reason': 'unsafe-history-entry'})
                if kind == 'blob' and oid not in seen:
                    seen.add(oid); blobs += 1
                    issues.extend({'file': name, 'reason': reason}
                                  for reason in file_findings(name, git(root, 'cat-file', 'blob', oid), assets))
    return {'allowed_files': len(allowed), 'history_blobs_checked': blobs,
            'passed': not issues, 'issues': issues}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT); p.add_argument('--git', action='store_true')
    args = p.parse_args()
    result = audit(args.root, args.git)
    print(json.dumps(result))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
