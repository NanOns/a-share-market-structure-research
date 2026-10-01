"""Full accepted 9/30 source read; independent source-AST probes and candidate handoff."""
from collections import Counter
from datetime import datetime,timezone
import gzip,json
from scripts.next_round_bundle_r1 import ROOT,write,atomic_bytes,bind,verify_protected
from scripts.v4_11_candidate_inputs_r1 import projection,positive_values
from scripts.v4_11_engineering_vectors_r1 import EXPECTED,event_vector,state_input
from src.v4.confirmation import detect_confirmation,package,exact
from src.v4.confirmation_d2_bridge import engineering_d2_publication
from src.v4.confirmation_events import state_events
BASE='reports/v4_11/candidate_r1/'

def gz(path,value):
    data=gzip.compress((json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf8'),mtime=0)
    p=ROOT/path
    if p.exists() and p.read_bytes()!=data:raise ValueError('IMMUTABLE_CANDIDATE_CONFLICT:'+path)
    if not p.exists():atomic_bytes(path,data)
    return bind(path)

def main():
    verify_protected();c,m,p,a,scanner=package();cutoff=datetime.now(timezone.utc).isoformat()
    inputs=projection(real=True,cutoff=cutoff);facts=detect_confirmation(inputs)
    ib=gz('data/v4/confirmation_candidates_r1/ACCEPTED_20260930_INPUT_PROJECTION_R1.json.gz',inputs)
    fb=gz('data/v4/confirmation_candidates_r1/CONFIRMATION_FACT_20260930_CANDIDATE_R1.json.gz',facts)
    oracle_namespace={};source=exact(m['legacy_source']).read_text(encoding='utf8');exec(compile(source,m['legacy_source']['path'],'exec'),oracle_namespace)
    oracle=oracle_namespace['scan_today_research'];probes=[];v=positive_values()
    for branch,field,boundary,negative in [('launch','clv',.60,.5999),('pullback','pullback_episode_confirmed',True,False),('recovery_turn','clv',.55,.5499),('trend_continue','rps20',.70,.6999)]:
        for label,value,expected in [('positive',v[field],True),('negative',negative,False),('boundary',boundary,True),('UNKNOWN',None,None)]:
            row=dict(v);row[field]=value;actual=oracle(row);runtime=scanner(row)
            if actual[branch]['eligible'] is not expected or actual!=runtime:raise ValueError('INDEPENDENT_SOURCE_AST_ORACLE_FAIL')
            probes.append(dict(branch=branch,case=label,source_facts=row,expected_legacy_eligible=expected,actual_legacy_eligible=actual[branch]['eligible'],full_source_AST_parity=True,
                formal_candidate='UNKNOWN_AMOUNT_OR_DOWNSTREAM_GATE' if branch!='pullback' else 'ENGINEERING_ONLY',scope='SYNTHETIC_PRIMITIVE_SOURCE_PROBE'))
    ob=write(BASE+'INDEPENDENT_SOURCE_AST_ORACLE_R1.json',dict(status='PASS_ENGINEERING_ORACLE',source=m['legacy_source'],probes=probes,external_acceptance=False))
    old,new,frozen,e=event_vector('PREWATCH');revisions=[];parent=None
    for delta in (0,1,2):
        pub=engineering_d2_publication([state_input('CONFIRMED',prior=old['rows'][0],delta=delta)])
        events=state_events(pub,frozen,revision_of=parent)
        if events[0]['primary_event']!='NEW_CONFIRMED':raise ValueError('REVISION_EVENT_CHANGED_PREDECESSOR')
        revisions.append(dict(d2_publication=pub,events=events,revision_of=parent));parent=pub['publication_id']
    replay=write(BASE+'SAME_DAY_REVISION_REPLAY_R1.json',dict(status='PASS_ENGINEERING_REPLAY',frozen_prior_session_state_head=frozen,revisions=revisions,
        scope='SYNTHETIC_ENGINEERING_ONLY',external_acceptance=False))
    scenario=Counter();unknown=Counter();statuses=Counter();multimatch=0
    for r in facts['rows']:
        statuses[r['confirmation_status']]+=1;scenario.update(r['matched_scenarios']);unknown.update(r['unknown_predicates']);multimatch+=len(r['matched_scenarios'])>1
    universe=len(inputs['rows'])
    summary=write(BASE+'FULL_MARKET_SUMMARY_R1.json',dict(contract_id='V4_11_REAL_FULL_MARKET_CANDIDATE_SUMMARY_V1',status='V4_11_CONFIRMATION_EVENTS_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',
        trade_date='2026-09-30',knowledge_cutoff=cutoff,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,accepted_data_head=c['accepted_data_head'],
        eligible_universe=universe,confirmation_rows=len(facts['rows']),confirmation_status_counts=dict(statuses),scenario_counts={s:scenario[s] for s in a['scenario_priority']},
        UNKNOWN_count=statuses['UNKNOWN'],UNKNOWN_reasons=dict(unknown),multi_scenario_count=multimatch,amount_A_disabled_security_count=universe,amount_A_disabled_branch_count=universe*3,
        real_event_counts=None,real_event_unknown_rows=universe,real_event_evaluation_status='UNAVAILABLE_ACCEPTED_TARGET_D2_AND_PRIOR_SESSION_STATE_PUBLICATIONS',
        hard_invalidation_conflicts=None,hard_invalidation_evaluation_status='UNAVAILABLE_ACCEPTED_REAL_D2',
        real_D2_publication=False,engineering_D2_event_engine_implemented=True,actual_bar_rows=sum(r['facts']['actual_bar']['value'] for r in inputs['rows']),
        input_publication=ib,confirmation_publication=fb,producer_contract_id='CONFIRMATION_DETECTOR_V1',parameter_set_id='V4_11_CONFIRMATION_PARAMETER_SET_V1',permissions=c['permissions']))
    # A publication availability table records every real entity, without manufacturing events.
    event_availability=gz('data/v4/confirmation_candidates_r1/STATE_EVENT_20260930_AVAILABILITY_R1.json.gz',dict(contract_id='STATE_EVENT_AVAILABILITY_V1',
        rows=[dict(security_id=r['security_id'],trade_date='2026-09-30',event_status='UNKNOWN_UNAVAILABLE_REAL_ACCEPTED_D2',primary_event=None) for r in inputs['rows']],accepted=False))
    expected=write(BASE+'INDEPENDENT_GOLDEN_EXPECTATIONS_R1.json',dict(contract_id='V4_11_INDEPENDENT_GOLDEN_VECTORS_V1',expected=EXPECTED,source='LITERAL_CONTRACT_EXPECTATIONS_NOT_PRODUCER_OUTPUT',
        executable_vectors=bind('tests/v4_11/test_confirmation.py'),persistence_vectors=bind('tests/v4_11/test_persistence.py')))
    runtime=[bind(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT/'src/v4').glob('confirmation*.py'))]
    handoff=write(BASE+'V4_11_CANDIDATE_EXTERNAL_REAUDIT_HANDOFF_R1.json',dict(contract_id='V4_11_CANDIDATE_HANDOFF_V1',status='V4_11_CONFIRMATION_EVENTS_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',
        stage_contract=c['stage_contract'],authority=[c['v4_10_head'],c['entry_contract'],c['executable_authority'],c['accepted_data_head']],
        contracts=[bind('config/v4_11_confirmation_detector_contract_r1.json'),c['legacy_manifest'],c['machine_ast'],c['parameters']],runtime=runtime,
        full_market=summary,independent_oracle=ob,same_day_replay=replay,golden_expectations=expected,event_availability=event_availability,
        migration=bind('src/workbench_db/migrations/v4_postgres/026_confirmation_events_candidate_r1.sql'),rollback=bind('src/workbench_db/migrations/v4_postgres_rollbacks/026_confirmation_events_candidate_r1.sql'),
        migration_allocator=bind('config/v4_migration_allocation_registry_r2.json'),
        engineering_completed=['EXACT_LEGACY_AST','D0_CANDIDATE','CONTROLLED_D2_PROOF','FROZEN_PRIOR_EVENTS','APPEND_ONLY_PERSISTENCE','RETRY_CONSUMER_ROLLBACK'],
        external_limits=['NO_TARGET_ACCEPTED_COMMON_SAFETY_EPISODE_FACT_PRODUCERS','AMOUNT_A_DISABLED','CURRENT_LOO_DIAGNOSTIC_ONLY','REAL_D2_ADOPTION_REQUIRES_NEXT_EXTERNAL_ACCEPTANCE'],
        clean_joint='reports/next_round_r1/BATCH_CLEAN_CHECKOUT_R1.json',accepted=False,permissions=c['permissions'],stage_head_promotion=False,data_head_promotion=False,
        v4_12_implemented=False,next_stage='STOP_WAIT_FOR_INDEPENDENT_EXTERNAL_REAUDIT'))
    verify_protected();print(json.dumps(dict(status='CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',universe=universe,counts=dict(statuses),handoff=handoff)))
if __name__=='__main__':main()
