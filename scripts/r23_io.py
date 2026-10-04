"""Atomic R23-only evidence persistence."""
import hashlib,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='942997f8a5bce06e34a6e37d013e4d27e7175438'
AUDIT='docs/evidence/r23/V4_R22R1_CLOCK_AUTHORITY_AND_GOVERNANCE_NORMALIZATION_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md'
ACCEPT='data/v4/V4_16_CLOCK_GOVERNANCE_ACCEPTED_HEAD_R1.json'
AUTH='config/v4_16_runtime_activation_authority_v1.json'
DEPS='config/v4_16_runtime_dependencies_v1.json'
def read(path,root=ROOT):return json.loads((Path(root)/path).read_bytes())
def ref(path,root=ROOT):
    raw=(Path(root)/path).read_bytes();return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def atomic(path,value,root=ROOT,raw=False):
    root=Path(root).resolve();p=(root/path).resolve()
    if not p.is_relative_to(root) or not (path in (ACCEPT,AUTH,DEPS) or path.startswith(('reports/r23/','docs/evidence/r23/','config/v4_16_r23_','migrations/v4_16_r23_'))):raise ValueError('R23_OUTPUT_ONLY')
    data=value if raw else (json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n').encode()
    if p.exists() and p.read_bytes()==data:return ref(path,root)
    if p.exists() and not path.startswith('reports/r23/'):raise ValueError('VERSIONED_IMMUTABLE')
    p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.tmp')
    with tmp.open('wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(tmp,p);return ref(path,root)
