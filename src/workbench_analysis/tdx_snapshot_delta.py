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


def resolve_tdx_package_source_candidates(project_root, target_date: str,
                                         parent_sha256: str, current_sha256: str):
    """Resolve both exact official package identities from PostgreSQL.

    A verified ZIP is not sufficient evidence for an operational delta: the
    exact provider date, revision, first-available clock and role must already
    have been recorded as separate PG source candidates.
    """
    date.fromisoformat(target_date)
    if parent_sha256 == current_sha256:
        raise TDXDeltaError("TDX_DELTA_PARENT_CURRENT_PACKAGE_MUST_DIFFER")
    from workbench_db.v4_forward_pg_r1 import ForwardFactStore
    store=ForwardFactStore(Path(project_root),"data/v4/historical_source_ingress_pg_r1")
    expected={"PARENT":parent_sha256,"CURRENT":current_sha256}
    resolved={}
    for binding in store.refs("tdx_source_package_candidate"):
        candidate=store.read(binding)
        identity=candidate.get("source_identity",{})
        role=identity.get("source_role","").removeprefix("OFFICIAL_").removesuffix("_PACKAGE")
        if role not in expected or identity.get("package_sha256")!=expected[role]:
            continue
        if identity.get("T0")!=target_date:
            continue
        if candidate.get("contract_id")!="V4_TDX_OFFICIAL_PACKAGE_SOURCE_PG_R1":
            continue
        if (candidate.get("accepted_head") is not False or candidate.get("PIT_ELIGIBLE") is not False
                or identity.get("AS_RECORDED") is not False or identity.get("PIT_ELIGIBLE") is not False):
            raise TDXDeltaError("TDX_DELTA_SOURCE_CANDIDATE_PERMISSION_OVERCLAIM")
        if identity.get("first_available_at") is None:
            raise TDXDeltaError("TDX_DELTA_SOURCE_FIRST_AVAILABLE_AT_REQUIRED")
        if identity.get("provider")!="TDX_OFFICIAL_DAILY_PACKAGE":
            raise TDXDeltaError("TDX_DELTA_OFFICIAL_PROVIDER_REQUIRED")
        if identity.get("zip_validation",{}).get("status")!="PASS":
            raise TDXDeltaError("TDX_DELTA_SOURCE_ZIP_VALIDATION_REQUIRED")
        source_id=f"TDX_OFFICIAL_{role}_PACKAGE_R1"
        if identity.get("source_id")!=source_id:
            raise TDXDeltaError("TDX_DELTA_SOURCE_ROLE_IDENTITY_MISMATCH")
        resolved.setdefault(role,[]).append((binding,identity))
    for role in expected:
        if len(resolved.get(role,[]))!=1:
            raise TDXDeltaError("TDX_DELTA_EXACT_PG_SOURCE_IDENTITY_REQUIRED:"+role)
    return {role:dict(binding=resolved[role][0][0],identity=resolved[role][0][1])
            for role in ("PARENT","CURRENT")}


