"""Immutable R1 input-snapshot manifests and same-cutoff source revisions."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from production.release import atomic_write_json


INPUT_SNAPSHOT_CONTRACT_VERSION = "input-snapshot-v1.0"
REVISION_ARCHIVE_VERSION = "source-revision-archive-v1.0"


def r1_gate(checks: dict[str, bool]) -> str:
    return "PASS" if checks and all(checks.values()) else "BLOCKED"


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf8")


def _sha(value: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def observed_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def next_source_revision_id(root: str | Path, cutoff_date: str, source_identity_sha256: str) -> int:
    """Return the stable revision number for a source identity at one cutoff."""
    archive = Path(root) / "reports" / "revisions" / str(cutoff_date)
    highest = 0
    if archive.exists():
        for path in sorted(archive.glob("revision-*/REVISION_RECORD.json")):
            try:
                value = json.loads(path.read_text("utf8"))
                revision = int(value["source_revision_id"])
                highest = max(highest, revision)
                if value.get("source_identity", {}).get("sha256") == source_identity_sha256:
                    return revision
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                continue
    return highest + 1


def build_input_snapshot_manifest(
    *, run_id: str, cutoff_date: str, source_revision_id: int,
    source_identity: dict[str, Any], source_fingerprint: dict[str, Any],
    computation_identity: dict[str, Any], render_identity: dict[str, Any],
    run_universe: dict[str, Any], observed_at: str | None = None,
) -> dict[str, Any]:
    components = source_fingerprint.get("source_fingerprint_components", {})
    value = {
        "contract_version": INPUT_SNAPSHOT_CONTRACT_VERSION,
        "run_id": run_id,
        "cutoff_date": str(cutoff_date),
        "observed_at": observed_at or observed_now(),
        "source_revision_id": int(source_revision_id),
        "source_identity_version": source_identity.get("version"),
        "source_identity": source_identity,
        "day_source_summary": source_fingerprint.get("day_fingerprint_summary", {}),
        "gbbq_sha256": components.get("gbbq"),
        "gbbq_map_sha256": components.get("gbbq_map"),
        "membership_hashes": {
            key: components.get(key) for key in ("tdxhy", "tdxzs", "infoharbor_block")
        },
        "security_master_hashes": {
            key: components.get(key) for key in ("sh_tnf", "sz_tnf", "bj_tnf")
        },
        "calendar_sha256": source_fingerprint.get("calendar_sha256") or components.get("master_calendar"),
        "run_universe_generation": run_universe.get("generation"),
        "run_universe_sha256": run_universe.get("sha256"),
        "run_universe_count": run_universe.get("count"),
        "adjustment_identity": "TDX_NATIVE_AFFINE_QFQ",
        "price_basis": "FORWARD_ADJUSTED / TDX_NATIVE_QFQ",
        "computation_identity": computation_identity,
        "render_identity": render_identity,
    }
    value["snapshot_manifest_sha256"] = _sha(value)
    return value


def validate_input_snapshot_manifest(value: dict[str, Any]) -> bool:
    expected = value.get("snapshot_manifest_sha256")
    payload = dict(value)
    payload.pop("snapshot_manifest_sha256", None)
    if value.get("contract_version") != INPUT_SNAPSHOT_CONTRACT_VERSION or expected != _sha(payload):
        raise ValueError("INPUT_SNAPSHOT_MANIFEST_HASH_MISMATCH")
    required = (
        "run_id", "cutoff_date", "observed_at", "source_revision_id", "source_identity",
        "day_source_summary", "gbbq_sha256", "gbbq_map_sha256", "membership_hashes",
        "security_master_hashes", "calendar_sha256", "run_universe_generation",
        "run_universe_sha256", "run_universe_count", "adjustment_identity", "price_basis",
        "computation_identity", "render_identity",
    )
    if any(key not in value for key in required):
        raise ValueError("INPUT_SNAPSHOT_MANIFEST_FIELD_MISSING")
    return True


def write_immutable_manifest(path: str | Path, value: dict[str, Any]) -> Path:
    validate_input_snapshot_manifest(value)
    path = Path(path)
    if path.exists():
        existing = json.loads(path.read_text("utf8"))
        if existing != value:
            raise FileExistsError("IMMUTABLE_INPUT_SNAPSHOT_EXISTS:" + str(path))
        return path
    atomic_write_json(path, value)
    return path


def archive_source_revision(
    root: str | Path, manifest: dict[str, Any], *, release_id: str,
    changed_source_components: list[str] | None = None,
) -> dict[str, Any]:
    """Archive one material source identity without overwriting older revisions."""
    validate_input_snapshot_manifest(manifest)
    root = Path(root)
    revision_id = int(manifest["source_revision_id"])
    directory = root / "reports" / "revisions" / str(manifest["cutoff_date"]) / f"revision-{revision_id:06d}"
    snapshot_path = directory / "INPUT_SNAPSHOT_MANIFEST.json"
    record_path = directory / "REVISION_RECORD.json"
    record = {
        "archive_version": REVISION_ARCHIVE_VERSION,
        "source_revision_id": revision_id,
        "cutoff_date": str(manifest["cutoff_date"]),
        "source_identity": manifest["source_identity"],
        "computation_identity": manifest["computation_identity"],
        "render_identity": manifest["render_identity"],
        "run_id": manifest["run_id"],
        "release_id": release_id,
        "observed_at": manifest["observed_at"],
        "changed_source_components": list(changed_source_components or ()),
        "snapshot_manifest_sha256": manifest["snapshot_manifest_sha256"],
    }
    if directory.exists():
        existing = json.loads(record_path.read_text("utf8"))
        if existing.get("source_identity", {}).get("sha256") != manifest["source_identity"].get("sha256"):
            raise FileExistsError("SOURCE_REVISION_ID_COLLISION")
        return {"created": False, "directory": str(directory), "record": existing}
    directory.parent.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix=f'.revision-{revision_id:06d}.',suffix='.tmp',dir=directory.parent))
    write_immutable_manifest(staging/snapshot_path.name,manifest)
    atomic_write_json(staging/record_path.name,record)
    os.replace(staging,directory)
    return {"created": True, "directory": str(directory), "record": record}
