"""FEP_E1_CONTRACTS_V1: canonical identities and exact local readbacks."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def instant(value):
    value = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if value.tzinfo is None:
        raise ValueError('FEP_UTC_TIME_REQUIRED')
    return value.astimezone(timezone.utc)


def exact(root, binding):
    from workbench_db.v4_historical_source_ingress_pg_r1 import read_bound
    raw = read_bound(root, binding['path'], binding['sha256'])['raw']
    if len(raw) != binding['bytes'] or hashlib.sha256(raw).hexdigest() != binding['sha256']:
        raise ValueError('FEP_EXACT_BINDING_MISMATCH')
    return json.loads(raw)


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8', newline='\n')
    os.replace(tmp, path)
