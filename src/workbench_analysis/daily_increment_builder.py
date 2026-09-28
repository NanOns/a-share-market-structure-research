from __future__ import annotations

"""Stage the TDX raw increment and gate all accepted runtime component builds."""

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from workbench_analysis.daily_data_head import CAPABILITIES, build_data_head, promote_data_head
from workbench_analysis.daily_source_freeze import ensure_outside_tdx, source_freeze_complete_v2


class DailyIncrementError(ValueError):
    pass


def affected_component_scopes(tdx_delta: Mapping[str, Any]) -> dict[str, list[str]]:
    """Map explicit source revisions to only their dependent accepted outputs."""
    revisions = list(tdx_delta.get("revision_events") or [])
    target_bars = list(tdx_delta.get("target_bars") or [])
    normal = list(CAPABILITIES) if target_bars else []
    revised = []
    if revisions:
        revised = ["RAW_DAILY", "ADJUSTED_DAILY", "PERIOD_RAW", "PERIOD_ADJUSTED", "PRICE_LIMIT"]
    return {
        "target_session_components": normal,
        "historical_revision_components": revised,
        "revision_security_ids": sorted({str(item["security_id"]) for item in revisions if item.get("security_id")}),
        "full_history_rebuild": False,
    }


def _atomic_bytes(path: Path, data: bytes, *, tdx_root: Path) -> None:
    ensure_outside_tdx(path, tdx_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    except Exception:
        Path(name).unlink(missing_ok=True)
        raise


def _atomic_json(path: Path, payload: Mapping[str, Any], *, tdx_root: Path) -> str:
    data = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    _atomic_bytes(path, data, tdx_root=tdx_root)
    return hashlib.sha256(data).hexdigest()


def build_raw_increment_staging(
    *,
    trade_date: str,
    source_snapshot_id: str,
    delta: Mapping[str, Any],
    output_path: Path,
    tdx_root: Path = Path("D:/new_tdx"),
) -> dict[str, Any]:
    """Write only TDX rows for one date; keep source codes unmapped and explicit."""
    if delta.get("status") != "READY" or delta.get("target_date") != trade_date:
        raise DailyIncrementError("TDX_TARGET_DATE_DELTA_NOT_READY")
    if not source_snapshot_id or delta.get("current_snapshot_id") != source_snapshot_id:
        raise DailyIncrementError("TDX_SOURCE_SNAPSHOT_BINDING_MISMATCH")
    rows = delta.get("target_bars")
    if not isinstance(rows, list) or not rows:
        raise DailyIncrementError("TDX_TARGET_DATE_ROWS_MISSING")
    normalized = []
    seen = set()
    target_num = int(trade_date.replace("-", ""))
    for row in rows:
        if int(row.get("trade_date", -1)) != target_num:
            raise DailyIncrementError("TDX_TARGET_DATE_ROW_MISMATCH")
        security_id = str(row.get("security_id") or "")
        if not security_id or security_id in seen:
            raise DailyIncrementError("TDX_SECURITY_ID_MISSING_OR_DUPLICATE")
        seen.add(security_id)
        normalized.append({
            "trade_date": trade_date,
            "source_security_key": security_id,
            "canonical_security_id": None,
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "amount": row["amount"],
            "volume": row["volume"],
            "source_snapshot_id": source_snapshot_id,
            "source_authority": "TDX_OFFICIAL_PACKAGE",
            "knowledge_lineage": "PIT_OBSERVED",
            "canonical_acceptance": "STAGING_ONLY_PENDING_IDENTITY_AND_COMPONENT_BUILD",
        })
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
             for row in sorted(normalized, key=lambda item: item["source_security_key"])]
    raw = b"".join(lines)
    _atomic_bytes(output_path, raw, tdx_root=tdx_root)
    return {
        "contract_id": "V4_DM01_RAW_DAILY_INCREMENT_STAGING_V1",
        "trade_date": trade_date,
        "status": "STAGING_READY",
        "rows": len(normalized),
        "artifact_path": str(output_path.resolve()),
        "artifact_bytes": len(raw),
        "artifact_sha256": hashlib.sha256(raw).hexdigest(),
        "bao_stock_ohlc_used": False,
        "canonical_security_identity_assigned": False,
        "tdx_root_write_count": 0,
    }


def _artifact_valid(result: Mapping[str, Any], *, tdx_root: Path) -> bool:
    if result.get("status") not in {"FULL_PASS", "DEGRADED_PASS", "NOT_APPLICABLE"}:
        return False
    artifact = result.get("artifact")
    if not isinstance(artifact, Mapping) or not artifact.get("path") or not artifact.get("sha256"):
        return False
    path = Path(str(artifact["path"]))
    ensure_outside_tdx(path, tdx_root)
    if not path.is_file():
        return False
    digest_obj = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest_obj.update(chunk)
    digest = digest_obj.hexdigest()
    return digest == artifact.get("sha256")


