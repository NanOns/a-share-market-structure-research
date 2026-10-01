"""Versioned candidate contract supersedes the missing-adapter assessment without editing its history."""
import ast
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts.build_v4_08_r2_membership_evidence import atomic_json,atomic_bytes
from workbench_analysis.daily_data_head import CAPABILITIES

def bind(p):
    b=(ROOT/p).read_bytes();return dict(path=p,sha256=hashlib.sha256(b).hexdigest(),byte_count=len(b))

def freeze():
    previous=json.loads((ROOT/'config/v4_dm01_accepted_builder_registry_v1.json').read_text(encoding='utf8'))
    exports={cap:'build_'+cap.lower() for cap in CAPABILITIES}
    module='src/workbench_analysis/dm01_incremental_component_builders.py'
    tree=ast.parse((ROOT/module).read_text(encoding='utf8'))
    functions={n.name:[a.arg for a in n.args.args] for n in tree.body if isinstance(n,ast.FunctionDef)}
    signature=['target_trade_date','parent_data_head','source_freeze','calendar_binding','identity_binding','staging_root']
    assert all(functions[name]==signature for name in exports.values())
    original=[]
    for entry in previous['capabilities'].values():
        for ref in entry['accepted_runtime']:
            assert bind(ref['path'])['sha256']==ref['sha256'],ref['path']
            if ref not in original:original.append(ref)
    extra=['scripts/build_v4_02_price_limits.py','src/workbench_analysis/limit_rules.py',
           'src/workbench_analysis/price_reference_state.py','src/workbench_analysis/v4_02_closure.py',
           'src/workbench_analysis/dm01_extracted_domain_r1.py',module,
           'src/workbench_analysis/dm01_independent_postcheck_r1.py','src/workbench_analysis/dm01_candidate_orchestrator_r1.py',
           'src/workbench_analysis/dm01_accepted_builder_registry.py','scripts/run_dm01_a01_next_session_r1.py']
    runtimes=[*original,*[bind(p) for p in extra]]
    extraction=json.loads((ROOT/'config/dm01_domain_extraction_r1.json').read_text(encoding='utf8'))
    assert all(bind(r['path'])['sha256']==r['sha256'] for r in extraction['sources'])
    manifest=json.loads((ROOT/'reports/v4_02/V4_02_FINAL_STAGING_MANIFEST_R6.json').read_text(encoding='utf8'))['components']
    contract=dict(contract_id='DM01_A01_INCREMENTAL_BUILDERS_R1',version='1.0.0',
        status='ENGINEERING_IMPLEMENTATION_CANDIDATE_EXTERNAL_ACCEPTANCE_PENDING',
        task=bind('docs/evidence/WP_A01_DM01_INCREMENTAL_BUILDERS_IMPLEMENTATION_TASK_R1_20261001.md'),
        supersedes_assessment=bind('config/v4_dm01_accepted_builder_registry_v1.json'),
        runtime_adapter_module='workbench_analysis.dm01_incremental_component_builders',runtime_bindings=runtimes,
        accepted_stage_bindings=previous['stage_acceptance_bindings'],domain_extraction=bind('config/dm01_domain_extraction_r1.json'),
        accepted_phase_bindings={k:bind(manifest[n]['path']) for k,n in [('event_store','R6_EVENTS'),('policy','R6_POLICY'),('rules','STANDARD_RULES')]},
        accepted_calendar_head=bind('data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_ACCEPTED_HEAD_R1.json'),
        gbbq_classification_binding=bind('config/v4_02_gbbq_price_impact_classification_v1.json'),
        accepted_identity_bindings=[bind('data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json'),
            bind('data/v4/artifact_store/v4_01/security_entity_map_GO_FORWARD_20260930_ACCEPTED_R1.json')],
        stage_entry_protected_heads=[bind(p) for p in ['data/v4/V4_DATA_ACCEPTED_HEAD.json','data/v4/V4_STAGE_ACCEPTED_HEAD.json',
            'data/v4/V4_DEV_BASELINE_HEAD.json','data/v4/V4_09_ACCEPTED_HEAD.json','data/v4/V4_10_ACCEPTED_HEAD.json']],
        capabilities={cap:dict(**{k:previous['capabilities'][cap][k] for k in ('owner_stage','accepted_algorithm_contract','incremental_input_contract','output_contract')},
            runtime_bindings=[*previous['capabilities'][cap]['accepted_runtime'],bind(module),bind('src/workbench_analysis/dm01_extracted_domain_r1.py')],
            builder_callable=exports[cap],signature=signature,target_date_artifact_builder_exported=True,
            unknown_policy='Explicit UNKNOWN with reason; unsupported scope never widened; no fallback 0/FALSE') for cap in CAPABILITIES},
        period_parent_protocol='DM01_PERIOD_PARENT_PLUS_TARGET_R1; frozen original digest + target facts; no hash-resume fiction',
        same_day_revision='Recompute from the SAME frozen previous-session accepted parent with revised source digest; immutable new candidate',
        candidate_namespace='STAGING_ONLY',publication='ALL_NINE_PLUS_INDEPENDENT_POSTCHECK_TO_ONE_READY_MARKER',
        data_head_promotion_permitted=False,production_permission=False,shadow_production_permission=False,focus_cutover_permission=False)
    atomic_json(ROOT/'config/dm01_incremental_builders_contract_r1.json',contract)
    atomic_json(ROOT/'reports/dm01/DM01_A01_CONTRACT_FREEZE_R1.json',dict(contract_id='DM01_A01_CONTRACT_FREEZE_R1',
        status='PASS_CONTRACT_FREEZE_ENGINEERING_SCOPE',contract=bind('config/dm01_incremental_builders_contract_r1.json'),
        task=contract['task'],protected_heads=contract['stage_entry_protected_heads'],historical_runtimes_unchanged=True,
        registry_assessment_superseded_not_rewritten=True,external_acceptance='PENDING',next_stage='NINE_ADAPTERS_TESTS_INDEPENDENT_ARTIFACT_POSTCHECK_REAL_NEXT_SESSION'))
    atomic_json(ROOT/'reports/dm01/DM01_A01_BUILDER_EXPORTS_R1.json',dict(status='PASS',exports=exports,signature=signature,
        runtime=bind(module),contract=bind('config/dm01_incremental_builders_contract_r1.json'),domain_extraction=contract['domain_extraction'],
        builder_count=9,dynamic_discovery=False,frozen_historical_CLI_invoked=False,external_acceptance='PENDING'))
    atomic_bytes(ROOT/'docs/evidence/DM01_A01_IMPLEMENTATION_STAGE_ENTRY_R1_20261001.md',(
        '# WP-A01 / DM01 implementation stage\n\nAuthorized task: WP_A01_DM01_INCREMENTAL_BUILDERS_IMPLEMENTATION_TASK_R1_20261001.md.\n\n'
        'Implement nine static target-date callable adapters; preserve pinned accepted formulas through verbatim domain extraction. '
        'Independent numeric and cross-component checks; all-or-none candidate marker; no Data/Stage/Dev head mutation.\n\n'
        'Acceptance: engineering candidate only, separate real next-session source gate and independent external reaudit. '
        'A01 remains OPEN. Next: external acceptance before Data Head promotion. V4-11 remains entry-only.\n').encode('utf8'))

if __name__=='__main__':freeze()
