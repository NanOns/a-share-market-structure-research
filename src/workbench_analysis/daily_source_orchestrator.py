from __future__ import annotations

"""Fail-closed daily readiness state machine for the versioned source set."""

from datetime import datetime, time
from typing import Any, Mapping
from zoneinfo import ZoneInfo


SHANGHAI = ZoneInfo("Asia/Shanghai")
MARKET_CLOSE = time(15, 0)


def _ready_record(record: Mapping[str, Any] | None, *, accepted_statuses: set[str]) -> bool:
    return bool(record and record.get("status") in accepted_statuses)


def evaluate_daily_source_readiness(
    *,
    trade_date: str,
    observed_at: str,
    official_session_confirmed: bool,
    tdx_capture: Mapping[str, Any] | None,
    baostock_capture: Mapping[str, Any] | None,
    baostock_capability_accepted: bool,
    gbbq_snapshot: Mapping[str, Any] | None,
    lifecycle_snapshot: Mapping[str, Any] | None,
    special_phase_snapshot: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return the first unmet publication state; never changes a data head."""
    try:
        now = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        if now.tzinfo is None:
            raise ValueError("timezone required")
        local_now = now.astimezone(SHANGHAI)
    except ValueError as exc:
        return {"status": "BLOCKED", "reason": "OBSERVED_AT_INVALID"}
    if not official_session_confirmed:
        return {"status": "NOT_APPLICABLE", "reason": "OFFICIAL_SESSION_NOT_CONFIRMED", "trade_date": trade_date}
    if local_now.date().isoformat() == trade_date and local_now.time() < MARKET_CLOSE:
        return {"status": "WAIT_MARKET_CLOSE", "trade_date": trade_date,
                "observed_at": now.isoformat(), "system_available_at": None}
    if not tdx_capture or tdx_capture.get("target_date") != trade_date:
        return {"status": "WAIT_TDX_PUBLICATION", "trade_date": trade_date,
                "reason": "TARGET_DATE_PAGE_CAPTURE_MISSING"}
    if tdx_capture.get("update_date") != trade_date:
        return {"status": "WAIT_TDX_PUBLICATION", "trade_date": trade_date,
                "observed_tdx_update_date": tdx_capture.get("update_date")}
    if tdx_capture.get("status") not in {"TDX_PACKAGE_READY", "NOOP_SOURCE_ALREADY_FROZEN"}:
        return {"status": "WAIT_TDX_PUBLICATION", "trade_date": trade_date,
                "reason": "TDX_PACKAGE_NOT_VALIDATED", "tdx_status": tdx_capture.get("status")}
    download = tdx_capture.get("download")
    zip_validation = tdx_capture.get("zip_validation")
    if not isinstance(download, Mapping) or not isinstance(zip_validation, Mapping):
        return {"status": "BLOCKED_TDX_PACKAGE_EVIDENCE_INVALID", "trade_date": trade_date}
    try:
        package_bytes = int(download.get("bytes", 0))
    except (TypeError, ValueError):
        package_bytes = 0
    if (not tdx_capture.get("snapshot_id") or download.get("sha256") != str(tdx_capture.get("snapshot_id", "")).removeprefix("sha256-")
            or package_bytes < 1 or zip_validation.get("crc_integrity") != "PASS"):
        return {"status": "BLOCKED_TDX_PACKAGE_EVIDENCE_INVALID", "trade_date": trade_date}
    if not baostock_capability_accepted:
        return {"status": "WAIT_BAOSTOCK_DAILY_UPDATE", "trade_date": trade_date,
                "reason": "BAOSTOCK_CAPABILITY_GATE_NOT_ACCEPTED"}
    if (not _ready_record(baostock_capture, accepted_statuses={"BAOSTOCK_DAILY_SNAPSHOT_READY", "NOOP_SOURCE_ALREADY_FROZEN"})
            or baostock_capture.get("trade_date") != trade_date
            or baostock_capture.get("provider_date") != trade_date
            or not baostock_capture.get("snapshot_id")
            or not baostock_capture.get("source_revision_id")
            or not baostock_capture.get("daily_rows")
            or "adjustment_factor_rows" not in baostock_capture):
        return {"status": "WAIT_BAOSTOCK_DAILY_UPDATE", "trade_date": trade_date,
                "baostock_status": baostock_capture.get("status") if baostock_capture else None}
    if not _ready_record(gbbq_snapshot, accepted_statuses={"GO_FORWARD_SNAPSHOT_FROZEN", "READY", "NOOP_SOURCE_ALREADY_FROZEN"}):
        return {"status": "WAIT_GBBQ_SNAPSHOT_IF_REQUIRED", "trade_date": trade_date}
    if not _ready_record(lifecycle_snapshot, accepted_statuses={"READY", "FULL_PASS", "DEGRADED_PASS"}):
        return {"status": "WAIT_IDENTITY_LIFECYCLE_SNAPSHOT", "trade_date": trade_date}
    if not _ready_record(special_phase_snapshot, accepted_statuses={"READY", "FULL_PASS", "DEGRADED_PASS"}):
        return {"status": "WAIT_SPECIAL_PHASE_SNAPSHOT", "trade_date": trade_date}
    return {"status": "SOURCE_FREEZE_READY", "trade_date": trade_date,
            "observed_at": now.isoformat(), "system_available_at": now.isoformat(),
            "tdx_snapshot_id": tdx_capture.get("snapshot_id"),
            "baostock_snapshot_id": baostock_capture.get("snapshot_id")}
