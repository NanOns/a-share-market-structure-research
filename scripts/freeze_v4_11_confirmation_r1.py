"""Extract exact legacy AST and parameters; record candidate-only D0 obligations."""
import ast,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.next_round_bundle_r1 import bind,read,write,verify_protected,DOCROOT,digest
from workbench_analysis.today_research_scanner_v3_3 import PARAMETER_CONTRACT,SCENARIOS
def freeze():
    verify_protected();entry=read('config/v4_11_entry_contracts_r1.json');src=entry['legacy_inventory']['source']
    text=(ROOT/src['path']).read_text(encoding='utf8');tree=ast.parse(text)
    functions={n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
    row_fields=sorted({n.args[0].value for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='row' and n.func.attr=='get' and n.args and isinstance(n.args[0],ast.Constant)}-{ 'security_id','trade_date'})
    row_fields=sorted(set(row_fields)|{n.args[1].value for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='_cmp' and len(n.args)>1 and isinstance(n.args[1],ast.Constant)})
    numeric={'break_margin_close20','ret1_adj','clv','amr20_mean_prior','prior5_below_ma20_count','rps5_delta3','close_to_ma20','close_to_ma5','ma5_to_ma20','slope20','rps20'}
    units={f:('fraction' if f in numeric else 'boolean') for f in row_fields};units['prior5_below_ma20_count']='market_session_count'
    roles={f:'TARGET_SESSION_D0' for f in row_fields}
    for field in ('amr20_mean_prior','prior5_below_ma20_count'):roles[field]='PRIOR_SESSION_WINDOW'
    roles['current_with_loo_breadth_support']='SAME_DAY_DOWNSTREAM'
    mapping=dict(LAUNCH='LAUNCH_CONFIRM',PULLBACK='STRONG_PULLBACK',RECOVERY_TURN='RECOVERY_TURN',TREND_CONTINUE='TREND_CONTINUE')
    manifest=dict(contract_id='LEGACY_ADAPTER_V1',legacy_source=src,exact_function_AST=functions,
        exact_function_source={n.name:ast.get_source_segment(text,n) for n in tree.body if isinstance(n,ast.FunctionDef)},
        branch_AST={n.targets[0].id:ast.dump(n,include_attributes=False) for n in ast.walk(tree) if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('common','safety','base','launch_checks','pullback_checks','r5','r20','recovery_checks','continue_stock_checks')},
        call_graph=entry['legacy_inventory']['call_graph'],scenario_mapping=mapping,source_scenario_order=list(SCENARIOS),
        input_fields=row_fields,input_units=units,input_time_roles=roles,
        legacy_UNKNOWN_semantics='EXACT tri_and known FALSE dominant; tri_or known TRUE dominant; unknown_checks always retained',
        governance_UNKNOWN_semantics='Required unavailable/unaccepted/conflicting/future facts => scenario UNKNOWN; no FALSE/0 fallback',
        output_semantics='One canonical fact row per security/publication; all matches retained; first frozen legacy scenario primary',
        forbidden_internal_dependencies=[],diagnostic_dependencies={'TREND_CONTINUE':['CURRENT_WITH_LOO_BREADTH_SUPPORT:SAME_DAY_DOWNSTREAM']},
        extraction_acceptance='CANDIDATE_ONLY_NOT_EXTERNAL_ACCEPTED')
    manifest_ref=write('config/v4_11_legacy_extraction_manifest_r1.json',manifest)
    param=write('config/v4_11_confirmation_parameter_set_v1.json',dict(parameter_set_id='V4_11_CONFIRMATION_PARAMETER_SET_V1',legacy_source=src,values=PARAMETER_CONTRACT,threshold_origin='EXACT_FROZEN_LEGACY_SOURCE_AST',status='CANDIDATE'))
    machine=write('config/v4_11_confirmation_machine_ast_v1.json',dict(contract_id='V4_11_CONFIRMATION_MACHINE_AST_V1',legacy_manifest=manifest_ref,
        scenario_priority=[mapping[s] for s in SCENARIOS],scenario_combination='KNOWN_TRUE_OR_ELSE_UNKNOWN_OR_ELSE_FALSE',
        event_priority=entry['events']['values'],amount_dependent_branches=['LAUNCH_CONFIRM','RECOVERY_TURN','TREND_CONTINUE'],
        amount_A_gate='DISABLED_UNTIL_NEXT_INDEPENDENT_EXTERNAL_ACCEPTANCE',security_dedup_key=['publication_id','security_id']))
    contract=dict(contract_id='CONFIRMATION_DETECTOR_V1',version='1.0.0',status='CANDIDATE_IMPLEMENTATION',
        stage_contract=bind(DOCROOT+'V4_11_CONFIRMATION_EVENTS_IMPLEMENTATION_TASK_R1_20261001.md'),
        entry_contract=bind('config/v4_11_entry_contracts_r1.json'),legacy_manifest=manifest_ref,parameters=param,machine_ast=machine,
        v4_10_head=bind('data/v4/V4_10_ACCEPTED_HEAD.json'),accepted_data_head=bind('data/v4/V4_DATA_ACCEPTED_HEAD.json'),executable_authority=entry['authority'],
        input_producer_contract_id='V4_11_ACCEPTED_SOURCE_PROJECTION_V1',input_parameter_set_id='V4_11_INPUT_PROJECTION_PARAMETERS_V1',
        amount_A=dict(audit_id='AUD-AMOUNT-A-06',formal_branch='DISABLED',candidate_A04_does_not_authorize=True),
        candidate_confirmation_not_accepted_by_D2=True,D0_writes_final_state=False,full_DAG_external_acceptance=False,
        target_data_cutoff='Accepted target trade date; no future trade_date',knowledge_cutoff='Actual run timestamp; reconstructed source availability must precede this cutoff',
        AS_RECORDED=False,permissions=dict(production=False,shadow=False,focus=False),migration_allocation=read('config/v4_migration_allocation_registry_r2.json')['allocations'][0],
        final_state_adapter_scope='ACCEPTED_REDUCER_SYNTHETIC_ENGINEERING_VECTORS_ONLY_UNTIL_V4_11_EXTERNAL_ACCEPTANCE')
    return write('config/v4_11_confirmation_detector_contract_r1.json',contract)
if __name__=='__main__':print(json.dumps(freeze()))
