"""R25 evidence writes are atomic and restricted to the stage output roots."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = '31db7c17463d7a314c4dbfb10023f701c1a9387b'


def read(path, root=ROOT):
    return json.loads((Path(root) / path).read_bytes())


def ref(path, root=ROOT):
    raw = (Path(root) / path).read_bytes()
    return dict(path=path, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def atomic(path, value, root=ROOT, raw=False):
    root = Path(root).resolve()
    target = (root / path).resolve()
    if not target.is_relative_to(root) or not path.startswith(('reports/r25/', 'docs/evidence/r25/')):
        raise ValueError('R25_OUTPUT_ROOT_REQUIRED')
    data = value if raw else (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n').encode()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + '.tmp')
    with temporary.open('wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)
    return ref(path, root)