def run_incremental_components(
    *,
    trade_date: str,
    source_freeze: Mapping[str, Any],
    tdx_delta: Mapping[str, Any],
    parent_artifacts: Mapping[str, Any],
    builders: Mapping[str, Callable[..., Mapping[str, Any]]],
    staging_root: Path,
    head_path: Path,
    stage_head_path: Path,
    dev_baseline_path: Path,
    independent_postcheck: Callable[[Mapping[str, Any]], str] | None,
    tdx_root: Path = Path("D:/new_tdx"),
) -> dict[str, Any]:
    """Run versioned component builders; publish only after independent PASS."""
    if not source_freeze_complete_v2(source_freeze):
        return {"status": "BLOCKED_SOURCE_FREEZE_INCOMPLETE", "head_moved": False}
    if (source_freeze.get("trade_date") != trade_date or tdx_delta.get("target_date") != trade_date
            or tdx_delta.get("status") != "READY"):
        return {"status": "BLOCKED_TARGET_DATE_MISMATCH", "head_moved": False}
    if not tdx_delta.get("target_bars"):
        return {"status": "BLOCKED_TDX_TARGET_DATE_BARS_MISSING", "head_moved": False}
    families = source_freeze.get("source_families", {})
    if (families.get("TDX_FULL_PACKAGE", {}).get("source_revision") != tdx_delta.get("current_snapshot_id")
            or families.get("TDX_PACKAGE_DELTA", {}).get("sha256") != tdx_delta.get("delta_sha256")):
        return {"status": "BLOCKED_TDX_SOURCE_BINDING_MISMATCH", "head_moved": False}
    missing = [capability for capability in CAPABILITIES if capability not in builders]
    if missing:
        return {"status": "BLOCKED_COMPONENT_BUILDERS_NOT_WIRED", "missing_components": missing,
                "head_moved": False, "tdx_root_write_count": 0}
    if independent_postcheck is None:
        return {"status": "BLOCKED_INDEPENDENT_POSTCHECK_NOT_WIRED", "head_moved": False}
    ensure_outside_tdx(staging_root, tdx_root)
    staging_root.mkdir(parents=True, exist_ok=True)
    component_receipts: dict[str, Mapping[str, Any]] = {}
    for capability in CAPABILITIES:
        result = dict(builders[capability](
            trade_date=trade_date,
            source_freeze=source_freeze,
            tdx_delta=tdx_delta,
            parent_artifacts=parent_artifacts,
            staging_root=staging_root,
            capability=capability,
        ))
        if not _artifact_valid(result, tdx_root=tdx_root):
            return {"status": "BLOCKED_COMPONENT_OUTPUT_INVALID", "failed_component": capability,
                    "component_receipts": component_receipts, "head_moved": False}
        if not result.get("contract_id") or not result.get("version"):
            return {"status": "BLOCKED_COMPONENT_CONTRACT_MISSING", "failed_component": capability,
                    "component_receipts": component_receipts, "head_moved": False}
        component_receipts[capability] = result
    current_head = json.loads(head_path.read_text(encoding="utf-8"))
    stage_sha = hashlib.sha256(stage_head_path.read_bytes()).hexdigest()
    dev_sha = hashlib.sha256(dev_baseline_path.read_bytes()).hexdigest()
    permission_map = {
        key: {"status": value["status"], "cutoff": trade_date,
              "source_receipt": value["contract_id"], "artifact": dict(value["artifact"])}
        for key, value in component_receipts.items()
    }
    source_revision = str(source_freeze.get("manifest_sha256") or "")
    canonical_revision = hashlib.sha256(json.dumps(
        {key: value["artifact"]["sha256"] for key, value in component_receipts.items()},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    candidate_manifest = {
        "contract_id": "V4_DM01_DAILY_INCREMENT_CANDIDATE_MANIFEST_V1",
        "version": "1.0.0",
        "status": "CANDIDATE_MANIFEST_READY",
        "trade_date": trade_date,
        "source_freeze_sha256": source_revision,
        "components": {key: dict(value) for key, value in component_receipts.items()},
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    manifest_path = staging_root / f"candidate_manifest_{trade_date.replace('-', '')}.json"
    manifest_sha = _atomic_json(manifest_path, candidate_manifest, tdx_root=tdx_root)
    candidate_head = build_data_head(
        trade_date=trade_date,
        source_revision=source_revision,
        canonical_data_revision=canonical_revision,
        manifest_path=str(manifest_path.resolve()),
        manifest_sha256=manifest_sha,
        parent_head_sha256=hashlib.sha256(head_path.read_bytes()).hexdigest(),
        stage_accepted_head_sha256=stage_sha,
        dev_baseline_sha256=dev_sha,
        component_permissions=permission_map,
    )
    postcheck = independent_postcheck({"manifest": candidate_manifest, "head": candidate_head})
    result = promote_data_head(
        head_path=head_path,
        candidate_head=candidate_head,
        candidate_manifest=candidate_manifest,
        source_freeze_pass=True,
        independent_postcheck_status=postcheck,
        stage_head_path=stage_head_path,
        dev_baseline_path=dev_baseline_path,
        tdx_root=tdx_root,
    )
    return {"status": result["status"], "promotion": result, "component_receipts": component_receipts,
            "candidate_manifest_path": str(manifest_path.resolve()), "candidate_manifest_sha256": manifest_sha,
            "parent_data_head_trade_date": current_head.get("accepted_trade_date"),
            "data_head_moved": result.get("head_moved", False), "tdx_root_write_count": 0}
