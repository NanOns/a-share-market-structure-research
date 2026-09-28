from __future__ import annotations

"""Probe the current GBBQ revision and reuse or freeze snapshots by content identity."""

import hashlib
import json
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from workbench_analysis.daily_source_freeze import ensure_outside_tdx


CONTRACT_ID = "GBBQ_SOURCE_REVISION_PROBE_V1"
SOURCE_FILES = ("gbbq", "gbbq.map")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_bytes(path: Path, raw: bytes, *, tdx_root: Path) -> None:
    ensure_outside_tdx(path, tdx_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def _atomic_json(path: Path, payload: Mapping[str, Any], *, tdx_root: Path) -> str:
    raw = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    _atomic_bytes(path, raw, tdx_root=tdx_root)
    return hashlib.sha256(raw).hexdigest()


def probe_gbbq_source_revision(
    *,
    target_date: str,
    current_source_root: Path,
    accepted_snapshot_root: Path,
    output_snapshot_root: Path,
    observed_at: str,
    official_sessions_after_target: list[str],
    tdx_root: Path = Path("D:/new_tdx"),
) -> dict[str, Any]:
    """Read local TDX GBBQ files without writing there; freeze changed revisions separately."""
    try:
        date.fromisoformat(target_date)
    except ValueError as exc:
        raise ValueError("GBBQ_TARGET_DATE_INVALID") from exc
    ensure_outside_tdx(accepted_snapshot_root, tdx_root)
    ensure_outside_tdx(output_snapshot_root, tdx_root)
    try:
        current_source_root.resolve().relative_to(tdx_root.resolve())
    except ValueError as exc:
        raise ValueError("GBBQ_CURRENT_SOURCE_OUTSIDE_TDX_ROOT") from exc
    accepted_manifest_path = accepted_snapshot_root / "manifest.json"
    try:
        accepted = json.loads(accepted_manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"contract_id": CONTRACT_ID, "status": "WAIT_GBBQ_ACCEPTED_SNAPSHOT_MISSING",
                "trade_date": target_date, "reason": type(exc).__name__, "tdx_root_write_count": 0}
    accepted_files = accepted.get("files", {})
    current_paths = {name: current_source_root / name for name in SOURCE_FILES}
    missing = [name for name, path in current_paths.items() if not path.is_file()]
    if missing:
        return {"contract_id": CONTRACT_ID, "status": "WAIT_GBBQ_CURRENT_SOURCE_UNAVAILABLE",
                "trade_date": target_date, "missing_source_files": missing,
                "accepted_snapshot_id": accepted.get("snapshot_id"),
                "accepted_manifest_sha256": _sha(accepted_manifest_path), "tdx_root_write_count": 0}
    current = {name: {"bytes": path.stat().st_size, "sha256": _sha(path)} for name, path in current_paths.items()}
    valid_accepted = all(
        name in accepted_files
        and (accepted_snapshot_root / name).is_file()
        and _sha(accepted_snapshot_root / name) == accepted_files[name].get("sha256")
        and (accepted_snapshot_root / name).stat().st_size == int(accepted_files[name].get("bytes", -1))
        for name in SOURCE_FILES
    )
    if not valid_accepted:
        return {"contract_id": CONTRACT_ID, "status": "BLOCKED_GBBQ_ACCEPTED_SNAPSHOT_INTEGRITY",
                "trade_date": target_date, "accepted_snapshot_id": accepted.get("snapshot_id"),
                "tdx_root_write_count": 0}
    if all(current[name] == {"bytes": accepted_files[name]["bytes"], "sha256": accepted_files[name]["sha256"]}
           for name in SOURCE_FILES):
        return {
            "contract_id": CONTRACT_ID,
            "status": "REUSE_ACCEPTED_GBBQ_SNAPSHOT",
            "trade_date": target_date,
            "accepted_snapshot_id": accepted.get("snapshot_id"),
            "accepted_manifest_path": str(accepted_manifest_path.resolve()),
            "accepted_manifest_sha256": _sha(accepted_manifest_path),
            "source_files": current,
            "first_eligible_formal_trade_date": accepted.get("first_eligible_formal_trade_date"),
            "tdx_root_write_count": 0,
        }
    identity = hashlib.sha256(json.dumps(current, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    snapshot_id = "sha256-" + identity
    snapshot_dir = output_snapshot_root / "gbbq" / snapshot_id
    ensure_outside_tdx(snapshot_dir, tdx_root)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for name, path in current_paths.items():
        destination = snapshot_dir / name
        if destination.exists() and _sha(destination) != current[name]["sha256"]:
            raise ValueError("GBBQ_IMMUTABLE_SNAPSHOT_COLLISION")
        if not destination.exists():
            _atomic_bytes(destination, path.read_bytes(), tdx_root=tdx_root)
    first_eligible = next((session for session in official_sessions_after_target if session > target_date), None)
    manifest = {
        "contract_id": "V4_02_GBBQ_FORWARD_SNAPSHOT_V1",
        "snapshot_id": snapshot_id,
        "source_revision_id": snapshot_id,
        "files": current,
        "source_snapshot_parent": accepted.get("snapshot_id"),
        "system_available_at": observed_at,
        "observed_at": observed_at,
        "ingested_at": observed_at,
        "first_eligible_formal_trade_date": first_eligible,
        "lineage_permission": "PIT_OBSERVED_ELIGIBLE_FROM_FIRST_FORMAL_PUBLICATION_AFTER_SYSTEM_AVAILABLE_AT",
        "immutable": True,
        "tdx_root_write_count": 0,
    }
    manifest_path = snapshot_dir / "manifest.json"
    manifest_sha = _atomic_json(manifest_path, manifest, tdx_root=tdx_root)
    return {
        "contract_id": CONTRACT_ID,
        "status": "NEW_GBBQ_REVISION_FROZEN_REQUIRES_ADJUSTMENT_IMPACT",
        "trade_date": target_date,
        "accepted_snapshot_id": accepted.get("snapshot_id"),
        "new_snapshot_id": snapshot_id,
        "manifest_path": str(manifest_path.resolve()),
        "manifest_sha256": manifest_sha,
        "source_files": current,
        "first_eligible_formal_trade_date": first_eligible,
        "eligible_for_target_date": bool(first_eligible and target_date >= first_eligible),
        "tdx_root_write_count": 0,
    }
