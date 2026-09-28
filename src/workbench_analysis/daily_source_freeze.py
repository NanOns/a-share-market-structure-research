from __future__ import annotations

"""Immutable, bounded source identities for daily V4 data maintenance."""

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

REQUIRED_SOURCE_FAMILIES = (
    "TDX",
    "EXCHANGE_CALENDAR",
    "BAOSTOCK_DAILY",
    "GBBQ",
    "IDENTITY_LIFECYCLE",
    "SPECIAL_PRICE_PHASE",
)

REQUIRED_SOURCE_FAMILIES_V2 = (
    "TDX_PAGE_CAPTURE",
    "TDX_FULL_PACKAGE",
    "TDX_PACKAGE_DELTA",
    "OFFICIAL_CALENDAR",
    "BAOSTOCK_DAILY_UPDATE",
    "BAOSTOCK_ADJUSTMENT_FACTOR",
    "GBBQ",
    "IDENTITY_LIFECYCLE",
    "SPECIAL_PRICE_PHASE",
)


class SourceFreezeError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ensure_outside_tdx(path: Path, tdx_root: Path) -> None:
    target = path.resolve()
    root = tdx_root.resolve()
    if target == root or root in target.parents:
        raise SourceFreezeError("OUTPUT_UNDER_TDX_ROOT_FORBIDDEN")


def file_record(path: Path, *, source_revision: str, source_family: str) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file() or not source_revision or not source_family:
        raise SourceFreezeError("SOURCE_FILE_OR_REVISION_MISSING")
    stat = resolved.stat()
    return {
        "path": str(resolved),
        "source_family": source_family,
        "source_revision": source_revision,
        "sha256": sha256_file(resolved),
        "bytes": stat.st_size,
        "modified_at_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).replace(microsecond=0).isoformat(),
    }


def _validate_timestamp(value: object, field: str) -> str:
    text = str(value or "")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceFreezeError(f"SOURCE_FREEZE_{field.upper()}_INVALID") from exc
    if parsed.tzinfo is None:
        raise SourceFreezeError(f"SOURCE_FREEZE_{field.upper()}_MUST_HAVE_TIMEZONE")
    return parsed.isoformat()


