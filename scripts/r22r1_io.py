"""Additive R22R1 evidence IO. Historical namespaces are immutable inputs."""
import hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='3fd69721fa8f61aa278b275cb9250bb6829c85a5'
AUDIT='docs/evidence/r22r1/V4_R22_V4_16_CONTRACT_FREEZE_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md'
ACCEPT='data/v4/V4_16_CONTRACT_ACCEPTED_HEAD_R1.json'
CLOCK='config/v4_16_clock_contract_v1.json'
SLOT='config/v4_16_observation_slot_contract_v2.json'
HEAD='data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3.json'
CONFIG='config/v4_cross_stage_current_audit_authority_v3.json'
VECTORS='config/v4_16_clock_machine_vectors_v1.json'
def read(path,root=ROOT):return json.loads((Path(root)/path).read_bytes())
def ref(path,root=ROOT):
    raw=(Path(root)/path).read_bytes();return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def atomic(path,value,root=ROOT,raw=False):
    root=Path(root).resolve();p=(root/path).resolve()
    if not p.is_relative_to(root) or not (path in (ACCEPT,CLOCK,SLOT,HEAD,CONFIG,VECTORS) or path.startswith(('docs/evidence/r22r1/','reports/r22r1/'))):raise ValueError('R22R1_OUTPUT_ONLY')
    data=value if raw else (json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n').encode()
    if p.exists() and p.read_bytes()==data:return ref(path,root)
    if p.exists() and not path.startswith('reports/r22r1/'):raise ValueError('VERSIONED_ARTIFACT_IMMUTABLE')
    p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.tmp')
    with tmp.open('wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(tmp,p);return ref(path,root)
