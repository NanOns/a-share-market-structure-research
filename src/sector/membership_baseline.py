"""Versioned, fail-closed membership snapshot primitives for V4-08."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence


FORMAL_SECTOR_TYPES = frozenset({"INDUSTRY", "THEME"})
FORMAL_REQUIRED_BOARDS = frozenset({"SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"})
FORMAL_IDENTITY_BLOCKERS = frozenset({"TRUE_IDENTITY_GAP", "AMBIGUOUS_IDENTITY"})
ALL_SECTOR_TYPES = frozenset({"INDUSTRY", "THEME", "STYLE", "UNKNOWN"})
MEMBERSHIP_BASES = frozenset({
    "PIT_OBSERVED", "CURRENT_TDX_MEMBERSHIP", "CURRENT_MEMBERSHIP_REPLAY", "DERIVED_PARENT_MEMBERSHIP"
})
FACT_KEY = ("sector_id", "security_id")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def parse_timestamp(value: str | datetime) -> datetime:
    result = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return result.astimezone(timezone.utc)


def canonical_timestamp(value: str | datetime) -> str:
    return parse_timestamp(value).isoformat(timespec="microseconds").replace("+00:00", "Z")


def identity_postcheck(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    duplicate_groups: dict[tuple[Any, Any], int] = defaultdict(int)
    sector_names: dict[tuple[Any, Any], set[str]] = defaultdict(set)
    unknown_identity_rows = []
    for row in rows:
        identity = row.get("security_id") or f"UNKNOWN:{row.get('source_security_key', '')}"
        key = (row.get("sector_id"), identity)
        duplicate_groups[key] += 1
        sector_names[(row.get("sector_type"), row.get("sector_code"))].add(str(row.get("sector_name", "")))
        if row.get("identity_status") != "MAPPED" or not row.get("security_id"):
            unknown_identity_rows.append(str(row.get("source_security_key", "")))
    duplicates = [list(k) for k, count in duplicate_groups.items() if count > 1]
    sector_name_conflicts = [list(k) for k, names in sector_names.items() if len(names) > 1]
    return {
        "row_count": len(rows),
        "duplicate_fact_count": len(duplicates),
        "duplicate_fact_keys": duplicates,
        "sector_name_conflict_count": len(sector_name_conflicts),
        "sector_name_conflicts": sector_name_conflicts,
        "unknown_identity_count": len(unknown_identity_rows),
        "unknown_identity_source_keys": sorted(set(unknown_identity_rows)),
        "status": "PASS" if not duplicates and not sector_name_conflicts and not unknown_identity_rows else "BLOCKED",
    }


def map_source_sector_type(source_type: str, registry: Mapping[str, str]) -> str:
    value = registry.get(str(source_type).lower(), "UNKNOWN")
    return value if value in ALL_SECTOR_TYPES else "UNKNOWN"


def formal_membership_eligible(row: Mapping[str, Any]) -> bool:
    try:
        cutoff = parse_timestamp(row.get("cutoff"))
        provider_available = parse_timestamp(row.get("provider_available_at"))
        system_available = parse_timestamp(row.get("system_available_at"))
        target_date = date.fromisoformat(str(row.get("target_trade_date")))
        asof_date = date.fromisoformat(str(row.get("membership_asof_date")))
    except (TypeError, ValueError):
        return False
    return (
        row.get("sector_type") in FORMAL_SECTOR_TYPES
        and row.get("membership_basis") == "PIT_OBSERVED"
        and row.get("membership_quality") == "PIT_OBSERVED_ACCEPTED"
        and row.get("snapshot_membership_quality") == "PIT_OBSERVED_ACCEPTED"
        and row.get("source_revision_quality") == "PIT_OBSERVED_ACCEPTED"
        and row.get("pit_observed") is True
        and row.get("historical_backtest_safe") is True
        and row.get("identity_status") == "MAPPED"
        and bool(row.get("security_id"))
        and row.get("source_revision_chain_valid") is True
        and provider_available <= cutoff
        and system_available <= cutoff
        and asof_date == target_date
    )


def build_source_revision_identity(source_bytes_digest: str, temporal_evidence: Mapping[str, Any]) -> dict[str, str]:
    """Bind immutable source bytes and a separately versionable temporal evidence record."""
    if len(source_bytes_digest) != 64 or any(ch not in "0123456789abcdef" for ch in source_bytes_digest):
        raise ValueError("source_bytes_digest must be lowercase SHA-256")
    evidence_digest = sha256_json(temporal_evidence)
    revision_digest = sha256_json({
        "source_bytes_digest": source_bytes_digest,
        "temporal_evidence_digest": evidence_digest,
    })
    return {
        "source_bytes_digest": source_bytes_digest,
        "temporal_evidence_digest": evidence_digest,
        "source_revision_id": f"sha256:{revision_digest}",
    }


def validate_snapshot_basis(rows: Sequence[Mapping[str, Any]], membership_basis: str) -> dict[str, Any]:
    """A snapshot header owns exactly one membership basis; rows may not override it."""
    mismatches = [
        {"sector_id": row.get("sector_id"), "source_security_key": row.get("source_security_key"),
         "row_basis": row.get("membership_basis")}
        for row in rows if row.get("membership_basis") != membership_basis
    ]
    return {
        "status": "PASS" if not mismatches else "BLOCKED",
        "snapshot_membership_basis": membership_basis,
        "row_count": len(rows),
        "basis_mismatch_count": len(mismatches),
        "basis_mismatches": mismatches,
    }


def formal_identity_scope_gate(classifications: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Only unresolved identities in required four-board scope block that scope."""
    blockers = [row for row in classifications
                if row.get("classification") in FORMAL_IDENTITY_BLOCKERS
                and row.get("formal_board_candidate") in FORMAL_REQUIRED_BOARDS]
    by_board = {board: sum(row.get("formal_board_candidate") == board for row in blockers)
                for board in sorted(FORMAL_REQUIRED_BOARDS)}
    return {
        "status": "BLOCKED" if blockers else "PASS",
        "blocking_key_count": len(blockers),
        "blocking_keys_by_board": by_board,
        "non_core_or_optional_keys_do_not_block": True,
    }


