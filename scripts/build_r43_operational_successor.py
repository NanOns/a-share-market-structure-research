"""Seal R4.3 operational candidate and exercise real isolated publication storage."""
from pathlib import Path
import argparse,json,sys,tempfile,shutil
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.r43_operational_sources import run_sources,ref,checked,DATES
from workbench_analysis.r43_operational_publication import POLICY,cas,digest,CandidateReadV2,rollback_staging
from workbench_analysis.scoped_successor_r421 import atomic,canonical,sha
OUT=ROOT/'docs/evidence/r4_3_four_session_closeout_20261009'

def write(name,x):atomic(OUT/name,canonical(x));return ref(ROOT,OUT/name)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sources-only',action='store_true');args=parser.parse_args()
    protected={p:sha(ROOT/p) for p in ['data/v4/V4_DATA_ACCEPTED_HEAD.json','data/v4/DM01_R4_RUNTIME_ACCEPTANCE_HEAD_V1.json','config/dm01_go_forward_runtime_contract_r4r1.json']}
    write('W2_W6_STAGE_ENTRY.json',dict(contract_id='R43_W2_W6_EXECUTION_V1',task=ref(ROOT,OUT/'R4_3_TASK_CONTRACT.md'),protected=protected,scope=['actual GBBQ binary adapter','date-valid lifecycle and special phase','operational successor policy','same-token candidate API','atomic isolated CAS and rollback'],next_stage='independent external review before live cutover'))
    trace=run_sources(ROOT,OUT)
    if args.sources_only:print(json.dumps(dict(status='FOUR_DAY_SOURCE_ADAPTER_READY',gbbq_events=trace['GBBQ']['record_count'])));return
    snapshot=ref(ROOT,OUT/'MEMBER_SNAPSHOT_S.json');s=json.loads(checked(ROOT,snapshot).read_bytes())
    owners={};unavailable=[]
    for day in DATES:
        folder=OUT/'owner_v3/owners'/day
        if not folder.exists():folder=OUT/'owner_v3'/day
        domains={}
        for domain,file in [('raw','raw.jsonl.gz'),('core','core.jsonl.gz'),('profile','profiles.jsonl.gz')]:
            path=folder/file
            if path.is_file():domains[domain]=ref(ROOT,path)
            else:unavailable.append(str(path))
        for domain,file in [('lifecycle','lifecycle.json'),('special_phase','special_phase.json')]:domains[domain]=ref(ROOT,OUT/'sources'/day/file)
        for domain,name in [('market','market_owner_candidate_v2.json'),('focus','corrected_d2.json.gz'),('prewatch','corrected_d0_prewatch.jsonl.gz')]:
            path=folder/name
            if path.is_file():domains[domain]=ref(ROOT,path)
        for domain,name in [('events','structure/events.jsonl'),('diagnostic','PROFILE_STRUCTURE_OWNER.json')]:
            path=folder/name
            if path.is_file():domains[domain]=ref(ROOT,path)
        forward=OUT/'owner_v3/CORRECTED_FOCUS_FORWARD.json.gz'
        if forward.is_file():domains['forward']=ref(ROOT,forward)
        for required in ['market','focus','forward','events','diagnostic']:
            if required not in domains:unavailable.append(day+':'+required)
        sfolder=OUT/'sector_v3/owners'/day
        for domain,names in [('sector',['sector_native.jsonl.gz','native.jsonl.gz','sector_native.jsonl']),('relative_sector',['relative_sector_loo.jsonl.gz','relative_sector.jsonl.gz']),('rotation',['rotation_candidate.jsonl.gz','rotation.jsonl.gz'])]:
            path=next((p for name in names for p in [sfolder/name,OUT/'sector_v3'/day/name] if p.is_file()),None)
            if path:domains[domain]=ref(ROOT,path)
            else:unavailable.append(day+':'+domain)
        owners[day]=domains
    if unavailable:write('W6_PENDING_ACTUAL_OWNER_INPUTS.json',dict(status='WAIT_ACTUAL_OWNER_BUILD',missing=unavailable));print(json.dumps(dict(status='WAIT_ACTUAL_OWNER_BUILD',missing=unavailable)));return
    sector_manifest=OUT/'sector_v3/SECTOR_REPLAY.json'
    if not sector_manifest.is_file():print(json.dumps(dict(status='WAIT_COMPLETE_SECTOR_RECEIPT')));return
    for item in json.loads(sector_manifest.read_bytes())['owners']:
        owners[item['trade_date']]['sector_receipt']=ref(ROOT,sector_manifest)
        owners[item['trade_date']]['seed']=item['seed']
        owners[item['trade_date']]['base_profile']=owners[item['trade_date']]['profile']
        owners[item['trade_date']]['profile']=item['enriched_profiles']
    code=[ref(ROOT,p) for p in [ROOT/'src/workbench_analysis/r43_operational_sources.py',ROOT/'src/workbench_analysis/r43_operational_publication.py',ROOT/'src/workbench_service/v4_server.py',ROOT/'scripts/serve_r43_candidate_preview.py',Path(__file__)]]
    code.append(ref(ROOT,ROOT/'config/v4_dated_operational_reconstructed_publication_v1.json'))
    code.append(ref(ROOT,ROOT/'src/workbench_service/static/r43-operational-preview.html'))
    for path in sorted((ROOT/'src/workbench_analysis').glob('*r43*.py')):
        binding=ref(ROOT,path)
        if binding not in code:code.append(binding)
    for name in ['src/tdx/gbbq_reader.py','src/adjustment/tdx_adjustment.py','src/v4/factors/core.py','src/sector/native_r5.py','src/sector/rotation_r5.py','src/workbench_analysis/v4_13_loo_runtime.py','config/v4_02_gbbq_price_impact_classification_v1.json']:
        code.append(ref(ROOT,ROOT/name))
    registry=write('R43_BUILDER_REGISTRY_SUCCESSOR_V1.json',dict(contract_id='R43_OPERATIONAL_BUILDER_REGISTRY_V1',status='CANDIDATE_REQUIRES_INDEPENDENT_ADMISSION',predecessor=ref(ROOT,ROOT/'config/dm01_go_forward_runtime_contract_r4r1.json'),bindings=code,input_snapshot=snapshot,source_adapter_trace=ref(ROOT,OUT/'04_TDX_BAOSTOCK_GBBQ_LIFECYCLE_AND_DELTA_SOURCE_TRACE.json'),owner_bindings=owners,historical_PIT_permission=False))
    candidate=dict(contract_id=POLICY,dates=DATES,accepted_trade_date='2026-10-08',membership_mode=s['membership_mode'],taxonomy=s['taxonomy'],membership_snapshot=snapshot,membership_snapshot_id=s['membership_snapshot_id'],membership_observed_at=s['membership_observed_at'],AS_RECORDED=False,historical_PIT_permission=False,production_eligible_scope='DATED_OPERATIONAL_RESEARCH_REPROJECTION_ONLY',owners=owners,registry=registry,old_last_good=ref(ROOT,ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json'))
    candidate['accepted_product_scope']=dict(required_boards=['SH_MAIN','SZ_MAIN','CHINEXT','STAR'],optional_degraded_boards=['BSE'],inherited_not_new_scope_reduction=True,all_market_claim=False,contracts=[ref(ROOT,ROOT/'config/v4_02_final_closure_contract_v1.json'),ref(ROOT,ROOT/'config/v4_01_historical_code_change_alias_completeness_v1.json')])
    binding=write('R43_OPERATIONAL_SUCCESSOR_CANDIDATE.json',candidate)
    api=CandidateReadV2(ROOT,candidate);context=api.context();readback=[]
    for day in DATES:
        for domain in ['raw','core','profile','sector','relative_sector','rotation','market','focus','forward','events','diagnostic','lifecycle','special_phase']:
            response=api.read(domain,day,context['context_token'])
            assert response['status']=='READY'
            if domain not in ['events']:assert response['rows']
            contents=response['rows']
            sample=contents[0] if isinstance(contents,list) and contents else contents if isinstance(contents,dict) else None
            if isinstance(sample,dict):sample={k:v[:1] if isinstance(v,list) else v for k,v in sample.items()}
            readback.append(dict(trade_date=day,domain=domain,context_token=response['context_token'],row_count=len(contents),empty_valid=domain=='events' and not contents,sample=sample))
    write('W6_CANDIDATE_API_SAME_CONTEXT_READBACK.json',dict(context=context,responses=readback,production_readback=False))
    Path('E:/r43_publication_qa').mkdir(parents=True,exist_ok=True);store=Path(tempfile.mkdtemp(dir='E:/r43_publication_qa'))
    # Actual immutable bytes copied into isolated project, not mocks.
    refs=[snapshot,registry,candidate['old_last_good']]+[b for domains in owners.values() for b in domains.values()]
    refs.extend([s['memberships'],s['identity_source']]+s['sources'])
    refs.extend(code+candidate['accepted_product_scope']['contracts'])
    for b in refs:
        source=checked(ROOT,b);destination=store/b['path'];destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
    head=store/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    original=canonical(dict(candidate,accepted_trade_date='2026-09-30',revision='original_isolated_predecessor'));atomic(head,original);oldsha=sha(head)
    checks=[]
    for name,action,error in [('stale',lambda:cas(store,head,candidate,'0'*64,staging=True),'STALE_OPERATIONAL_HEAD_CAS'),('crash',lambda:cas(store,head,candidate,oldsha,staging=True,inject_failure=True),'INJECTED_BEFORE_ATOMIC_REPLACE'),('bad_source',lambda:cas(store,head,dict(candidate,membership_snapshot=dict(snapshot,sha256='0'*64)),oldsha,staging=True),'R43_SOURCE_DIGEST_MISMATCH'),('wrong_taxonomy',lambda:cas(store,head,dict(candidate,taxonomy='BAO_CSRC'),oldsha,staging=True),'TDX_LATEST_PRIMARY_MEMBERSHIP_REQUIRED'),('PIT',lambda:cas(store,head,dict(candidate,historical_PIT_permission=True),oldsha,staging=True),'PIT_ESCALATION_FORBIDDEN'),('missing_external',lambda:cas(ROOT,ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json',candidate,None),'INDEPENDENT_EXTERNAL_ACCEPTANCE_REQUIRED')]:
        try:action();raise AssertionError('negative accepted:'+name)
        except ValueError as exc:assert str(exc).startswith(error);checks.append(dict(case=name,status='PASS',reason=str(exc)))
        assert sha(head)==oldsha
    first=cas(store,head,candidate,oldsha,staging=True);noop=cas(store,head,candidate,first['sha256'],staging=True)
    try:cas(store,head,candidate,oldsha,staging=True);raise AssertionError('same bytes stale accepted')
    except ValueError as exc:assert str(exc)=='STALE_OPERATIONAL_HEAD_CAS';checks.append(dict(case='same_bytes_stale',status='PASS',reason=str(exc)))
    predecessor=head.parent/'predecessors'/(oldsha+'.json');assert sha(predecessor)==oldsha
    try:rollback_staging(store,head,first['sha256'],'f'*64);raise AssertionError('wrong predecessor accepted')
    except ValueError as exc:assert str(exc)=='EXACT_PREDECESSOR_REQUIRED';checks.append(dict(case='wrong_rollback_predecessor',status='PASS',reason=str(exc)))
    rollback_result=rollback_staging(store,head,first['sha256'],oldsha);assert head.read_bytes()==original
    def attempt():
        try:return cas(store,head,candidate,oldsha,staging=True)['status']
        except (ValueError,FileExistsError) as exc:return str(exc) if isinstance(exc,ValueError) else 'PROMOTION_LOCKED'
    with ThreadPoolExecutor(max_workers=2) as pool:
        concurrent=list(pool.map(lambda _:attempt(),range(2)))
    assert concurrent.count('STAGING_OPERATIONAL_UPDATED')==1 and sum(x in ['STALE_OPERATIONAL_HEAD_CAS','PROMOTION_LOCKED'] for x in concurrent)==1
    checks.append(dict(case='concurrent_CAS',status='PASS',outcomes=concurrent))
    rollback_staging(store,head,sha(head),oldsha)
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    write('10_SUCCESSOR_ATOMIC_CAS_BAD_SOURCE_ROLLBACK_QA.json',dict(candidate=binding,negative_cases=checks,actual_CAS=first,repeat=noop,rollback=rollback_result,test_store=str(store),production_data_head_moved=False,protected_unchanged=protected,scope='Actual candidate source bytes and disk pointers; isolated store only'))
    write('08_CANONICAL_IDENTITY_AND_CORRECTED_OWNER_ADMISSION.json',dict(candidate=binding,registry=registry,status='SCOPED_PRODUCTION_SUCCESSOR_READY_FOR_INDEPENDENT_REVIEW',date_scope=DATES,operational_scope='RECONSTRUCTED_CURRENT_RESEARCH',historical_PIT_permission=False,production_external_acceptance='NOT_PRESENT_NO_LIVE_CUTOVER',unsupported_identity='Explicit lifecycle unknown rows retained; no prefix-only admission'))
    atomic(OUT/'09_NEW_OPERATIONAL_PUBLICATION_POLICY_AND_OLD_PIT_MIGRATION.md',('# R4.3 operational publication policy\n\nThe executable `r43_operational_publication.py` accepts date-bounded reconstructed operational owners with one TDX latest-member snapshot S. It preserves AS_RECORDED=false and historical_PIT_permission=false.\n\nProduction CAS requires an independently supplied EXTERNALLY_ACCEPTED_R43_OPERATIONAL record bound to the exact candidate digest; this build does not create that authority. Legacy 9/30 accepted head and strict PIT contracts remain unchanged. Current-read V2 supplies one context token across four dates and real RAW/Core/Profile/TDX sector rows.\n\nIsolated disk CAS tests cover stale predecessor, bad SHA, namespace/PIT rejection, injected failure, duplicate no-op and byte-exact predecessor rollback. A successful candidate read is not live cutover.\n').encode())
    print(json.dumps(dict(status='SCOPED_PRODUCTION_SUCCESSOR_READY',publication_id=api.token,live_cutover=False)))

if __name__=='__main__':main()
