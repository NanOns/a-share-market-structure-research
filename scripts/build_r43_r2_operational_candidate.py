"""Seal new QA/consumer code while reusing exact frozen S/Owner bytes."""
import json
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.r43_operational_sources import checked,ref,DATES
from workbench_analysis.r43_operational_publication import cas,digest,validate,CandidateReadV2,rollback_staging
from workbench_analysis.scoped_successor_r421 import atomic,canonical,sha
OLD=ROOT/'docs/evidence/r4_3_r1_targeted_repair_20261009'
OUT=ROOT/'docs/evidence/r4_3_r2_release_control_20261009'

def write(name,value):atomic(OUT/name,canonical(value));return ref(ROOT,OUT/name)

def main():
    prior=json.loads((OLD/'R43_OPERATIONAL_SUCCESSOR_CANDIDATE_V2.json').read_bytes())
    registry=json.loads(checked(ROOT,prior['registry']).read_bytes())
    bindings=[ref(ROOT,ROOT/b['path']) for b in registry['bindings']]
    for name in ['src/workbench_analysis/r43_release_control.py','scripts/promote_r43_operational_v1.py','scripts/build_r43_r2_operational_candidate.py','scripts/audit_r43_r2_ui_compatibility.py','config/v4_r43_user_authorized_cutover_v1.json']:
        bindings.append(ref(ROOT,ROOT/name))
    registry.update(bindings=bindings,predecessor_registry=prior['registry'],revision='R43_R2_RELEASE_CONTROL_V3',owner_rebuild_required=False,immutable_owner_origin='Original registry and owner producer execution bindings remain frozen; only source QA and consumer compatibility changed',source_reparse_verification=ref(ROOT,OLD/'SOURCE_CAPTURE_REPARSE_VERIFICATION_V2.json'))
    new_registry=write('R43_BUILDER_REGISTRY_SUCCESSOR_V3.json',registry)
    candidate=dict(prior,registry=new_registry,revision='R43_R2_SCOPED_RELEASE_V3',predecessor_candidate=ref(ROOT,OLD/'R43_OPERATIONAL_SUCCESSOR_CANDIDATE_V2.json'),source_reparse_verification=ref(ROOT,OLD/'SOURCE_CAPTURE_REPARSE_VERIFICATION_V2.json'),task_contract=ref(ROOT,OUT/'TASK_R2.md'))
    candidate.update(external_review_contract='R43_SCOPED_EXTERNAL_ADMISSION_V2',required_independently_accepted_domains=['raw','core','profile','sector','relative_sector','market'],rotation_validation_state='VALIDATION_ONGOING',scope_boundary='Per-domain independent disposition; nonaccepted domains fail closed; no strict PIT or complete FP claim')
    candidate.update(authority_mode='USER_AUTHORIZED_SCOPED_OPERATIONAL_V1',user_request_evidence=ref(ROOT,OUT/'DIRECT_USER_CUTOVER_AUTHORIZATION.md'),scope_boundary='Direct human user authorizes immediate operational production; not independent acceptance; Rotation validation ongoing')
    binding=write('R43_OPERATIONAL_SUCCESSOR_CANDIDATE_V3.json',candidate)
    validate(ROOT,candidate)
    api=CandidateReadV2(ROOT,candidate);reads=[]
    for day in DATES:
        for domain in ['raw','core','profile','sector','relative_sector','rotation','market','focus','forward','events','diagnostic','lifecycle','special_phase']:
            value=api.read(domain,day,api.token)
            assert value['status']=='READY' and value['trade_date']==day and value['context_token']==api.token
            assert value['AS_RECORDED'] is False and value['PIT_ELIGIBLE'] is False
            reads.append(dict(trade_date=day,domain=domain,count=len(value['rows']),context_token=api.token))
    write('R43_R2_FOUR_DATE_CANDIDATE_READBACK.json',dict(candidate=binding,responses=reads,production_cutover=False))
    sandbox=Path(tempfile.mkdtemp(prefix='r43_r1_cas_',dir='E:/codex_tmp'))
    snapshot=json.loads(checked(ROOT,candidate['membership_snapshot']).read_bytes())
    references=[candidate['membership_snapshot'],new_registry,candidate['old_last_good']]+bindings+candidate['accepted_product_scope']['contracts']+[snapshot['memberships'],snapshot['identity_source']]+snapshot['sources']
    references.extend(b for domains in candidate['owners'].values() for b in domains.values())
    for b in references:
        p=sandbox/b['path'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(checked(ROOT,b),p)
    head=sandbox/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    predecessor=canonical(dict(candidate,revision='ISOLATED_CAS_PREDECESSOR_TEST_BYTES'))
    atomic(head,predecessor);expected=sha(head);tests=[]
    cases=[('stale',lambda:cas(sandbox,head,candidate,'0'*64,staging=True),'STALE_OPERATIONAL_HEAD_CAS'),
           ('crash',lambda:cas(sandbox,head,candidate,expected,staging=True,inject_failure=True),'INJECTED_BEFORE_ATOMIC_REPLACE'),
           ('bad_source',lambda:cas(sandbox,head,dict(candidate,membership_snapshot=dict(candidate['membership_snapshot'],sha256='0'*64)),expected,staging=True),'R43_SOURCE_DIGEST_MISMATCH'),
           ('no_user_authorization',lambda:cas(ROOT,ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json',candidate,None),'EXACT_USER_AUTHORIZATION_REQUIRED')]
    for name,call,error in cases:
        try:call();raise AssertionError('NEGATIVE_ACCEPTED:'+name)
        except ValueError as exc:assert str(exc).startswith(error);tests.append(dict(case=name,result='REJECTED',reason=str(exc)))
        assert sha(head)==expected
    first=cas(sandbox,head,candidate,expected,staging=True)
    repeat=cas(sandbox,head,candidate,first['sha256'],staging=True)
    assert repeat['status']=='NOOP_IDENTICAL'
    try:cas(sandbox,head,candidate,expected,staging=True);raise AssertionError('SAME_BYTES_STALE_ACCEPTED')
    except ValueError as exc:tests.append(dict(case='same_bytes_stale',result='REJECTED',reason=str(exc)))
    try:rollback_staging(sandbox,head,first['sha256'],'f'*64);raise AssertionError('WRONG_PREDECESSOR_ACCEPTED')
    except ValueError as exc:tests.append(dict(case='wrong_predecessor',result='REJECTED',reason=str(exc)))
    rollback=rollback_staging(sandbox,head,first['sha256'],expected);assert head.read_bytes()==predecessor
    def attempt():
        try:return cas(sandbox,head,candidate,expected,staging=True)['status']
        except (ValueError,FileExistsError) as exc:return str(exc) if isinstance(exc,ValueError) else 'PROMOTION_LOCKED'
    with ThreadPoolExecutor(max_workers=2) as pool:concurrent=list(pool.map(lambda _:attempt(),range(2)))
    assert concurrent.count('STAGING_OPERATIONAL_UPDATED')==1
    rollback_staging(sandbox,head,sha(head),expected)
    write('R43_R2_CANDIDATE_AND_ISOLATED_CAS.json',dict(candidate=binding,candidate_digest=api.token,registry=new_registry,original_S_and_owners_reused_exactly=True,isolated_store=str(sandbox),tests=tests,first_CAS=first,NOOP=repeat,rollback=rollback,concurrent=concurrent,production_CAS_executed=False,external_acceptance_status='NOT_SIGNED_NO_AUTHORITY_CREATED',accepted_permissions=[],missing_permissions=['Independent source/numeric/compatibility acceptance bound to this exact candidate digest'],acceptance='CANDIDATE_AND_ISOLATED_CAS_ENGINEERING_PASS'))
    print(json.dumps(dict(candidate_digest=api.token,reads=len(reads),CAS='ISOLATED_PASS',production=False)))

if __name__=='__main__':main()
