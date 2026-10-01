"""Real 9/30 candidate plus independent semantic and frozen-event replay evidence."""
from collections import Counter
from datetime import datetime,timezone
from scripts.next_round_bundle_r2 import ROOT,write,atomic_bytes,bind,verify_protected,read
from scripts.build_v4_11_confirmation_candidate_r1 import gz
from scripts.v4_11_candidate_inputs_r2 import projection
from scripts.verify_v4_11_semantics_r2 import verify
from scripts.v4_11_engineering_vectors_r1 import EXPECTED,event_vector,state_input
from src.v4.confirmation import detect_confirmation,package
from src.v4.confirmation_d2_bridge import engineering_d2_publication
from src.v4.confirmation_events import state_events
BASE='reports/v4_11/candidate_r2/'
STATUS='V4_11_R2_SEMANTIC_REPAIR_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT'

def main():
    verify_protected();c,m,p,a,_=package();cutoff=datetime.now(timezone.utc).isoformat()
    inputs=projection(real=True,cutoff=cutoff);facts=detect_confirmation(inputs)
    ib=gz('data/v4/confirmation_candidates_r2/ACCEPTED_20260930_INPUT_PROJECTION_R2.json.gz',inputs)
    fb=gz('data/v4/confirmation_candidates_r2/CONFIRMATION_FACT_20260930_CANDIDATE_R2.json.gz',facts)
    oracle=write(BASE+'INDEPENDENT_SEMANTIC_ORACLE_R1.json',verify())
    statuses=Counter(r['confirmation_status'] for r in facts['rows']);scenarios=Counter();unknown=Counter()
    for row in facts['rows']:scenarios.update(row['matched_scenarios']);unknown.update(row['unknown_predicates'])
    amount_count=sum(v for k,v in unknown.items() if 'AUD-AMOUNT-A-06' in k)
    assert len(facts['rows'])==5224 and statuses['UNKNOWN']==5224 and amount_count==0
    summary=write(BASE+'FULL_MARKET_SUMMARY_R1.json',dict(contract_id='V4_11_REAL_FULL_MARKET_SEMANTIC_SUMMARY_R2',status=STATUS,
        trade_date='2026-09-30',actual_run_cutoff=cutoff,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,
        accepted_data_head=c['accepted_data_head'],eligible_universe=5224,confirmation_rows=len(facts['rows']),
        confirmation_status_counts=dict(statuses),scenario_counts={s:scenarios[s] for s in a['scenario_priority']},
        UNKNOWN_count=statuses['UNKNOWN'],UNKNOWN_reasons=dict(unknown),AUD_AMOUNT_A_06_UNKNOWN_count=amount_count,
        amr20_target_accepted_publication=None,stock_amr20_status='UNKNOWN_TARGET_PRODUCER_NOT_ACCEPTED',
        actual_bar_rows=sum(r['facts']['actual_bar']['value'] for r in inputs['rows']),
        multi_scenario_count=sum(len(r['matched_scenarios'])>1 for r in facts['rows']),
        real_event_counts=None,real_event_unknown_rows=5224,real_D2_publication=False,
        real_event_evaluation_status='UNAVAILABLE_ACCEPTED_TARGET_D2_AND_PRIOR_SESSION_STATE_PUBLICATIONS',
        CURRENT_WITH_LOO_BREADTH_SUPPORT='DIAGNOSTIC_ONLY',D0_writes_final_state=False,
        input_publication=ib,confirmation_publication=fb,semantic_erratum=c['semantic_erratum'],permissions=c['permissions']))
    old,new,frozen,events=event_vector('PREWATCH');revisions=[];parent=None
    for delta in (0,1,2):
        d2=engineering_d2_publication([state_input('CONFIRMED',prior=old['rows'][0],delta=delta)])
        e=state_events(d2,frozen,revision_of=parent)
        assert e[0]['primary_event']=='NEW_CONFIRMED'
        revisions.append(dict(d2_publication=d2,events=e,revision_of=parent));parent=d2['publication_id']
    replay=write(BASE+'SAME_DAY_REVISION_REPLAY_R1.json',dict(status='PASS_ENGINEERING',frozen_prior_session_state_head=frozen,
        revisions=revisions,scope='SYNTHETIC_ENGINEERING_ONLY',real_D2_adoption=False))
    expected=dict(EXPECTED);retired=expected.pop('AMOUNT_A_DISABLED')
    expected.update(AMR20_KNOWN_TRUE='TRUE',AMR20_KNOWN_FALSE='FALSE',AMR20_UNKNOWN='UNKNOWN',SECTOR_AMOUNT_A_STATUS_IRRELEVANT='UNCHANGED')
    golden=write(BASE+'ACTIVE_GOLDEN_EXPECTATIONS_R2.json',dict(active_expected=expected,retired={'AMOUNT_A_DISABLED':retired},
        retirement_authority=c['external_audit_authority'],source='LITERAL_INDEPENDENT_EXPECTATIONS',
        old_inventory_preserved=bind('reports/v4_11/candidate_r1/INDEPENDENT_GOLDEN_EXPECTATIONS_R1.json'),
        active_tests=[bind('tests/v4_11/test_confirmation.py'),bind('tests/v4_11/test_semantic_r2.py'),bind('tests/v4_11/test_persistence.py')]))
    baseline=read('reports/next_round_r2/BASELINE_RUNTIME_ARCHIVE_R1.json')['archives']
    path='tests/v4_11/test_persistence.py';archive='data/v4/source_evidence/next_round_r2_baseline/'+path
    old_binding=bind(archive);old_binding['path']=path
    supersession=write(BASE+'BASELINE_SUPERSESSION_R1.json',dict(baseline_commit=read('reports/next_round_r2/BATCH_STAGE_ENTRY_R1.json')['baseline_commit'],
        old_r1_evidence_and_contracts_preserved=True,archives=baseline+[dict(original_binding=old_binding,original_bytes_archive=bind(archive))],
        interpretation='R1 historical runtime and vectors resolve to baseline original byte archives; current runtime is independently bound by R2.',
        unchanged_migration_026=bind('src/workbench_db/migrations/v4_postgres/026_confirmation_events_candidate_r1.sql')))
    handoff=write(BASE+'V4_11_SEMANTIC_REPAIR_EXTERNAL_REAUDIT_HANDOFF_R1.json',dict(contract_id='V4_11_SEMANTIC_REPAIR_HANDOFF_R2',status=STATUS,
        stage_contract=c['stage_contract'],external_audit_authority=c['external_audit_authority'],accepted=False,
        runtime=[bind(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT/'src/v4').glob('confirmation*.py'))],
        contracts=[bind('config/v4_11_confirmation_detector_contract_r2.json'),c['legacy_manifest'],c['semantic_erratum'],c['machine_ast'],c['parameters']],
        full_market=summary,independent_oracle=oracle,frozen_event_replay=replay,active_golden=golden,baseline_supersession=supersession,
        migration=bind('src/workbench_db/migrations/v4_postgres/027_confirmation_stock_amr20_semantic_r2.sql'),
        rollback=bind('src/workbench_db/migrations/v4_postgres_rollbacks/027_confirmation_stock_amr20_semantic_r2.sql'),
        allocator=bind('config/v4_migration_allocation_registry_r3.json'),
        external_limits=['TARGET_AMR20_ACCEPTED_PRODUCER_MISSING','TARGET_COMMON_SAFETY_EPISODE_ACCEPTED_PRODUCERS_MISSING',
            'CURRENT_LOO_DIAGNOSTIC_ONLY','REAL_D2_ADOPTION_REQUIRES_EXTERNAL_ACCEPTANCE'],
        permissions=c['permissions'],StageHead='KEEP',DataHead='KEEP',V4_12_implemented=False,
        clean_joint='reports/next_round_r2/BATCH_CLEAN_CHECKOUT_R1.json',next_stage='STOP_WAIT_FOR_INDEPENDENT_EXTERNAL_REAUDIT'))
    verify_protected();print(dict(status=STATUS,handoff=handoff,counts=dict(statuses),sector_audit_UNKNOWN_count=amount_count))

if __name__=='__main__':main()
