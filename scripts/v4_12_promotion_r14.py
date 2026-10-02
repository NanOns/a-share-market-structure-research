"""Exact scoped promotion transaction; explicit bundle source, no discovery."""
import argparse,json,hashlib,subprocess,os,tempfile
from pathlib import Path
from copy import deepcopy
from scripts.v4_11_promotion_contract_r1 import ROOT
BASE='33b1949a1c05b0fe6c9068e6db9f219a9f11378b'
OUT='reports/v4_12_promotion_r14/'
ARCH='docs/evidence/next_round_r14/'
HEAD='data/v4/V4_12_ACCEPTED_HEAD.json'
STAGE='data/v4/V4_STAGE_ACCEPTED_HEAD.json'
DATA='data/v4/V4_DATA_ACCEPTED_HEAD.json'
PERMISSIONS=dict(production_permission=False,shadow_production_permission=False,focus_cutover_permission=False,global_mandatory_adoption=False)
CAP={n:'ENGINEERING_ACCEPTED' for n in ['MULTI_ANCHOR_SNAPSHOT_V2','PER_ANCHOR_SUPPORT_ACCEPTANCE','PER_ANCHOR_PULLBACK_RECOVERY_RETENTION','ACTIVE_ANCHOR_SELECTOR','BREAKOUT_EPISODE_CONTINUITY','BREAKOUT_DUPLICATE_CREATION_GUARD','BREAKOUT_OWNER_ANCHOR_IMMUTABILITY','BREAKOUT_SAME_DAY_REVISION_PREDECESSOR','BREAKOUT_SECURITY_PROJECTION','BREAKOUT_TRANSITION_IDENTITY','SOURCE_AUTHORITY_FAIL_CLOSED','TIME_COUNTER_SEMANTICS']}
CAP.update(ANCHOR_COORDINATE_REBASE='ENGINEERING_ACCEPTED_CAPABILITY_SCOPED',REAL_TARGET_DATE_STRUCTURE_SIGNAL='DEGRADED_BY_ACCEPTED_OWNER_CAPABILITY',HISTORICAL_AS_RECORDED_D1='NOT_PROVEN',FULL_D0_D1_D2_REPLAY='NOT_YET_ACCEPTED_V4_14',V4_13_PROFILE_ADVANCED_PROJECTION='NOT_IMPLEMENTED')
def canonical(v):return (json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def read(p):return json.loads((ROOT/p).read_bytes())
def ref(p):
 b=(ROOT/p).read_bytes();return dict(path=p,sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def exact(r):
 p=(ROOT/r['path']).resolve();assert p.is_relative_to(ROOT.resolve());b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==r['sha256'] and len(b)==r['bytes'],r['path'];return b
def write(p,v,raw=False):
 b=v if raw else canonical(v);target=ROOT/p;target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists() and target.read_bytes()==b:return 0
 fd,tmp=tempfile.mkstemp(dir=target.parent,prefix='.r14-',suffix='.tmp')
 with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.replace(tmp,target);return 1
def prepare(bundle):
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==BASE
 for n in ['V4_R13_INDEPENDENT_EXTERNAL_ACCEPTANCE_R1_20261002.md','V4_NEXT_ROUND_EXECUTION_MASTER_R14_20261002.md','V4_12_ACCEPTED_HEAD_PROMOTION_TASK_R14A_20261002.md','V4_13_R1_PROFILE_ADVANCED_PROJECTION_CONTRACT_FREEZE_TASK_20261002.md']:write(ARCH+n,(Path(bundle)/n).read_bytes(),True)
 write(ARCH+'.gitattributes',b'* -text\n',True);write(OUT+'.gitattributes',b'* -text\n',True)
 write(OUT+'PARENT_STAGE_HEAD.json',(ROOT/STAGE).read_bytes(),True)
 tracked=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=ROOT,text=True).splitlines()
 paths=[p for p in tracked if p.startswith(('config/v4_12_','src/workbench_analysis/v4_12_','reports/v4_12','docs/evidence/next_round_v4_12')) or (p.startswith('scripts/') and 'v4_12' in p)]
 rounds={name:[ref(p) for p in paths if p.startswith(prefix)] for name,prefix in [('R8','reports/v4_12_r2/'),('R9','reports/v4_12_r2_1/'),('R10','reports/v4_12_runtime_r1/'),('R11','reports/v4_12_runtime_r11/'),('R12','reports/v4_12_runtime_r12/'),('R13','reports/v4_12_runtime_r13/')]}
 candidate=dict(contract_id='V4_12_ACCEPTED_HEAD_V1',status='PASS_SCOPED_ENGINEERING',acceptance_scope='SCOPED_ENGINEERING_ACCEPTANCE',baseline=BASE,tested_source='180606d6fe06f47b3639acf25e1549de1c19429f',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,capabilities=CAP,**PERMISSIONS,parent_stage=ref(OUT+'PARENT_STAGE_HEAD.json'),v4_11_parent=ref('data/v4/V4_11_ACCEPTED_HEAD.json'),data_head=ref(DATA),external_acceptance=ref(ARCH+'V4_R13_INDEPENDENT_EXTERNAL_ACCEPTANCE_R1_20261002.md'),contracts_runtime_validators_external_evidence=[ref(p) for p in paths],round_bindings=rounds,promotion_validator=ref('scripts/validate_v4_12_promotion_r14.py'),promotion_transaction=ref('scripts/v4_12_promotion_r14.py'),blocked_capabilities=read('reports/v4_12_runtime_r13/R13_RUNTIME_HANDOFF.json')['blocked_capabilities'],limitations={k:CAP[k] for k in ['REAL_TARGET_DATE_STRUCTURE_SIGNAL','HISTORICAL_AS_RECORDED_D1','FULL_D0_D1_D2_REPLAY','V4_13_PROFILE_ADVANCED_PROJECTION']})
 candidate['publication_authority']=dict(runtime_contract_id='V4_12_R13_RUNTIME_CANDIDATE_MANIFEST',authorized_manifests=[ref(p) for p in paths if p.endswith('/runtime_manifest.json') and p.startswith(('reports/v4_12_runtime_r13/synthetic/','reports/v4_12_runtime_r13/real/'))],scope='SCOPED_ENGINEERING_ONLY_NOT_PRODUCTION',other_bound_artifacts='HISTORICAL_CONTRACT_OR_REGRESSION_EVIDENCE_NOT_CURRENT_PUBLICATION_AUTHORITY')
 write(OUT+'V4_12_ACCEPTED_HEAD_CANDIDATE.json',candidate)
 write(OUT+'R14_STAGE_CONTRACT.json',dict(baseline=BASE,phase0=read(STAGE)['phase0_status'],order=['R14A','EXACT_PROMOTION_VALIDATION_PASS','R14B_CONTRACT_ONLY','UNIFIED_COMMIT_PUSH','STOP'],upgrade=ref('docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'),sections=['10E','20.1','20.2','20.3','20.4','41A.3','78','87A'],protected=[ref('AGENTS.md'),ref(DATA),ref('data/v4/V4_11_ACCEPTED_HEAD.json')],next_stage='WAIT_INDEPENDENT_EXTERNAL_AUDIT'))
def expected_stage(h):
 parent=read(OUT+'PARENT_STAGE_HEAD.json');out=deepcopy(parent)
 out.update(accepted_stage_range='V4_00_TO_V4_12_ACCEPTED',v4_12_binding=ref(HEAD),v4_12_status=h['status'],v4_12_external_acceptance=h['external_acceptance'],v4_12_capabilities=h['capabilities'])
 return out
def promote():
 from scripts.validate_v4_12_promotion_r14 import validate
 if (ROOT/HEAD).exists():validate(post=True);print('PASS_IDEMPOTENT_ZERO_MUTATIONS');return
 pre=validate();assert pre['status']=='PASS';write(OUT+'R14A_PRE_PROMOTION_VALIDATION.json',pre)
 mutations=write(HEAD,(ROOT/(OUT+'V4_12_ACCEPTED_HEAD_CANDIDATE.json')).read_bytes(),True)
 try:
  mutations+=write(STAGE,expected_stage(read(HEAD)));post=validate(post=True)
 except Exception:
  write(STAGE,(ROOT/(OUT+'PARENT_STAGE_HEAD.json')).read_bytes(),True);raise
 write(OUT+'R14A_POST_PROMOTION_VALIDATION.json',dict(**post,mutations=mutations));print('V4_12_ACCEPTED_HEAD_PROMOTION=PASS_SCOPED_ENGINEERING')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--bundle-dir');a=p.parse_args();prepare(a.bundle_dir) if a.bundle_dir else promote()
