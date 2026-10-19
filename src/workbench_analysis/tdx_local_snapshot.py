"""Copy a configured TDX input tree into an immutable, project-managed snapshot."""
from __future__ import annotations

import hashlib
import json
import os
import stat
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


class LocalSnapshotError(ValueError):
    pass


def _snapshot_store(snapshot_root: Path):
    repo_root = Path(__file__).resolve().parents[2]
    if not Path(snapshot_root).resolve().is_relative_to(repo_root):
        raise LocalSnapshotError("LOCAL_SNAPSHOT_WORKSPACE_ROOT_REQUIRED")
    from workbench_db.v4_forward_pg_r1 import ForwardFactStore
    return ForwardFactStore(repo_root, "data/v4/historical_source_ingress_pg_r1")


def _persist_manifest_pg(snapshot_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    store = _snapshot_store(snapshot_root)
    record = {"contract_id": "V4_TDX_LOCAL_SNAPSHOT_CANDIDATE_PG_R1",
              "contract_version": "1.0.0", "candidate_status": "DIAGNOSTIC_ONLY",
              "snapshot_id": manifest["snapshot_id"], "content_digest": manifest["content_digest"],
              "manifest": manifest, "AS_RECORDED": False, "PIT_ELIGIBLE": False,
              "accepted_head": False}
    binding = store.append("tdx_local_snapshot_candidate", manifest["snapshot_id"], record,
                           migration_timeout_seconds=120)
    if store.read(binding) != record:
        raise LocalSnapshotError("LOCAL_SNAPSHOT_PG_READBACK_MISMATCH")
    return binding


def _read_manifest_pg(snapshot_root: Path, snapshot_id: str):
    store = _snapshot_store(snapshot_root)
    for binding in store.refs("tdx_local_snapshot_candidate"):
        if binding.get("pg_descriptor", {}).get("fact_key") == snapshot_id:
            record = store.read(binding)
            manifest = record.get("manifest")
            if (record.get("contract_id") != "V4_TDX_LOCAL_SNAPSHOT_CANDIDATE_PG_R1"
                    or record.get("snapshot_id") != snapshot_id
                    or not isinstance(manifest, dict)
                    or manifest.get("content_digest") != record.get("content_digest")
                    or record.get("accepted_head") is not False):
                raise LocalSnapshotError("LOCAL_SNAPSHOT_PG_IDENTITY_INVALID")
            return manifest, binding
    return None


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


def build_local_snapshot(
    source_root: Path,
    output_root: Path,
    *,
    persist_to_pg: bool = False,
) -> dict[str, Any]:
    """仅读取本地日线文件并原子复制到独立快照目录；入库须显式启用。"""
    def reject_reparse(path):
        info=path.lstat()
        if path.is_symlink() or stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0) & getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400):
            raise LocalSnapshotError('TDX_INPUT_SYMLINK_REJECTED')
    reject_reparse(source_root)
    reject_reparse(source_root/'vipdoc')
    source = source_root.resolve(strict=True)
    vipdoc = (source / "vipdoc").resolve(strict=True)
    if source == output_root.resolve() or source in output_root.resolve().parents:
        raise LocalSnapshotError("SNAPSHOT_OUTPUT_MUST_BE_OUTSIDE_TDX_ROOT")
    files: list[tuple[str, Path]] = []
    for market in ("sh", "sz", "bj"):
        market_root = vipdoc / market / "lday"
        if market_root.is_dir():
            reject_reparse(vipdoc/market)
            reject_reparse(market_root)
            for path in market_root.glob("*.day"):
                reject_reparse(path)
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
            binding = _persist_manifest_pg(output_root, prior) if persist_to_pg else None
            return {"snapshot_id": snapshot_id, "manifest_path": str(prior_path), "file_count": len(inventory), "byte_count": total_bytes, "content_digest": content_digest, "pg_binding": binding, "status": "REUSED_IDENTICAL_SNAPSHOT"}
        os.replace(staging, final)
        binding = _persist_manifest_pg(output_root, manifest) if persist_to_pg else None
        return {"snapshot_id": snapshot_id, "manifest_path": str(final / "snapshot_manifest.json"), "file_count": len(inventory), "byte_count": total_bytes, "content_digest": content_digest, "pg_binding": binding, "status": "SNAPSHOT_CREATED"}
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def verify_local_snapshot(
    snapshot_root: Path,
    snapshot_id: str,
    *,
    require_pg_binding: bool = False,
) -> dict[str, Any]:
    """重新计算本地快照摘要；仅显式要求时才读取 PostgreSQL 绑定。"""
    snapshot = (snapshot_root / snapshot_id).resolve(strict=True)
    manifest_path = snapshot / "snapshot_manifest.json"
    binding = None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if require_pg_binding:
        pg_manifest = _read_manifest_pg(snapshot_root, snapshot_id)
        if pg_manifest is None:
            raise LocalSnapshotError("LOCAL_SNAPSHOT_PG_INGRESS_READBACK_REQUIRED")
        manifest, binding = pg_manifest
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
        "pg_binding": binding,
    }
