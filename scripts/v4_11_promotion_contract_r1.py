"""R6 immutable promotion constants; no V4-12 runtime."""
from pathlib import Path
import hashlib,json,gzip,os,tempfile
ROOT=Path(__file__).resolve().parents[1]
IMPLEMENTATION='a8635c6802dc31e3c879207cd470bd63021e35ca'
SEALED='1c46d6681ba1d0540551bcc0f75b35c545ff2769'
DECISION='V4_11_EXTERNAL_ACCEPTANCE_PASS_R5_CAPABILITY_SCOPED_ENGINEERING'
P='reports/next_round_r6/'
DOC='docs/evidence/next_round_r6/'
AUDIT=DOC+'V4_11_R5_INDEPENDENT_EXTERNAL_ACCEPTANCE_R1_20261002.md'
MASTER=DOC+'V4_NEXT_ROUND_EXECUTION_MASTER_R6_20261002.md'
TASK=DOC+'V4_11_ACCEPTED_HEAD_PROMOTION_AND_V4_12_STAGE_ENTRY_TASK_R1_20261002.md'
UPGRADE='docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'
CANDIDATE=P+'V4_11_ACCEPTED_HEAD_CANDIDATE_R1.json'
HEAD='data/v4/V4_11_ACCEPTED_HEAD.json'
GLOBAL='data/v4/V4_STAGE_ACCEPTED_HEAD.json'
PARENT='data/v4/V4_10_ACCEPTED_HEAD.json'
ARCHIVE=P+'PARENT_STAGE_HEAD_ORIGINAL_BYTES.json'
ENTRY='reports/v4_12/V4_12_STRUCTURE_ANCHOR_SUPPORT_STAGE_ENTRY_R1.json'
CLEAN=P+'V4_11_PROMOTION_CLEAN_DETACHED_R1.json'
PERMISSIONS={k:False for k in ('production_permission','shadow_production_permission','focus_cutover_permission','global_mandatory_adoption')}
CAPABILITIES=dict(CONFIRMATION_LAUNCH_CONFIRM='ENGINEERING_ACCEPTED_FORMAL_D0_CAPABILITY',CONFIRMATION_RECOVERY_TURN='ENGINEERING_ACCEPTED_FORMAL_D0_CAPABILITY',CONFIRMATION_STRONG_PULLBACK='DIAGNOSTIC_ONLY_NOT_FORMAL',CONFIRMATION_TREND_CONTINUE='DIAGNOSTIC_ONLY_NOT_FORMAL',D2_SEALED_OWNER_BRIDGE='ENGINEERING_ACCEPTED',STATE_EVENT_V1='ENGINEERING_ACCEPTED_RECONSTRUCTED_LEFT_CENSORED_SCOPE',HISTORICAL_AS_RECORDED_EVENT='NOT_PROVEN',FULL_D0_D1_D2_DAG='NOT_IMPLEMENTED',V4_12_STRUCTURE_SUPPORT='NOT_IMPLEMENTED')
EVIDENCE=[
'reports/v4_11_r4a/R4A_SEALED_PRODUCER_SET.json',
*['reports/v4_11_r5a/'+n+'.json' for n in ('V4_07_V4_09_EXACT_OWNER_PARITY','INDEPENDENT_OWNER_INPUT_ORACLE','OWNER_INPUT_AUTHORITY_MATRIX','R5A_SEALED_OWNER_PRODUCER_SET')],
*['reports/v4_11_r5/'+n+'.json' for n in ('V4_11_R5_D2_ADAPTER_AST_EVIDENCE','INDEPENDENT_D2_OWNER_INPUT_ORACLE','RESIDUAL_UNKNOWN_ATTRIBUTION','R4_TO_R5_BUSINESS_DIFF','V4_11_R5_D2_READBACK','V4_11_R5_EVENT_REPLAY','V4_11_R5_SCENARIO_CAPABILITY_MATRIX','V4_11_R5_CLEAN_CHECKOUT','FULL_REPOSITORY_COLLECTION','V4_11_ACCEPTANCE_CANDIDATE')],AUDIT]
VALIDATORS=['scripts/v4_11_promotion_contract_r1.py','scripts/validate_v4_11_promotion_r1.py','scripts/promote_v4_11_accepted_head_r1.py']
def read(path):return json.loads((ROOT/path).read_bytes())
def bind(path):
    raw=(ROOT/path).read_bytes();return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def exact(ref):
    path=(ROOT/ref['path']).resolve()
    if not path.is_relative_to(ROOT):raise ValueError('PROMOTION_SOURCE_ESCAPE')
    raw=path.read_bytes()
    if len(raw)!=ref.get('bytes',ref.get('byte_count')) or hashlib.sha256(raw).hexdigest()!=ref['sha256']:raise ValueError('PROMOTION_EXACT_BYTE_MISMATCH:'+ref['path'])
    return path
def bound(ref):
    p=exact(ref);return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def atomic(path,raw):
    p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=p.name+'.',dir=p.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
def write(path,value,replace=False):
    raw=(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf8')
    if (ROOT/path).exists() and not replace:
        if (ROOT/path).read_bytes()!=raw:raise ValueError('IMMUTABLE_PROMOTION_ARTIFACT_EXISTS:'+path)
        return bind(path)
    atomic(path,raw);return bind(path)
