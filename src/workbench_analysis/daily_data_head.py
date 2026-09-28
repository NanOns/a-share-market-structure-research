from __future__ import annotations

"""Atomic and independently gated pointers for accepted daily data."""

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from workbench_analysis.daily_source_freeze import ensure_outside_tdx

CAPABILITIES = (
    "RAW_DAILY",
    "IDENTITY_UNIVERSE",
    "TRADING_STATUS",
    "ISST",
    "ADJUSTED_DAILY",
    "PERIOD_RAW",
    "PERIOD_ADJUSTED",
    "PRICE_LIMIT",
    "SPECIAL_PHASE",
)
CAPABILITY_STATUSES = frozenset({"FULL_PASS", "DEGRADED_PASS", "BLOCKED", "NOT_APPLICABLE"})


class DataHeadError(ValueError):
    pass


def canonical_digest(payload: Mapping[str, Any]) -> str:
    material = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, payload: Mapping[str, Any], *, tdx_root: Path) -> str:
    ensure_outside_tdx(path, tdx_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
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
    return hashlib.sha256(data).hexdigest()


def validate_capabilities(capabilities: Mapping[str, Any], *, required: tuple[str, ...] = CAPABILITIES) -> list[str]:
    errors = []
    for name in required:
        item = capabilities.get(name)
        status = item.get("status") if isinstance(item, Mapping) else item
        if status not in CAPABILITY_STATUSES:
            errors.append(f"CAPABILITY_STATUS_INVALID:{name}")
        elif status == "BLOCKED":
            errors.append(f"CAPABILITY_BLOCKED:{name}")
    return errors


def build_data_head(
    *,
    trade_date: str,
    source_revision: str,
    canonical_data_revision: str,
    manifest_path: str,
    manifest_sha256: str,
    parent_head_sha256: str | None,
    stage_accepted_head_sha256: str,
    dev_baseline_sha256: str,
    component_permissions: Mapping[str, Any],
) -> dict[str, Any]:
    missing = [name for name in CAPABILITIES if name not in component_permissions]
    if missing:
        raise DataHeadError("DATA_HEAD_COMPONENTS_MISSING:" + ",".join(missing))
    errors = validate_capabilities(component_permissions)
    if errors:
        raise DataHeadError(";".join(errors))
    if not source_revision or not canonical_data_revision or not manifest_sha256:
        raise DataHeadError("DATA_HEAD_REVISION_OR_MANIFEST_MISSING")
    return {
        "contract_id": "V4_DATA_ACCEPTED_HEAD_V1",
        "version": "1.0.0",
        "accepted_trade_date": trade_date,
        "source_revision": source_revision,
        "canonical_data_revision": canonical_data_revision,
        "manifest_path": manifest_path,
        "manifest_sha256": manifest_sha256,
        "parent_head_sha256": parent_head_sha256,
        "stage_accepted_head_sha256": stage_accepted_head_sha256,
        "dev_baseline_sha256": dev_baseline_sha256,
        "component_permissions": dict(component_permissions),
    }


def promote_data_head(
    *,
    head_path: Path,
    candidate_head: Mapping[str, Any],
    candidate_manifest: Mapping[str, Any],
    source_freeze_pass: bool,
    independent_postcheck_status: str,
    stage_head_path: Path,
    dev_baseline_path: Path,
    tdx_root: Path,
) -> dict[str, Any]:
    """Publish only after all gates pass; previous pointer survives any rejection."""
    ensure_outside_tdx(head_path, tdx_root)
    before_stage = stage_head_path.read_bytes()
    before_dev = dev_baseline_path.read_bytes()
    current = read_json(head_path) if head_path.exists() else None
    if current and (
        current.get("manifest_sha256") == candidate_head.get("manifest_sha256")
        and current.get("accepted_trade_date") == candidate_head.get("accepted_trade_date")
    ):
        return {"status": "NOOP_ALREADY_ACCEPTED", "head_sha256": canonical_digest(current), "head_moved": False}
    errors = validate_capabilities(candidate_head.get("component_permissions", {}))
    if not source_freeze_pass:
        errors.append("SOURCE_FREEZE_INCOMPLETE")
    if independent_postcheck_status != "PASS":
        errors.append("INDEPENDENT_POSTCHECK_NOT_PASS")
    if candidate_manifest.get("status") not in {"CANDIDATE_MANIFEST_READY", "PASS"}:
        errors.append("CANDIDATE_MANIFEST_NOT_READY")
    expected_stage = hashlib.sha256(before_stage).hexdigest()
    expected_dev = hashlib.sha256(before_dev).hexdigest()
    if candidate_head.get("stage_accepted_head_sha256") != expected_stage:
        errors.append("STAGE_ACCEPTED_HEAD_CHANGED")
    if candidate_head.get("dev_baseline_sha256") != expected_dev:
        errors.append("DEV_BASELINE_HEAD_CHANGED")
    current_digest = hashlib.sha256(head_path.read_bytes()).hexdigest() if head_path.exists() else None
    if candidate_head.get("parent_head_sha256") != current_digest:
        errors.append("DATA_HEAD_PARENT_MISMATCH")
    if errors:
        return {"status": "BLOCKED", "errors": errors, "head_moved": False}
    written_sha = write_json_atomic(head_path, candidate_head, tdx_root=tdx_root)
    if stage_head_path.read_bytes() != before_stage or dev_baseline_path.read_bytes() != before_dev:
        raise DataHeadError("IMMUTABLE_BASELINE_HEAD_CHANGED_DURING_PROMOTION")
    return {"status": "PROMOTED", "head_sha256": written_sha, "head_moved": True}
