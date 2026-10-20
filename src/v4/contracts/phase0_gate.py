from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
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


# Stage00 diagnostic runtime. These names select approved PG rows and contain
# no fallback contract content themselves.
STAGE00_CONTRACTS = {
    "V4_PHASE0_FINAL_ACCEPTANCE_R3": "3.0.0",
    "V4_ALGORITHM_CONTRACT_FRAMEWORK_V1": "1.1.0",
    "PARAMETER_REGISTRY_V1": "1.1.0",
    "CAPABILITY_CUTOVER_AND_ROLLBACK_V1": "1.0.0",
    "V4_PERFORMANCE_MEASUREMENT_CONTRACT_V1": "1.1.0",
}
STAGE00_TABLES = (
    "contract_versions", "contract_approval_events", "source_packages",
    "source_package_facts", "source_revisions", "security_lifecycle_facts", "security_lifecycle_history",
    "publications", "model_namespaces", "publication_heads", "state_heads", "stage00_raw_owner_receipts",
)
TDX_BOARD_SCOPES = ("SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR")
TDX_SAMPLES = TDX_BOARD_SCOPES
MAX_ACCEPTED_PACKAGE_CANDIDATES = 50
MAX_PACKAGE_FACT_ROWS = 500


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _source_head_sha() -> str:
    import subprocess
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=_repo_root(), check=True,
            capture_output=True, text=True, timeout=5,
        )
        value = result.stdout.strip()
        return value if re.fullmatch(r"[0-9a-f]{40}", value) else "UNKNOWN"
    except (OSError, subprocess.SubprocessError):
        return "UNKNOWN"


