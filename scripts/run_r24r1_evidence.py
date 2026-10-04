"""Stage gates from isolated execution and independent persisted-state checks."""
import tempfile
from pathlib import Path
from scripts.r24r1_io import ROOT, BASE, ref, read, atomic
from scripts.r24r1_protection import protected_bytes
from scripts.validate_r24r1_activation import inspect, protected
from tests.test_r24r1_authority import positive, daily_negative, F_CASES, corruption
from tests.test_r24r1_a20 import negative, REASONS

def run():
    before=protected_bytes()
    x=positive('persisted_'+__import__('uuid').uuid4().hex)
    context=x['context']; oracle=inspect(ROOT/context['database'],context['manifest'])
    f=[daily_negative(case) for case in F_CASES]
    a=[negative(case) for case in REASONS]
    with tempfile.TemporaryDirectory(prefix='r24r1-oracle-') as temporary:
        c=[corruption(case,Path(temporary)) for case in ['C01','C02','C03','C04']]
        s=[corruption(case,Path(temporary)) for case in ['S01','S02','S03','S04']]
    after=protected_bytes(); assert before==after
    common=dict(status='PASS_LOCAL',external_acceptance='NOT_GRANTED',runtime_authorized=False,real_shadow_authorized=False,
        execution_baseline=BASE,NEXT='STOP_WAIT_R24R1_INDEPENDENT_EXTERNAL_AUDIT')
    reports={
        'FORWARD_INPUT_AUTHORITY_GATE':dict(contract=ref('config/v4_16_go_forward_input_authority_v1.json'),dependencies=ref('config/v4_16_runtime_dependencies_v3.json'),
            immutable_algorithm_layer=True,exact_daily_layer=True,historical_data_head_role='IMMUTABLE_HISTORICAL_ACCEPTANCE'),
        'FUTURE_SESSION_REACHABILITY_GATE':dict(x,database_binding=ref(context['database']),manifest_binding=ref(context['manifest'])),
        'DAILY_INPUT_NEGATIVE_MATRIX':dict(count=len(f),cases=f),
        'COHORT_IDENTITY_GATE':dict(contract=ref('config/v4_15_cohort_contract_v1.json'),cases=c,formula='SHA256(canonical([logical_event_id, cohort_namespace]))',oracle=oracle),
        'REALTIME_ADMISSION_GATE':dict(contract=ref('config/v4_16_realtime_admission_contract_v1.json'),cases=s,owner_projection_role='CANDIDATE_ENROLLMENT_TEMPLATE / NOT_COHORT_ACCEPTANCE',
            accepted_slot_and_exact_owner_event_required=True,publication_transaction_atomic=True),
        'INDEPENDENT_R24R1_ORACLE':dict(oracle=oracle,context=context,validator=ref('scripts/validate_r24r1_activation.py'),writer_imported=False,
            checks=['daily_head_digest','exact_target_previous_session','source_max_date','internal_receipts','18_field_slot','source_manifest','owner_event','cohort_key','publication_CAS','schema','storage_origin']),
        'A01_A20_REGRESSION':dict(count=len(a),cases=a),
        'PROTECTED_BYTES':dict(before=before,after=after,unchanged=True,disabled_authority=protected()),
    }
    for name,payload in reports.items():atomic('reports/r24r1/'+name+'.json',dict(common,**payload))
    atomic('reports/r24r1/STAGE_CONTRACT_AND_AUDIT_ITEMS.json',dict(common,
        stage_contract=ref('config/v4_16_runtime_dependencies_v3.json'),
        task=ref('docs/evidence/r24r1/V4_16_R24R1_GO_FORWARD_INPUT_AUTHORITY_AND_COHORT_IDENTITY_REPAIR_TASK_20261004.md'),
        latest_upgrade_document=ref('docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'),
        acceptance='PASS_LOCAL_PENDING_CLEAN_REGRESSION_AND_EXTERNAL_AUDIT',
        separate_audit_items=[dict(id=i,scope=scope,acceptance='CLOSED_LOCAL_PENDING_EXTERNAL_AUDIT',evidence=ref('reports/r24r1/'+e+'.json')) for i,scope,e in [
            ('R24_P0_FORWARD_AUTHORITY','Future-session input authority independent of frozen historical Data head','FORWARD_INPUT_AUTHORITY_GATE'),
            ('R24_P0_COHORT_IDENTITY','Persisted COHORT_V1 key identity and original uniqueness','COHORT_IDENTITY_GATE'),
            ('R24_P1_REALTIME_ADMISSION','Candidate template versus slot-backed acceptance','REALTIME_ADMISSION_GATE')]]))
    print(dict(status='PASS_LOCAL',future_session=context['request']['trade_date'],daily_cases=len(f),identity_cases=len(c),admission_cases=len(s),a20=len(a)),flush=True)

if __name__=='__main__':run()