def build_source_freeze_manifest(
    *,
    trade_date: str,
    tdx_snapshot_identity: Mapping[str, Any],
    changed_tdx_files: Iterable[Mapping[str, Any]],
    exchange_calendar_revision: Mapping[str, Any],
    baostock_source_identity: Mapping[str, Any],
    gbbq_snapshot: Mapping[str, Any],
    identity_lifecycle_manifest: Mapping[str, Any],
    special_price_phase_manifest: Mapping[str, Any],
    observed_at: str,
    ingested_at: str,
    system_available_at: str,
) -> dict[str, Any]:
    """Build a source-consumption freeze using changed files, not a full rehash."""
    for value, field in (
        (observed_at, "observed_at"),
        (ingested_at, "ingested_at"),
        (system_available_at, "system_available_at"),
    ):
        _validate_timestamp(value, field)
    sources: dict[str, Mapping[str, Any]] = {
        "TDX": tdx_snapshot_identity,
        "EXCHANGE_CALENDAR": exchange_calendar_revision,
        "BAOSTOCK_DAILY": baostock_source_identity,
        "GBBQ": gbbq_snapshot,
        "IDENTITY_LIFECYCLE": identity_lifecycle_manifest,
        "SPECIAL_PRICE_PHASE": special_price_phase_manifest,
    }
    for family, record in sources.items():
        if not record.get("source_revision") or not record.get("sha256"):
            raise SourceFreezeError(f"SOURCE_FREEZE_{family}_IDENTITY_INCOMPLETE")
        if int(record.get("bytes", -1)) < 0:
            raise SourceFreezeError(f"SOURCE_FREEZE_{family}_BYTES_INVALID")
    changed = []
    for row in changed_tdx_files:
        item = dict(row)
        if not item.get("path") or not item.get("sha256") or int(item.get("bytes", -1)) < 0:
            raise SourceFreezeError("SOURCE_FREEZE_CHANGED_FILE_MANIFEST_INVALID")
        changed.append(item)
    changed.sort(key=lambda item: (str(item.get("trade_date") or ""), str(item["path"])))
    payload = {
        "contract_id": "V4_DAILY_SOURCE_FREEZE_V1",
        "version": "1.0.0",
        "trade_date": trade_date,
        "observed_at": _validate_timestamp(observed_at, "observed_at"),
        "ingested_at": _validate_timestamp(ingested_at, "ingested_at"),
        "system_available_at": _validate_timestamp(system_available_at, "system_available_at"),
        "source_families": {
            family: dict(record) for family, record in sources.items()
        },
        "tdx_increment": {
            "changed_file_count": len(changed),
            "changed_files": changed,
            "full_history_rehash_performed": False,
        },
        "tdx_root_write_count": 0,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    payload["manifest_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def write_source_freeze_atomic(path: Path, manifest: Mapping[str, Any], *, tdx_root: Path) -> str:
    ensure_outside_tdx(path, tdx_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(manifest, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
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


def source_freeze_complete(manifest: Mapping[str, Any]) -> bool:
    if manifest.get("contract_id") != "V4_DAILY_SOURCE_FREEZE_V1":
        return False
    families = manifest.get("source_families")
    if not isinstance(families, Mapping):
        return False
    return all(
        family in families
        and bool(families[family].get("source_revision"))
        and bool(families[family].get("sha256"))
        and int(families[family].get("bytes", -1)) >= 0
        for family in REQUIRED_SOURCE_FAMILIES
    )


def build_source_freeze_manifest_v2(
    *,
    trade_date: str,
    sources: Mapping[str, Mapping[str, Any]],
    changed_tdx_files: Iterable[Mapping[str, Any]],
    observed_at: str,
    ingested_at: str,
    system_available_at: str,
) -> dict[str, Any]:
    """Freeze the official TDX full package, delta, BaoStock batches and other facts."""
    for value, field in (
        (observed_at, "observed_at"),
        (ingested_at, "ingested_at"),
        (system_available_at, "system_available_at"),
    ):
        _validate_timestamp(value, field)
    missing = [family for family in REQUIRED_SOURCE_FAMILIES_V2 if family not in sources]
    if missing:
        raise SourceFreezeError("SOURCE_FREEZE_V2_REQUIRED_FAMILIES_MISSING:" + ",".join(missing))
    normalized: dict[str, dict[str, Any]] = {}
    for family in REQUIRED_SOURCE_FAMILIES_V2:
        record = dict(sources[family])
        if not record.get("source_revision") or not record.get("sha256"):
            raise SourceFreezeError(f"SOURCE_FREEZE_V2_{family}_IDENTITY_INCOMPLETE")
        if int(record.get("bytes", -1)) < 0:
            raise SourceFreezeError(f"SOURCE_FREEZE_V2_{family}_BYTES_INVALID")
        normalized[family] = record
    changed = []
    for row in changed_tdx_files:
        item = dict(row)
        if not item.get("path") or not item.get("sha256") or int(item.get("bytes", -1)) < 0:
            raise SourceFreezeError("SOURCE_FREEZE_V2_CHANGED_FILE_MANIFEST_INVALID")
        changed.append(item)
    changed.sort(key=lambda item: (str(item.get("trade_date") or ""), str(item["path"])))
    payload: dict[str, Any] = {
        "contract_id": "V4_DAILY_SOURCE_FREEZE_V2",
        "version": "2.0.0",
        "trade_date": trade_date,
        "observed_at": _validate_timestamp(observed_at, "observed_at"),
        "ingested_at": _validate_timestamp(ingested_at, "ingested_at"),
        "system_available_at": _validate_timestamp(system_available_at, "system_available_at"),
        "source_families": normalized,
        "tdx_increment": {
            "changed_file_count": len(changed),
            "changed_files": changed,
            "full_historical_rehash_performed": False,
        },
        "raw_daily_authority": "TDX_OFFICIAL_FULL_PACKAGE",
        "bao_stock_ohlc_substitution_permitted": False,
        "bao_stock_adjustment_factor_role": "AUDIT_FACT_NOT_CANONICAL_QFQ_AUTHORITY",
        "tdx_root_write_count": 0,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    payload["manifest_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def source_freeze_complete_v2(manifest: Mapping[str, Any]) -> bool:
    if manifest.get("contract_id") != "V4_DAILY_SOURCE_FREEZE_V2":
        return False
    families = manifest.get("source_families")
    if not isinstance(families, Mapping):
        return False
    complete = all(
        family in families
        and bool(families[family].get("source_revision"))
        and bool(families[family].get("sha256"))
        and int(families[family].get("bytes", -1)) >= 0
        for family in REQUIRED_SOURCE_FAMILIES_V2
    )
    if not complete:
        return False
    supplied = str(manifest.get("manifest_sha256") or "")
    material = dict(manifest)
    material.pop("manifest_sha256", None)
    canonical = json.dumps(material, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return supplied == hashlib.sha256(canonical).hexdigest()
