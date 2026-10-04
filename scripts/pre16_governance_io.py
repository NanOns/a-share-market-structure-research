"""PRE16 governance-only atomic output namespace and exact baseline IO."""
import hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='a1bb12f19e758784e55a1a93acaad1954861a0fc'
HEAD='data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V1.json'
CONTRACT='config/v4_cross_stage_current_audit_authority_v1.json'
R1='reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R1.json'
R10='reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R10.json'
R15='reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R15_BATCH_R3_FINAL.json'
DISPOSITION='data/v4/V4_SOURCE_AUTHORITY_SCOPED_DISPOSITION_REGISTRY_R5_INACTIVE.json'
AUDIT='docs/evidence/pre16_governance/V4_PRE16_STAGE10_TO_STAGE15_INDEPENDENT_ACCEPTANCE_AUDIT_R1_20261004.md'
ARCH='docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'
LEDGER='docs/audits/V4_PRE16_CROSS_STAGE_GOVERNANCE_RECONCILIATION_20261004.md'
def ref(path,root=ROOT):
    raw=(Path(root)/path).read_bytes();return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def read(path,root=ROOT):return json.loads((Path(root)/path).read_bytes())
def baseline(path,root=ROOT):return subprocess.check_output(['git','show',BASE+':'+path],cwd=root)
def atomic(path,value,root=ROOT,raw=False):
    root=Path(root).resolve();p=(root/path).resolve()
    if not p.is_relative_to(root) or not (path in [HEAD,CONTRACT,LEDGER] or any(p.is_relative_to(root/n) for n in ['reports/pre16_governance','docs/evidence/pre16_governance'])):raise ValueError('GOVERNANCE_OUTPUT_ONLY')
    data=value if raw else (json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()
    if p.exists() and p.read_bytes()==data:return ref(path,root)
    if p.exists() and path in [HEAD,CONTRACT]:raise ValueError('CURRENT_AUTHORITY_IMMUTABLE_VERSION')
    p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.tmp')
    with t.open('wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(t,p);return ref(path,root)
