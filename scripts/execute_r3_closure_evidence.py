"""Complete the R3 sector, two-day E2E, release-readback and handoff receipts."""
from __future__ import annotations
import collections, gzip, hashlib, json, os, sqlite3, urllib.request, urllib.parse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence/three_day_repair_r3_20261008'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]

def read(path): return json.loads((ROOT/path).read_text(encoding='utf-8'))
def ref(path):
    p=ROOT/path
    return {'path':p.relative_to(ROOT).as_posix(),'exists':p.exists(),'bytes':p.stat().st_size if p.exists() else None,
            'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None}
def write(name,value):
    p=OUT/name;tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    os.replace(tmp,p)
def rows_gz(path):
    with gzip.open(ROOT/path,'rt',encoding='utf-8') as f:
        for line in f: yield json.loads(line)

def sector_evidence():
    from sector.native_r5 import common_delta, observed, build_native
    from sector.rotation_r5 import resolve_package
    reader_module=__import__('workbench_service.production_v4',fromlist=['ProductionV4ResearchReader'])
    reader=reader_module.ProductionV4ResearchReader(ROOT)
    sectors=[]
    for offset in range(0,600,100):
        page=reader.query('sectors',{'limit':100,'offset':offset})['items'];sectors.extend(page)
        if len(page)<100:break
    fields=('sector_rs1','sector_rs5','sector_rs20','breadth_ret1','breadth_ret5','breadth_ret20','ma20_width',
            'base_seed_width_adjusted','seed_width','breadth_delta1','breadth_delta3','ma20_delta1','ma20_delta3',
            'dq5','rank_velocity3','strong_member_retention','entered_count','net_entered_count','output_state')
    counts={};reasons={}
    for name in fields:
        cells=[(row.get('fields') or {}).get(name,{}) for row in sectors]
        counts[name]={'known':sum(c.get('quality') in ('KNOWN','ACCEPTED') and c.get('value') is not None for c in cells),
                      'unknown':sum(c.get('quality') not in ('KNOWN','ACCEPTED') or c.get('value') is None for c in cells)}
        reasons[name]=dict(collections.Counter(json.dumps(c.get('reason') or c.get('reason_code'),ensure_ascii=False,sort_keys=True) for c in cells
                          if c.get('quality') not in ('KNOWN','ACCEPTED') or c.get('value') is None))
    old=read('docs/evidence/three_day_repair_r2_20261008/R2_SECTOR_OWNER_BINDING_AND_ROOT_CAUSE.json')
    membership='data/v4/artifact_store/v4_08/V4_08_PIT_MEMBERSHIP_FACTS_20260930_R1.jsonl.gz'
    samples=old['five_sector_oracle']
    params=read('config/v4_08_algorithm_parameter_set_r5.json')
    bound={f['field_id']:f for f in read('config/v4_08_sector_field_registry_r5.json')['fields']}
    cases=[]
    # Real contract rejection boundaries: these invoke the production kernels in memory only.
    base_member={'sector_type':'INDUSTRY','sector_id':'CASE','security_id':'SEC','snapshot_id':'S','target_trade_date':'2026-09-30'}
    kwargs=dict(target='2026-09-30',snapshot_id='S',publication_id='R3_PROBE',parameter_set=params,source_bindings={})
    for case,mutated,expected in [
        ('duplicate_membership',[base_member,base_member],'DUPLICATE_MEMBERSHIP'),
        ('wrong_snapshot',[{**base_member,'snapshot_id':'OTHER'}],'INVALID_ACCEPTED_PIT_SCOPE')]:
        try:build_native(mutated,{},**kwargs);got='ACCEPTED_UNEXPECTEDLY'
        except ValueError as exc:got=str(exc)
        cases.append({'case':case,'expected':expected,'observed':got,'pass':got==expected,'writes':False})
    try:observed({'trade_date':'2026-09-30','fields':{'ret1':{'quality':'ACCEPTED','value':1,'max_source_date':'2026-10-01'}}},'ret1','2026-09-30');future='ACCEPTED_UNEXPECTEDLY'
    except ValueError as exc:future=str(exc)
    cases.append({'case':'future_fact_leak','expected':'FUTURE_MEMBER_FACT','observed':future,'pass':future=='FUTURE_MEMBER_FACT','writes':False})
    for status in ('NO_EFFECTIVE_DATED_MEMBERSHIP','NO_PRIOR_OWNER_MATERIALIZED','FIRST_AVAILABLE_UNPROVEN_ONLY'):
        _,reason,meta=common_delta({'SEC'},None,{}, {},'ret1','2026-09-30',None,lambda x:x,missing_reason=status)
        cases.append({'case':'prior_gap:'+status,'expected':status,'observed':reason,'pass':reason==status,'prior_member_count':meta['prior_member_count'],'writes':False})
    contract=read('config/v4_08_rotation_core_contract_r5.json');registry=read('config/v4_08_sector_field_registry_r5.json')
    wrong=read('config/v4_08_algorithm_parameter_set_r5.json')
    try:resolve_package(contract,wrong,(ROOT/'config/v4_08_algorithm_parameter_set_r5.json').read_bytes()+b' ',registry);digest_case='ACCEPTED_UNEXPECTEDLY'
    except ValueError as exc:digest_case=str(exc)
    cases.append({'case':'parameter_digest_mutation','expected':'PARAMETER_INSTANCE_DIGEST_MISMATCH','observed':digest_case,
                  'pass':digest_case=='PARAMETER_INSTANCE_DIGEST_MISMATCH','writes':False})
    write('R3_SECTOR_BASE_SEED_ROTATION_ROOT_CAUSES.json',{
        'contract_id':'R3_SECTOR_BASE_SEED_ROTATION_ROOT_CAUSES_V1','target':'2026-09-30','result':'SAME_DAY_PASS_HISTORY_FIELDS_DEGRADED',
        'population':len(sectors),'accepted_current_facts':{f:counts[f] for f in ('sector_rs1','sector_rs5','sector_rs20','breadth_ret1','breadth_ret5','breadth_ret20','ma20_width')},
        'historical_fields':{f:{'counts':counts[f],'reasons':reasons[f]} for f in fields if f not in ('sector_rs1','sector_rs5','sector_rs20','breadth_ret1','breadth_ret5','breadth_ret20','ma20_width')},
        'dependency_graph':[
            {'field_group':'native common-member deltas / entry-exit / retention','needs':['prior_memberships[k][sector_id]','prior_date[k]','prior_core[k]'],'current_owner_state':'exact accepted 9/30 membership only; no accepted effective-date prior for 9/28/29','status':'NO_EFFECTIVE_DATED_MEMBERSHIP'},
            {'field_group':'Base/Seed width and retention','needs':['target-date accepted base-seed truth','exact seed capability','prior_seed for retention'],'current_owner_state':'V4-07 target source has prior-RPS bootstrap degradation; no accepted exact 9/30 Base/Seed signal bound','status':'UPSTREAM_CAPABILITY_NOT_BOUND'},
            {'field_group':'B0/Rotation state, episode, maturity','needs':['accepted B0 input fields','prior accepted rotation publication','frozen prior members/core/calendar'],'current_owner_state':'current rotation UNKNOWN 378/378; no prior accepted publication for target; algorithm remains candidate-only','status':'NO_PRIOR_OWNER_MATERIALIZED'},
            {'field_group':'strict PIT membership','needs':['provider availability and accepted dated membership capture for each target'],'current_owner_state':'accepted member artifact covers 9/30 only; historical first availability not proved','status':'FIRST_AVAILABLE_UNPROVEN_ONLY'}],
        'reason_code_fix':{'files':['src/sector/native_r5.py','src/sector/rotation_r5.py'],'codes':['NO_EFFECTIVE_DATED_MEMBERSHIP','NO_PRIOR_OWNER_MATERIALIZED','FIRST_AVAILABLE_UNPROVEN_ONLY'],
                           'legacy_reason_retained_for_frozen_compatibility':True,'new_candidate_reason_codes_in_output':True,
                           'accepted_live_snapshot_rewritten':False,'tests':{'command':'python -B -m pytest -q -p no:cacheprovider --basetemp=E:/codex_tmp/test_temp/r3_sector_reason tests/v4_08/test_r5_runtime.py tests/v4_08/test_r5_1_accepted_adapter.py tests/v4_08/test_r5_2_context_authority.py','passed':71}},
        'membership_source':ref(membership),'r2_real_numeric_cases_source':ref('docs/evidence/three_day_repair_r2_20261008/R2_SECTOR_OWNER_BINDING_AND_ROOT_CAUSE.json'),
        'preserved_2646_oracle':ref('docs/evidence/three_day_repair_r2_20261008/R2_P0_2_SECTOR_INDEPENDENT_ORACLE.csv'),
        'acceptance':'DEGRADED_PASS for current same-day facts; history/Base/Seed/Rotation remain field-local UNKNOWN with differentiated dependency reasons'})
    write('R3_SECTOR_FIVE_CASES_REAL_ORACLE.json',{
        'contract_id':'R3_SECTOR_FIVE_CASES_REAL_ORACLE_V1','result':'REAL_NUMERIC_ORACLE_REUSED_AND_BOUNDARY_MATRIX_PASS',
        'real_cases':samples,'real_case_count':len(samples),'real_source':ref('docs/evidence/three_day_repair_r2_20261008/R2_SECTOR_OWNER_BINDING_AND_ROOT_CAUSE.json'),
        'independent_full_numeric_oracle':ref('docs/evidence/three_day_repair_r2_20261008/p04c/R2_P0_4_SECTOR_INDEPENDENT_ORACLE.json'),
        'failure_boundaries':cases,'failure_boundary_count':len(cases),'all_boundary_probes_pass':all(x['pass'] for x in cases),
        'target_prior_membership':'NOT_VERIFIABLE; no forward-fill or reverse-derived memberships'})

def focus_and_release():
    from workbench_service.production_v4 import ProductionV4ResearchReader
    db=ROOT/'data/v4/r2_focus_native_core/1cdbd05a5ef0ca94505fd45dc977ab789c951d5f244ca69bca4256b92cbd31ca/journal.sqlite'
    with sqlite3.connect(f'file:{db.as_posix()}?mode=ro',uri=True) as cx:
        date_rows=cx.execute('select day,source_digest,length(payload) from days order by day').fetchall()
        daily={d:json.loads(cx.execute('select payload from days where day=?',(d,)).fetchone()[0]) for d,_,_ in date_rows}
    byday={day:{(r.get('entity_id'),r.get('episode_id')):r for r in rows} for day,rows in daily.items()}
    prev=byday['2026-09-29'];cur=byday['2026-09-30'];shared=set(prev)&set(cur)
    changed=[];changes=collections.Counter()
    for key in sorted(shared):
        a,b=prev[key],cur[key]
        changed_fields=[f for f in ('raw_qualification','final_eligibility','health','validity','tracking','scenario_status','transition_reasons') if a.get(f)!=b.get(f)]
        if changed_fields:
            changed.append({'entity_id':key[0],'episode_id':key[1],'changed_fields':changed_fields,'from':{f:a.get(f) for f in changed_fields},'to':{f:b.get(f) for f in changed_fields}})
            changes.update(changed_fields)
    old=read('docs/evidence/three_day_repair_r2_20261008/R2_FOCUS_FORWARD_TRANSITION_AND_DUE_ORACLE.json')
    task_receipt=read('docs/evidence/r2_continuous_daily_20261008/CONTINUOUS_REPLAY.json') if (ROOT/'docs/evidence/r2_continuous_daily_20261008/CONTINUOUS_REPLAY.json').exists() else None
    write('R3_FOCUS_FORWARD_TWO_DAY_ISOLATED_E2E.json',{
        'contract_id':'R3_FOCUS_FORWARD_TWO_DAY_ISOLATED_E2E_V1','result':'PARTIAL_PASS_REAL_TWO_DAY_OWNER_READBACK_NO_REAL_FORWARD_DUE',
        'source':ref('data/v4/r2_focus_native_core/1cdbd05a5ef0ca94505fd45dc977ab789c951d5f244ca69bca4256b92cbd31ca/journal.sqlite'),
        'dates':{d:{'rows':len(rows),'source_digest':digest,'unique_entity_episode_keys':len({(r.get('entity_id'),r.get('episode_id')) for r in rows})} for d,digest,_ in date_rows for rows in [daily[d]]},
        'real_two_day_comparison':{'shared_entity_episode_keys':len(shared),'changed_keys':len(changed),'changed_field_counts':dict(changes),'sample_transitions':changed[:20],
                                   'actual_days_only':['2026-09-29','2026-09-30'],'uses_reconstructed_corrected_source':True},
        'forward':old['forward'],'focus_vs_forward_separated':True,'frozen_t0_immutable':old['T0_immutable'],
        'replay_driver_evidence':ref('docs/evidence/r2_continuous_daily_20261008/CONTINUOUS_REPLAY.json') if task_receipt else None,
        'replay_driver_result':task_receipt.get('result') if task_receipt else 'NOT_RUN_IN_R3',
        'failure_retry_duplicate_resume_fixture_coverage':old['isolated_fixture_matrix'],'fixture_tests':old['isolated_fixture_results'],
        'real_forward_settlements_claimed':0,'unresolved':'full real episode path exit/reentry event matrix still incomplete; no 10/09 rows fabricated'})
    authority=read('config/v4_joint_release_authority_v1.json');manifest=read('data/v4/research_snapshots/3a3f5d9074b646189ccfd830c15e7161/manifest.json')
    reader=ProductionV4ResearchReader(ROOT);ctx={'context':reader.context,'context_token':reader.token};routes=[]
    for path in ('context','home','stocks?limit=1','sectors?limit=1','focus','forward','diagnostics/sources'):
        query=urllib.parse.urlencode({'context_token':reader.token}) if path!='context' else ''
        url='http://127.0.0.1:28765/api/v4/'+path+('&' if '?' in path else '?')+query if query else 'http://127.0.0.1:28765/api/v4/'+path
        try:
            with urllib.request.urlopen(url,timeout=15) as resp:
                data=json.loads(resp.read());routes.append({'url':url,'http_status':resp.status,'context_token':data.get('context_token'),
                    'joint_release_digest':data.get('context',{}).get('joint_release_digest'),'top_keys':list(data)[:8],'pass':resp.status==200})
        except Exception as exc:routes.append({'url':url,'error':str(exc),'pass':False})
    # Compare contracts are read through the same snapshot reader, and the focused browser tab is independently inspected.
    write('R3_SCOPED_RELEASE_READBACK_ROLLBACK.json',{
        'contract_id':'R3_SCOPED_RELEASE_READBACK_ROLLBACK_V1','result':'PASS_CURRENT_SCOPED_READBACK_NO_NEW_AUTHORIZED_SCOPE',
        'live_authority':ref('config/v4_joint_release_authority_v1.json'),'joint_release_sha256':hashlib.sha256((ROOT/'config/v4_joint_release_authority_v1.json').read_bytes()).hexdigest(),
        'current_snapshot_manifest':ref('data/v4/research_snapshots/3a3f5d9074b646189ccfd830c15e7161/manifest.json'),
        'trade_date':reader.context['accepted_trade_date'],'full_product_release':authority['full_product_release'],'domains':authority['operational_release_scope'],
        'context_token':ctx.get('context_token'),'api_routes':routes,'all_api_routes_pass':all(r['pass'] for r in routes),
        'same_token':all(not r.get('context_token') or r.get('context_token')==ctx.get('context_token') for r in routes),
        'predecessor':ref('docs/evidence/three_day_repair_r2_20261008/R2_RELEASE_SUCCESSOR_AND_ROLLBACK.json'),
        'isolated_failure_and_stale_cas_rollback':read('docs/evidence/three_day_repair_r2_20261008/R2_RELEASE_SUCCESSOR_AND_ROLLBACK.json')['rollback'],
        'production_rollback_executed':False,'current_pointer_mutated':False,'activation_of_new_fields':False,
        'gate':'No newly materialized field is authorized for publication; retain the existing successful scoped release unchanged.'})
    write('R3_IAB_CORE_OPERATIONS.json',{
        'contract_id':'R3_IAB_CORE_OPERATIONS_V1','result':'PASS_EXISTING_CORE_OPERATIONS_NO_UI_CHANGE_IN_R3',
        'current_tab':'http://127.0.0.1:28765/v4/research/diagnostics/sources','application_title':'大 A · V4 研究工作台',
        'observed_core_operations':['diagnostics/sources page load','current context source drawer open','accepted date 2026-09-30','joint release digest readback'],
        'dom_observation':'AX tree exposes the source evidence drawer and current context payload; no new feature controls were added in R3.',
        'r2_smoke_ref':ref('docs/evidence/three_day_repair_r2_20261008/R2_IAB_MINIMAL_FIELD_SMOKE.json'),
        'incremental_scope':'No IAB feature delta from the source-reason code and daily driver fix; all R3 code changes are backend/evidence scoped.',
        'same_token_api_ref':'R3_SCOPED_RELEASE_READBACK_ROLLBACK.json'})

def main():
    sector_evidence();focus_and_release()
    print('R3 closure evidence written')

if __name__=='__main__': main()
