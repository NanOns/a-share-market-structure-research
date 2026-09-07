"""Immutable generation publication primitives."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable


RELEASE_FILES = (
    "market_summary.html", "sectors.csv", "stocks.csv", "candidates.csv",
    "run_audit.json", "PERFORMANCE_AUDIT.json", "INPUT_SNAPSHOT_MANIFEST.json",
    "manifest.json", "PRODUCTION_RECEIPT.json",
)


class PublicationValidationError(RuntimeError):
    pass


def sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fsync_directory(path: str | Path) -> None:
    """Best-effort directory fsync; Windows does not expose it consistently."""
    try:
        fd = os.open(Path(path), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except (OSError, ValueError):
        pass


def atomic_write_bytes(path: str | Path, payload: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def atomic_write_json(path: str | Path, value: dict[str, Any]) -> None:
    atomic_write_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def validate_release_generation(path: str | Path, *, expected_manifest_sha256: str | None = None) -> dict[str, Any]:
    path = Path(path)
    missing = [name for name in RELEASE_FILES if not (path / name).is_file()]
    if missing:
        raise PublicationValidationError("RELEASE_FILES_MISSING:" + ",".join(missing))
    try:
        manifest = json.loads((path / "manifest.json").read_text("utf-8"))
        receipt = json.loads((path / "PRODUCTION_RECEIPT.json").read_text("utf-8"))
    except (OSError, ValueError) as exc:
        raise PublicationValidationError(f"RELEASE_METADATA_INVALID:{exc}") from exc
    for item in manifest.get("files", []):
        filename = item.get("filename")
        if not filename or not (path / filename).is_file():
            raise PublicationValidationError(f"MANIFEST_FILE_MISSING:{filename}")
        if sha256(path / filename) != item.get("sha256"):
            raise PublicationValidationError(f"MANIFEST_HASH_MISMATCH:{filename}")
    manifest_hash = sha256(path / "manifest.json")
    if receipt.get("manifest_sha256") != manifest_hash:
        raise PublicationValidationError("PRODUCTION_MANIFEST_MISMATCH")
    if expected_manifest_sha256 and expected_manifest_sha256 != manifest_hash:
        raise PublicationValidationError("EXPECTED_MANIFEST_MISMATCH")
    return {"manifest": manifest, "receipt": receipt, "manifest_sha256": manifest_hash}


def build_pointer(*, cutoff_date: str, run_id: str, release_path: str | Path,
                  manifest_sha256: str, production_version: str,
                  source_identity: dict[str, Any], computation_identity: dict[str, Any],
                  render_identity: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": str(cutoff_date), "run_id": run_id, "release_path": str(Path(release_path)),
        "manifest_sha256": manifest_sha256, "production_version": production_version,
        "source_identity": source_identity, "computation_identity": computation_identity,
        "render_identity": render_identity,
    }


def publish_generation(generation: str | Path, pointer: str | Path, pointer_payload: dict[str, Any],
                       *, failure_hook=None) -> dict[str, Any]:
    """Validate a complete generation, then atomically replace its tiny pointer.

    All callbacks that can reject publication run before ``os.replace`` inside
    ``atomic_write_json``.  After that single commit point there is no business
    validation capable of invalidating the newly visible generation.
    """
    generation = Path(generation)
    pointer = Path(pointer)
    validation = validate_release_generation(generation)
    if failure_hook:
        failure_hook("FAIL_BEFORE_POINTER_SWAP")
        failure_hook("FAIL_DURING_POINTER_SWAP")
    atomic_write_json(pointer, pointer_payload)
    fsync_directory(pointer.parent)
    return validation


def read_pointer(pointer: str | Path) -> dict[str, Any] | None:
    path = Path(pointer)
    if not path.exists():
        return None
    return json.loads(path.read_text("utf-8"))
