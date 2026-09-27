from __future__ import annotations

"""Machine gate for the V4-00/01/02 joint final receipt."""

from typing import Mapping

PHASE0_STAGES = tuple(f"V4-00{letter}" for letter in "ABCDEFGH")


def key_set_diagnostics(expected: set[str], actual: set[str], duplicate_rows: int = 0) -> dict[str, int]:
    return {
        "missing_key_count": len(expected - actual),
        "extra_key_count": len(actual - expected),
        "duplicate_rows": int(duplicate_rows),
    }


def identity_set_is_compatible(required_identity_ids: set[str], downstream_identity_ids: set[str]) -> bool:
    return downstream_identity_ids.issubset(required_identity_ids)


def evaluate_joint_gate(
    *,
    phase0: Mapping[str, object],
    v4_01: Mapping[str, object],
    alias_gate: Mapping[str, object],
    v4_02: Mapping[str, object],
    external_v4_02: Mapping[str, object],
    cross_stage: Mapping[str, object],
    tests: Mapping[str, object],
    gate_contract: Mapping[str, object],
    evidence_change: Mapping[str, object],
) -> dict[str, object]:
    stages = phase0.get("stages", [])
    if isinstance(stages, list):
        statuses = {
            str(row.get("stage")): str(row.get("status"))
            for row in stages
            if isinstance(row, Mapping)
        }
    elif isinstance(stages, Mapping):
        statuses = {
            str(stage): str(row.get("status"))
            for stage, row in stages.items()
            if isinstance(row, Mapping)
        }
    else:
        statuses = {}
    test_counts = tests.get("test_summary", {})
    criteria = {
        "versioned_joint_gate_contract": gate_contract.get("contract_id") == "V4_00_01_02_JOINT_FINAL_GATE_V1",
        "phase0_stage_obligation_full_pass": phase0.get("phase0_status") == "FULL_PASS"
        and all(statuses.get(stage) == "FULL_PASS" for stage in PHASE0_STAGES)
        and phase0.get("core_blockers", []) == [],
        "v4_01_required_scope_pass": v4_01.get("required_scope_status") == "PASS"
        and v4_01.get("status") == "PASS_WITH_BSE_SCOPE_DEGRADED"
        and v4_01.get("stage_completion_authorized") is True,
        "v4_01_optional_bse_degraded_separately": v4_01.get("scope", {}).get("optional_bse") == "DEGRADED_BSE",
        "generic_alias_completeness_pass": alias_gate.get("status") == "PASS"
        and int(alias_gate.get("unresolved_required_scope_candidate_count", -1)) == 0,
        "v4_02_externally_accepted_scope_pass": v4_02.get("status") == "PASS_WITH_BSE_SCOPE_DEGRADED"
        and external_v4_02.get("acceptance_result", {}).get("external_acceptance") == "EXTERNALLY_ACCEPTED"
        and external_v4_02.get("acceptance_result", {}).get("stage_closed") is True,
        "cross_stage_consistency_pass": cross_stage.get("status") == "PASS",
        "test_gate_pass": tests.get("status") == "PASS"
        and int(test_counts.get("failed", -1)) == 0
        and int(test_counts.get("skipped", -1)) == 0,
        "no_business_code_changed_after_tested_head": evidence_change.get("status") == "PASS"
        and evidence_change.get("business_code_changed_after_tested_head") is False
        and evidence_change.get("evidence_base_head") == tests.get("execution_commit"),
    }
    blockers = [name for name, passed in criteria.items() if not passed]
    return {
        "joint_status": "FULL_PASS" if not blockers else "BLOCKED",
        "v4_03_entry": "READY_FOR_EXTERNAL_ACCEPTANCE" if not blockers else "BLOCKED",
        "criteria": criteria,
        "required_scope_blockers": blockers,
        "stage_statuses": statuses,
        "external_acceptance_required": not blockers,
    }
