from __future__ import annotations

from workbench_analysis.v4_joint_receipt import (
    PHASE0_STAGES,
    evaluate_joint_gate,
    identity_set_is_compatible,
    key_set_diagnostics,
)


def _inputs() -> dict[str, object]:
    return {
        "phase0": {
            "phase0_status": "FULL_PASS",
            "core_blockers": [],
            "stages": [{"stage": stage, "status": "FULL_PASS"} for stage in PHASE0_STAGES],
        },
        "v4_01": {
            "status": "PASS_WITH_BSE_SCOPE_DEGRADED",
            "required_scope_status": "PASS",
            "stage_completion_authorized": True,
            "scope": {"optional_bse": "DEGRADED_BSE"},
        },
        "alias_gate": {"status": "PASS", "unresolved_required_scope_candidate_count": 0},
        "v4_02": {"status": "PASS_WITH_BSE_SCOPE_DEGRADED"},
        "external_v4_02": {
            "acceptance_result": {"external_acceptance": "EXTERNALLY_ACCEPTED", "stage_closed": True}
        },
        "cross_stage": {"status": "PASS"},
        "tests": {"status": "PASS", "execution_commit": "code-head",
                  "test_summary": {"passed": 10, "failed": 0, "skipped": 0}},
        "gate_contract": {"contract_id": "V4_00_01_02_JOINT_FINAL_GATE_V1"},
        "evidence_change": {"status": "PASS", "business_code_changed_after_tested_head": False,
                            "evidence_base_head": "code-head"},
    }


def test_joint_receipt_gate_requires_every_stage_and_external_v4_02_acceptance() -> None:
    inputs = _inputs()
    result = evaluate_joint_gate(**inputs)
    assert result["joint_status"] == "FULL_PASS"
    assert result["v4_03_entry"] == "READY_FOR_EXTERNAL_ACCEPTANCE"
    inputs["external_v4_02"] = {"acceptance_result": {"external_acceptance": "PENDING", "stage_closed": False}}
    blocked = evaluate_joint_gate(**inputs)
    assert blocked["joint_status"] == "BLOCKED"
    assert "v4_02_externally_accepted_scope_pass" in blocked["required_scope_blockers"]


def test_joint_receipt_blocks_phase0_owner_stage_degradation() -> None:
    inputs = _inputs()
    inputs["phase0"]["stages"][5]["status"] = "DEGRADED_PASS"
    result = evaluate_joint_gate(**inputs)
    assert result["joint_status"] == "BLOCKED"
    assert "phase0_stage_obligation_full_pass" in result["required_scope_blockers"]


def test_joint_receipt_accepts_final_phase0_stage_map_shape() -> None:
    inputs = _inputs()
    inputs["phase0"]["stages"] = {
        row["stage"]: {"status": row["status"]}
        for row in inputs["phase0"]["stages"]
    }
    result = evaluate_joint_gate(**inputs)
    assert result["joint_status"] == "FULL_PASS"


def test_cross_stage_key_set_comparison_detects_missing_extra_and_duplicates() -> None:
    assert key_set_diagnostics({"A", "B"}, {"A", "C"}, duplicate_rows=1) == {
        "missing_key_count": 1,
        "extra_key_count": 1,
        "duplicate_rows": 1,
    }


def test_downstream_period_identities_must_be_a_subset_of_r8_universe() -> None:
    assert identity_set_is_compatible({"A", "B"}, {"A"})
    assert not identity_set_is_compatible({"A", "B"}, {"A", "C"})
