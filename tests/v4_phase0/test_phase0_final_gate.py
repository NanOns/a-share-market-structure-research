import json
from pathlib import Path
import pytest

from v4.contracts.phase0_gate import STAGES, evaluate_phase0

ROOT = Path(__file__).resolve().parents[2]


def records(status):
    result = {stage: {"status": status} for stage in STAGES}
    result["V4-00B"]["allowed_capabilities"] = ["LIFECYCLE_SCHEMA"]
    result["V4-00C"]["allowed_capabilities"] = ["PUBLICATION_IDENTITY"]
    result["V4-00D"]["allowed_capabilities"] = ["A_STOCK_TDX_SOURCE"]
    result["V4-00E"]["allowed_capabilities"] = ["RAW_BOOTSTRAP"]
    return result


def test_all_full_stages_without_limits_yield_full_pass():
    result = evaluate_phase0(records("FULL_PASS"))
    assert result["phase0_status"] == "FULL_PASS"
    assert result["v4_01_entry_permission"] == "AUTHORIZED"
    assert result["scanner_permission"] == "NOT_APPLICABLE_UNTIL_V4_05"


def test_independent_degraded_scope_yields_degraded_pass_and_authorizes_raw():
    data = records("FULL_PASS")
    data["V4-00H"] = {"status": "DEGRADED_PASS", "blocked_scopes": ["MARKED_RELATIVE_BENCHMARK_CONSUMER"], "degraded_scopes": ["BENCHMARK_THRESHOLDS_UNSET"], "blocks_v4_01": False}
    result = evaluate_phase0(data, nonblocking_limitations=["marked benchmark gate unset"])
    assert result["phase0_status"] == "DEGRADED_PASS"
    assert result["v4_01_entry_permission"] == "AUTHORIZED"
    assert result["raw_bootstrap_permission"] == "AUTHORIZED"
    assert result["entry_gate"]["blocked_scopes"] == ["MARKED_RELATIVE_BENCHMARK_CONSUMER"]
    assert result["entry_gate"]["blocked_required_scopes"] == []


def test_any_degraded_stage_cannot_aggregate_to_full_pass():
    data = records("DEGRADED_PASS")
    result = evaluate_phase0(data)
    assert result["phase0_status"] == "DEGRADED_PASS"
    assert result["v4_01_entry_permission"] == "AUTHORIZED"


def test_v4_01_required_blocked_scope_blocks_entry():
    data = records("FULL_PASS")
    data["V4-00B"] = {"status": "DEGRADED_PASS", "blocked_scopes": ["LIFECYCLE_SCHEMA"], "blocks_v4_01": True}
    result = evaluate_phase0(data)
    assert result["phase0_status"] == "BLOCKED"
    assert result["v4_01_entry_permission"] == "BLOCKED"
    assert result["raw_bootstrap_permission"] == "BLOCKED"
    assert result["entry_gate"]["blocked_required_scopes"] == ["LIFECYCLE_SCHEMA"]


def test_core_blocker_blocks_entry_but_scanner_remains_stage_scoped():
    result = evaluate_phase0(records("FULL_PASS"), ["A_STOCK_SOURCE_UNACCEPTED"])
    assert result["phase0_status"] == "BLOCKED"
    assert result["v4_01_entry_permission"] == "BLOCKED"
    assert result["scanner_permission"] == "NOT_APPLICABLE_UNTIL_V4_05"


def test_missing_or_invalid_stage_is_blocked():
    data = records("FULL_PASS")
    data.pop("V4-00G")
    assert evaluate_phase0(data)["phase0_status"] == "BLOCKED"
    data["V4-00G"] = {"status": "UNKNOWN"}
    assert evaluate_phase0(data)["phase0_status"] == "BLOCKED"


def test_full_labels_without_explicit_scope_acceptance_do_not_authorize_entry():
    data = {stage: {"status": "FULL_PASS"} for stage in STAGES}
    result = evaluate_phase0(data)
    assert result["phase0_status"] == "BLOCKED"
    assert result["v4_01_entry_permission"] == "BLOCKED"


