"""R21 exact promotion IO. The stage pointer is the transaction commit point."""
import hashlib,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='14b183dedf8a55b12e9368229482ab4bdb3395b1'
TESTED='81d989af438bdeda583a581f1ef7f311205e6139'
TAG='codex/r20r1r2-tested-source-20261003-r1'
AUDIT='docs/evidence/r21/V4_R20R1R2_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md'
STAGE='data/v4/V4_STAGE_ACCEPTED_HEAD.json'
HEAD='data/v4/V4_15_ACCEPTED_HEAD.json'
def ref(path,root=ROOT):
    raw=(Path(root)/path).read_bytes()
    return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def atomic(path,value,root=ROOT,raw=False):
    root=Path(root).resolve();p=(root/path).resolve()
    if not p.is_relative_to(root):raise ValueError('PATH_ESCAPE')
    allowed=['reports/r21','docs/evidence/r21']
    if not any(p.is_relative_to(root/x) for x in allowed) and path not in [STAGE,HEAD,'config/v4_15_accepted_entry_contract_v1.json','config/v4_current_stage_authority_v2.json']:raise ValueError('R21_NAMESPACE_ONLY')
    data=value if raw else (json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()
    if p.exists() and p.read_bytes()==data:return ref(path,root)
    if p.exists() and path!=STAGE and not path.startswith('reports/r21/'):raise ValueError('IMMUTABLE_PROMOTION_ARTIFACT')
    p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.tmp')
    with t.open('wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(t,p);return ref(path,root)
