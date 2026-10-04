"""R31R2 deterministic repair of an exact Git baseline; no historical evidence writes."""
import hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE='abe8311d55db3fecc086a77c3ce8a16f4309df54'
CONTRACT='config/v4_22_independent_audit_contract_v1.json'
TAG='codex/r31r2-v4-22-audit-contract-failclosed-tested-source-20261005-v3'
BASE_SHA='d6a45fe4fedf483e8a188d8cab884c4d1cd16f8910c27de9f6a15ee1ba58f9f9'
def build_bytes(root=ROOT):
    raw=subprocess.check_output(['git','show',BASE+':'+CONTRACT],cwd=root)
    if hashlib.sha256(raw).hexdigest()!=BASE_SHA: raise ValueError('BASELINE_CONTRACT_DIGEST_MISMATCH')
    c=json.loads(raw)
    c['version']='1.0.2'
    c['baseline']=BASE
    c['next_stage']='STOP_WAIT_R31R2_INDEPENDENT_EXTERNAL_AUDIT'
    c['status']='LOCAL_R31R2_CONTRACT_CANDIDATE_NOT_EXTERNAL_ACCEPTANCE'
    c['repair_provenance']=dict(stage='R31R2',baseline=BASE,baseline_contract_sha256=BASE_SHA,builder_model='B_HISTORICAL_ONLY_PLUS_DETERMINISTIC_REPAIR',builder='reports/r31r2/build_contract.py',external_authority='docs/evidence/r31r2/V4_R31R1_V4_22_AUDIT_CONTRACT_REPAIR_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md')
    c['closure_authority_authorizations']={}
    c['open_item_closure_binding_schema']=dict(required=['item_id','capability_scope','canonical_sha256','closure_authority','exact_evidence'],authority_rule='EXACT_AUTHORIZED_AUTHORITY_FILE_WITH_MATCHING_CLOSURE_AUTHORIZATION; OPENER_IS_NOT_AUTOMATIC_CLOSER',evidence_rule='NONEMPTY_ARRAY_OF_REPO_CONTAINED_EXACT_PATH_SHA256_AND_CONTRACT_ID_WHERE_PRESENT; INDEPENDENT_READBACK',current_real_closures='NONE')
    c['referential_integrity']['schema_order']='ALL_REQUIRED_FIELDS_THEN_EXACT_V421_LANE_REGISTRY_THEN_LANE_SEMANTICS_THEN_REAL_PARENT_LOGIC'
    c['tested_source_governance']['annotated_tag']=TAG
    c['tested_source_governance']['allowed_post_test_delta_prefixes']=['reports/r31r2/','docs/evidence/r31r2/']
    c['tested_source_governance']['explicit_closure_allowlist']=['reports/r31r2/'+n for n in ['clean-tests.xml','clean-output.txt','clean-summary.json','CLEAN_REGRESSION.json','LOCAL_TEST_SUMMARY.json','TESTED_SOURCE_GOVERNANCE.json','R31R2_CANDIDATE_SEAL.json','CLEAN_CHECKOUT_PROOF.json']]+['docs/evidence/r31r2/R31R2_REPAIR_ACCEPTANCE.md']
    return (json.dumps(c,sort_keys=True,indent=2,ensure_ascii=False)+'\n').encode()
def build(root=ROOT):
    root=Path(root).resolve(); raw=build_bytes(root); p=root/CONTRACT
    if p.exists():
        current=p.read_bytes()
        if current!=raw and hashlib.sha256(current).hexdigest()!=BASE_SHA: raise ValueError('REFUSE_UNDECLARED_CANONICAL_SOURCE')
    t=p.with_name(p.name+'.r31r2-staging')
    with t.open('wb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
    os.replace(t,p)
    return hashlib.sha256(raw).hexdigest()
if __name__=='__main__': print(build())