@pytest.mark.parametrize(("wrong_stage", "scope"), [
    ("V4-00F", "PUBLICATION_IDENTITY"),
    ("V4-00F", "LIFECYCLE_SCHEMA"),
    ("V4-00F", "A_STOCK_TDX_SOURCE"),
])
def test_required_scope_cannot_be_satisfied_by_unrelated_stage(wrong_stage, scope):
    data = records("FULL_PASS")
    owner = {"PUBLICATION_IDENTITY": "V4-00C", "LIFECYCLE_SCHEMA": "V4-00B", "A_STOCK_TDX_SOURCE": "V4-00D"}[scope]
    data[owner]["allowed_capabilities"] = []
    data[wrong_stage]["allowed_capabilities"] = [scope]
    result = evaluate_phase0(data)
    assert result["phase0_status"] == "BLOCKED"
    assert f"REQUIRED_SCOPE_OWNER_MISMATCH:{scope}:{wrong_stage}:EXPECTED:{owner}" in result["core_blockers"]


def test_raw_bootstrap_is_derived_and_unowned_claim_does_not_authorize():
    data = records("FULL_PASS")
    data["V4-00E"]["allowed_capabilities"] = []
    data["V4-00A"]["allowed_capabilities"] = ["RAW_BOOTSTRAP"]
    result = evaluate_phase0(data)
    assert result["phase0_status"] == "BLOCKED"
    assert result["raw_bootstrap_permission"] == "BLOCKED"
    assert result["entry_gate"]["raw_bootstrap_derivation"]["status"] == "NOT_SATISFIED"


def test_blocked_stage_never_counts_as_accepted_even_when_blocks_flag_is_false():
    data = records("FULL_PASS")
    data["V4-00F"] = {"status": "BLOCKED", "blocks_v4_01": False, "blocked_scopes": ["OPTIONAL_SUPPLEMENTAL"]}
    result = evaluate_phase0(data)
    assert result["phase0_status"] == "BLOCKED"
    assert "STAGE_BLOCKED:V4-00F" in result["core_blockers"]


def test_non_entry_blocked_capability_requires_degraded_stage():
    data = records("FULL_PASS")
    data["V4-00F"] = {"status": "FULL_PASS", "blocks_v4_01": False, "blocked_scopes": ["OPTIONAL_SUPPLEMENTAL"]}
    result = evaluate_phase0(data)
    assert result["phase0_status"] == "BLOCKED"
    assert "BLOCKED_SCOPE_REQUIRES_DEGRADED_STAGE:V4-00F" in result["core_blockers"]
    data["V4-00F"]["status"] = "DEGRADED_PASS"
    result = evaluate_phase0(data)
    assert result["phase0_status"] == "DEGRADED_PASS"
    assert result["v4_01_entry_permission"] == "AUTHORIZED"


def test_cutover_and_benchmark_contract_does_not_promote_unset_thresholds():
    policy = json.loads((ROOT / "config/v4_capability_cutover_policy_v1.json").read_text("utf-8"))
    benchmark = policy["benchmark_missing_and_consumer_policy"]
    assert benchmark["coverage_gate_value"] is None
    assert benchmark["suspension_quote_age_gate_value"] is None
    assert benchmark["quality_consumer_matrix_status"] == "UNSET_PENDING_REPRESENTATIVE_SAMPLE_ACCEPTANCE"
    assert benchmark["marked_relative_permission"] is False
    perf = json.loads((ROOT / "config/v4_performance_measurement_contract_v1.json").read_text("utf-8"))
    assert "V4-00" in perf["measurement_stage"]
    assert "NOT_IMPLEMENTED" in perf["unavailable_metric_policy"]
    final_gate = json.loads((ROOT / "config/v4_phase0_final_gate_v1.json").read_text("utf-8"))
    assert final_gate["physical_backup_is_acceptance_requirement"] is False
    assert final_gate["physical_backup_role"] == "INFORMATIONAL_NON_AUTHORITATIVE"
    assert final_gate["physical_backup_request_truth"] == "USER_EXPLICITLY_REQUESTED_PRE_DELETE_SAFETY_MEASURE"
    assert final_gate["physical_backup_is_v4_migration_input"] is False
    assert final_gate["required_scope_owners"] == {"A_STOCK_TDX_SOURCE": "V4-00D", "LIFECYCLE_SCHEMA": "V4-00B", "PUBLICATION_IDENTITY": "V4-00C"}
    assert final_gate["raw_bootstrap_derivation"]["single_stage_self_declaration_satisfies_permission"] is False
