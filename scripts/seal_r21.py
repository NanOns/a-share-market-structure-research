"""Bind independently validated promotion and exact detached regression."""
import json,subprocess,sys
from scripts.r21_io import ROOT,BASE,TESTED,TAG,HEAD,STAGE,atomic,ref
from scripts.validate_r21_promotion import validate
def seal(source,tag):
    result=validate()
    clean=json.loads((ROOT/'reports/r21/clean_regression/CLEAN_DETACHED_REGRESSION.json').read_bytes())
    assert clean['status']=='PASS_LOCAL' and clean['tested_source']==source and clean['total_passed']==251
    assert subprocess.check_output(['git','rev-parse',tag+'^{commit}'],cwd=ROOT).decode().strip()==source
    assert subprocess.run(['git','merge-base','--is-ancestor',BASE,source],cwd=ROOT,capture_output=True).returncode==0
    paths=['V4_15_PROMOTION_GATE.json','CURRENT_V4_15_AUTHORITY_GATE.json','V4_14_REPLAY_COMPATIBILITY_GATE.json','ROLLBACK_VALIDATION.json','LOCAL_TEST_SUMMARY.json','SUPERSEDED_CURRENT_STAGE_TESTS.json','OPEN_AUDIT_ITEMS.json','clean_regression/CLEAN_DETACHED_REGRESSION.json']
    receipt=dict(result,contract_id='V4_15_PROMOTION_CANDIDATE_R21_SEAL_V1',execution_baseline=BASE,externally_audited_runtime_tested_source=TESTED,externally_audited_runtime_tag=TAG,promotion_tested_source=source,promotion_immutable_tag=tag,source_publication='IMMUTABLE_ANNOTATED_TAG_AND_FINAL_BRANCH_ANCESTRY_ATOMIC_PUSH_REQUIRED',bundle_only=False,bindings={p:ref('reports/r21/'+p) for p in paths},accepted_head=ref(HEAD),stage_head=ref(STAGE),current_authority=ref('config/v4_current_stage_authority_v2.json'),parent_archives=[ref('reports/r21/'+p) for p in ['PARENT_STAGE_HEAD.json','PARENT_CURRENT_STAGE_AUTHORITY.json','PARENT_CURRENT_STAGE_AUTHORITY_READER.py','PARENT_REPLAY_AUTHORITY_READER.py','PARENT_RADAR_COHORT_AUTHORITY_ADAPTER.py']],external_promotion_audit='PENDING')
    atomic('reports/r21/V4_15_PROMOTION_CANDIDATE_SEAL.json',receipt)
    print(json.dumps(result))
if __name__=='__main__':seal(*sys.argv[1:])
