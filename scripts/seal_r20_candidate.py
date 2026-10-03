"""Evidence-only candidate seal; remote predicate independently checked after atomic push."""
import json,subprocess,sys
from scripts.r20_io import ROOT,BASE,read,ref,atomic

def call(args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True,encoding='utf8').strip()

def seal(source,clean_path,tag):
    if call(['rev-parse','HEAD'])!=source:raise ValueError('SEAL_FROM_EXACT_TESTED_IMPLEMENTATION_ONLY')
    if call(['rev-parse','refs/tags/'+tag+'^{commit}'])!=source:raise ValueError('IMMUTABLE_TESTED_TAG_BINDING')
    clean=read(clean_path)
    if clean['status']!='PASS_LOCAL' or clean['tested_source']!=source:raise ValueError('EXACT_CLEAN_TESTED_SOURCE_REQUIRED')
    subprocess.run(['git','merge-base','--is-ancestor',BASE,source],cwd=ROOT,check=True)
    gates={'current_authority':'reports/r20a/CURRENT_AUTHORITY_GATE.json','portability':'reports/r20b/stage_gate.json','radar_cohort':'reports/r20c/INDEPENDENT_RADAR_COHORT_GATE.json','settlement':'reports/r20d/SETTLEMENT_GATE.json','persisted_e2e':'reports/r20e/INDEPENDENT_E2E_GATE.json'}
    required=['R20A_CURRENT_STAGE_AUTHORITY','R20B_BYTE_IDENTITY_PORTABILITY','R20C_V4_15_RADAR_COHORT_RUNTIME','R20D_V4_15_SETTLEMENT_RUNTIME','R20E_V4_15_FULL_PERSISTED_E2E','R20E_INDEPENDENT_ORACLE']
    merged={}
    for path in gates.values():merged.update(read(path))
    if any(merged.get(k)!='PASS_LOCAL' for k in required):raise ValueError('ALL_R20_GATES_REQUIRED')
    stage=read('data/v4/V4_STAGE_ACCEPTED_HEAD.json');data=read('data/v4/V4_DATA_ACCEPTED_HEAD.json')
    if stage['accepted_stage_range']!='V4_00_TO_V4_14_ACCEPTED' or data['accepted_trade_date']!='2026-09-30':raise ValueError('PROTECTED_POINTERS')
    if (ROOT/'data/v4/V4_15_ACCEPTED_HEAD.json').exists():raise ValueError('NO_V4_15_ACCEPTED_HEAD')
    for path in ['data/v4/V4_14_ACCEPTED_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json']:
        original=subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT)
        if (ROOT/path).read_bytes()!=original:raise ValueError('PROTECTED_HEAD_BYTES_KEEP')
    branch=call(['symbolic-ref','--short','HEAD'])
    result={k:'PASS_LOCAL' for k in required}
    result.update(contract_id='V4_15_RUNTIME_CANDIDATE_R20_SEAL_V1',execution_baseline=BASE,tested_source=source,tested_source_governance={'mode':'IMMUTABLE_COMMIT_PUBLISHED_TAG_AND_FINAL_BRANCH_ANCESTRY','remote_url':call(['remote','get-url','origin']),'immutable_tag_ref':'refs/tags/'+tag,'tag_commit':source,'final_branch_ref':'refs/heads/'+branch,'local_git_object_verified':True,'remote_verification_command':'python -m scripts.verify_r20_remote_source','publication_requirement':'FINAL_ATOMIC_PUSH_MUST_EXPOSE_EXACT_TAG_AND_BRANCH; VERIFY_REMOTE_BEFORE_REPORTING_COMPLETE','bundle_only':False},bindings={k:ref(v) for k,v in gates.items()},persisted_processes={k:ref('reports/r20e/'+k) for k in ['PRODUCER_RECEIPT.json','SETTLEMENT_RECEIPT.json']},real_capability_evidence=ref('reports/r20e/SETTLEMENT_RECEIPT.json'),clean_regression=ref(clean_path),protected_heads={p:ref(p) for p in ['data/v4/V4_14_ACCEPTED_HEAD.json','data/v4/V4_STAGE_ACCEPTED_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json']},representation_registry=ref('data/v4/V4_EXACT_BYTE_PORTABILITY_REGISTRY_R1.json'),R19_AUDIT_01='CLOSED_LOCAL',R19_AUDIT_02='CLOSED_LOCAL',V4_15_RUNTIME_CANDIDATE='READY_FOR_INDEPENDENT_EXTERNAL_AUDIT',REAL_ACCEPTED_SOURCE_V4_15='PASS_CAPABILITY_SCOPED',real_forward_scope='REAL_SEPT30_T0_AND_FIVE_PENDING_HORIZONS; MATURE_NUMERICAL_PATHS_ENGINEERING_ONLY',HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',ALGORITHM_STATE_REPLAY_PASS='DEGRADED_PASS_CAPABILITY_SCOPED',V4_15_ACCEPTED_HEAD='NOT_CREATED',V4_STAGE_ACCEPTED_HEAD='V4_00_TO_V4_14_ACCEPTED',V4_DATA_ACCEPTED_HEAD='2026-09-30',Production=False,Shadow=False,Focus=False,V4_16=False,NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
    atomic('reports/r20e/V4_15_RUNTIME_CANDIDATE_R20_SEAL.json',result)
    print(json.dumps(result))
if __name__=='__main__':seal(*sys.argv[1:])
