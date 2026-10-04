"""R22 contract-only, exact baseline IO and atomic scoped artifact persistence."""
import hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='b2c3dd81c4bfed2364b6ea2693860114421f990c'
OLD_HEAD='data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V1.json'
OLD_CONFIG='config/v4_cross_stage_current_audit_authority_v1.json'
HEAD='data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V2.json'
CONFIG='config/v4_cross_stage_current_audit_authority_v2.json'
ACCEPT='data/v4/V4_PRE16_GOVERNANCE_ACCEPTED_HEAD_R1.json'
AUDIT='docs/evidence/r22/V4_PRE16_GOVERNANCE_R1_1_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md'
R21_AUDIT='docs/evidence/r22/V4_R21_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md'
ARCH='docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'

def read(path,root=ROOT):return json.loads((Path(root)/path).read_bytes())
def ref(path,root=ROOT):
    raw=(Path(root)/path).read_bytes();return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def baseline(path,root=ROOT):return subprocess.check_output(['git','show',BASE+':'+path],cwd=root)
def atomic(path,value,root=ROOT,raw=False):
    root=Path(root).resolve();p=(root/path).resolve()
    allowed=path in [HEAD,CONFIG,ACCEPT] or path.startswith(('config/v4_16_','reports/r22/','reports/pre16_finalization/','docs/evidence/r22/')) or path=='docs/audits/V4_R22_V4_16_CONTRACT_FREEZE_20261004.md'
    if not p.is_relative_to(root) or not allowed:raise ValueError('R22_CONTRACT_OUTPUT_ONLY')
    data=value if raw else (json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()
    if p.exists() and p.read_bytes()==data:return ref(path,root)
    if p.exists() and (path in [HEAD,CONFIG,ACCEPT] or path.startswith('config/v4_16_')):raise ValueError('VERSIONED_CONTRACT_IMMUTABLE')
    p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.tmp')
    with t.open('wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(t,p);return ref(path,root)
