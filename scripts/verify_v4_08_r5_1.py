"""Reproducible R5.1 targeted engineering evidence, TEST_ONLY fixtures."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'src')]
from build_v4_08_r2_membership_evidence import atomic_json
from scan_no_symbol_specific_runtime_logic import run


def read(path):return json.loads((ROOT/path).read_text(encoding='utf8'))
def bind(path):return dict(path=path,sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest())
def report(name,value):atomic_json(ROOT/f'reports/v4_08/V4_08_R5_1_{name}.json',value)


def compact_scan(scan):
    """Keep SHA-bound per-file receipts and hard-gate findings, omit duplicates."""
    result={k:v for k,v in scan.items() if k not in {'all_symbol_literals','results'}}
    result['allowed_literal_inventory_count']=len(scan['all_symbol_literals'])
    result['allowed_literal_inventory_digest']=hashlib.sha256(json.dumps(scan['all_symbol_literals'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    result['hard_gate_results']=[r for r in scan['results'] if r.get('category') in {'PRODUCTION_RUNTIME','SYSTEM_PIPELINE','GOVERNANCE_MUTATION','RUNTIME_CONFIGURATION'} and r.get('hits')]
    for key in ('allowed_evidence_test_user_fact_reference_hits','audit_only_hits'):
        inventory=result[key]
        result[key]={k:v for k,v in inventory.items() if k!='indexes'}
        result[key]['encoding']='count; full inventory bound by allowed_literal_inventory_digest'
    return result


def main(*, scan_governance=True):
    with tempfile.TemporaryDirectory(prefix='v4_08_r5_1_test_only_') as temp:
        junit=Path(temp)/'tests.xml'
        result=subprocess.run([sys.executable,'-m','pytest','-q','tests/v4_08/test_r5_1_accepted_adapter.py','tests/v4_08/test_r5_runtime.py',f'--junitxml={junit}'],cwd=ROOT,capture_output=True,text=True,encoding='utf8')
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
        cases=[dict(name=n.attrib['name'],status='PASS' if not list(n) else 'FAIL') for n in ET.parse(junit).getroot().iter('testcase')]
        if any(c['status']!='PASS' for c in cases):raise RuntimeError('TARGETED_TEST_NOT_PASS')
    ast=read('config/v4_08_b2_machine_ast_r5.json')
    from sector.machine_ast_r3 import ast_digest
    for dependency in ast['semantic_dependencies']:
        if bind(dependency['path'])['sha256']!=dependency['sha256']:raise RuntimeError('SEMANTIC_DEPENDENCY_CHANGED')
    common=dict(status='PASS',contract='V4_08_R5_1_THREE_BLOCKER_TARGETED_REPAIR',test_only_fixture=True,fixture_entered_formal_head=False,adapter=bind('src/sector/accepted_input_r5_1.py'),test_source=bind('tests/v4_08/test_r5_1_accepted_adapter.py'))
    groups={
        'B2_RANK_UNIVERSE_PARITY':'test_actual_legacy_current_function_against_pit_adapter',
        'B2_LEGACY_MIXED_SEMANTIC_GOLDEN':'test_actual_legacy_current_function_against_pit_adapter',
        'CONCENTRATION_INTEGRATION':('test_raw_amount_adapter_concentration','test_target_date_mismatch_unknown','test_future_source_rejected','test_digest_mismatch_rejected','test_missing_source_payload_degrades_unknown'),
        'ROTATION_PRICE_PATH_INTEGRATION':('test_price_basis_pulse_adapter','test_future_adjustment_revision_rejected','test_target_date_mismatch_unknown','test_price_logical_digest_mismatch_rejected','test_missing_source_payload_degrades_unknown'),
        'FEEDBACK_ISOLATION':'test_b2_feedback_isolation'}
    for name,prefix in groups.items():
        report(name,{**common,'test_cases':[c for c in cases if c['name'].startswith(prefix)]})
    report('ACCEPTED_INPUT_ADAPTER_INTEGRATION',{**common,'test_count':len(cases),'cases':cases,'route':'accepted heads + SHA-bound canonical artifacts -> load_accepted_current -> current -> Native / B0 / Rotation / B2','unknown_semantic_provenance_is_distinct_from_explicit_unknown_tag':True})
    report('B2_SEMANTIC_PROVENANCE',dict(status='PASS',contract_id='V4_08_B2_SEMANTIC_MAPPING_R5_1',dependencies=ast['semantic_dependencies'],semantic_dependency_digest=ast['semantic_dependency_digest'],adapter_model_digest=ast['adapter_model_digest'],sector_valid_producer='src/sector/phase2.py:prepare -> sectors -> validity',exact_inputs=['identity valid_member regex','missing_state present','not FILE_MISSING/DELISTED_OR_INACTIVE','distinct member count','sector role'],mapping='Accepted exact legacy_valid_member producer observations -> same validity rule; absent producer observations -> UNKNOWN. EXCLUDED_ROLE proves sector_valid false independently.',pit_membership_implies_legacy_valid_true=False,unknown_rank_pool='If any eligibility is unknown, entire affected type rank pool remains UNKNOWN',semantic_registry='Exact legacy resolve_semantics(record), no new override behavior'))
    candidate=read('reports/v4_08/V4_08_R5_STAGE_CANDIDATE_MANIFEST.json')
    binding=candidate['input_bindings']['canonical_input_binding']
    report('RAW_AMOUNT_INPUT_BINDING',dict(status='PASS_ACCEPTED_AUTHORITY_WIRED_TARGET_SOURCE_UNAVAILABLE',**binding,amount_field='canonical_daily.amount',amount_unit='CNY',amount_ratio20_substituted=False,missing_coerced_to_zero=False,date_mismatch='UNKNOWN',future_source='REJECT',digest_mismatch='REJECT'))
    report('PRICE_BASIS_INPUT_BINDING',dict(status='PASS_ACCEPTED_AUTHORITY_WIRED_TARGET_SOURCE_UNAVAILABLE',**binding,close_authority='price_artifact.qfq_ohlc[3]',price_basis_id='coordinate_basis:adjustment_snapshot_id',revision_authority='adjustment_snapshot_digest',cross_day='exact per-member identity equality',corporate_action_transition='UNKNOWN; no accepted affine conversion contract applied',synthetic_constant_used_in_production=False))
    governance=run(ROOT) if scan_governance else None
    if governance is not None:
        report('NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN',compact_scan(governance))
        if governance['status']!='PASS':raise RuntimeError('NO_SYMBOL_GATE_FAILED')
    report('STAGE_CANDIDATE_MANIFEST',dict(status='R5_1_ENGINEERING_CANDIDATE_PENDING_CLEAN_VERIFICATION',artifacts=candidate['artifacts'],input_bindings=candidate['input_bindings'],b2_adapter_model_digest=ast['adapter_model_digest'],parameter_sha256=bind('config/v4_08_algorithm_parameter_set_r5.json')['sha256'],final_v4_08_accepted_head_written=False,production_permission=False,next_stage='INDEPENDENT_EXTERNAL_REAUDIT',independent_open_audits=['Prior-RPS','AUD-AMOUNT-A-06','target accepted Core availability','V4-01 dated roster']))
    print(json.dumps(dict(status='PASS',targeted_tests=len(cases),no_symbol_scan=governance['status'] if governance is not None else 'NOT_EXECUTED_TARGETED_ONLY')))


if __name__=='__main__':main(scan_governance='--targeted-only' not in sys.argv)
