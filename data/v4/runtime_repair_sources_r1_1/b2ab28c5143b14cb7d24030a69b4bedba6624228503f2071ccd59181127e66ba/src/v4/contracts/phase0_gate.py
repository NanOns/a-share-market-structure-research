from __future__ import annotations

from typing import Any, Mapping


STAGES = ("V4-00A", "V4-00B", "V4-00C", "V4-00D", "V4-00E", "V4-00F", "V4-00G", "V4-00H")
ACCEPTED = {"FULL_PASS", "DEGRADED_PASS"}
STATUSES = ACCEPTED | {"BLOCKED"}
V4_01_REQUIRED_SCOPES = ("RAW_BOOTSTRAP", "A_STOCK_TDX_SOURCE", "LIFECYCLE_SCHEMA", "PUBLICATION_IDENTITY")
REQUIRED_SCOPE_OWNERS = {
    "A_STOCK_TDX_SOURCE": "V4-00D",
    "LIFECYCLE_SCHEMA": "V4-00B",
    "PUBLICATION_IDENTITY": "V4-00C",
}
RAW_BOOTSTRAP_OWNER = "V4-00E"


def evaluate_phase0(
    stages: Mapping[str, Any],
    core_blockers: list[str] | None = None,
    *,
    required_scopes: tuple[str, ...] = V4_01_REQUIRED_SCOPES,
    nonblocking_limitations: list[str] | None = None,
    future_stage_transfers: list[Mapping[str, str]] | None = None,
    contract_conflicts: list[str] | None = None,
) -> dict[str, Any]:
    """Aggregate stage status and capability scopes without conflating degraded with full pass."""
    blockers = list(core_blockers or [])
    normalized: dict[str, dict[str, Any]] = {}
    missing = [stage for stage in STAGES if stage not in stages]
    if missing:
        blockers.extend(f"STAGE_MISSING:{stage}" for stage in missing)

    any_degraded = False
    stage_blockers: list[str] = []
    accepted_scopes: set[str] = set()
    raw_bootstrap_claimed = False
    blocked_scopes: set[str] = set()
    all_blocked_scopes: set[str] = set()
    for stage in STAGES:
        if stage not in stages:
            continue
        raw = stages[stage]
        record = {"status": raw} if isinstance(raw, str) else dict(raw) if isinstance(raw, Mapping) else {"status": "INVALID"}
        status = record.get("status")
        if status not in STATUSES:
            stage_blockers.append(f"STAGE_STATUS_INVALID:{stage}:{status}")
            blocked_scopes.update(required_scopes)
        if status == "BLOCKED":
            stage_blockers.append(f"STAGE_BLOCKED:{stage}")
        capabilities = record.get("allowed_capabilities", [])
        if not isinstance(capabilities, list) or any(not isinstance(scope, str) or not scope for scope in capabilities):
            stage_blockers.append(f"STAGE_CAPABILITY_LIST_INVALID:{stage}")
            capabilities = []
        if status == "FULL_PASS" and record.get("blocked_scopes"):
            stage_blockers.append(f"BLOCKED_SCOPE_REQUIRES_DEGRADED_STAGE:{stage}")

        for scope in capabilities:
            if scope == "RAW_BOOTSTRAP":
                if stage == RAW_BOOTSTRAP_OWNER and status in ACCEPTED:
                    raw_bootstrap_claimed = True
                continue
            required_owner = REQUIRED_SCOPE_OWNERS.get(scope)
            if required_owner is not None and required_owner != stage:
                stage_blockers.append(f"REQUIRED_SCOPE_OWNER_MISMATCH:{scope}:{stage}:EXPECTED:{required_owner}")
                continue
            if status in ACCEPTED and (required_owner == stage or required_owner is None):
                accepted_scopes.add(scope)

        if status == "BLOCKED":
            scopes = set(record.get("blocked_scopes", []))
            all_blocked_scopes.update(scopes)
        elif status == "DEGRADED_PASS":
            any_degraded = True
            scopes = set(record.get("blocked_scopes", []))
            all_blocked_scopes.update(scopes)
            blocks_entry = bool(record.get("blocks_v4_01", False)) or bool(scopes & set(required_scopes))
            if blocks_entry:
                blocked_scopes.update(scopes & set(required_scopes) if scopes else set(required_scopes))
        normalized[stage] = {
            "status": status,
            "degraded_scopes": list(record.get("degraded_scopes", [])),
            "blocked_scopes": list(record.get("blocked_scopes", [])),
            "allowed_capabilities": list(capabilities),
            "capability_claims_effective": [
                scope for scope in capabilities
                if scope == "RAW_BOOTSTRAP" and stage == RAW_BOOTSTRAP_OWNER
                or REQUIRED_SCOPE_OWNERS.get(scope) == stage
                or scope not in REQUIRED_SCOPE_OWNERS and scope != "RAW_BOOTSTRAP"
            ],
            "blocks_v4_01": bool(record.get("blocks_v4_01", status == "BLOCKED")),
            "reason_codes": list(record.get("reason_codes", [])),
            "evidence": list(record.get("evidence", [])),
        }
        if normalized[stage]["degraded_scopes"] or normalized[stage]["blocked_scopes"]:
            any_degraded = True
        if normalized[stage]["blocks_v4_01"]:
            stage_blockers.append(f"V4_01_SCOPE_BLOCKED:{stage}")
            if not normalized[stage]["blocked_scopes"]:
                blocked_scopes.update(required_scopes)
                all_blocked_scopes.update(required_scopes)
            else:
                blocked_scopes.update(set(normalized[stage]["blocked_scopes"]) & set(required_scopes))
                all_blocked_scopes.update(normalized[stage]["blocked_scopes"])

    blockers.extend(stage_blockers)
    conflict_list = list(contract_conflicts or [])
    if conflict_list:
        blockers.extend(f"CONTRACT_CONFLICT:{item}" for item in conflict_list)
    if set(core_blockers or []):
        blocked_scopes.update(required_scopes)
        all_blocked_scopes.update(required_scopes)
    accepted_scopes.difference_update(blocked_scopes)

    unknown_required_owners = set(required_scopes) - set(REQUIRED_SCOPE_OWNERS) - {"RAW_BOOTSTRAP"}
    if unknown_required_owners:
        blockers.extend(f"REQUIRED_SCOPE_OWNER_UNDEFINED:{scope}" for scope in sorted(unknown_required_owners))
    raw_requirements_accepted = (
        raw_bootstrap_claimed
        and all(normalized.get(stage, {}).get("status") in ACCEPTED for stage in STAGES)
        and not blockers
        and not blocked_scopes
        and set(required_scopes) - {"RAW_BOOTSTRAP"} <= accepted_scopes
    )
    if raw_requirements_accepted:
        accepted_scopes.add("RAW_BOOTSTRAP")

    entry_ready = not blockers and not blocked_scopes and set(required_scopes).issubset(accepted_scopes)
    if not entry_ready:
        phase0 = "BLOCKED"
        v4_01 = "BLOCKED"
    elif any_degraded or nonblocking_limitations or future_stage_transfers:
        phase0 = "DEGRADED_PASS"
        v4_01 = "AUTHORIZED"
    else:
        phase0 = "FULL_PASS"
        v4_01 = "AUTHORIZED"

    return {
        "phase0_status": phase0,
        "v4_01_entry_permission": v4_01,
        "raw_bootstrap_permission": "AUTHORIZED" if entry_ready else "BLOCKED",
        "adjusted_bootstrap_permission": "SCOPE_DEPENDENT" if entry_ready else "BLOCKED",
        "supplemental_permission": "OPTIONAL",
        "scanner_permission": "NOT_APPLICABLE_UNTIL_V4_05",
        "production_cutover_permission": "NOT_APPLICABLE_UNTIL_LATER_GATES",
        "stages": normalized,
        "entry_gate": {
            "required_scopes": list(required_scopes),
            "accepted_scopes": sorted(accepted_scopes),
            "blocked_scopes": sorted(all_blocked_scopes),
            "blocked_required_scopes": sorted(blocked_scopes),
            "raw_bootstrap_derivation": {
                "status": "SATISFIED" if raw_requirements_accepted else "NOT_SATISFIED",
                "owner_stage": RAW_BOOTSTRAP_OWNER,
                "requires_all_phase0_stages_accepted": True,
                "required_owner_scopes_accepted": sorted(set(required_scopes) - {"RAW_BOOTSTRAP"}),
            },
        },
        "core_blockers": sorted(set(blockers)),
        "nonblocking_limitations": list(nonblocking_limitations or []),
        "future_stage_transfers": [dict(item) for item in (future_stage_transfers or [])],
        "contract_conflicts": conflict_list,
    }
