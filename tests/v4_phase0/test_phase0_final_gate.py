import json
from pathlib import Path

from v4.contracts.phase0_gate import STAGES, evaluate_phase0

ROOT=Path(__file__).resolve().parents[2]


def test_v4_01_does_not_require_v4_01_02_implementation_or_scanner():
    passed=evaluate_phase0({stage:"FULL_PASS" for stage in STAGES},[])
    assert passed["phase0_status"]=="FULL_PASS"
    assert passed["v4_01_entry_permission"]=="AUTHORIZED"
    assert passed["scanner_permission"]=="NOT_APPLICABLE_UNTIL_V4_05"


def test_core_blocker_blocks_entry_but_scanner_remains_stage_scoped():
    blocked=evaluate_phase0({stage:"FULL_PASS" for stage in STAGES},["A_STOCK_SOURCE_UNACCEPTED"])
    assert blocked["phase0_status"]=="BLOCKED"
    assert blocked["v4_01_entry_permission"]=="BLOCKED"
    assert blocked["scanner_permission"]=="NOT_APPLICABLE_UNTIL_V4_05"


def test_optional_scope_gaps_are_not_core_blockers():
    passed=evaluate_phase0({stage:"DEGRADED_PASS" for stage in STAGES},[])
    assert passed["phase0_status"]=="FULL_PASS"
    assert passed["supplemental_permission"]=="OPTIONAL"


def test_frozen_cutover_policy_has_split_permissions_and_future_performance_gate():
    policy=json.loads((ROOT/"config/v4_capability_cutover_policy_v1.json").read_text("utf-8"))
    assert policy["phase0"]["status"]=="FULL_PASS"
    assert policy["phase0"]["v4_01_entry_permission"]=="AUTHORIZED"
    assert policy["phase0"]["raw_bootstrap_permission"]=="AUTHORIZED"
    assert policy["phase0"]["scanner_permission"]=="NOT_APPLICABLE_UNTIL_V4_05"
    assert policy["phase0"]["production_cutover_permission"]=="NOT_APPLICABLE_UNTIL_LATER_GATES"
    perf=json.loads((ROOT/"config/v4_performance_measurement_contract_v1.json").read_text("utf-8"))
    assert {"wall_time","peak_ram","cpu_utilization","stage_time","rows_in","rows_out","postgres_write_time","api_p50","api_p95","payload_size","db_growth","cache_state","hardware_identity","dataset_identity"} <= set(perf["fields"])
