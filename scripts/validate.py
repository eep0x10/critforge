"""One-command offline validation. Does not call Meshy or launch desktop apps."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
commands = [
    [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
    [sys.executable, 'scripts/public_audit.py'],
]
for command in commands:
    result = subprocess.run(command, cwd=root)
    if result.returncode:
        raise SystemExit(result.returncode)
print('Offline validation passed; no paid requests or printer actions performed.')
