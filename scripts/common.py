"""Private project state. No credentials or service URLs are persisted here."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

SKILL_ROOT = Path(__file__).resolve().parents[1]
FOLDERS = ('00-documentacao', '01-imagens', '02-meshy-original',
           '03-modelo-corrigido', '04-chitubox', '05-impressao',
           '06-verificacao', '90-processamento')
STAGES = ('visual', 'mesh', 'orient', 'hollow', 'drill', 'support',
          'layout', 'slice-review', 'reopen')


class WorkflowError(Exception):
    pass


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def project_root(path):
    root = Path(path).resolve()
    if root == SKILL_ROOT or SKILL_ROOT in root.parents:
        raise WorkflowError('Keep private projects outside the skill checkout.')
    return root


def inside(root, relative):
    path = (root / relative).resolve()
    if path == root or root not in path.parents:
        raise WorkflowError('Artifact must be inside the project.')
    return path


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.writing-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write('\n')
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load(root):
    path = root / 'project.json'
    if not path.is_file():
        raise WorkflowError('Run workflow.py init first.')
    state = json.loads(path.read_text(encoding='utf-8'))
    if state.get('schema') != 1:
        raise WorkflowError('Unsupported project schema.')
    return state


def save(root, state):
    atomic_json(root / 'project.json', state)


@contextlib.contextmanager
def lock(root):
    path = root / '.workflow.lock'
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise WorkflowError('Project busy or interrupted: inspect .workflow.lock before manual recovery.') from None
    try:
        os.close(fd)
        yield
    finally:
        path.unlink(missing_ok=True)


def validate_task_id(value):
    if not re.fullmatch(r'[a-zA-Z0-9-]{8,80}', value):
        raise WorkflowError('Invalid task ID.')
    return value


def emit(data):
    print(json.dumps(data, ensure_ascii=False, allow_nan=False))


def run(main):
    try:
        main()
    except (WorkflowError, OSError, ValueError, KeyError) as exc:
        # Never print arbitrary exception text: it may include a URL, path or key.
        message = str(exc) if isinstance(exc, WorkflowError) else type(exc).__name__
        emit({'error': message})
        raise SystemExit(2)