def validate_forward_target_date(target_trade_date: str, first_complete_observation_at: str | datetime) -> dict[str, Any]:
    """Never let a forward candidate date precede the first complete observed source bundle."""
    observation_date = parse_timestamp(first_complete_observation_at).date()
    target = date.fromisoformat(target_trade_date)
    return {
        "status": "PASS" if target >= observation_date else "BLOCKED",
        "target_trade_date": target.isoformat(),
        "first_complete_observation_date": observation_date.isoformat(),
        "reason": None if target >= observation_date else "TARGET_PRECEDES_FIRST_COMPLETE_SOURCE_OBSERVATION",
    }


def select_available_revisions(revisions: Sequence[Mapping[str, Any]], cutoff: str | datetime) -> list[Mapping[str, Any]]:
    cutoff_dt = parse_timestamp(cutoff)
    selected = []
    for revision in revisions:
        available = revision.get("system_available_at")
        if not available:
            raise ValueError("system_available_at is required; unknown availability cannot be treated as available")
        if parse_timestamp(available) <= cutoff_dt:
            selected.append(revision)
    return selected


def validate_revision_chain(revisions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_id: dict[str, Mapping[str, Any]] = {}
    successor_count: dict[str, int] = defaultdict(int)
    errors: list[str] = []
    for revision in revisions:
        revision_id = str(revision.get("source_revision_id", ""))
        if not revision_id or revision_id in by_id:
            errors.append("MISSING_OR_DUPLICATE_REVISION_ID")
            continue
        by_id[revision_id] = revision
        previous = revision.get("supersedes_revision_id")
        if previous:
            successor_count[str(previous)] += 1
    if any(count > 1 for count in successor_count.values()):
        errors.append("REVISION_FORK")
    for revision in revisions:
        previous = revision.get("supersedes_revision_id")
        if previous and str(previous) not in by_id:
            errors.append("MISSING_SUPERSEDED_REVISION")
        seen = {str(revision.get("source_revision_id"))}
        cursor = previous
        while cursor:
            if str(cursor) in seen:
                errors.append("REVISION_CYCLE")
                break
            seen.add(str(cursor))
            parent = by_id.get(str(cursor))
            cursor = parent.get("supersedes_revision_id") if parent else None
    return {"status": "PASS" if not errors else "BLOCKED", "errors": sorted(set(errors)), "revision_count": len(by_id)}


def verify_file_digests(expected: Mapping[str, str], actual: Mapping[str, str]) -> dict[str, Any]:
    mismatches = [key for key, value in expected.items() if actual.get(key) != value]
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    return {"status": "PASS" if not mismatches and not missing and not extra else "BLOCKED", "mismatches": mismatches, "missing": missing, "extra": extra}


def snapshot_payload(
    *, target_trade_date: str | date, cutoff: str | datetime, sector_type_registry_digest: str,
    source_revision_ids: Iterable[str], source_digest: str, source_file_digests: Mapping[str, str],
    rows: Sequence[Mapping[str, Any]], membership_basis: str, membership_quality: str,
    parent_snapshot_id: str | None = None,
) -> dict[str, Any]:
    if membership_basis not in MEMBERSHIP_BASES:
        raise ValueError(f"unsupported membership basis: {membership_basis}")
    stable_rows = []
    for row in rows:
        stable_rows.append({key: row.get(key) for key in (
            "sector_id", "sector_code", "sector_name", "sector_type", "security_id", "source_security_key",
            "source_sector_type", "membership_basis", "membership_quality", "pit_observed",
            "historical_backtest_safe", "identity_status", "child_sector_ids",
            "source_snapshot_id", "parent_snapshot_id", "parent_source_revision_id",
        ) if key in row})
    stable_rows.sort(key=lambda row: (
        str(row.get("sector_type", "")), str(row.get("sector_id", "")),
        str(row.get("security_id", "")), str(row.get("source_security_key", ""))
    ))
    return {
        "target_trade_date": str(target_trade_date),
        "cutoff": canonical_timestamp(cutoff),
        "sector_type_registry_digest": sector_type_registry_digest,
        "source_revision_ids": sorted(set(str(x) for x in source_revision_ids)),
        "source_digest": source_digest,
        "source_file_digests": dict(sorted(source_file_digests.items())),
        "membership_rows": stable_rows,
        "membership_basis": membership_basis,
        "membership_quality": membership_quality,
        "parent_snapshot_id": parent_snapshot_id,
    }


def snapshot_digest(**kwargs: Any) -> str:
    return sha256_json(snapshot_payload(**kwargs))


def classify_replay_rows(rows: Sequence[Mapping[str, Any]], target_trade_date: str) -> list[dict[str, Any]]:
    replayed = []
    for row in rows:
        is_parent = row.get("membership_basis") == "DERIVED_PARENT_MEMBERSHIP"
        replayed.append({
            **row,
            "target_trade_date": target_trade_date,
            "membership_asof_date": None,
            "membership_basis": "DERIVED_PARENT_MEMBERSHIP" if is_parent else "CURRENT_MEMBERSHIP_REPLAY",
            "membership_quality": "DERIVED_PARENT_DIAGNOSTIC" if is_parent else "CURRENT_REPLAY_DIAGNOSTIC",
            "pit_observed": False,
            "historical_backtest_safe": False,
            "membership_asof_reason": "DERIVED_PARENT_REPLAY_RETAINS_PARENT_PROVENANCE" if is_parent else "CURRENT_SOURCE_EFFECTIVE_DATE_UNVERIFIED",
        })
    return replayed


def derive_parent_membership(
    child_rows: Sequence[Mapping[str, Any]], *, parent_code: str, child_code_to_parent: Mapping[str, str]
) -> list[dict[str, Any]]:
    output_by_security: dict[str, dict[str, Any]] = {}
    for row in child_rows:
        if row.get("sector_type") != "INDUSTRY":
            raise ValueError("parent union accepts only INDUSTRY child rows")
        child_code = str(row.get("sector_code", ""))
        if child_code_to_parent.get(child_code) != parent_code:
            raise ValueError(f"impossible cross-industry derivation: {child_code} is not a child of {parent_code}")
        security_id = str(row.get("security_id") or "")
        if not security_id:
            raise ValueError("parent union cannot silently drop an unknown security identity")
        current = output_by_security.setdefault(security_id, {
            "sector_id": f"INDUSTRY:{parent_code}", "sector_code": parent_code,
            "sector_name": str(row.get("parent_name", parent_code)), "sector_type": "INDUSTRY",
            "security_id": security_id, "source_security_key": row.get("source_security_key", security_id),
            "membership_basis": "DERIVED_PARENT_MEMBERSHIP", "membership_quality": "DERIVED_PARENT_DIAGNOSTIC",
            "pit_observed": False, "historical_backtest_safe": False, "identity_status": "MAPPED",
            "child_sector_ids": []
        })
        current["child_sector_ids"].append(str(row["sector_id"]))
    for value in output_by_security.values():
        value["child_sector_ids"] = sorted(set(value["child_sector_ids"]))
    return [output_by_security[key] for key in sorted(output_by_security)]


def seed_dependent_state(*, v4_07_real_signal_capability: str, value: Any = None) -> dict[str, Any]:
    if v4_07_real_signal_capability != "FULL":
        return {"value": None, "quality": "UNKNOWN", "reason": "DEGRADED_BY_UPSTREAM_BASE_SEED_SIGNAL"}
    return {"value": value, "quality": "OBSERVED", "reason": None}
