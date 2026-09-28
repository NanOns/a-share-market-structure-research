from __future__ import annotations

"""Daily lifecycle and special-price-phase source manifests bound to accepted inputs."""

import hashlib
import json
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

from workbench_analysis.daily_source_freeze import ensure_outside_tdx
from workbench_analysis.security_identity_event_discovery import discover_identity_events
from workbench_analysis.special_price_phases import PhasePolicyRegistry, SpecialPhaseEventStore


SPECIAL_MANIFEST_CONTRACT = "SPECIAL_PHASE_SOURCE_MANIFEST_V1"
LIFECYCLE_MANIFEST_CONTRACT = "CURRENT_LIFECYCLE_SNAPSHOT_V1"


def _source_key(value: object) -> str:
    return str(value or "").strip().upper()


def build_current_lifecycle_snapshot(
    *,
    trade_date: str,
    baseline_date: str,
    baseline_data_head: Mapping[str, Any],
    parent_universe_rows: list[Mapping[str, Any]],
    identity_records: list[Mapping[str, Any]],
    baostock_snapshot: Mapping[str, Any],
    official_session_bridge: Mapping[str, Any],
    source_evidence: Mapping[str, Any],
    observed_at: str,
    official_events: list[Mapping[str, Any]] | None = None,
    verified_evidence_digests: set[str] | None = None,
) -> dict[str, Any]:
    """Build a daily lifecycle view from accepted parent inputs and a date-bound roster.

    Absence from the current daily roster is never treated as delisting evidence.
    Ambiguous code-boundary candidates are isolated as IDENTITY_UNKNOWN rows.
    """
    try:
        target = date.fromisoformat(trade_date)
        baseline = date.fromisoformat(baseline_date)
        parsed_observed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("LIFECYCLE_SNAPSHOT_DATE_INVALID") from exc
    if baseline >= target or parsed_observed.tzinfo is None:
        raise ValueError("LIFECYCLE_SNAPSHOT_BASELINE_OR_TIME_INVALID")
    identity_permission = baseline_data_head.get("component_permissions", {}).get("IDENTITY_UNIVERSE", {})
    if (baseline_data_head.get("accepted_trade_date") != baseline_date
            or identity_permission.get("cutoff") != baseline_date
            or identity_permission.get("status") not in {"FULL_PASS", "DEGRADED_PASS"}):
        raise ValueError("LIFECYCLE_PARENT_DATA_HEAD_NOT_ACCEPTED_FOR_BASELINE")
    if (official_session_bridge.get("status") != "PASS"
            or official_session_bridge.get("latest_completed_official_session") != baseline_date
            or trade_date not in official_session_bridge.get("official_sessions_after_base_cutoff", [])):
        raise ValueError("LIFECYCLE_OFFICIAL_SESSION_BRIDGE_NOT_ACCEPTED")
    if (baostock_snapshot.get("trade_date") != trade_date
            or baostock_snapshot.get("provider_date") != trade_date
            or baostock_snapshot.get("status") not in {"BAOSTOCK_DAILY_SNAPSHOT_READY", "NOOP_SOURCE_ALREADY_FROZEN"}
            or not baostock_snapshot.get("snapshot_id")):
        raise ValueError("LIFECYCLE_TARGET_ROSTER_SOURCE_NOT_READY")

    parent_keys = {
        _source_key(row.get("source_security_key"))
        for row in parent_universe_rows
        if row.get("trade_date") == baseline_date and row.get("source_security_key")
    }
    if not parent_keys:
        raise ValueError("LIFECYCLE_ACCEPTED_PARENT_UNIVERSE_EMPTY")
    records_by_key: dict[str, list[Mapping[str, Any]]] = {}
    for record in identity_records:
        key = _source_key(record.get("source_security_key") or record.get("symbol"))
        if key:
            records_by_key.setdefault(key, []).append(record)
    active_records: dict[str, Mapping[str, Any]] = {}
    ambiguous_identity_map_keys: set[str] = set()
    for key, records in records_by_key.items():
        eligible = []
        for row in records:
            start = str(row.get("symbol_effective_from") or row.get("effective_from") or row.get("list_date") or "")
            end = str(row.get("symbol_effective_to") or row.get("effective_to") or row.get("delist_date") or "")
            if (not start or start <= trade_date) and (not end or end >= trade_date):
                eligible.append(row)
        # Dated aliases can have overlapping list/delist fields; choose the
        # latest effective source-key row only when stable identity and board agree.
        if eligible:
            identity_signatures = {
                (str(row.get("security_id") or ""), str(row.get("board") or row.get("board_scope") or ""))
                for row in eligible
            }
            if len(identity_signatures) > 1:
                ambiguous_identity_map_keys.add(key)
                continue
            active_records[key] = max(eligible,
                                      key=lambda row: str(row.get("symbol_effective_from") or row.get("effective_from") or row.get("list_date") or ""))

    daily_rows = baostock_snapshot.get("daily_rows")
    if not isinstance(daily_rows, list) or not daily_rows:
        raise ValueError("LIFECYCLE_TARGET_ROSTER_EMPTY")
    current_keys: set[str] = set()
    for row in daily_rows:
        key = _source_key(row.get("code") or row.get("source_security_key"))
        if not key or row.get("date") != trade_date or key in current_keys:
            raise ValueError("LIFECYCLE_TARGET_ROSTER_INVALID_OR_DUPLICATE")
        current_keys.add(key)

    # Use the already accepted event detector. We intentionally omit roster
    # absence transitions because a daily provider roster alone does not prove
    # delisting; dated lifecycle and official events remain eligible evidence.
    identity_lookup = {key: row for key, row in active_records.items()}
    detector = discover_identity_events(
        mode="DAILY_INCREMENTAL",
        session_dates=[baseline_date, trade_date],
        identities=identity_lookup,
        required_scope_source_keys=parent_keys | current_keys,
        lifecycle_records=identity_records,
        official_events=official_events or [],
        verified_evidence_digests=verified_evidence_digests or set(),
        target_date=trade_date,
    )
    detector_events = list(detector.get("events") or [])
    boundary_events = list(detector.get("boundary_events") or [])
    unresolved_keys = {
        _source_key(key)
        for event in detector_events
        if event.get("resolution_status") == "UNRESOLVED"
        for key in event.get("source_keys", [])
    }
    new_keys = sorted(current_keys - parent_keys)
    listing_start_keys = {
        _source_key(event.get("source_security_key"))
        for event in boundary_events if event.get("event_type") == "LISTING_START"
    }
    resolved_event_keys = {
        _source_key(key)
        for event in detector_events
        if event.get("resolution_status") != "UNRESOLVED"
        for key in event.get("source_keys", [])
    }
    missing_identity_keys = {
        key for key in current_keys
        if not active_records.get(key) or not active_records[key].get("security_id")
    }
    unknown_keys = sorted(
        missing_identity_keys | (current_keys & unresolved_keys)
        | (current_keys & ambiguous_identity_map_keys)
        | (set(new_keys) - listing_start_keys - resolved_event_keys)
    )
    rows = []
    for key in sorted(current_keys):
        identity = active_records.get(key)
        unknown = key in unknown_keys
        rows.append({
            "trade_date": trade_date,
            "source_security_key": key,
            "security_id": None if unknown or identity is None else identity.get("security_id"),
            "identity_status": "IDENTITY_UNKNOWN_REVIEW_REQUIRED" if unknown
            else "IDENTITY_BOUND" if identity and identity.get("security_id") else "IDENTITY_UNKNOWN_REVIEW_REQUIRED",
            "reason": "AMBIGUOUS_ACCEPTED_IDENTITY_MAP_ROWS" if key in ambiguous_identity_map_keys
            else "NEW_OR_UNMAPPED_SOURCE_KEY" if key in new_keys and (not identity or not identity.get("security_id"))
            else "IDENTITY_SECURITY_ID_MISSING" if key in missing_identity_keys
            else "AMBIGUOUS_ACCEPTED_IDENTITY_CANDIDATE" if key in unresolved_keys else None,
            "bao_daily_row_is_identity_authority": False,
        })
    status = "DEGRADED_PASS" if unknown_keys else "READY"
    if detector.get("candidate_count", 0) == 0 and not new_keys and not unknown_keys:
        event_status = "PASS_NO_IDENTITY_EVENT"
    elif detector.get("candidate_count", 0) == 0 and new_keys:
        event_status = "NEW_SOURCE_KEYS_ISOLATED_UNKNOWN"
    elif detector.get("candidate_count", 0) == 0 and unknown_keys:
        event_status = "EXISTING_SOURCE_KEYS_IDENTITY_UNKNOWN"
    elif unresolved_keys:
        event_status = "AMBIGUOUS_CANDIDATES_ISOLATED_TO_AFFECTED_SECURITIES"
    else:
        event_status = "DATED_IDENTITY_EVENTS_BOUND"
    payload: dict[str, Any] = {
        "contract_id": LIFECYCLE_MANIFEST_CONTRACT,
        "version": "1.0.0",
        "status": status,
        "trade_date": trade_date,
        "baseline_trade_date": baseline_date,
        "observed_at": parsed_observed.isoformat(),
        "system_available_at": parsed_observed.isoformat(),
        "source_evidence": dict(source_evidence),
        "source_revision": hashlib.sha256(
            json.dumps(source_evidence, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest(),
        "baseline_data_head_sha256": source_evidence.get("baseline_data_head_sha256"),
        "parent_universe_key_count": len(parent_keys),
        "current_roster_key_count": len(current_keys),
        "new_source_keys": new_keys,
        "unknown_source_keys": unknown_keys,
        "active_security_ids": sorted({str(row["security_id"]) for row in rows if row.get("security_id")}),
        "source_rows": rows,
        "boundary_events": boundary_events,
        "identity_detector": {"contract_id": detector.get("contract_id"),
                               "version": detector.get("version"),
                               "candidate_count": detector.get("candidate_count"),
                               "candidate_status_counts": detector.get("candidate_status_counts", {}),
                               "unresolved_required_scope_candidate_count": detector.get("unresolved_required_scope_candidate_count")},
        "event_status": event_status,
        "absence_is_delisting_evidence": False,
        "tdx_root_write_count": 0,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["manifest_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolve_inside(root: Path, relative: str, *, tdx_root: Path) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("DAILY_SOURCE_ARTIFACT_OUTSIDE_PROJECT") from exc
    ensure_outside_tdx(path, tdx_root)
    return path


def build_special_phase_source_manifest(
    *,
    trade_date: str,
    project_root: Path,
    v402_external_acceptance_path: Path,
    v402_stage_manifest_path: Path,
    event_store_path: Path,
    policy_path: Path,
    lifecycle_snapshot: Mapping[str, Any],
    observed_at: str,
    tdx_root: Path = Path("D:/new_tdx"),
) -> dict[str, Any]:
    """Bind the accepted event store and policy even when no new event starts on T."""
    try:
        date.fromisoformat(trade_date)
        parsed_observed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("SPECIAL_PHASE_MANIFEST_DATE_INVALID") from exc
    if parsed_observed.tzinfo is None:
        raise ValueError("SPECIAL_PHASE_MANIFEST_TIMEZONE_REQUIRED")
    root = project_root.resolve()
    for path in (v402_external_acceptance_path, v402_stage_manifest_path, event_store_path, policy_path):
        ensure_outside_tdx(path, tdx_root)
    acceptance = json.loads(v402_external_acceptance_path.read_text(encoding="utf-8"))
    if acceptance.get("acceptance_result", {}).get("external_acceptance") != "EXTERNALLY_ACCEPTED":
        raise ValueError("SPECIAL_PHASE_V402_ACCEPTANCE_NOT_EXTERNAL_PASS")
    stage_manifest = json.loads(v402_stage_manifest_path.read_text(encoding="utf-8"))
    accepted_manifest_ref = acceptance.get("evidence", {}).get("manifest", {})
    stage_manifest_sha = _sha(v402_stage_manifest_path)
    if accepted_manifest_ref.get("sha256") != stage_manifest_sha:
        raise ValueError("SPECIAL_PHASE_V402_MANIFEST_DIGEST_MISMATCH")
    components = stage_manifest.get("components", {})
    required_components = {
        "R6_EVENTS": event_store_path,
        "R6_POLICY": policy_path,
    }
    for component, path in required_components.items():
        record = components.get(component)
        if not isinstance(record, Mapping) or record.get("path") != path.relative_to(root).as_posix():
            raise ValueError("SPECIAL_PHASE_ACCEPTED_COMPONENT_BINDING_MISMATCH:" + component)
        if _sha(path) != record.get("sha256") or path.stat().st_size != int(record.get("bytes", -1)):
            raise ValueError("SPECIAL_PHASE_ACCEPTED_COMPONENT_DIGEST_MISMATCH:" + component)
    if (lifecycle_snapshot.get("contract_id") != LIFECYCLE_MANIFEST_CONTRACT
            or lifecycle_snapshot.get("trade_date") != trade_date
            or lifecycle_snapshot.get("status") not in {"READY", "FULL_PASS", "DEGRADED_PASS"}):
        raise ValueError("SPECIAL_PHASE_LIFECYCLE_SNAPSHOT_NOT_READY")
    lifecycle_artifact = _resolve_inside(root, str(lifecycle_snapshot.get("artifact_path") or ""), tdx_root=tdx_root)
    if _sha(lifecycle_artifact) != lifecycle_snapshot.get("artifact_sha256"):
        raise ValueError("SPECIAL_PHASE_LIFECYCLE_SNAPSHOT_DIGEST_MISMATCH")
    # Reuse the accepted runtime's event/policy validators; do not add a second phase implementation.
    events = SpecialPhaseEventStore.from_jsonl(event_store_path).events
    policies = PhasePolicyRegistry.from_json(policy_path)
    active_ids = set(str(item) for item in lifecycle_snapshot.get("active_security_ids", []))
    active_events = [
        event for event in events
        if event.security_id in active_ids
        and event.phase_effective_from <= trade_date
        and (event.phase_effective_to is None or trade_date <= event.phase_effective_to)
        and event.system_available_at[:10] <= trade_date
    ]
    newly_effective = [event.event_id for event in active_events if event.phase_effective_from == trade_date]
    payload: dict[str, Any] = {
        "contract_id": SPECIAL_MANIFEST_CONTRACT,
        "version": "1.0.0",
        "status": "READY",
        "trade_date": trade_date,
        "observed_at": parsed_observed.isoformat(),
        "system_available_at": parsed_observed.isoformat(),
        "accepted_v402_external_acceptance": {"path": v402_external_acceptance_path.relative_to(root).as_posix(),
                                               "sha256": _sha(v402_external_acceptance_path)},
        "accepted_v402_stage_manifest": {"path": v402_stage_manifest_path.relative_to(root).as_posix(),
                                         "sha256": stage_manifest_sha},
        "event_store": {"path": event_store_path.relative_to(root).as_posix(), "sha256": _sha(event_store_path),
                        "event_count": len(events)},
        "policy": {"path": policy_path.relative_to(root).as_posix(), "sha256": _sha(policy_path),
                   "contract_id": policies.contract.get("contract_id")},
        "lifecycle_snapshot": {"path": lifecycle_snapshot["artifact_path"],
                               "sha256": lifecycle_snapshot["artifact_sha256"],
                               "source_revision": lifecycle_snapshot.get("source_revision")},
        "active_event_count": len(active_events),
        "active_event_ids": sorted(event.event_id for event in active_events),
        "newly_effective_event_count": len(newly_effective),
        "newly_effective_event_ids": sorted(newly_effective),
        "event_status": "NO_NEW_SPECIAL_PHASE_EVENT" if not newly_effective else "NEW_SPECIAL_PHASE_EVENT_BOUND",
        "special_phase_runtime_reused": "src/workbench_analysis/special_price_phases.py",
        "tdx_root_write_count": 0,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["manifest_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload
