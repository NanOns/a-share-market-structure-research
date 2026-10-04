"""Atomic R24R1 outputs; historical accepted objects are never output targets."""
import hashlib, json, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = '0c9f59fbe723fe0fb0e9d1a6750c339894bc7a5b'

def read(path, root=ROOT):
    return json.loads((Path(root)/path).read_bytes())

def ref(path, root=ROOT):
    raw=(Path(root)/path).read_bytes()
    return dict(path=path, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def atomic(path, value, root=ROOT, raw=False):
    root=Path(root).resolve(); target=(root/path).resolve()
    if not target.is_relative_to(root) or not path.startswith(('reports/r24r1/','docs/evidence/r24r1/','config/v4_16_go_forward_','config/v4_16_runtime_dependencies_v3','config/v4_16_runtime_activation_authority_v3','config/v4_16_realtime_admission_')):
        raise ValueError('R24R1_OUTPUT_ONLY')
    data=value if raw else (json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n').encode()
    if target.exists() and target.read_bytes()!=data and not path.startswith('reports/r24r1/'):
        raise ValueError('VERSIONED_CONTRACT_IMMUTABLE')
    target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_name(target.name+'.tmp')
    with temp.open('wb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    os.replace(temp,target)
    return ref(path,root)
