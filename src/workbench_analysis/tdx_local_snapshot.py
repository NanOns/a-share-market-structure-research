"""Copy a configured TDX input tree into an immutable, project-managed snapshot."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


class LocalSnapshotError(ValueError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    except Exception:
        Path(temp).unlink(missing_ok=True)
        raise


def _safe_relative(path: Path, base: Path) -> str:
    relative = path.relative_to(base).as_posix()
    parts = PurePosixPath(relative).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise LocalSnapshotError("TDX_RELATIVE_PATH_INVALID")
    return relative


def build_local_snapshot(source_root: Path, output_root: Path) -> dict[str, Any]:
    """Read only `{root}/vipdoc/{sh,sz,bj}/lday/*.day` and atomically copy out."""
    source = source_root.resolve(strict=True)
    vipdoc = (source / "vipdoc").resolve(strict=True)
    if source == output_root.resolve() or source in output_root.resolve().parents:
        raise LocalSnapshotError("SNAPSHOT_OUTPUT_MUST_BE_OUTSIDE_TDX_ROOT")
    files: list[tuple[str, Path]] = []
    for market in ("sh", "sz", "bj"):
        market_root = vipdoc / market / "lday"
        if market_root.is_dir():
            for path in market_root.glob("*.day"):
                if path.is_symlink():
                    raise LocalSnapshotError("TDX_INPUT_SYMLINK_REJECTED")
                if path.is_file():
                    files.append((_safe_relative(path, vipdoc), path))
    files.sort(key=lambda item: item[0].casefold())
    if not files:
        raise LocalSnapshotError("NO_TDX_DAY_FILES_FOUND")

    output_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=output_root))
    digest = hashlib.sha256()
    inventory: list[dict[str, Any]] = []
    total_bytes = 0
    try:
        for relative, source_file in files:
            before = source_file.stat()
            destination = staging / Path(*PurePosixPath(relative).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            item_digest = hashlib.sha256()
            byte_count = 0
            with source_file.open("rb") as src, destination.open("xb") as dst:
                for block in iter(lambda: src.read(1024 * 1024), b""):
                    item_digest.update(block)
                    dst.write(block)
                    byte_count += len(block)
                dst.flush()
                os.fsync(dst.fileno())
            after = source_file.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or byte_count != before.st_size:
                raise LocalSnapshotError("TDX_SOURCE_CHANGED_DURING_SNAPSHOT")
            file_sha = item_digest.hexdigest()
            inventory.append({"relative_path": relative, "byte_count": byte_count, "sha256": file_sha})
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(str(byte_count).encode("ascii"))
            digest.update(b"\0")
            digest.update(file_sha.encode("ascii"))
            digest.update(b"\n")
            total_bytes += byte_count

        content_digest = digest.hexdigest()
        snapshot_id = content_digest
        manifest = {
            "contract_id": "V4_TDX_LOCAL_SNAPSHOT_V1",
            "snapshot_id": snapshot_id,
            "content_digest": content_digest,
            "content_digest_algorithm": "SHA256(sorted relative_path NUL byte_count NUL file_sha256 LF)",
            "source_root": str(source),
            "source_scope": "vipdoc/{sh,sz,bj}/lday/*.day",
            "source_root_read_only": True,
            "copied_outside_source_root": True,
            "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "file_count": len(inventory),
            "byte_count": total_bytes,
            "files": inventory,
        }
        manifest_path = staging / "snapshot_manifest.json"
        _atomic_json(manifest_path, manifest)
        final = output_root / snapshot_id
        if final.exists():
            prior_path = final / "snapshot_manifest.json"
            if not prior_path.is_file():
                raise LocalSnapshotError("IMMUTABLE_SNAPSHOT_ID_COLLISION")
            prior = json.loads(prior_path.read_text(encoding="utf-8"))
            if prior.get("snapshot_id") != snapshot_id or prior.get("content_digest") != content_digest:
                raise LocalSnapshotError("IMMUTABLE_SNAPSHOT_ID_COLLISION")
            if prior.get("files") != inventory:
                raise LocalSnapshotError("IMMUTABLE_SNAPSHOT_INVENTORY_MISMATCH")
            for item in inventory:
                stored = final / Path(*PurePosixPath(item["relative_path"]).parts)
                if not stored.is_file() or stored.stat().st_size != item["byte_count"] or _sha256(stored) != item["sha256"]:
                    raise LocalSnapshotError("IMMUTABLE_SNAPSHOT_CONTENT_CHANGED")
            shutil.rmtree(staging)
            return {"snapshot_id": snapshot_id, "manifest_path": str(prior_path), "file_count": len(inventory), "byte_count": total_bytes, "content_digest": content_digest, "status": "REUSED_IDENTICAL_SNAPSHOT"}
        os.replace(staging, final)
        return {"snapshot_id": snapshot_id, "manifest_path": str(final / "snapshot_manifest.json"), "file_count": len(inventory), "byte_count": total_bytes, "content_digest": content_digest, "status": "SNAPSHOT_CREATED"}
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def verify_local_snapshot(snapshot_root: Path, snapshot_id: str) -> dict[str, Any]:
    """Re-hash a project snapshot without consulting or writing the source TDX root."""
    snapshot = (snapshot_root / snapshot_id).resolve(strict=True)
    manifest_path = snapshot / "snapshot_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("snapshot_id") != snapshot_id or manifest.get("content_digest_algorithm") != "SHA256(sorted relative_path NUL byte_count NUL file_sha256 LF)":
        raise LocalSnapshotError("LOCAL_SNAPSHOT_MANIFEST_IDENTITY_MISMATCH")
    digest = hashlib.sha256()
    total_bytes = 0
    seen: set[str] = set()
    for item in sorted(manifest.get("files", []), key=lambda row: row["relative_path"].casefold()):
        relative = item["relative_path"]
        posix = PurePosixPath(relative)
        if posix.is_absolute() or any(part in {"", ".", ".."} for part in posix.parts) or relative in seen:
            raise LocalSnapshotError("LOCAL_SNAPSHOT_INVENTORY_INVALID")
        seen.add(relative)
        path = (snapshot / Path(*posix.parts)).resolve(strict=True)
        if snapshot not in path.parents or not path.is_file() or path.stat().st_size != int(item["byte_count"]):
            raise LocalSnapshotError("LOCAL_SNAPSHOT_FILE_SIZE_OR_PATH_MISMATCH")
        actual_sha = _sha256(path)
        if actual_sha != item["sha256"]:
            raise LocalSnapshotError("LOCAL_SNAPSHOT_FILE_HASH_MISMATCH")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(path.stat().st_size).encode("ascii"))
        digest.update(b"\0")
        digest.update(actual_sha.encode("ascii"))
        digest.update(b"\n")
        total_bytes += path.stat().st_size
    actual_digest = digest.hexdigest()
    if actual_digest != snapshot_id or actual_digest != manifest.get("content_digest"):
        raise LocalSnapshotError("LOCAL_SNAPSHOT_CONTENT_DIGEST_MISMATCH")
    if len(seen) != int(manifest.get("file_count", -1)) or total_bytes != int(manifest.get("byte_count", -1)):
        raise LocalSnapshotError("LOCAL_SNAPSHOT_INVENTORY_TOTAL_MISMATCH")
    return {
        "status": "PASS",
        "snapshot_id": snapshot_id,
        "content_digest": actual_digest,
        "file_count": len(seen),
        "byte_count": total_bytes,
        "manifest_path": str(manifest_path),
    }
