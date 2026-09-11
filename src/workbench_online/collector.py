"""Atomic local batch persistence for M14 personal research mode."""

from __future__ import annotations

import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .base import OnlineFetchPolicy, sha256_bytes
from .eastmoney_hot_rank import fetch_eastmoney_hot_rank
from .ths_hot_rank import fetch_ths_hot_rank


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def _atomic_json(path: Path, payload: object) -> None:
    _atomic_bytes(path, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")


def _commit_raw_and_batch(raw_path: Path, raw_content: bytes, batch_path: Path, batch: dict) -> None:
    """Commit a deduplicated raw object and its batch without leaving a new orphan."""
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    batch_path.parent.mkdir(parents=True, exist_ok=True)
    raw_existed = raw_path.exists()
    batch_existed = batch_path.exists()
    raw_temp = None
    batch_temp = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=raw_path.parent, delete=False) as handle:
            handle.write(raw_content)
            raw_temp = Path(handle.name)
        with tempfile.NamedTemporaryFile("wb", dir=batch_path.parent, delete=False) as handle:
            handle.write(json.dumps(batch, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
            batch_temp = Path(handle.name)
        if raw_existed:
            raw_temp.unlink(missing_ok=True)
            raw_temp = None
        else:
            raw_temp.replace(raw_path)
            raw_temp = None
        batch_temp.replace(batch_path)
        batch_temp = None
    except Exception:
        if not raw_existed and raw_path.exists():
            raw_path.unlink(missing_ok=True)
        if not batch_existed and batch_path.exists() and batch_path.is_file():
            batch_path.unlink(missing_ok=True)
        raise
    finally:
        if raw_temp is not None:
            raw_temp.unlink(missing_ok=True)
        if batch_temp is not None:
            batch_temp.unlink(missing_ok=True)


def collect_ths_hot_rank(output_root: str | Path, policy: OnlineFetchPolicy | None = None) -> dict:
    policy = policy or OnlineFetchPolicy()
    result, normalized = fetch_ths_hot_rank(policy)
    observed_at = result.received_at_utc
    batch_material = {
        "source_id": normalized["source_id"],
        "dataset": normalized["dataset"],
        "list_type": normalized["list_type"],
        "raw_sha256": result.raw_sha256,
        "observed_at_utc": observed_at,
        "source_as_of": normalized["source_as_of"],
        "contract_id": "M14_BATCH_FOUNDATION_V1_0",
        "capability_status": normalized["capability_status"],
    }
    batch_id = "m14b-" + hashlib.sha256(json.dumps(batch_material, sort_keys=True).encode("utf-8")).hexdigest()[:24]
    root = Path(output_root)
    raw_path = root / "raw" / f"{result.raw_sha256}.json"
    batch_path = root / "batches" / f"{batch_id}.json"
    batch = {
        **batch_material,
        "batch_id": batch_id,
        "fetch": {
            "url": result.url,
            "requested_at_utc": result.requested_at_utc,
            "received_at_utc": result.received_at_utc,
            "status_code": result.status_code,
            "content_type": result.content_type,
            "byte_count": result.byte_count,
            "raw_sha256": result.raw_sha256,
        },
        "personal_research_only": True,
        "publication_enabled": False,
        "rows": normalized["rows"],
    }
    _commit_raw_and_batch(raw_path, result.body, batch_path, batch)
    return {
        "status": "DEGRADED_PASS",
        "stage": "M14-02",
        "batch_id": batch_id,
        "source_id": normalized["source_id"],
        "dataset": normalized["dataset"],
        "row_count": len(normalized["rows"]),
        "mapped_security_count": sum(row["security_id"] is not None for row in normalized["rows"]),
        "source_as_of": None,
        "observed_at_utc": observed_at,
        "personal_research_only": True,
        "publication_enabled": False,
        "raw_sha256": result.raw_sha256,
        "raw_path": str(raw_path),
        "batch_path": str(batch_path),
        "storage_atomic": True,
        "local_snapshot_mutated": False,
    }


def collect_eastmoney_hot_rank(output_root: str | Path, policy: OnlineFetchPolicy | None = None, *, page: int = 1) -> dict:
    policy = policy or OnlineFetchPolicy()
    result, normalized = fetch_eastmoney_hot_rank(policy, page=page)
    batch_material = {
        "source_id": normalized["source_id"],
        "dataset": normalized["dataset"],
        "list_type": normalized["list_type"],
        "page": normalized["page"],
        "raw_sha256": result.raw_sha256,
        "observed_at_utc": result.received_at_utc,
        "source_as_of": normalized["source_as_of"],
        "decoder_version": normalized["decoder_version"],
        "contract_id": "M14_BATCH_FOUNDATION_V1_0",
    }
    import hashlib
    batch_id = "m14b-" + hashlib.sha256(json.dumps(batch_material, sort_keys=True).encode("utf-8")).hexdigest()[:24]
    root = Path(output_root)
    raw_path = root / "raw" / f"{result.raw_sha256}.js"
    batch_path = root / "batches" / f"{batch_id}.json"
    batch = {
        **batch_material,
        "batch_id": batch_id,
        "fetch": {
            "url": result.url,
            "requested_at_utc": result.requested_at_utc,
            "received_at_utc": result.received_at_utc,
            "status_code": result.status_code,
            "content_type": result.content_type,
            "byte_count": result.byte_count,
            "raw_sha256": result.raw_sha256,
        },
        "personal_research_only": True,
        "publication_enabled": False,
        "rows": normalized["rows"],
    }
    _commit_raw_and_batch(raw_path, result.body, batch_path, batch)
    return {
        "status": "DEGRADED_PASS",
        "stage": "M14-02-VERIFY",
        "batch_id": batch_id,
        "source_id": normalized["source_id"],
        "dataset": normalized["dataset"],
        "row_count": len(normalized["rows"]),
        "mapped_security_count": sum(row["security_id"] is not None for row in normalized["rows"]),
        "source_as_of": normalized["source_as_of"],
        "observed_at_utc": result.received_at_utc,
        "decoder_version": normalized["decoder_version"],
        "personal_research_only": True,
        "publication_enabled": False,
        "raw_sha256": result.raw_sha256,
        "raw_path": str(raw_path),
        "batch_path": str(batch_path),
        "storage_atomic": True,
        "local_snapshot_mutated": False,
    }
