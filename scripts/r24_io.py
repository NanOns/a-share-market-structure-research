"""R24 atomic evidence and versioned contracts, outside all source roots."""
import hashlib, json, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'b6b3105e713187462f49054e62fa70df8b9bd292'

def read(path, root=ROOT):
    return json.loads((Path(root) / path).read_bytes())

def ref(path, root=ROOT):
    raw = (Path(root) / path).read_bytes()
    return dict(path=path, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))

def atomic(path, value, root=ROOT, raw=False):
    root = Path(root).resolve()
    target = (root / path).resolve()
    allowed = ('reports/r24/', 'docs/evidence/r24/', 'config/v4_16_',
               'migrations/v4_16_r24_', 'data/v4/V4_16_RUNTIME_ENGINEERING_ACCEPTED_HEAD_R1.json')
    if not target.is_relative_to(root) or not path.startswith(allowed):
        raise ValueError('R24_OUTPUT_ONLY')
    data = value if raw else (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)+'\n').encode()
    if target.exists():
        if target.read_bytes() == data:
            return ref(path, root)
        if not path.startswith('reports/r24/'):
            raise ValueError('VERSIONED_CONTRACT_IMMUTABLE')
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + '.tmp')
    with temp.open('wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, target)
    return ref(path, root)