def _package_acceptance_errors(
    package: Mapping[str, Any], facts: list[Mapping[str, Any]], *,
    acceptance_verified: bool,
) -> list[str]:
    """Validate persisted, accepted package provenance for the Stage00 D scope."""
    errors: list[str] = []
    manifest = package.get("manifest")
    if package.get("accepted_scope") != "ACCEPTED_SOURCE_PACKAGE":
        errors.append("PACKAGE_SCOPE_NOT_ACCEPTED")
    if not acceptance_verified:
        errors.append("INDEPENDENT_ACCEPTANCE_PROOF_INVALID")
    if not isinstance(manifest, Mapping):
        return errors + ["PACKAGE_MANIFEST_INVALID"]
    package_id = package.get("package_id")
    package_sha = str(package.get("package_sha256") or "").strip().lower()
    target = str(package.get("target_trade_date") or "")
    if (not package_id or manifest.get("package_id") != package_id
            or manifest.get("package_sha256") != package_sha):
        errors.append("PACKAGE_IDENTITY_BINDING_MISMATCH")
    if (not re.fullmatch(r"\d{4}-\d{2}-\d{2}", target)
            or manifest.get("trade_date") != target):
        errors.append("PACKAGE_T0_BINDING_MISMATCH")
    if manifest.get("accepted_scope") != "ACCEPTED_SOURCE_PACKAGE":
        errors.append("MANIFEST_SCOPE_NOT_ACCEPTED")
    if manifest.get("AS_RECORDED") is not True:
        errors.append("PACKAGE_AS_RECORDED_AUTHORITY_NOT_ACCEPTED")
    proof = manifest.get("acceptance_proof")
    if not isinstance(proof, Mapping) or not proof.get("receipt_sha256") or not proof.get("issuer_id"):
        errors.append("PACKAGE_ACCEPTANCE_RECEIPT_MISSING")
    bindings = manifest.get("source_fact_bindings")
    if not isinstance(bindings, list) or not bindings:
        errors.append("PACKAGE_SOURCE_FACT_BINDINGS_MISSING")
    else:
        binding_rows = {(row.get("source_key"), row.get("logical_fact_id"), row.get("fact_digest")): row
                        for row in bindings if isinstance(row, Mapping)}
        binding_keys = set(binding_rows)
        fact_keys = {(row.get("source_key"), row.get("logical_fact_id"), row.get("fact_digest"))
                     for row in facts}
        if len(fact_keys) != len(facts) or binding_keys != fact_keys:
            errors.append("PACKAGE_FACT_SET_MISMATCH")
        revisions = [row for row in facts if row.get("source_revision_id")]
        if len(revisions) != len(bindings):
            errors.append("PACKAGE_SOURCE_REVISION_SET_INCOMPLETE")
        if any(row.get("source_package_id") != package_id
               or row.get("source_package_source_key") != row.get("source_key")
               or row.get("source_fact_digest") != row.get("fact_digest")
               or row.get("digest") != row.get("fact_digest")
               or row.get("revision_no", 0) < 1
               or not row.get("observed_at") or not row.get("ingested_at")
               or not row.get("system_available_at")
               for row in revisions):
            errors.append("PACKAGE_SOURCE_REVISION_BINDING_INVALID")
        if any(
            binding_rows.get((row.get("source_key"), row.get("logical_fact_id"), row.get("fact_digest")), {}).get("record_locator")
            != row.get("record_locator")
            or binding_rows.get((row.get("source_key"), row.get("logical_fact_id"), row.get("fact_digest")), {}).get("source_fact_sha256")
            != row.get("source_fact_sha256")
            or binding_rows.get((row.get("source_key"), row.get("logical_fact_id"), row.get("fact_digest")), {}).get("record_count")
            != row.get("record_count")
            or binding_rows.get((row.get("source_key"), row.get("logical_fact_id"), row.get("fact_digest")), {}).get("byte_count")
            != row.get("byte_count")
            for row in facts
        ):
            errors.append("PACKAGE_FACT_MANIFEST_BINDING_MISMATCH")
    tdx_packages = manifest.get("tdx_source_packages")
    if not isinstance(tdx_packages, list) or not tdx_packages:
        errors.append("TDX_OFFICIAL_PACKAGE_EVIDENCE_MISSING")
    else:
        official = [row for row in tdx_packages if isinstance(row, Mapping)
                    and row.get("source_role") == "OFFICIAL_CURRENT_PACKAGE"]
        if not official:
            errors.append("TDX_OFFICIAL_PACKAGE_EVIDENCE_MISSING")
        for row in official:
            if (row.get("T0") != target or not row.get("provider_package_date")
                    or not isinstance(row.get("first_available_at"), str)
                    or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("package_sha256") or ""))
                    or not isinstance(row.get("package_bytes"), int) or row.get("package_bytes", 0) <= 0
                    or not isinstance(row.get("source_revision_number"), int)
                    or row.get("AS_RECORDED") is not False or row.get("PIT_ELIGIBLE") is not False):
                errors.append("TDX_OFFICIAL_PACKAGE_BINDING_INVALID")
    # Stage00's accepted source scope is four boards; exchange-only universe
    # coverage is insufficient. The producing acceptance must report a board
    # inventory bound into its accepted manifest.
    coverage = manifest.get("accepted_board_coverage")
    coverage_counts = coverage.get("counts") if isinstance(coverage, Mapping) else None
    coverage_body = ({key: value for key, value in coverage.items() if key != "digest"}
                     if isinstance(coverage, Mapping) and isinstance(coverage_counts, Mapping) else None)
    universe_fact = next((row for row in facts if row.get("source_key") == "security_universe"), None)
    universe_locator = universe_fact.get("record_locator") if isinstance(universe_fact, Mapping) else None
    suspended_counts = coverage.get("suspended_counts") if isinstance(coverage, Mapping) else None
    coverage_digest = hashlib.sha256(json.dumps(
        coverage_body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest() if coverage_body is not None else None
    if (not isinstance(coverage, Mapping) or not isinstance(coverage_counts, Mapping)
            or set(coverage.get("boards", ())) != set(TDX_BOARD_SCOPES)
            or any(isinstance(coverage_counts.get(board), bool)
                   or not isinstance(coverage_counts.get(board), int)
                   or coverage_counts[board] <= 0 for board in TDX_BOARD_SCOPES)
            or coverage.get("target_trade_date") != target
            or not isinstance(coverage.get("roster_count"), int)
            or not isinstance(coverage.get("scope_roster_count"), int)
            or not isinstance(coverage.get("trading_row_count"), int)
            or not isinstance(coverage.get("suspended_row_count"), int)
            or not isinstance(suspended_counts, Mapping)
            or any(isinstance(suspended_counts.get(board), bool)
                   or not isinstance(suspended_counts.get(board), int)
                   or suspended_counts[board] < 0 for board in TDX_BOARD_SCOPES)
            or coverage.get("scope_roster_count") != coverage.get("trading_row_count") + coverage.get("suspended_row_count")
            or coverage.get("scope_roster_count") > coverage.get("roster_count")
            or sum(coverage_counts.values()) != coverage.get("trading_row_count")
            or sum(suspended_counts.values()) != coverage.get("suspended_row_count")
            or not isinstance(universe_locator, Mapping)
            or coverage.get("universe_id") != universe_locator.get("universe_id")
            or coverage.get("universe_sha256") != universe_locator.get("universe_sha256")
            or coverage.get("roster_count") != universe_locator.get("record_count")
            or not isinstance(coverage.get("roster_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", coverage["roster_sha256"])
            or not isinstance(coverage.get("tdx_ohlcva_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", coverage["tdx_ohlcva_sha256"])
            or coverage.get("digest") != coverage_digest):
        errors.append("FOUR_BOARD_COVERAGE_UNPROVEN")
    elif not any(
        row.get("source_key") == "tdx_board_coverage"
        and row.get("fact_digest") == coverage.get("digest")
        and row.get("source_fact_sha256") == coverage.get("digest")
        and row.get("record_locator") == coverage_body
        and row.get("record_count") == coverage.get("roster_count")
        for row in bindings if isinstance(row, Mapping)
    ):
        errors.append("FOUR_BOARD_COVERAGE_NOT_BOUND_TO_ACCEPTED_PACKAGE")
    return sorted(set(errors))


def _raw_bootstrap_errors(receipt: Mapping[str, Any] | None, source: Mapping[str, Any], *, receipt_verified: bool = False) -> list[str]:
    """Check a normalized RAW receipt against accepted source and B/C/D owner evidence."""
    if not isinstance(receipt, Mapping):
        return ["RAW_RECEIPT_SOURCE_NOT_ACCEPTED"] if not source.get("accepted") else ["RAW_OWNER_RECEIPT_NOT_FOUND"]
    errors: list[str] = []
    if not receipt_verified:
        errors.append("RAW_RECEIPT_AUTHORITY_NOT_VERIFIED")
    package = source.get("package") if isinstance(source, Mapping) else None
    facts = source.get("facts", []) if isinstance(source, Mapping) else []
    if not source.get("accepted") or not isinstance(package, Mapping):
        errors.append("RAW_RECEIPT_SOURCE_NOT_ACCEPTED")
    package_id = package.get("package_id") if isinstance(package, Mapping) else None
    target = package.get("target_trade_date") if isinstance(package, Mapping) else None
    source_revision_ids = {row.get("source_revision_id") for row in facts if row.get("source_revision_id")}
    if (receipt.get("owner") != RAW_BOOTSTRAP_OWNER
            or receipt.get("status") not in {"ACCEPTED", "DEGRADED_ACCEPTED"}
            or receipt.get("scope") != "RAW_BOOTSTRAP"):
        errors.append("RAW_RECEIPT_OWNER_OR_STATUS_INVALID")
    if receipt.get("trade_date") != target or receipt.get("source_package_id") != package_id:
        errors.append("RAW_RECEIPT_T0_OR_PACKAGE_MISMATCH")
    if (receipt.get("source_revision_id") not in source_revision_ids
            or receipt.get("source_revision_sha256") != next((row.get("digest") for row in facts
                if row.get("source_revision_id") == receipt.get("source_revision_id")), None)):
        errors.append("RAW_RECEIPT_SOURCE_REVISION_MISMATCH")
    if receipt.get("raw_basis") != "TDX_GBBQ_UNCHANGED":
        errors.append("RAW_RECEIPT_BASIS_MISMATCH")
    if receipt.get("source_identity_status") != "RESOLVED":
        errors.append("RAW_RECEIPT_SOURCE_IDENTITY_UNRESOLVED")
    if receipt.get("source_trading_status") not in {"TRADING", "TRADING_WITH_SUSPENSIONS"}:
        errors.append("RAW_RECEIPT_SOURCE_NOT_TRADING")
    if receipt.get("source_knowledge_status") != "AS_RECORDED":
        errors.append("RAW_RECEIPT_SOURCE_KNOWLEDGE_NOT_AS_RECORDED")
    manifest = package.get("manifest") if isinstance(package, Mapping) else None
    if (not isinstance(manifest, Mapping)
            or receipt.get("source_pit_eligible") is not manifest.get("PIT_ELIGIBLE")):
        errors.append("RAW_RECEIPT_PIT_SCOPE_MISMATCH")
    try:
        signed_at = datetime.fromisoformat(str(receipt.get("signed_at")).replace("Z", "+00:00"))
        if signed_at.tzinfo is None:
            raise ValueError
        available = [datetime.fromisoformat(str(row.get(key)).replace("Z", "+00:00"))
                     for row in facts if row.get("source_revision_id") == receipt.get("source_revision_id")
                     for key in ("observed_at", "ingested_at", "system_available_at")]
        if available and signed_at.astimezone(timezone.utc) < max(value.astimezone(timezone.utc) for value in available):
            errors.append("RAW_RECEIPT_SIGNED_BEFORE_SOURCE_AVAILABLE")
    except (TypeError, ValueError):
        errors.append("RAW_RECEIPT_SIGNED_AT_INVALID")
    if receipt.get("source_package_sha256") != (package.get("package_sha256") if isinstance(package, Mapping) else None):
        errors.append("RAW_RECEIPT_PACKAGE_DIGEST_MISMATCH")
    coverage = manifest.get("accepted_board_coverage") if isinstance(manifest, Mapping) else None
    if (not isinstance(coverage, Mapping)
            or receipt.get("source_universe_id") != coverage.get("universe_id")
            or receipt.get("source_universe_sha256") != coverage.get("universe_sha256")
            or receipt.get("source_roster_sha256") != coverage.get("roster_sha256")
            or receipt.get("source_roster_count") != coverage.get("roster_count")
            or receipt.get("source_scope_roster_count") != coverage.get("scope_roster_count")
            or receipt.get("source_trading_row_count") != coverage.get("trading_row_count")
            or receipt.get("source_suspended_row_count") != coverage.get("suspended_row_count")
            or receipt.get("source_tdx_ohlcva_sha256") != coverage.get("tdx_ohlcva_sha256")
            or receipt.get("source_tdx_record_count") != next((row.get("record_count") for row in facts
                if row.get("source_revision_id") == receipt.get("source_revision_id")), None)):
        errors.append("RAW_RECEIPT_ROSTER_OR_TDX_BINDING_MISMATCH")
    owner_results = receipt.get("owner_results")
    if not isinstance(owner_results, Mapping):
        errors.append("RAW_RECEIPT_OWNER_RESULTS_MISSING")
    else:
        expected = {"V4-00B": "LIFECYCLE_SCHEMA", "V4-00C": "PUBLICATION_IDENTITY",
                    "V4-00D": "A_STOCK_TDX_SOURCE"}
        for owner, scope in expected.items():
            result = owner_results.get(owner)
            if (not isinstance(result, Mapping) or result.get("status") not in ACCEPTED
                    or result.get("owner") != owner or scope not in result.get("accepted_scopes", [])
                    or result.get("trade_date") != target
                    or result.get("source_package_id") != package_id
                    or result.get("source_package_sha256") != (package.get("package_sha256") if isinstance(package, Mapping) else None)
                    or result.get("source_revision_id") != receipt.get("source_revision_id")):
                errors.append("RAW_RECEIPT_OWNER_EVIDENCE_INVALID:" + owner)
    receipt_sha = receipt.get("receipt_sha256")
    unsigned_receipt = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    expected_receipt_sha = hashlib.sha256(json.dumps(
        unsigned_receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()
    if (not receipt.get("receipt_id") or not isinstance(receipt_sha, str)
            or not re.fullmatch(r"[0-9a-f]{64}", receipt_sha)
            or receipt_sha != expected_receipt_sha):
        errors.append("RAW_RECEIPT_IDENTITY_MISSING")
    return sorted(set(errors))


def _source_owner_stage(source_acceptance: Mapping[str, Any], sample_ready: bool, tdx: Mapping[str, Any]) -> dict[str, Any]:
    accepted = source_acceptance.get("status") == "ACCEPTED"
    errors = list(source_acceptance.get("candidate_errors", []))
    if not accepted and not errors and not source_acceptance.get("candidate_count"):
        errors = ["NO_ACCEPTED_SOURCE_PACKAGE"]
    elif not accepted and not errors:
        errors = ["ACCEPTED_SOURCE_PACKAGE_EVIDENCE_INVALID"]
    return {
        "status": "FULL_PASS" if accepted else ("DEGRADED_PASS" if sample_ready else "BLOCKED"),
        "owner": "V4-00D", "scope": "A_STOCK_TDX_SOURCE",
        "source": "PG accepted source package/facts/revisions plus independent receipt verification",
        "evidence": [
            f"accepted_source_packages={source_acceptance.get('accepted_candidate_count', 0)}",
            f"tdx_samples={tdx.get('valid_sample_count', 0)}/{len(TDX_SAMPLES)}",
        ],
        "blocked_scopes": [] if accepted else ["A_STOCK_TDX_SOURCE"],
        "allowed_capabilities": ["A_STOCK_TDX_SOURCE"] if accepted else [],
        "blocks_v4_01": not accepted,
        "reason_codes": [] if accepted else errors,
    }


def _raw_owner_stage(raw_errors: list[str]) -> dict[str, Any]:
    accepted = not raw_errors
    return {
        "status": "FULL_PASS" if accepted else "BLOCKED",
        "owner": "V4-00E", "scope": "RAW_BOOTSTRAP",
        "source": "PG RAW receipt bound to accepted source and B/C/D owner evidence",
        "evidence": ["receipt fields and source/owner bindings verified" if accepted else "RAW receipt or binding evidence missing/invalid"],
        "blocked_scopes": [] if accepted else ["RAW_BOOTSTRAP"],
        "allowed_capabilities": ["RAW_BOOTSTRAP"] if accepted else [],
        "blocks_v4_01": not accepted,
        "reason_codes": raw_errors,
    }


def _raw_receipt_reason(*, table_exists: bool, accepted_source_exists: bool,
                        receipt_exists: bool = False, verified: bool = False,
                        read_error: str | None = None) -> str | None:
    """区分运行组件缺失与上游真实来源/收据尚未到位。"""
    if not table_exists:
        return "MISSING_RUNTIME_RECEIPT_PRODUCER"
    if not accepted_source_exists:
        return "NO_ACCEPTED_SOURCE_PACKAGE"
    if read_error:
        return "RAW_OWNER_RECEIPT_READ_OR_VERIFY_FAILED:" + read_error
    if not receipt_exists:
        return "RAW_OWNER_RECEIPT_NOT_FOUND"
    if not verified:
        return "RAW_OWNER_RECEIPT_NOT_VERIFIED"
    return None


def _tdx_root(config_path: Path, override: str | None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    try:
        import yaml
    except ImportError:
        yaml = None
    config = yaml.safe_load(config_path.read_text(encoding="utf-8-sig")) if yaml is not None else None
    if config is None:
        raw = next((line.split(":", 1)[1].strip().strip(chr(34)).strip(chr(39)) for line in config_path.read_text(encoding="utf-8-sig").splitlines() if re.match(r"^\s+source_root\s*:", line)), None)
        config = {"tdx": {"source_root": raw}}
    raw = (config.get("tdx") or {}).get("source_root")
    if not isinstance(raw, str) or not raw.strip():
        raise RuntimeError("TDX_SOURCE_ROOT_NOT_CONFIGURED")
    path = Path(raw)
    return (path if path.is_absolute() else _repo_root() / path).resolve()


def _read_tdx_samples(root: Path) -> dict[str, Any]:
    from tdx.day_reader import read_edge_records, validate_day_file
    from workbench_analysis.v4_01_required_scope import required_board
    from workbench_analysis.security_entity_identity import bao_source_entity

    if not root.is_dir():
        raise FileNotFoundError("TDX_SOURCE_ROOT_UNAVAILABLE")
    selected = {}
    for market in ("sh", "sz"):
        directory = root / "vipdoc" / market / "lday"
        if not directory.is_dir():
            continue
        for candidate in sorted(directory.glob(f"{market}*.day")):
            symbol = f"{market.upper()}.{candidate.stem[2:]}"
            code = candidate.stem[2:]
            if market == "sh":
                board = "STAR" if code.startswith(("688", "689")) else "SH_MAIN" if code.startswith(("600", "601", "603", "605")) else None
            else:
                board = "CHINEXT" if code.startswith(("300", "301")) else "SZ_MAIN" if code.startswith(("000", "001", "002", "003")) else None
            if board in TDX_BOARD_SCOPES and board not in selected:
                selected[board] = (symbol, candidate)
            if len(selected) == len(TDX_BOARD_SCOPES):
                break
        if len(selected) == len(TDX_BOARD_SCOPES):
            break
    rows = []
    failures = []
    observation_dates = []
    for expected_board in TDX_BOARD_SCOPES:
        selection = selected.get(expected_board)
        if selection is None:
            failures.append(f"TDX_BOARD_SAMPLE_MISSING:{expected_board}")
            rows.append({"board": expected_board, "status": "MISSING"})
            continue
        symbol, path = selection
        exchange, code = symbol.split(".")
        row: dict[str, Any] = {"symbol": symbol, "path_exists": path.is_file()}
        if not path.is_file():
            row["status"] = "MISSING"
            failures.append(f"TDX_SAMPLE_MISSING:{symbol}")
            rows.append(row)
            continue
        try:
            validated = validate_day_file(path, exchange.lower())
            first, last = read_edge_records(path)
            if not validated.get("valid"):
                raise ValueError("TDX_DAY_VALIDATION_FAILED:" + ",".join(validated.get("errors", [])))
            board_exchange = exchange
            board = {"SH_MAIN": "MAIN", "SZ_MAIN": "MAIN", "CHINEXT": "CHINEXT", "STAR": "STAR"}[expected_board]
            identity_facts = bao_source_entity(board_exchange, symbol, None)
            identity_check = required_board({
                "security_type": "A_STOCK", "exchange": board_exchange, "board": board,
            })
            if identity_check is None or identity_facts["identity_anchor_symbol"] != symbol:
                raise ValueError("TDX_SAMPLE_IDENTITY_CLASSIFICATION_FAILED")
            observation_date = str(validated["last_date"])
            observation_dates.append(observation_date)
            st = path.stat()
            rows.append({
                "symbol": symbol, "board": expected_board, "status": "READ_ONLY_SAMPLE_VALID",
                "record_count": validated["record_count"],
                "first_trade_date": str(validated["first_date"]),
                "last_trade_date": observation_date,
                "file_mtime_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                "file_bytes": st.st_size,
                "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "board_scope_check": identity_check,
                "identity_evidence": identity_facts,
                "raw_ohlcva_check": {
                    "status": "PASS", "basis": "TDX_RAW_NATIVE",
                    "price_divisor": 100.0, "raw_price_ohlc_positive": min(
                        first.open, first.high, first.low, first.close,
                        last.open, last.high, last.low, last.close,
                    ) > 0,
                    "first_record_amount_nonnegative": first.amount >= 0,
                    "last_record_amount_nonnegative": last.amount >= 0,
                    "first_record_volume": first.volume, "last_record_volume": last.volume,
                },
                "identity_authority": "PG_IDENTITY_NOT_INFERRED_FROM_LOCAL_TICKER",
            })
        except (OSError, ValueError) as exc:
            row.update(status="DAMAGED", reason=str(exc))
            failures.append(f"TDX_SAMPLE_DAMAGED:{symbol}")
            rows.append(row)
    damaged = [row for row in rows if row.get("status") == "DAMAGED"]
    if damaged:
        raise ValueError("TDX_SAMPLE_DATA_DAMAGED:" + ",".join(
            f"{row['symbol']}:{row.get('reason', 'UNKNOWN')}" for row in damaged
        ))
    return {
        "root": str(root), "sample_count": len(rows), "valid_sample_count": sum(
            row.get("status") == "READ_ONLY_SAMPLE_VALID" for row in rows
        ), "tdx_observation_date": max(observation_dates) if observation_dates else None,
        "samples": rows, "failures": failures,
    }


def _count_lifecycle_t0_board_facts(
    cursor: Any, target_trade_date: str, *, knowledge_cutoff: datetime | None = None,
) -> dict[str, int]:
    """Count accepted T0 identities; omit the cutoff for ordinary as-recorded EOD use.

    Strict historical PIT callers must pass the actual knowledge cutoff. Source
    availability timestamps are never rewritten to the target trade date.
    """
    if (knowledge_cutoff is not None
            and (knowledge_cutoff.tzinfo is None or knowledge_cutoff.utcoffset() is None)):
        raise ValueError("LIFECYCLE_PIT_CUTOFF_MUST_BE_TIMEZONE_AWARE")
    rows = cursor.execute(
        """WITH accepted_identity_map AS (
                 SELECT DISTINCT f.security_id, h.symbol, f.board
              FROM v4.security_lifecycle_facts f
              JOIN v4.source_revisions r
                ON r.source_revision_id=f.source_revision_id
               AND r.observed_at=f.observed_at
               AND r.ingested_at=f.ingested_at
               AND r.system_available_at=f.system_available_at
               AND r.effective_from=f.effective_from
               AND r.effective_to IS NOT DISTINCT FROM f.effective_to
               AND r.supersedes_revision_id IS NOT DISTINCT FROM f.supersedes_revision_id
              JOIN v4.source_packages p
                ON p.package_id=r.source_package_id
               AND p.accepted_scope='ACCEPTED_SOURCE_PACKAGE'
               AND p.target_trade_date=%s
              JOIN v4.source_package_facts sf
                ON sf.package_id=r.source_package_id
               AND sf.source_key=r.source_package_source_key
               AND sf.logical_fact_id=r.logical_fact_id
               AND sf.fact_digest=r.source_fact_digest
               AND sf.fact_digest=r.digest
               AND sf.source_fact_sha256=r.payload->>'source_fact_sha256'
               AND sf.source_key=r.payload->>'source_key'
               AND sf.acceptance_receipt_id=r.payload->>'producer_receipt_id'
              JOIN v4.security_lifecycle_history h
                ON h.security_id=f.security_id
               AND h.board=f.board
               AND h.security_type='A_STOCK'
               AND h.effective_from <= %s
               AND (h.effective_to IS NULL OR h.effective_to >= %s)
              JOIN v4.source_revisions hr
                ON hr.source_revision_id=h.source_revision_id
               AND hr.observed_at=h.observed_at
               AND hr.ingested_at=h.ingested_at
               AND hr.system_available_at=h.system_available_at
               AND hr.effective_from=h.effective_from
               AND hr.effective_to IS NOT DISTINCT FROM h.effective_to
               AND hr.supersedes_revision_id IS NOT DISTINCT FROM h.supersedes_revision_id
              JOIN v4.source_packages hp
                ON hp.package_id=hr.source_package_id
               AND hp.accepted_scope='ACCEPTED_SOURCE_PACKAGE'
               AND hp.target_trade_date=%s
              JOIN v4.source_package_facts hsf
                ON hsf.package_id=hr.source_package_id
               AND hsf.source_key=hr.source_package_source_key
               AND hsf.logical_fact_id=hr.logical_fact_id
               AND hsf.fact_digest=hr.source_fact_digest
               AND hsf.fact_digest=hr.digest
               AND hsf.source_fact_sha256=hr.payload->>'source_fact_sha256'
               AND hsf.source_key=hr.payload->>'source_key'
               AND hsf.acceptance_receipt_id=hr.payload->>'producer_receipt_id'
             WHERE f.security_type='A_STOCK'
               AND f.effective_from <= %s
               AND (f.effective_to IS NULL OR f.effective_to >= %s)
               AND btrim(f.source_identity) <> ''
               AND f.quality IN ('OBSERVED','CORRECTED','ACCEPTED','PIT_OBSERVED_ACCEPTED')
               AND h.quality IN ('OBSERVED','CORRECTED','ACCEPTED','PIT_OBSERVED_ACCEPTED')
               AND btrim(h.source_identity) <> ''
               AND (%s::timestamptz IS NULL OR f.system_available_at <= %s)
               AND (%s::timestamptz IS NULL OR h.system_available_at <= %s)
             ), unambiguous_symbol AS (
                 SELECT security_id, symbol, board
                   FROM accepted_identity_map
                  WHERE symbol IN (
                        SELECT symbol FROM accepted_identity_map
                         GROUP BY symbol HAVING count(DISTINCT security_id)=1
                  )
             ), unambiguous_identity AS (
                 SELECT security_id, min(symbol) AS symbol, min(board) AS board
                   FROM unambiguous_symbol
                  GROUP BY security_id
                 HAVING count(DISTINCT symbol)=1 AND count(DISTINCT board)=1
             )
             SELECT CASE
                      WHEN left(symbol,3)='SH.' AND board='MAIN' THEN 'SH_MAIN'
                      WHEN left(symbol,3)='SZ.' AND board='MAIN' THEN 'SZ_MAIN'
                      WHEN left(symbol,3)='SZ.' AND board='CHINEXT' THEN 'CHINEXT'
                      WHEN left(symbol,3)='SH.' AND board='STAR' THEN 'STAR'
                    END AS board_key,
                    count(DISTINCT security_id)
               FROM unambiguous_identity
              GROUP BY board_key""",
        (target_trade_date, target_trade_date, target_trade_date,
         target_trade_date, target_trade_date, target_trade_date,
         knowledge_cutoff, knowledge_cutoff, knowledge_cutoff, knowledge_cutoff),
    ).fetchall()
    return {row[0]: int(row[1]) for row in rows if row[0]}


def _count_valid_t0_publication_heads(cursor: Any, target_trade_date: str) -> int:
    return int(cursor.execute(
        """SELECT count(*)
             FROM v4.publication_heads h
             JOIN v4.publications p
               ON p.publication_id=h.publication_id
              AND p.trade_date=h.trade_date
              AND p.model_namespace_id=h.model_namespace_id
              AND p.status='ACCEPTED'
              AND p.accepted_at IS NOT NULL
             JOIN v4.model_namespaces n
               ON n.namespace_id=h.model_namespace_id
              AND btrim(n.namespace) <> ''
              AND n.execution_mode IN ('PRODUCTION','SHADOW','REPLAY')
             JOIN v4.state_heads sh
               ON sh.namespace_id=h.model_namespace_id
              AND sh.state_head_id=h.state_head_id
              AND sh.publication_id=h.publication_id
              AND sh.logical_digest=h.state_logical_digest
            WHERE h.trade_date=%s
              AND h.state_head_id IS NOT NULL
              AND btrim(h.state_head_id) <> ''
              AND h.state_logical_digest IS NOT NULL
              AND jsonb_typeof(p.contract_bindings)='object'
              AND p.contract_bindings <> '{}'::jsonb
              AND p.source_manifest_contract_id IN (
                  'V4_PG_CONSUMED_SOURCE_MANIFEST_R2',
                  'V4_PG_CONSUMED_SOURCE_MANIFEST_R3')""",
        (target_trade_date,),
    ).fetchone()[0])


def _pg_snapshot(*, target_trade_date: str | None = None) -> dict[str, Any]:
    from workbench_db.v4_publication_reader import PgPublicationReader, readonly_connection
    from workbench_analysis.contract_registry_pg_v1 import (
        ContractRegistryError, load_unique_current_approved_contract,
        load_unapproved_dev_contract_candidate,
    )
    from workbench_db.v4_daily_source_ingest_r6 import (
        verify_source_package_manifest_authority, read_raw_owner_receipt,
    )

    with readonly_connection() as pg:
        identity = PgPublicationReader._read_database_identity(pg)
        role = PgPublicationReader._attest_read_role(pg)
        if (identity.get("database") != "market_research"
                or str(identity.get("host") or "").split("/")[0] != "127.0.0.1"
                or identity.get("port") != 5432):
            raise RuntimeError("PG_DATABASE_IDENTITY_MISMATCH")
        cursor = pg.cursor()
        catalog = {}
        for table in STAGE00_TABLES:
            row = cursor.execute("SELECT to_regclass(%s)", ("v4." + table,)).fetchone()
            catalog[table] = bool(row and row[0])
        counts = {}
        for key, table, sql in (
            ("source_revision_count", "source_revisions", "SELECT count(*) FROM v4.source_revisions"),
            ("accepted_source_package_count", "source_packages", "SELECT count(*) FROM v4.source_packages WHERE accepted_scope='ACCEPTED_SOURCE_PACKAGE'"),
            ("publication_head_count", "publication_heads", "SELECT count(*) FROM v4.publication_heads"),
            ("model_namespace_count", "model_namespaces", "SELECT count(*) FROM v4.model_namespaces"),
            ("lifecycle_history_count", "security_lifecycle_history", "SELECT count(*) FROM v4.security_lifecycle_history"),
            ("lifecycle_history_security_count", "security_lifecycle_history", "SELECT count(DISTINCT security_id) FROM v4.security_lifecycle_history"),
            ("lifecycle_fact_count", "security_lifecycle_facts", "SELECT count(*) FROM v4.security_lifecycle_facts"),
            ("raw_owner_receipt_count", "stage00_raw_owner_receipts", "SELECT count(*) FROM v4.stage00_raw_owner_receipts"),
        ):
            counts[key] = int(cursor.execute(sql).fetchone()[0]) if catalog[table] else None
        lifecycle_t0_board_counts = {}
        valid_publication_head_count = 0
        if target_trade_date and catalog["security_lifecycle_facts"] and all(
            catalog.get(name, False) for name in ("source_revisions", "source_packages", "source_package_facts")
        ):
            lifecycle_t0_board_counts = _count_lifecycle_t0_board_facts(cursor, target_trade_date)
        if target_trade_date and all(catalog.get(name, False) for name in (
            "publication_heads", "publications", "model_namespaces", "state_heads",
        )):
            valid_publication_head_count = _count_valid_t0_publication_heads(cursor, target_trade_date)
        contracts = {}
        for contract_id, version in STAGE00_CONTRACTS.items():
            entry = {"version": version, "status": "MISSING", "reason": None}
            if not catalog["contract_versions"] or not catalog["contract_approval_events"]:
                entry["reason"] = "PG_CATALOG_RELATION_MISSING"
                contracts[contract_id] = entry
                continue
            try:
                registered = load_unique_current_approved_contract(
                    cursor, contract_id, version, expected_database_identity=identity,
                )
                entry.update(status="APPROVED_READ", raw_sha256=registered.raw_sha256,
                             namespace=registered.namespace, source_revision=registered.approval_source_revision)
            except ContractRegistryError as exc:
                entry["reason"] = str(exc)
                if str(exc) == "V4_PG_CONTRACT_VERSION_NOT_FOUND":
                    try:
                        candidate = load_unapproved_dev_contract_candidate(
                            cursor, contract_id, version, expected_database_identity=identity,
                        )
                        entry.update(status="DEV_CANDIDATE_READ", raw_sha256=candidate.raw_sha256,
                                     namespace=candidate.namespace, source_revision=candidate.source_revision,
                                     reason="APPROVAL_EVENT_REQUIRED")
                    except ContractRegistryError:
                        pass
            contracts[contract_id] = entry
        development_local_native_source = {
            "status": "NOT_CHECKED", "formal_source_acceptance": False,
            "official_tdx_zip": False, "production_head_eligible": False,
        }
        if target_trade_date:
            try:
                from workbench_db.v4_native import workspace_logical_id
                from workbench_analysis.tdx_local_snapshot import (
                    LOCAL_NATIVE_DEV_CONTRACT_ID, LOCAL_NATIVE_DEV_CONTRACT_VERSION,
                    _canonical_json, validate_local_native_dev_record,
                )
                forward_table = cursor.execute("SELECT to_regclass('v4.forward_facts')").fetchone()
                if forward_table and forward_table[0]:
                    candidate_contract = load_unapproved_dev_contract_candidate(
                        cursor, LOCAL_NATIVE_DEV_CONTRACT_ID, LOCAL_NATIVE_DEV_CONTRACT_VERSION,
                        expected_database_identity=identity,
                    )
                    fact_key_prefix = "tdx-local-native:" + target_trade_date.replace("-", "") + ":"
                    fact = cursor.execute(
                        """SELECT payload,payload_sha256,fact_key FROM v4.forward_facts
                            WHERE workspace_namespace=%s AND kind=%s AND fact_key LIKE %s
                            ORDER BY payload::jsonb #>> '{manifest,source_observed_at_utc}' DESC,
                                     fact_key COLLATE "C" DESC LIMIT 1""",
                        (workspace_logical_id(_repo_root() / "data/v4/historical_source_ingress_pg_r1") + ":forward",
                         "tdx_local_native_dev_candidate", fact_key_prefix + "%"),
                    ).fetchone()
                    if fact:
                        raw = str(fact[0]).encode("utf-8")
                        record = json.loads(raw)
                        payload_sha = hashlib.sha256(raw).hexdigest()
                        expected_candidate_sha = hashlib.sha256(_canonical_json(
                            {key: value for key, value in record.items() if key != "candidate_sha256"}
                        )).hexdigest()
                        errors = validate_local_native_dev_record(
                            record, contract_sha256=candidate_contract.raw_sha256,
                        )
                        if payload_sha != str(fact[1]).strip():
                            errors.append("LOCAL_NATIVE_DEV_PG_PAYLOAD_SHA_MISMATCH")
                        if expected_candidate_sha != record.get("candidate_sha256"):
                            errors.append("LOCAL_NATIVE_DEV_CANDIDATE_SHA_MISMATCH")
                        if fact[2] != fact_key_prefix + str(record.get("candidate_sha256")):
                            errors.append("LOCAL_NATIVE_DEV_FACT_KEY_MISMATCH")
                        if record.get("manifest", {}).get("trade_date") != target_trade_date:
                            errors.append("LOCAL_NATIVE_DEV_T0_MISMATCH")
                        if not errors:
                            development_local_native_source = {
                                "status": "DEV_VALIDATED_READ_ONLY_PG_READER",
                                "trade_date": target_trade_date,
                                "candidate_sha256": record["candidate_sha256"],
                                "pg_payload_sha256": payload_sha,
                                "target_rows_sha256": record["manifest"]["target_rows_sha256"],
                                "target_bar_count": record["manifest"]["target_bar_count"],
                                "universe_candidate_count": record["manifest"]["universe_count"],
                                "contract_id": candidate_contract.contract_id,
                                "contract_raw_sha256": candidate_contract.raw_sha256,
                                "contract_status": "DEV_CANDIDATE_NO_APPROVAL_EVENT",
                                "owner_candidate_status": record.get("owner_candidate", {}).get("status"),
                                "baostock_diagnostic_status": record["manifest"]["baostock_diagnostics"]["result"]["status"],
                                "baostock_diagnostic_only": True,
                                "formal_source_acceptance": False, "official_tdx_zip": False,
                                "production_head_eligible": False,
                            }
                        else:
                            development_local_native_source.update(
                                status="BLOCKED_INVALID_DEV_CANDIDATE", fact_key=fact[2], reason_codes=errors,
                            )
                    else:
                        development_local_native_source.update(
                            status="NOT_FOUND_FOR_TARGET_T0", trade_date=target_trade_date,
                        )
            except Exception as exc:
                development_local_native_source.update(
                    status="READER_ERROR", reason_code=str(exc).split(":", 1)[0],
                )
        try:
            acceptance_authority = load_unique_current_approved_contract(
                cursor, "V4_DAILY_SOURCE_ACCEPTANCE_AUTHORITY_REGISTRY_R1", "1.0.0",
                expected_database_identity=identity,
            )
            source_acceptance_authority = {
                "status": "APPROVED_READ", "raw_sha256": acceptance_authority.raw_sha256,
                "namespace": acceptance_authority.namespace,
                "source_revision": acceptance_authority.approval_source_revision,
            }
        except ContractRegistryError as exc:
            source_acceptance_authority = {"status": "MISSING", "reason": str(exc)}
        try:
            bao_contract = load_unique_current_approved_contract(
                cursor, "BAOSTOCK_SUPPLEMENTAL_SOURCE_V1", "1.1.0",
                expected_database_identity=identity,
            )
            bao_document = bao_contract.parsed_json
            baostock_supplemental_contract = {
                "registry_status": "APPROVED_READ", "raw_sha256": bao_contract.raw_sha256,
                "contract_status": bao_document.get("status") if isinstance(bao_document, Mapping) else None,
            }
        except ContractRegistryError as exc:
            baostock_supplemental_contract = {"registry_status": "MISSING", "reason": str(exc)}
        source_candidates = []
        source_candidate_errors = []
        source_relations = ("source_packages", "source_package_facts", "source_revisions")
        missing_source_relations = [name for name in source_relations if not catalog[name]]
        candidate_overflow = False
        if missing_source_relations:
            source_candidate_errors.append(
                "SOURCE_ACCEPTANCE_RELATION_MISSING:" + ",".join(missing_source_relations)
            )
        else:
            if target_trade_date is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", target_trade_date):
                raise ValueError("TARGET_TRADE_DATE_INVALID")
            if target_trade_date is None:
                package_rows = cursor.execute(
                    """SELECT package_id, package_sha256, target_trade_date, manifest, accepted_scope
                         FROM v4.source_packages
                        WHERE accepted_scope='ACCEPTED_SOURCE_PACKAGE'
                          AND pg_column_size(manifest) <= 1048576
                        ORDER BY target_trade_date DESC, created_at DESC, package_id
                        LIMIT %s""", (MAX_ACCEPTED_PACKAGE_CANDIDATES + 1,),
                ).fetchall()
            else:
                package_rows = cursor.execute(
                    """SELECT package_id, package_sha256, target_trade_date, manifest, accepted_scope
                         FROM v4.source_packages
                        WHERE accepted_scope='ACCEPTED_SOURCE_PACKAGE'
                          AND target_trade_date=%s AND pg_column_size(manifest) <= 1048576
                        ORDER BY created_at DESC, package_id
                        LIMIT %s""", (target_trade_date, MAX_ACCEPTED_PACKAGE_CANDIDATES + 1),
                ).fetchall()
            candidate_overflow = len(package_rows) > MAX_ACCEPTED_PACKAGE_CANDIDATES
            packages = package_rows[:MAX_ACCEPTED_PACKAGE_CANDIDATES]
            if candidate_overflow:
                source_candidate_errors.append("SOURCE_CANDIDATE_LIMIT_EXCEEDED")
            for package_id, package_sha, target_date, manifest, accepted_scope in packages:
                package = {
                    "package_id": package_id, "package_sha256": str(package_sha).strip().lower(),
                    "target_trade_date": target_date.isoformat() if hasattr(target_date, "isoformat") else str(target_date),
                    "manifest": manifest, "accepted_scope": accepted_scope,
                }
                rows = cursor.execute(
                    """SELECT f.source_key, f.logical_fact_id, trim(f.fact_digest),
                              f.source_fact_sha256, f.record_locator, f.record_count, f.byte_count,
                              r.source_revision_id, r.revision_no, r.digest,
                              r.source_package_id, r.source_package_source_key,
                              trim(r.source_fact_digest), r.observed_at, r.ingested_at,
                              r.system_available_at
                         FROM v4.source_package_facts AS f
                         LEFT JOIN v4.source_revisions AS r
                           ON r.source_package_id=f.package_id
                          AND r.logical_fact_id=f.logical_fact_id
                        WHERE f.package_id=%s
                        ORDER BY f.source_key, f.logical_fact_id
                        LIMIT %s""",
                    (package_id, MAX_PACKAGE_FACT_ROWS + 1),
                ).fetchall()
                facts = [{
                    "source_key": row[0], "logical_fact_id": row[1], "fact_digest": row[2],
                    "source_fact_sha256": str(row[3]).strip() if row[3] else None,
                    "record_locator": row[4], "record_count": row[5], "byte_count": row[6],
                    "source_revision_id": row[7], "revision_no": row[8], "digest": str(row[9]).strip() if row[9] else None,
                    "source_package_id": row[10], "source_package_source_key": row[11],
                    "source_fact_digest": str(row[12]).strip() if row[12] else None,
                    "observed_at": row[13], "ingested_at": row[14], "system_available_at": row[15],
                } for row in rows]
                if len(facts) > MAX_PACKAGE_FACT_ROWS:
                    errors = ["PACKAGE_FACT_ROW_LIMIT_EXCEEDED"]
                    verified = False
                else:
                    try:
                        verify_source_package_manifest_authority(manifest, pg=cursor)
                        verified = True
                    except Exception:
                        verified = False
                    errors = _package_acceptance_errors(package, facts, acceptance_verified=verified)
                item = {"package": package, "facts": facts, "accepted": not errors, "errors": errors}
                source_candidates.append(item)
                if errors:
                    source_candidate_errors.extend(errors)
        accepted_source = None if candidate_overflow else next((item for item in source_candidates if item["accepted"]), None)
        raw_receipt, raw_receipt_verified = None, False
        raw_reason = _raw_receipt_reason(
            table_exists=bool(catalog.get("stage00_raw_owner_receipts")),
            accepted_source_exists=bool(accepted_source),
        )
        if accepted_source and catalog.get("stage00_raw_owner_receipts"):
            tdx_fact = next((row for row in accepted_source["facts"] if row.get("source_key") == "tdx"), None)
            if tdx_fact and tdx_fact.get("source_revision_id"):
                try:
                    raw_receipt, raw_receipt_verified = read_raw_owner_receipt(
                        cursor, trade_date=accepted_source["package"]["target_trade_date"],
                        source_package_id=accepted_source["package"]["package_id"],
                        source_revision_id=tdx_fact["source_revision_id"],
                    )
                    raw_reason = _raw_receipt_reason(
                        table_exists=True, accepted_source_exists=True,
                        receipt_exists=raw_receipt is not None,
                        verified=bool(raw_receipt_verified),
                    )
                except Exception as exc:
                    raw_receipt = None
                    raw_reason = _raw_receipt_reason(
                        table_exists=True, accepted_source_exists=True, read_error=str(exc),
                    )
        catalog_missing = [name for name, found in catalog.items() if not found]
        return {
            "database_identity": identity, "read_role": role, "catalog": catalog,
            "catalog_missing": catalog_missing, "contracts": contracts,
            "development_local_native_source": development_local_native_source,
            "source_acceptance_authority": source_acceptance_authority,
            "baostock_supplemental_contract": baostock_supplemental_contract,
            "missing_contract_versions": [key for key, value in contracts.items() if value["status"] != "APPROVED_READ"],
            **counts,
            "source_acceptance": {
                "status": "ACCEPTED" if accepted_source else ("UNKNOWN" if missing_source_relations else "BLOCKED"),
                "candidate_count": len(source_candidates),
                "accepted_candidate_count": sum(1 for item in source_candidates if item["accepted"]),
                "candidate_errors": sorted(set(source_candidate_errors)),
                "accepted_evidence": accepted_source,
            },
            "raw_bootstrap_receipt": raw_receipt,
            "raw_bootstrap_receipt_verified": raw_receipt_verified,
            "raw_bootstrap": {"status": "PRESENT" if raw_receipt_verified else "NOT_PRESENT", "reason": raw_reason or None},
            "lifecycle_t0_board_counts": lifecycle_t0_board_counts,
            "valid_publication_head_count": valid_publication_head_count,
            "target_trade_date": target_trade_date,
        }



def _supplemental_baostock_stage(pg: Mapping[str, Any]) -> dict[str, Any]:
    contract = pg.get("baostock_supplemental_contract", {})
    source = pg.get("source_acceptance", {})
    evidence = source.get("accepted_evidence") if isinstance(source, Mapping) else None
    facts = evidence.get("facts", []) if isinstance(evidence, Mapping) else []
    bound = bool(source.get("status") == "ACCEPTED" and any(
        row.get("source_key") == "native_baostock" and row.get("source_revision_id")
        for row in facts if isinstance(row, Mapping)
    ))
    operational_contract = (
        contract.get("registry_status") == "APPROVED_READ"
        and contract.get("contract_status") in {"ACCEPTED", "OPERATIONAL_ACCEPTED"}
    )
    ready = operational_contract and bound
    reasons = []
    if contract.get("registry_status") != "APPROVED_READ":
        reasons.append("BAOSTOCK_SUPPLEMENTAL_PG_CONTRACT_NOT_APPROVED")
    elif not operational_contract:
        reasons.append("BAOSTOCK_SUPPLEMENTAL_CONTRACT_NOT_OPERATIONALLY_ACCEPTED")
    if not bound:
        reasons.append("BAOSTOCK_SUPPLEMENTAL_ACCEPTED_SOURCE_EVIDENCE_MISSING")
    return {
        "status": "DEGRADED_PASS", "owner": "V4-00F",
        "source": "PG-approved BaoStock supplemental contract and accepted native source revision",
        "evidence": [f"baostock_contract={contract}", f"accepted_native_baostock_revision={bound}"],
        "degraded_scopes": [] if ready else ["BAOSTOCK_SUPPLEMENTAL"],
        "blocked_scopes": [] if ready else ["BAOSTOCK_SUPPLEMENTAL"],
        "allowed_capabilities": ["BAOSTOCK_SUPPLEMENTAL"] if ready else [],
        "blocks_v4_01": False, "reason_codes": reasons or ["SUPPLEMENTAL_SOURCE_OPTIONAL"],
    }


def run_stage00_diagnostic(*, mode: str = "doctor", tdx_root: str | None = None, trade_date: str | None = None) -> dict[str, Any]:
    """Run bounded real Stage00 diagnostics without modifying PG or source files."""
    report: dict[str, Any] = {
        "git_commit_sha": _source_head_sha(), "sampled_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_mode": mode, "execution_status": "FAILED", "phase0_status": "BLOCKED",
        "v4_01_entry_permission": "BLOCKED", "database_identity": "UNKNOWN",
        "contract_versions_read": [], "missing_contract_versions": list(STAGE00_CONTRACTS),
        "tdx_observation_date": None, "real_source_acceptance": "UNKNOWN",
        "raw_bootstrap": {"status": "UNKNOWN", "reason": "NOT_CHECKED"}, "side_effects": "NONE",
    }
    try:
        if mode == "acceptance" and not trade_date:
            raise ValueError("TARGET_TRADE_DATE_REQUIRED")
        pg = _pg_snapshot(target_trade_date=trade_date) if trade_date else _pg_snapshot()
        report["target_trade_date"] = trade_date
        report["database_identity"] = pg["database_identity"]
        report["pg_read_role"] = pg["read_role"]
        report["pg_catalog"] = pg["catalog"]
        report["pg_catalog_missing"] = pg["catalog_missing"]
        report["contract_registry"] = pg["contracts"]
        report["source_acceptance_authority"] = pg.get("source_acceptance_authority", {"status": "UNKNOWN"})
        report["development_local_native_source"] = pg.get("development_local_native_source", {
            "status": "NOT_CHECKED", "formal_source_acceptance": False,
            "official_tdx_zip": False, "production_head_eligible": False,
        })
        report["contract_versions_read"] = [
            {"contract_id": key, **{name: value[name] for name in ("version", "raw_sha256", "namespace", "source_revision", "status", "reason") if name in value}}
            for key, value in pg["contracts"].items() if value.get("raw_sha256")
        ]
        report["missing_contract_versions"] = pg["missing_contract_versions"]
        report["pg_counts"] = {
            key: pg.get(key) for key in (
                "source_revision_count", "accepted_source_package_count", "publication_head_count",
                "model_namespace_count", "lifecycle_history_count", "lifecycle_history_security_count",
                "lifecycle_fact_count", "raw_owner_receipt_count",
                "valid_publication_head_count",
            )
        }
        report["lifecycle_t0_board_counts"] = pg.get("lifecycle_t0_board_counts", {})
        report["raw_bootstrap"] = pg["raw_bootstrap"]
        report["source_acceptance"] = {
            key: pg["source_acceptance"][key]
            for key in ("status", "candidate_count", "accepted_candidate_count", "candidate_errors")
        }
        report["real_source_acceptance"] = pg["source_acceptance"]["status"]
        config_path = _repo_root() / "config" / "paths.yaml"
        root = _tdx_root(config_path, tdx_root)
        tdx = _read_tdx_samples(root)
        report["tdx"] = tdx
        report["tdx_observation_date"] = tdx["tdx_observation_date"]
        contract_missing = pg["missing_contract_versions"]
        source_acceptance = pg["source_acceptance"]
        source_accepted = source_acceptance["status"] == "ACCEPTED"
        raw_errors = _raw_bootstrap_errors(
            pg.get("raw_bootstrap_receipt"), source_acceptance.get("accepted_evidence") or {},
            receipt_verified=bool(pg.get("raw_bootstrap_receipt_verified", False)),
        )
        read_status = pg.get("raw_bootstrap", {}).get("reason")
        if read_status and read_status.startswith(("MISSING_RUNTIME_RECEIPT_PRODUCER", "RAW_OWNER_RECEIPT_READ_OR_VERIFY_FAILED")):
            raw_errors.append(read_status)
        report["raw_bootstrap"] = {
            "status": "ACCEPTED" if not raw_errors else "BLOCKED",
            "reason_codes": raw_errors,
            "receipt_read_status": pg.get("raw_bootstrap", {}).get("reason"),
        }
        namespaces_present = bool(pg["model_namespace_count"])
        publication_schema_ready = all(pg["catalog"].get(name, False) for name in (
            "publications", "model_namespaces", "publication_heads", "state_heads",
        ))
        heads_present = bool(pg["publication_head_count"])
        lifecycle_schema_ready = pg["catalog"]["security_lifecycle_facts"] and pg["catalog"]["security_lifecycle_history"]
        accepted_evidence = source_acceptance.get("accepted_evidence") or {}
        package = accepted_evidence.get("package") if isinstance(accepted_evidence, Mapping) else None
        coverage = package.get("manifest", {}).get("accepted_board_coverage") if isinstance(package, Mapping) else None
        expected_lifecycle_counts = {}
        if isinstance(coverage, Mapping):
            coverage_counts = coverage.get("counts", {})
            suspended_counts = coverage.get("suspended_counts", {})
            if isinstance(coverage_counts, Mapping) and isinstance(suspended_counts, Mapping):
                expected_lifecycle_counts = {
                    board: int(coverage_counts.get(board, 0)) + int(suspended_counts.get(board, 0))
                    for board in TDX_BOARD_SCOPES
                }
        actual_lifecycle_counts = pg.get("lifecycle_t0_board_counts", {})
        lifecycle_scope_ready = bool(
            lifecycle_schema_ready and trade_date and source_accepted and package
            and package.get("target_trade_date") == trade_date
            and set(expected_lifecycle_counts) == set(TDX_BOARD_SCOPES)
            and actual_lifecycle_counts == expected_lifecycle_counts
            and all(value > 0 for value in expected_lifecycle_counts.values())
        )
        lifecycle_reason = (
            "LIFECYCLE_T0_SOURCE_SCOPE_VERIFIED" if lifecycle_scope_ready else
            "LIFECYCLE_T0_DATE_REQUIRED" if not trade_date else
            "LIFECYCLE_ACCEPTED_SOURCE_REQUIRED" if not source_accepted else
            "LIFECYCLE_OWNER_FACTS_OR_BOARD_COVERAGE_MISMATCH"
        )
        # PUBLICATION_IDENTITY is the usable publication/namespace mechanism,
        # which V4-01 needs in order to create its first candidate. Requiring an
        # already accepted T0 Head here would make first startup circular.
        publication_scope_ready = publication_schema_ready
        publication_reason = (
            "PUBLICATION_IDENTITY_MECHANISM_READY"
            if publication_scope_ready and pg.get("valid_publication_head_count", 0) == 0 else
            "PUBLICATION_T0_HEAD_BINDING_VERIFIED" if publication_scope_ready else
            "PUBLICATION_IDENTITY_RELATION_MISSING"
        )
        sample_ready = not tdx["failures"] and tdx["valid_sample_count"] == len(TDX_SAMPLES)
        stages = {
            "V4-00A": {"status": "DEGRADED_PASS", "owner": "V4-00A", "source": "PG identity/catalog read", "evidence": ["database identity attested", "repeatable-read transaction is read-only"], "reason_codes": ["BACKUP_RECOVERY_RECEIPT_NOT_CHECKED"]},
            "V4-00B": {"status": "DEGRADED_PASS" if lifecycle_schema_ready else "BLOCKED", "owner": "V4-00B", "scope": "LIFECYCLE_SCHEMA", "source": "T0 accepted-source-bound PG Owner facts", "evidence": [f"history_rows={pg.get('lifecycle_history_count')}", f"lifecycle_fact_rows={pg.get('lifecycle_fact_count')}", f"accepted_t0_board_counts={actual_lifecycle_counts}", f"expected_t0_board_counts={expected_lifecycle_counts}"], "blocked_scopes": [] if lifecycle_scope_ready else ["LIFECYCLE_SCHEMA"], "allowed_capabilities": ["LIFECYCLE_SCHEMA"] if lifecycle_scope_ready else [], "blocks_v4_01": not lifecycle_scope_ready, "reason_codes": [lifecycle_reason]},
            "V4-00C": {"status": "DEGRADED_PASS" if publication_schema_ready else "BLOCKED", "owner": "V4-00C", "scope": "PUBLICATION_IDENTITY", "source": "Accepted publication, namespace and state-head PG bindings", "evidence": ["publication identity relations present" if publication_schema_ready else "publication identity relation missing", f"publication_heads={pg['publication_head_count']}", f"valid_t0_publication_heads={pg.get('valid_publication_head_count', 0)}"], "blocked_scopes": [] if publication_scope_ready else ["PUBLICATION_IDENTITY"], "allowed_capabilities": ["PUBLICATION_IDENTITY"] if publication_scope_ready else [], "blocks_v4_01": not publication_scope_ready, "reason_codes": [publication_reason]},
            "V4-00D": _source_owner_stage(source_acceptance, sample_ready, tdx),
            "V4-00E": _raw_owner_stage(raw_errors),
            "V4-00F": _supplemental_baostock_stage(pg),
            "V4-00G": {"status": "BLOCKED" if contract_missing else "DEGRADED_PASS", "owner": "V4-00G", "source": "PG-only contract registry", "evidence": [f"approved_required_contracts={len(STAGE00_CONTRACTS)-len(contract_missing)}/{len(STAGE00_CONTRACTS)}", f"dev_candidate_contracts={sum(1 for row in pg['contracts'].values() if row['status'] == 'DEV_CANDIDATE_READ')}"], "reason_codes": ["CONTRACT_APPROVAL_EVENT_REQUIRED"] if any(row["status"] == "DEV_CANDIDATE_READ" for row in pg["contracts"].values()) else (["APPROVED_STAGE00_CONTRACTS_MISSING"] if contract_missing else ["PARAMETER_EFFECTIVE_STATE_NOT_PROVEN"])},
            "V4-00H": {"status": "BLOCKED" if contract_missing else "DEGRADED_PASS", "owner": "V4-00H", "source": "PG-only final acceptance contract and actual Stage00 evidence", "evidence": [f"missing_contract_versions={len(contract_missing)}"], "reason_codes": ["FINAL_ACCEPTANCE_CONTRACT_OR_EVIDENCE_MISSING"] if contract_missing else ["EXTERNAL_ACCEPTANCE_NOT_COMPLETE"]},
        }
        # Keep the gate's existing scope ownership and required-scope semantics.
        gate = evaluate_phase0(stages)
        report["stages"] = {
            key: {**value, **gate["stages"].get(key, {})} for key, value in stages.items()
        }
        report["entry_gate"] = gate["entry_gate"]
        report["phase0_status"] = gate["phase0_status"]
        report["v4_01_entry_permission"] = gate["v4_01_entry_permission"]
        report["execution_status"] = "OK"
        report["execution_reason"] = "DIAGNOSTICS_COMPLETED; BUSINESS_ACCEPTANCE_GAPS_REPORTED_AS_BLOCKED"
        report["head_present"] = heads_present
        report["namespace_present"] = namespaces_present
    except Exception as exc:
        report["execution_status"] = "FAILED"
        report["execution_reason"] = str(exc) if str(exc) else type(exc).__name__
        report["failure_type"] = type(exc).__name__
    return report


def fixture_test_result() -> dict[str, Any]:
    """Exercise fail-closed aggregation without PG or market data inputs."""
    stages = {stage: {"status": "BLOCKED", "reason_codes": ["FIXTURE_MISSING_REAL_EVIDENCE"]} for stage in STAGES}
    result = evaluate_phase0(stages)
    passed = result["phase0_status"] == "BLOCKED" and result["v4_01_entry_permission"] == "BLOCKED"
    return {"run_mode": "fixture-test", "execution_status": "OK" if passed else "FAILED",
            "fixture_test_status": "PASS" if passed else "FAIL",
            "phase0_status": result["phase0_status"], "v4_01_entry_permission": result["v4_01_entry_permission"],
            "side_effects": "NONE", "scope": "PURE_GATE_RULES_ONLY"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="V4 Stage00 real read-only diagnostics")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("doctor", "acceptance"):
        child = sub.add_parser(command)
        child.add_argument("--json", action="store_true", help="emit structured JSON")
        child.add_argument("--tdx-root", help="read-only source root override for bounded diagnostics")
        child.add_argument("--trade-date", required=command == "acceptance", help="exact T0 required for acceptance")
    fixture = sub.add_parser("fixture-test")
    fixture.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "fixture-test":
        result = fixture_test_result()
        exit_code = 0 if result["execution_status"] == "OK" else 1
    else:
        result = run_stage00_diagnostic(mode=args.command, tdx_root=args.tdx_root,
                                        trade_date=getattr(args, "trade_date", None))
        if result["execution_status"] != "OK":
            exit_code = 1
        elif args.command == "acceptance" and result["phase0_status"] == "BLOCKED":
            exit_code = 2
        else:
            exit_code = 0
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
