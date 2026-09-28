from __future__ import annotations

"""Compare official full TDX zip snapshots and emit append/revision events."""

import hashlib
import json
import math
import re
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

from tdx.day_reader import DAY_RECORD_LENGTH, decode_record


class TDXDeltaError(ValueError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _entry_index(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    entries: dict[str, zipfile.ZipInfo] = {}
    for info in archive.infolist():
        name = info.filename.replace("\\", "/")
        parts = name.split("/")
        if name.startswith("/") or re.match(r"^[a-zA-Z]:", name) or any(p in {".", ".."} for p in parts):
            raise TDXDeltaError("TDX_ZIP_UNSAFE_ENTRY_PATH")
        if name.casefold() in entries:
            raise TDXDeltaError("TDX_ZIP_DUPLICATE_ENTRY_PATH")
        entries[name.casefold()] = info
    return entries


def _records(raw: bytes) -> list[tuple[bytes, dict[str, Any]]]:
    if not raw or len(raw) % DAY_RECORD_LENGTH:
        raise TDXDeltaError("TDX_DAY_FILE_LENGTH_INVALID")
    records = []
    previous = 0
    for offset in range(0, len(raw), DAY_RECORD_LENGTH):
        chunk = raw[offset:offset + DAY_RECORD_LENGTH]
        try:
            record = decode_record(chunk)
            date.fromisoformat(f"{record.trade_date // 10000:04d}-{(record.trade_date // 100) % 100:02d}-{record.trade_date % 100:02d}")
        except (ValueError, OverflowError) as exc:
            raise TDXDeltaError("TDX_DAY_FILE_DATE_INVALID") from exc
        if record.trade_date <= previous:
            raise TDXDeltaError("TDX_DAY_FILE_DATE_ORDER_INVALID")
        if (not all(math.isfinite(value) for value in (record.open, record.high, record.low, record.close, record.amount))
                or record.amount < 0 or min(record.open, record.high, record.low, record.close) < 0
                or (record.open or record.high or record.low or record.close) and
                (record.high < max(record.open, record.low, record.close) or record.low > min(record.open, record.high, record.close))):
            raise TDXDeltaError("TDX_DAY_FILE_OHLC_INVALID")
        previous = record.trade_date
        records.append((chunk, {
            "trade_date": record.trade_date,
            "open": record.open,
            "high": record.high,
            "low": record.low,
            "close": record.close,
            "amount": record.amount,
            "volume": record.volume,
        }))
    return records


def _security_key(path: str) -> str:
    match = re.fullmatch(r"(?:[^/]+/)*([a-z]{2})(\d{6})\.day", path, re.I)
    if not match:
        raise TDXDeltaError("TDX_DAY_ENTRY_NAME_INVALID")
    market, code = match.group(1).lower(), match.group(2)
    if market not in {"sh", "sz", "bj"}:
        raise TDXDeltaError("TDX_DAY_ENTRY_MARKET_INVALID")
    return f"{market.upper()}.{code}"


def build_tdx_package_delta(
    *,
    parent_zip: Path,
    current_zip: Path,
    target_date: str,
    parent_snapshot_id: str,
    current_snapshot_id: str,
) -> dict[str, Any]:
    """Consume only changed/new day entries and classify vendor revisions."""
    try:
        date.fromisoformat(target_date)
    except ValueError as exc:
        raise TDXDeltaError("TARGET_DATE_INVALID") from exc
    if not parent_snapshot_id or not current_snapshot_id or parent_snapshot_id == current_snapshot_id:
        raise TDXDeltaError("TDX_SNAPSHOT_PARENT_IDENTITY_INVALID")
    try:
        with zipfile.ZipFile(parent_zip) as parent, zipfile.ZipFile(current_zip) as current:
            old_entries, new_entries = _entry_index(parent), _entry_index(current)
            old_names, new_names = set(old_entries), set(new_entries)
            unchanged, changed, added = [], [], []
            removed = sorted(old_names - new_names)
            for key in sorted(old_names & new_names):
                old, new = old_entries[key], new_entries[key]
                if (old.CRC, old.file_size, old.compress_size) == (new.CRC, new.file_size, new.compress_size):
                    unchanged.append(new.filename)
                else:
                    changed.append(new.filename)
            added = sorted((new_entries[key].filename for key in new_names - old_names))
            if removed:
                raise TDXDeltaError("SOURCE_REVISION_ANOMALY_REMOVED_ENTRY")
            target_num = int(target_date.replace("-", ""))
            target_bars: list[dict[str, Any]] = []
            appended_bars: list[dict[str, Any]] = []
            revisions: list[dict[str, Any]] = []
            entry_events: list[dict[str, Any]] = []
            parsed_count = 0
            for path in sorted(set(changed + added)):
                lower = path.lower()
                if not lower.endswith(".day"):
                    entry_events.append({"path": path, "classification": "CHANGED_NON_DAILY_ENTRY" if path in changed else "NEW_NON_DAILY_ENTRY"})
                    continue
                key = _security_key(lower)
                current_raw = current.read(new_entries[lower])
                new_records = _records(current_raw)
                parsed_count += 1
                old_records: list[tuple[bytes, dict[str, Any]]] = []
                if lower in old_entries:
                    old_records = _records(parent.read(old_entries[lower]))
                old_chunks = [chunk for chunk, _ in old_records]
                new_chunks = [chunk for chunk, _ in new_records]
                if len(new_chunks) < len(old_chunks):
                    raise TDXDeltaError("SOURCE_REVISION_ANOMALY_TRUNCATION")
                common = min(len(old_chunks), len(new_chunks))
                changed_indices = [i for i in range(common) if old_chunks[i] != new_chunks[i]]
                same_date_prefix = len(new_records) >= len(old_records) and all(
                    old_records[index][1]["trade_date"] == new_records[index][1]["trade_date"]
                    for index in range(len(old_records))
                )
                if len(new_records) > len(old_records) and not same_date_prefix:
                    raise TDXDeltaError("SOURCE_REVISION_ANOMALY_REWRITE")
                appended = len(new_chunks) > len(old_chunks) and same_date_prefix
                if changed_indices:
                    affected = [old_records[i][1]["trade_date"] for i in changed_indices]
                    revisions.append({
                        "security_id": key,
                        "affected_from": min(affected),
                        "affected_to": max(affected),
                        "source_snapshot_old": parent_snapshot_id,
                        "source_snapshot_new": current_snapshot_id,
                        "old_rows_sha256": _sha(b"".join(old_chunks[i] for i in changed_indices)),
                        "new_rows_sha256": _sha(b"".join(new_chunks[i] for i in changed_indices)),
                        "changed_record_count": len(changed_indices),
                        "reason": "VENDOR_SOURCE_REVISION",
                        "classification": "HISTORICAL_CORRECTION",
                    })
                elif old_records and not appended and new_chunks != old_chunks:
                    raise TDXDeltaError("SOURCE_REVISION_ANOMALY_REWRITE")
                for _, row in new_records:
                    if row["trade_date"] == target_num:
                        target_bars.append({"security_id": key, **row})
                if appended:
                    appended_records = new_records[len(old_records):]
                    appended_bars.extend(
                        {"security_id": key, **row} for _, row in appended_records
                    )
                    target_count = sum(row["trade_date"] == target_num for _, row in appended_records)
                    if target_count:
                        classification = "APPEND_ONLY_TARGET_DATE" if not changed_indices else "APPEND_WITH_HISTORICAL_CORRECTION"
                    else:
                        classification = "APPEND_NON_TARGET_DATE"
                    entry_events.append({"path": path, "security_id": key, "classification": classification,
                                         "old_record_count": len(old_records), "new_record_count": len(new_records),
                                         "target_date_records": target_count})
                elif not old_records:
                    entry_events.append({"path": path, "security_id": key, "classification": "NEW_ENTRY",
                                         "new_record_count": len(new_records),
                                         "target_date_records": sum(row["trade_date"] == target_num for _, row in new_records)})
                elif changed_indices:
                    entry_events.append({"path": path, "security_id": key, "classification": "HISTORICAL_CORRECTION",
                                         "changed_record_count": len(changed_indices)})
                else:
                    raise TDXDeltaError("SOURCE_REVISION_ANOMALY_REWRITE")
            target_bars.sort(key=lambda row: row["security_id"])
            appended_bars.sort(key=lambda row: (row["trade_date"], row["security_id"]))
            payload: dict[str, Any] = {
                "contract_id": "TDX_PACKAGE_DELTA_V1",
                "version": "1.0.0",
                "status": "READY" if target_bars else "NO_TARGET_DATE_BARS",
                "target_date": target_date,
                "parent_snapshot_id": parent_snapshot_id,
                "current_snapshot_id": current_snapshot_id,
                "entry_counts": {"unchanged": len(unchanged), "changed": len(changed), "new": len(added), "removed": 0},
                "unchanged_entries": unchanged,
                "changed_entries": changed,
                "new_entries": added,
                "parsed_changed_or_new_day_entries": parsed_count,
                "target_bars": target_bars,
                "target_bar_count": len(target_bars),
                "appended_bars": appended_bars,
                "appended_bar_count": len(appended_bars),
                "revision_events": revisions,
                "entry_events": entry_events,
                "full_historical_rehash_performed": False,
                "tdx_root_write_count": 0,
            }
            canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
            payload["delta_sha256"] = hashlib.sha256(canonical).hexdigest()
            return payload
    except zipfile.BadZipFile as exc:
        raise TDXDeltaError("TDX_ZIP_INVALID") from exc
