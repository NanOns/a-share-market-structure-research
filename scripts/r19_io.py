"""R19 artifact I/O; no source, scanner, database or runtime access."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'f4ad7d632e53734798c064f011e2b53ecd99bc27'
TESTED = '04b310c2b011dbeb99dd1c2430165201917dd328'

def blob(path):
    return subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT)

def read(path):
    return json.loads((ROOT / path).read_bytes())

def ref(path):
    raw = (ROOT / path).read_bytes()
    return {'path': path, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}

def atomic(path, value, raw=False):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    data = value if raw else (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode()
    temp = target.with_name(target.name + '.r19.tmp')
    with temp.open('wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, target)