def persist_tdx_delta_candidate_pg(project_root, parent_zip: Path, current_zip: Path,
                                  delta: dict[str, Any], *, contract_id: str | None = None,
                                  source_candidates: dict[str, dict[str, Any]] | None = None):
    """Bind distinct parent/current package identities and delta rows in PG."""
    from datetime import datetime, timezone
    from workbench_db.v4_forward_pg_r1 import ForwardFactStore, canonical, digest
    parent=Path(parent_zip).resolve();current=Path(current_zip).resolve()
    with parent.open('rb') as stream: parent_sha=hashlib.file_digest(stream,'sha256').hexdigest()
    with current.open('rb') as stream: current_sha=hashlib.file_digest(stream,'sha256').hexdigest()
    expected_parent=str(delta.get('parent_snapshot_id') or delta.get('parent_package_sha256') or '').removeprefix('sha256-')
    expected_current=str(delta.get('current_snapshot_id') or delta.get('current_package_sha256') or '').removeprefix('sha256-')
    if (parent_sha!=expected_parent or current_sha!=expected_current or parent_sha==current_sha):
        raise TDXDeltaError('TDX_DELTA_PG_SOURCE_PACKAGE_IDENTITY_MISMATCH')
    target_date=delta.get('target_date')
    if target_date is None and delta.get('target_dates'):
        target_date=delta['target_dates'][-1]
    if not isinstance(target_date,str):
        raise TDXDeltaError('TDX_DELTA_PG_T0_REQUIRED')
    source_packages=[]
    for role,source_id,sha,path in (
        ('PARENT','TDX_OFFICIAL_PARENT_PACKAGE_R1',parent_sha,parent),
        ('CURRENT','TDX_OFFICIAL_CURRENT_PACKAGE_R1',current_sha,current),
    ):
        metadata=(source_candidates or {}).get(role)
        identity=(metadata or {}).get('identity',{})
        if metadata is not None:
            if (identity.get('source_id')!=source_id or identity.get('source_role')!=f'OFFICIAL_{role}_PACKAGE'
                    or identity.get('T0')!=target_date or identity.get('package_sha256')!=sha
                    or identity.get('package_bytes')!=path.stat().st_size
                    or identity.get('first_available_at') is None
                    or identity.get('zip_validation',{}).get('status')!='PASS'):
                raise TDXDeltaError('TDX_DELTA_PG_SOURCE_METADATA_MISMATCH:'+role)
            source_packages.append({k:identity.get(k) for k in (
                'source_id','source_role','provider','T0','provider_package_date',
                'source_revision_number','package_sha256','package_bytes','first_available_at',
                'parser_contract','zip_validation','AS_RECORDED','PIT_ELIGIBLE')})
        else:
            source_packages.append({'source_id':source_id,'role':role,'package_sha256':sha,
                'package_bytes':path.stat().st_size,'zip_validation':'PASS','first_available_at':None})
    availability_complete=all(source.get('first_available_at') is not None for source in source_packages)
    record={'contract_id':'V4_TDX_PACKAGE_DELTA_CANDIDATE_PG_R1','contract_version':'1.0.0',
        'candidate_status':'DIAGNOSTIC_ONLY','source_contract_id':contract_id or delta.get('contract_id'),
        'T0':target_date,'captured_at':datetime.now(timezone.utc).isoformat(),
        'source_packages':source_packages,
        'source_availability_complete':availability_complete,
        'availability_gap':None if availability_complete else 'PARENT_CURRENT_FIRST_AVAILABLE_AT_NOT_PROVEN',
        'delta_sha256':delta.get('delta_sha256'),'delta':delta,
        'AS_RECORDED':False,'PIT_ELIGIBLE':False,'accepted_head':False,'publication_id':None}
    key=digest(canonical(record))
    store=ForwardFactStore(Path(project_root),'data/v4/historical_source_ingress_pg_r1')
    binding=store.append('tdx_package_delta_candidate',key,record,migration_timeout_seconds=120)
    readback=store.read(binding)
    if readback!=record or digest(canonical(readback['delta']))!=digest(canonical(delta)):
        raise TDXDeltaError('TDX_DELTA_PG_CANDIDATE_READBACK_MISMATCH')
    return dict(binding=binding,readback='PASS',T0=target_date,
                parent_source_id='TDX_OFFICIAL_PARENT_PACKAGE_R1',
                current_source_id='TDX_OFFICIAL_CURRENT_PACKAGE_R1',
                parent_package_sha256=parent_sha,current_package_sha256=current_sha,
                candidate_status='DIAGNOSTIC_ONLY',availability_complete=availability_complete,
                parent_first_available_at=source_packages[0].get('first_available_at'),
                current_first_available_at=source_packages[1].get('first_available_at'))


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
        quality_codes = []
        ohlc_amount = (record.open, record.high, record.low, record.close, record.amount)
        if not all(math.isfinite(value) for value in ohlc_amount):
            quality_codes.append("NON_FINITE_OHLC_OR_AMOUNT")
        elif record.amount < 0 or min(record.open, record.high, record.low, record.close) < 0:
            quality_codes.append("NEGATIVE_OHLC_OR_AMOUNT")
        elif ((record.open or record.high or record.low or record.close)
              and (record.high < max(record.open, record.low, record.close)
                   or record.low > min(record.open, record.high, record.close))):
            quality_codes.append("OHLC_ENVELOPE_INVALID")
        previous = record.trade_date
        records.append((chunk, {
            "trade_date": record.trade_date,
            "open": record.open,
            "high": record.high,
            "low": record.low,
            "close": record.close,
            "amount": record.amount,
            "volume": record.volume,
            "source_quality_codes": quality_codes,
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
            changed_file_manifest: list[dict[str, Any]] = []
            parsed_count = 0
            quality_anomalies: list[dict[str, Any]] = []
            quality_anomaly_count = 0
            invalid_target_records: list[dict[str, Any]] = []
            invalid_target_record_count = 0
            for path in sorted(set(changed + added)):
                lower = path.replace("\\", "/").lower()
                current_raw = current.read(new_entries[lower])
                changed_file_manifest.append({
                    "path": path,
                    "trade_date": target_date,
                    "sha256": _sha(current_raw),
                    "bytes": len(current_raw),
                    "classification": "CHANGED" if lower in old_entries else "NEW",
                })
                if not lower.endswith(".day"):
                    entry_events.append({"path": path, "classification": "CHANGED_NON_DAILY_ENTRY" if path in changed else "NEW_NON_DAILY_ENTRY"})
                    continue
                key = _security_key(lower)
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
                if any(
                    old_records[index][1]["trade_date"] != new_records[index][1]["trade_date"]
                    for index in range(common)
                ):
                    raise TDXDeltaError("SOURCE_REVISION_ANOMALY_REWRITE")
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
                        "affected_trade_dates": sorted(set(affected)),
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
                    if not row["source_quality_codes"]:
                        if row["trade_date"] == target_num:
                            target_bars.append({"security_id": key, **row})
                        continue
                    anomaly = {"security_id": key, "trade_date": row["trade_date"],
                               "quality_codes": row["source_quality_codes"]}
                    quality_anomaly_count += 1
                    if len(quality_anomalies) < 100:
                        quality_anomalies.append(anomaly)
                    if row["trade_date"] == target_num:
                        invalid_target_record_count += 1
                        if len(invalid_target_records) < 100:
                            invalid_target_records.append(anomaly)
                if appended:
                    appended_records = new_records[len(old_records):]
                    appended_bars.extend({"security_id": key, **row} for _, row in appended_records
                                          if not row["source_quality_codes"])
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
                "status": ("TARGET_DATE_SOURCE_QUALITY_GAP" if invalid_target_records else
                           "READY_WITH_HISTORICAL_QUALITY_GAPS" if quality_anomalies and target_bars else
                           "READY" if target_bars else "NO_TARGET_DATE_BARS"),
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
                "source_quality_anomaly_count": quality_anomaly_count,
                "source_quality_anomalies": quality_anomalies,
                "source_quality_anomalies_truncated": quality_anomaly_count > len(quality_anomalies),
                "invalid_target_record_count": invalid_target_record_count,
                "invalid_target_records": invalid_target_records,
                "invalid_target_records_truncated": invalid_target_record_count > len(invalid_target_records),
                "appended_bars": appended_bars,
                "appended_bar_count": len(appended_bars),
                "revision_events": revisions,
                "entry_events": entry_events,
                "changed_file_manifest": changed_file_manifest,
                "full_historical_rehash_performed": False,
                "tdx_root_write_count": 0,
            }
            canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
            payload["delta_sha256"] = hashlib.sha256(canonical).hexdigest()
            return payload
    except zipfile.BadZipFile as exc:
        raise TDXDeltaError("TDX_ZIP_INVALID") from exc


def build_tdx_session_delta_view(package_delta: dict[str, Any], trade_date: str) -> dict[str, Any]:
    """Select one official session from a single full-package source delta."""
    try:
        date.fromisoformat(trade_date)
    except ValueError as exc:
        raise TDXDeltaError("TARGET_DATE_INVALID") from exc
    if package_delta.get("contract_id") != "TDX_PACKAGE_DELTA_V1" or not package_delta.get("delta_sha256"):
        raise TDXDeltaError("TDX_PACKAGE_DELTA_IDENTITY_MISSING")
    parent = package_delta.get("parent_snapshot_id")
    current = package_delta.get("current_snapshot_id")
    if not parent or not current or parent == current:
        raise TDXDeltaError("TDX_PACKAGE_DELTA_LINEAGE_INVALID")
    day = int(trade_date.replace("-", ""))
    source_rows = package_delta.get("appended_bars", [])
    rows = [dict(row) for row in source_rows if int(row.get("trade_date", -1)) == day]
    corrections = [
        dict(event) for event in package_delta.get("revision_events", [])
        if day in {int(value) for value in event.get("affected_trade_dates", [])}
    ]
    rows.sort(key=lambda row: (str(row.get("security_id") or ""), int(row["trade_date"])))
    payload = {
        "contract_id": "TDX_SESSION_DELTA_VIEW_V1",
        "version": "1.0.0",
        "status": ("TARGET_DATE_SOURCE_QUALITY_GAP" if package_delta.get("invalid_target_records")
                   else "READY" if rows else "NO_TARGET_DATE_BARS"),
        "source_quality_status": package_delta.get("status"),
        "target_date": trade_date,
        "parent_snapshot_id": parent,
        "current_snapshot_id": current,
        "package_delta_sha256": package_delta["delta_sha256"],
        "target_bars": rows,
        "target_bar_count": len(rows),
        "source_quality_anomaly_count": package_delta.get("source_quality_anomaly_count", 0),
        "source_quality_anomalies": package_delta.get("source_quality_anomalies", []),
        "invalid_target_records": package_delta.get("invalid_target_records", []),
        "historical_corrections": corrections,
        "revision_events": corrections,
        "historical_correction_count": len(corrections),
        "full_historical_rehash_performed": False,
        "tdx_root_write_count": 0,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    payload["session_delta_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload
