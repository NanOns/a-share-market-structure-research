"""R5.2 source decision and context engineering evidence; no head promotion."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]
from build_v4_08_r2_membership_evidence import atomic_json
from sector.accepted_context_r5_2 import resolve_daily_context,static_engineering_context
from sector.accepted_input_r5_1 import load_accepted_current
from scan_no_symbol_specific_runtime_logic import run
from verify_v4_08_r5_1 import compact_scan


def read(path):return json.loads((ROOT/path).read_text(encoding='utf8'))
def bind(path):return dict(path=path,sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest())
def report(name,value):atomic_json(ROOT/f'reports/v4_08/V4_08_R5_2_{name}.json',value)


def main(scan_governance=True):
    with tempfile.TemporaryDirectory(prefix='v4_08_r5_2_test_only_') as temp:
        junit=Path(temp)/'tests.xml'
        command=[sys.executable,'-m','pytest','-q','tests/v4_08/test_r5_2_context_authority.py','tests/v4_08/test_r5_1_accepted_adapter.py','tests/v4_08/test_r5_runtime.py',f'--junitxml={junit}']
        proc=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf8')
        if proc.returncode:raise RuntimeError(proc.stdout+proc.stderr)
        cases=[dict(name=n.attrib['name'],status='PASS' if not list(n) else 'FAIL') for n in ET.parse(junit).getroot().iter('testcase')]
        if any(c['status']!='PASS' for c in cases):raise RuntimeError('TARGETED_CONTEXT_TEST_FAILED')
    contract=read('config/v4_08_accepted_context_contract_r5_2.json')
    common=dict(status='PASS',test_only=True,fixture_entered_formal_head=False,test_source=bind('tests/v4_08/test_r5_2_context_authority.py'),adapter=bind('src/sector/accepted_input_r5_1.py'),resolver=bind('src/sector/accepted_context_r5_2.py'))
    report('ACCEPTED_CONTEXT_CONTRACT',dict(**common,contract=contract,contract_binding=bind('config/v4_08_accepted_context_contract_r5_2.json'),test_count=len(cases),cases=cases))
    report('MULTI_CONTEXT_GENERALIZATION',dict(**common,cases=[c for c in cases if c['name'].startswith(('test_multi_context','test_context_negative','test_blocked_component'))],same_source=True,static_v4_02_heads_written=False,bindings_change=['target','artifact path','SHA','amount','price snapshot']))
    report('FROZEN_CONTEXT_IMMUTABILITY',dict(**common,cases=[c for c in cases if c['name'].startswith('test_frozen_t')],frozen_t_result_unchanged=True,frozen_t_digest_unchanged=True,t_can_be_replayed=True))
    target='2026-09-30';context=resolve_daily_context(ROOT,target=target)
    current,binding=load_accepted_current(ROOT,read('data/v4/V4_05_ACCEPTED_HEAD.json'),target=target,cutoff=target+'T23:59:59+08:00',accepted_input_context=context)
    assert binding['availability']=='TARGET_ACCEPTED_DATA_UNAVAILABLE' and not current
    report('DAILY_HEAD_ROUTING',dict(**common,cases=[c for c in cases if c['name'].startswith(('test_daily_','test_context_negative'))],real_context=context,real_binding=binding,real_target_core_count=len(current),static_fallback_used=False,static_replay_context=static_engineering_context(ROOT),route='V4_DATA_ACCEPTED_HEAD -> immutable manifest.accepted_input_context',fourth_daily_authority_created=False))
    import pyarrow.parquet as pq
    daily='data/v4/artifact_store/v4_02/V4_02_ADJUSTED_CANONICAL_DAILY_R7_20260927.parquet'
    daily_schema=pq.ParquetFile(ROOT/daily).schema.names
    core_head=read('data/v4/V4_05_ACCEPTED_HEAD.json')
    factor_keys=set();factor_fields=set();profile_keys=set();injected_rows=0;count=0
    with gzip.open(ROOT/core_head['accepted_artifacts']['full_scope_factors']['path'],'rt',encoding='utf8') as stream:
        for line in stream:
            row=json.loads(line);count+=1;factor_keys.update(row);factor_fields.update(row['fields']);injected_rows+=int('legacy_valid_member' in row)
    with gzip.open(ROOT/core_head['accepted_artifact']['path'],'rt',encoding='utf8') as stream:
        for line in stream:profile_keys.update(json.loads(line))
    status_path='data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R7_20260927.jsonl.gz'
    with gzip.open(ROOT/status_path,'rt',encoding='utf8') as stream:status_fields=sorted(json.loads(next(stream)))
    assert 'missing_state' not in factor_keys|factor_fields|profile_keys|set(daily_schema)|set(status_fields) and injected_rows==0
    report('LEGACY_VALID_MEMBER_SOURCE_DECISION',dict(status='OPTION_B_CAPABILITY_DOWNGRADE',decision='B',exact_producer=bind('src/sector/phase2.py'),legacy_rule='security_id regex AND missing_state known AND not FILE_MISSING/DELISTED_OR_INACTIVE; then validity(total,valid,role)',
        accepted_source_inventory=dict(core_head=bind('data/v4/V4_05_ACCEPTED_HEAD.json'),full_scope_factors=core_head['accepted_artifacts']['full_scope_factors'],factor_row_count=count,factor_keys=sorted(factor_keys),factor_fields=sorted(factor_fields),legacy_valid_member_rows=injected_rows,profile_keys=sorted(profile_keys),canonical_daily=bind(daily),canonical_daily_schema=daily_schema,trading_status=bind(status_path),trading_status_fields=status_fields),
        missing_authority='No accepted exact missing_state producer or accepted equivalence mapping; trading_status/bar/universe/membership cannot substitute',producer_implemented=False,factor_48_added=False,synthetic_final_boolean_used_to_enable=False,independent_capabilities_preserved=['Sector Native','B0','B1 Rotation'],engineering_scope_excludes=['legacy B2 confirmed','legacy B2 warm']))
    report('B2_CAPABILITY_DOWNGRADE',dict(**common,decision='B',cases=[c for c in cases if c['name'].startswith(('test_b05_','test_semantic_mapping_formal'))],B2_NON_AMOUNT_A='NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE',B2_AMOUNT_A='DIAGNOSTIC_AUDIT_OPEN',confirmed_raw='UNKNOWN',warm_raw='UNKNOWN',confirmed_diagnostic='PURE_ALGORITHM_ONLY_NO_FORMAL_PERMISSION',ENABLED_ENGINEERING_claim_removed=True))
    manifest=read('reports/v4_08/V4_08_R5_STAGE_CANDIDATE_MANIFEST.json')
    report('STAGE_CANDIDATE_MANIFEST',dict(status='R5_2_CANDIDATE_PENDING_CLEAN_VERIFICATION',artifacts=manifest['artifacts'],input_bindings=manifest['input_bindings'],capabilities=manifest['capabilities'],b05_decision='B',engineering_scope_excludes=['legacy B2 confirmed','legacy B2 warm'],target_trade_date=target,next_stage='INDEPENDENT_EXTERNAL_REAUDIT',production_permission=False,final_v4_08_accepted_head_written=False,global_stage_range='V4_00_TO_V4_07_ACCEPTED',protected_head_bindings=[bind(p) for p in ['data/v4/V4_STAGE_ACCEPTED_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json','data/v4/V4_DEV_BASELINE_HEAD.json','data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json']]))
    if scan_governance:
        governance=run(ROOT);report('NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN',compact_scan(governance))
        if governance['status']!='PASS':raise RuntimeError('NO_SYMBOL_GATE_FAILED')
    print(json.dumps(dict(status='PASS_TARGETED',tests=len(cases),B05='OPTION_B',real_context_availability=binding['availability'])))


if __name__=='__main__':main(scan_governance='--targeted-only' not in sys.argv)
