"""Record gated design obligations; deliberately exports no V4-11 detector/event runtime."""
import ast
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_v4_08_r2_membership_evidence import atomic_json,atomic_bytes
from scripts.validate_v4_10_promotion_r1 import validate,read,bind,HEAD,GLOBAL

def enter():
    if validate()['status']!='PASS' or not (ROOT/HEAD).exists(): raise ValueError('PROMOTION_PASS_REQUIRED')
    source='src/workbench_analysis/today_research_scanner_v3_3.py'
    tree=ast.parse((ROOT/source).read_text(encoding='utf8'))
    symbols=[n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))]
    calls=sorted({ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n,ast.Call)})
    vectors=['NONE_TO_CONFIRMED','SEED_TO_CONFIRMED','PREWATCH_TO_CONFIRMED','PERSISTENT_CONFIRMED',
        'SAME_DAY_R1_R2_R3_NEW_CONFIRMED','RECONFIRMED','SCENARIO_UPGRADED','SCENARIO_CHANGED_NOT_UPGRADED',
        'CONFIRMATION_WEAKENED','HARD_INVALIDATION_WINS','REQUIRED_FACT_UNKNOWN','AMOUNT_A_DISABLED',
        'MULTI_SCENARIO_DEDUP','PRODUCER_MISMATCH','PARAMETER_MISMATCH','PUBLICATION_MISMATCH',
        'FUTURE_TIMESTAMP_REJECTED','SAME_DAY_FEEDBACK_REJECTED','NO_SYMBOL']
    fields=['security_id','trade_date','confirmation_status','matched_scenarios','primary_scenario',
        'scenario_evidence','raw_predicates','unknown_predicates','producer_contract_id','parameter_set_id',
        'source_publication_ids','input_digest']
    contracts=dict(contract_id='V4_11_CONFIRMATION_EVENTS_ENTRY_CONTRACT_R1',version='1.0.0',
        status='ENTRY_DESIGN_OBLIGATIONS_FROZEN_RUNTIME_NOT_IMPLEMENTED',
        authority=bind('docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'),
        task=bind('docs/evidence/V4_10_ACCEPTED_HEAD_PROMOTION_AND_V4_11_ENTRY_TASK_20261001.md'),
        registered_contracts=['LEGACY_ADAPTER_V1','CONFIRMATION_DETECTOR_V1','STATE_EVENT_V1'],
        scenarios=['LAUNCH_CONFIRM','RECOVERY_TURN','STRONG_PULLBACK','TREND_CONTINUE'],
        legacy_inventory=dict(source=bind(source),symbols=symbols,call_graph=calls,
            parameter_source='DEFAULT_POLICY and branch-specific checks in the bound source',
            extraction_status='INVENTORIED_NOT_EXTRACTED_NOT_ACCEPTED',
            required_extraction=['exact_branch_AST','parameters','input_units','input_time_roles','output_semantics','UNKNOWN_semantics'],
            forbidden_dependencies=['Final State','Focus','same-day downstream','online supplemental','future outcome'],
            until_extraction_accepted='DIAGNOSTIC_ONLY'),
        field_registry={k:dict(owner='V4-11',time_role='TARGET_SESSION_D0',status='DESIGN_REGISTERED') for k in fields},
        producer_identity=dict(contract_id='CONFIRMATION_DETECTOR_V1',status='NOT_IMPLEMENTED_NOT_PUBLISHED'),
        parameter_set=dict(id='V4_11_CONFIRMATION_PARAMETER_SET_V1',status='PENDING_EXACT_LEGACY_EXTRACTION'),
        machine_AST=dict(id='V4_11_CONFIRMATION_MACHINE_AST_V1',status='PENDING_EXACT_LEGACY_EXTRACTION'),
        golden_vectors=dict(id='V4_11_INDEPENDENT_GOLDEN_VECTORS_V1',coverage_required=vectors,status='INVENTORY_ONLY_NO_EXPECTATIONS_OR_RUN'),
        unknown_semantics='Required missing, unavailable, conflicting or unaccepted facts remain UNKNOWN; no 0/FALSE fallback',
        amount_A=dict(audit_id='AUD-AMOUNT-A-06',status='OPEN',formal_branch='DISABLED',diagnostic='UNKNOWN',staging_read=False),
        input_publication_contract=dict(required=['accepted_data_head','producer_contract_id','parameter_set_id',
            'source_publication_ids','input_digest','cutoff_timestamp'],future_or_feedback='REJECT',
            target_data_requires_actual_accepted_data_head=True),
        output_schema=dict(id='CONFIRMATION_FACT_V1',required_fields=fields,canonical_key=['publication_id','security_id'],
            cardinality='ONE_ROW_PER_KEY',D0_modifies_Final_State=False,consumer='ACCEPTED_V4_10_D2_REDUCER'),
        events=dict(contract_id='STATE_EVENT_V1',after='D2 final state',predecessor='frozen prior_session_state_head',
            forbidden_predecessor='same_day_revision_parent',same_day_first_confirmation='NEW_CONFIRMED for r1/r2/r3',
            values=['FIRST_OBSERVED','CONFIRMATION_INVALIDATED','RECONFIRMED','NEW_CONFIRMED','SCENARIO_UPGRADED',
                    'CONFIRMATION_WEAKENED','PERSISTENT_CONFIRMED','SCENARIO_CHANGED','NONE']),
        migration_governance=dict(registry='config/v4_migration_allocation_registry_r1.json',
            allocate_before_schema_work=True,historical_migrations_immutable=True),
        implementation_gate='STOP_PENDING_NEXT_INDEPENDENT_AUDIT',production_permission=False,
        shadow_production_permission=False,focus_cutover_permission=False)
    atomic_json(ROOT/'config/v4_11_entry_contracts_r1.json',contracts)
    migrations=[bind(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT/'src/workbench_db/migrations/v4_postgres').glob('*.sql'))]
    atomic_json(ROOT/'config/v4_migration_allocation_registry_r1.json',dict(contract_id='V4_MIGRATION_ALLOCATION_REGISTRY_R1',
        historical_bindings=migrations,next_free_number=25,allocations=[],pending_requestors=['V4-11','WP-A09-V4-09-N02'],
        rule='One serialized registry allocation per number before writing any new migration; no allocation authorized in entry stage'))
    entry=dict(contract_id='V4_11_STAGE_ENTRY_R1',status='AUTHORIZED',v4_10_accepted_head=bind(HEAD),global_stage_head=bind(GLOBAL),
        contract_freeze=bind('config/v4_11_entry_contracts_r1.json'),migration_registry=bind('config/v4_migration_allocation_registry_r1.json'),
        external_acceptance='NOT_ACCEPTED_ENTRY_ONLY',algorithm_implemented=False,full_DAG_accepted=False,
        next_stage='STOP_WAIT_FOR_INDEPENDENT_ENTRY_AUDIT_BEFORE_V4_11_IMPLEMENTATION')
    atomic_json(ROOT/'reports/v4_11/V4_11_CONFIRMATION_EVENTS_STAGE_ENTRY_R1.json',entry)
    atomic_bytes(ROOT/'reports/v4_joint/V4_10_PROMOTION_AND_V4_11_ENTRY_CLOSURE_R1.md',(
        '# V4-10 promotion / V4-11 entry\n\nV4_10_ACCEPTED_HEAD_PROMOTION = PASS\n\n'
        'V4_11_CONFIRMATION_EVENTS_ENTRY = AUTHORIZED\n\n'
        'R1.2 engineering interface/authority/persistence only. All 25 promotion gates pass. '
        'V4-09 retained, A01–A09 OPEN, Data/Dev/PIT Membership heads unchanged; all permissions false.\n\n'
        'V4-11 source inventory and design obligations registered; exact legacy AST/parameter extraction and '
        'independent goldens remain gated implementation work. STOP pending independent entry audit.\n').encode('utf8'))
    return entry

if __name__=='__main__':
    import json
    print(json.dumps(enter()))
