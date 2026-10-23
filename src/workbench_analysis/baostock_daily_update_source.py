from __future__ import annotations

"""Bounded BaoStock date-level daily K and adjustment-factor capture."""

import hashlib
import json
import math
import os
import re
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from workbench_analysis.baostock_supplemental import (
    BaoStockClient,
    BaoStockError,
    package_metadata,
)
from workbench_analysis.daily_source_freeze import ensure_outside_tdx
from workbench_analysis.baostock_runtime_acceptance import runtime_acceptance_error


CONTRACT_ID = "BAOSTOCK_DAILY_UPDATE_SOURCE_V1"
CONTRACT_VERSION = "1.1.0"
DAILY_OPERATION = "query_daily_history_k_AStock"
FACTOR_OPERATION = "query_daily_adjust_factor"
DAILY_METHOD = "query_daily_history_k_AStock"
FACTOR_METHOD = "query_daily_adjust_factor"
MAX_DAILY_ROWS = 20_000
MAX_FACTOR_ROWS = 20_000
DAILY_REQUIRED_FIELDS = frozenset({"date", "code", "open", "high", "low", "close", "volume", "amount", "tradestatus", "isST"})
FACTOR_REQUIRED_FIELDS = frozenset({"code", "dividOperateDate", "foreAdjustFactor", "backAdjustFactor", "adjustFactor"})
CODE_PATTERN = re.compile(r"^(?:sh|sz|bj)\.\d{6}$", re.I)


class BaoStockDailyUpdateError(ValueError):
    pass


def _canonical_rows_digest(rows: list[Mapping[str, Any]]) -> str:
    raw = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _atomic_json(path: Path, payload: Mapping[str, Any], *, tdx_root: Path) -> None:
    ensure_outside_tdx(path, tdx_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    except Exception:
        Path(name).unlink(missing_ok=True)
        raise


def _validate_daily_rows(rows: list[dict[str, str]], trade_date: str) -> None:
    if len(rows) > MAX_DAILY_ROWS:
        raise BaoStockDailyUpdateError("BAOSTOCK_DAILY_ROW_LIMIT_EXCEEDED")
    seen: set[str] = set()
    for row in rows:
        if not DAILY_REQUIRED_FIELDS.issubset(row):
            raise BaoStockDailyUpdateError("BAOSTOCK_DAILY_REQUIRED_FIELDS_MISSING")
        if row.get("date") != trade_date:
            raise BaoStockDailyUpdateError("BAOSTOCK_PROVIDER_DATE_MISMATCH")
        code = str(row.get("code") or "").lower()
        if not CODE_PATTERN.fullmatch(code):
            raise BaoStockDailyUpdateError("BAOSTOCK_DAILY_CODE_INVALID")
        if code in seen:
            raise BaoStockDailyUpdateError("BAOSTOCK_DAILY_DUPLICATE_SECURITY")
        seen.add(code)
        tradestatus = str(row.get("tradestatus"))
        if tradestatus not in {"0", "1"} or str(row.get("isST")) not in {"0", "1"}:
            raise BaoStockDailyUpdateError("BAOSTOCK_DAILY_STATUS_INVALID")
        for field in ("open", "high", "low", "close"):
            try:
                number = float(row[field])
            except (TypeError, ValueError) as exc:
                raise BaoStockDailyUpdateError("BAOSTOCK_DAILY_PRICE_INVALID") from exc
            if not math.isfinite(number) or number < 0:
                raise BaoStockDailyUpdateError("BAOSTOCK_DAILY_PRICE_INVALID")
        for field in ("volume", "amount"):
            raw = str(row.get(field) or "").strip()
            if tradestatus == "1" and not raw:
                raise BaoStockDailyUpdateError("BAOSTOCK_DAILY_VALUE_MISSING")
            if raw:
                try:
                    value = float(raw)
                except ValueError as exc:
                    raise BaoStockDailyUpdateError("BAOSTOCK_DAILY_VALUE_INVALID") from exc
                if not math.isfinite(value) or value < 0 or (field == "volume" and not value.is_integer()):
                    raise BaoStockDailyUpdateError("BAOSTOCK_DAILY_VALUE_INVALID")


def _validate_factor_rows(rows: list[dict[str, str]], trade_date: str) -> None:
    if len(rows) > MAX_FACTOR_ROWS:
        raise BaoStockDailyUpdateError("BAOSTOCK_FACTOR_ROW_LIMIT_EXCEEDED")
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if not FACTOR_REQUIRED_FIELDS.issubset(row):
            raise BaoStockDailyUpdateError("BAOSTOCK_FACTOR_REQUIRED_FIELDS_MISSING")
        code = str(row.get("code") or "").lower()
        effective = str(row.get("dividOperateDate") or "")
        if not CODE_PATTERN.fullmatch(code):
            raise BaoStockDailyUpdateError("BAOSTOCK_FACTOR_CODE_INVALID")
        try:
            date.fromisoformat(effective)
        except ValueError as exc:
            raise BaoStockDailyUpdateError("BAOSTOCK_FACTOR_EFFECTIVE_DATE_INVALID") from exc
        if effective > trade_date:
            raise BaoStockDailyUpdateError("BAOSTOCK_FACTOR_FUTURE_DATE_INVALID")
        identity = (code, effective)
        if identity in seen:
            raise BaoStockDailyUpdateError("BAOSTOCK_FACTOR_DUPLICATE_SECURITY_DATE")
        seen.add(identity)
        for field in ("foreAdjustFactor", "backAdjustFactor", "adjustFactor"):
            try:
                value = float(row[field])
            except (TypeError, ValueError) as exc:
                raise BaoStockDailyUpdateError("BAOSTOCK_FACTOR_VALUE_INVALID") from exc
            if not math.isfinite(value) or not (value > 0):
                raise BaoStockDailyUpdateError("BAOSTOCK_FACTOR_VALUE_INVALID")


def _normalize_factor_schema(rows, fields, *, sdk, adapter_path=None):
    """Normalize the one hash-pinned BaoStock 0.9.3 factor header alias."""
    raw_fields=list(fields or [])
    if len(raw_fields)!=len(set(raw_fields)):
        raise BaoStockDailyUpdateError("BAOSTOCK_FACTOR_SCHEMA_DUPLICATE_FIELD")
    if not rows and not raw_fields:
        return [],dict(raw_fields=[],normalized_fields=[],adapter_status='EMPTY_RESPONSE_SCHEMA_NOT_OBSERVED',
            adapter_contract_id=None,adapter_version=None,adapter_sha256=None,field_map={})
    if set(raw_fields)==FACTOR_REQUIRED_FIELDS:
        return list(rows),dict(raw_fields=raw_fields,normalized_fields=raw_fields,
            adapter_status='NATIVE_REQUIRED_SCHEMA',adapter_contract_id=None,adapter_version=None,
            adapter_sha256=None,field_map={})
    path=Path(adapter_path) if adapter_path is not None else Path(__file__).resolve().parents[2]/'config/baostock_dm01_sdk_schema_adapter_v2.json'
    try:
        raw=path.read_bytes();adapter=json.loads(raw)
    except (OSError,ValueError) as exc:
        raise BaoStockDailyUpdateError("BAOSTOCK_FACTOR_SCHEMA_ADAPTER_UNAVAILABLE") from exc
    alias=adapter.get('factor_header_alias')
    raw_schema=adapter.get('factor_raw_schema')
    if (adapter.get('contract_id')!='BAOSTOCK_DM01_SDK_SCHEMA_ADAPTER_V2'
            or adapter.get('version')!='2.0.0' or adapter.get('sdk_version')!=sdk.get('version')
            or adapter.get('sdk_python_sources_sha256')!=sdk.get('installed_python_sources_sha256')
            or not isinstance(raw_schema,list) or not isinstance(alias,dict)
            or alias!={'adjustFacto':'adjustFactor'} or set(raw_fields)!=set(raw_schema)):
        raise BaoStockDailyUpdateError("BAOSTOCK_FACTOR_SCHEMA_ADAPTER_BINDING_MISMATCH")
    normalized_fields=[alias.get(name,name) for name in raw_fields]
    if set(normalized_fields)!=FACTOR_REQUIRED_FIELDS or len(normalized_fields)!=len(FACTOR_REQUIRED_FIELDS):
        raise BaoStockDailyUpdateError("BAOSTOCK_FACTOR_SCHEMA_UNSUPPORTED")
    normalized=[]
    for row in rows:
        if 'adjustFacto' not in row or 'adjustFactor' in row:
            raise BaoStockDailyUpdateError("BAOSTOCK_FACTOR_SCHEMA_ROW_ALIAS_MISMATCH")
        normalized.append({alias.get(name,name):value for name,value in row.items()})
    return normalized,dict(raw_fields=raw_fields,normalized_fields=normalized_fields,
        adapter_status=adapter.get('status'),adapter_contract_id=adapter['contract_id'],
        adapter_version=adapter['version'],adapter_sha256=hashlib.sha256(raw).hexdigest(),
        field_map=alias,sdk_version=sdk['version'],sdk_sources_sha256=sdk['installed_python_sources_sha256'])


def crosscheck_tdx_with_baostock(
    *,
    trade_date: str,
    tdx_rows: list[Mapping[str, Any]],
    baostock_rows: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Emit exact-match diagnostics; TDX remains authoritative for every field."""
    tdx_by_code = {str(row.get("security_id") or "").lower(): row for row in tdx_rows}
    bao_by_code = {str(row.get("code") or "").lower(): row for row in baostock_rows}
    comparisons, conflicts, set_gaps = [], [], []
    for code in sorted(set(tdx_by_code) | set(bao_by_code)):
        local, source = tdx_by_code.get(code), bao_by_code.get(code)
        if local is None or source is None:
            gap = {"code": code, "status": "IDENTITY_OR_BAR_SET_MISMATCH",
                   "tdx_bar_present": local is not None, "baostock_row_present": source is not None}
            comparisons.append(gap)
            set_gaps.append(gap)
            continue
        mismatch = {}
        for field in ("close", "volume", "amount"):
            try:
                left, right = float(local[field]), float(source[field])
            except (KeyError, TypeError, ValueError):
                mismatch[field] = "UNAVAILABLE"
                continue
            if left != right:
                mismatch[field] = {"tdx": left, "baostock": right}
        if str(source.get("tradestatus")) == "0":
            mismatch["tradestatus"] = "BAOSTOCK_SUSPENDED_WHILE_TDX_BAR_EXISTS"
        status = "CONFLICT" if mismatch else "EXACT_FINGERPRINT_MATCH"
        item = {"code": code, "status": status, "mismatches": mismatch}
        comparisons.append(item)
        if mismatch:
            conflicts.append(item)
    canonical = json.dumps(comparisons, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "contract_id": "TDX_BAOSTOCK_DAILY_CONFLICT_RECEIPT_V1",
        "trade_date": trade_date,
        "status": "CONFLICTS_FOUND" if conflicts else "CROSSCHECK_SET_GAPS_PRESENT" if set_gaps else "NO_EXACT_VALUE_CONFLICTS",
        "comparison_mode": "EXACT_DIAGNOSTIC_NO_UNACCEPTED_TOLERANCE_APPLIED",
        "comparisons": comparisons,
        "conflicts": conflicts,
        "set_gaps": set_gaps,
        "gate_effect": "DIAGNOSTIC_ONLY",
        "data_head_blocking": False,
        "tdx_remains_canonical_authority": True,
        "baostock_rows_promoted_to_raw": False,
        "sha256": hashlib.sha256(canonical).hexdigest(),
    }


def _revision_paths(root: Path, target: str) -> list[Path]:
    folder = root / "baostock" / target.replace("-", "")
    return [path for path in folder.glob("sha256-*") if (path / "daily_update.json").is_file()]


def capture_baostock_daily_update(
    *,
    trade_date: str,
    client: BaoStockClient,
    snapshot_root: Path,
    tdx_root: Path = Path("D:/new_tdx"),
    observed_at: str | None = None,
    runtime_acceptance_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Fetch two date-level batch responses through the bounded shared client."""
    try:
        date.fromisoformat(trade_date)
    except ValueError as exc:
        raise BaoStockDailyUpdateError("TARGET_DATE_INVALID") from exc
    ensure_outside_tdx(snapshot_root, tdx_root)
    if not client.logged_in or client.sdk is None:
        raise BaoStockDailyUpdateError("BAOSTOCK_SESSION_NOT_READY")
    if not callable(getattr(client.sdk, DAILY_METHOD, None)) or not callable(getattr(client.sdk, FACTOR_METHOD, None)):
        raise BaoStockDailyUpdateError("BAOSTOCK_DAILYUPDATE_API_NOT_AVAILABLE")
    try:
        sdk = package_metadata()
    except BaoStockError as exc:
        raise BaoStockDailyUpdateError("BAOSTOCK_RUNTIME_NOT_PINNED") from exc
    runtime_error = runtime_acceptance_error(
        runtime_acceptance_manifest,
        sdk=sdk,
        auth_mode=str(getattr(client, "auth_mode", "PUBLIC_ANONYMOUS")),
    )
    if runtime_error:
        raise BaoStockDailyUpdateError("BAOSTOCK_" + runtime_error)
    if runtime_acceptance_manifest["live_smoke"]["target_date"] != trade_date:
        raise BaoStockDailyUpdateError("BAOSTOCK_RUNTIME_ACCEPTANCE_TARGET_DATE_MISMATCH")
    observed = observed_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    try:
        parsed_observed = datetime.fromisoformat(observed.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BaoStockDailyUpdateError("OBSERVED_AT_INVALID") from exc
    if parsed_observed.tzinfo is None:
        raise BaoStockDailyUpdateError("OBSERVED_AT_MUST_HAVE_TIMEZONE")

    daily_rows, daily_meta = client.query_rows(
        DAILY_OPERATION, DAILY_METHOD, date=trade_date, max_rows=MAX_DAILY_ROWS, max_pages=1
    )
    _validate_daily_rows(daily_rows, trade_date)
    if daily_meta.get("page_count") != 1:
        raise BaoStockDailyUpdateError("BAOSTOCK_DAILY_BATCH_PAGINATION_UNEXPECTED")
    if not daily_rows:
        return {
            "contract_id": CONTRACT_ID,
            "version": CONTRACT_VERSION,
            "status": "WAIT_BAOSTOCK_DAILY_UPDATE",
            "trade_date": trade_date,
            "observed_at": parsed_observed.isoformat(),
            "reason": "NO_DAILY_ROWS_FOR_TARGET_DATE",
            "request_count": 1,
            "api_operations": [DAILY_OPERATION],
        }
    raw_factor_rows, raw_factor_meta = client.query_rows(
        FACTOR_OPERATION, FACTOR_METHOD, date=trade_date, max_rows=MAX_FACTOR_ROWS, max_pages=1
    )
    factor_rows,factor_schema=_normalize_factor_schema(raw_factor_rows,raw_factor_meta.get('fields'),sdk=sdk)
    factor_meta=dict(raw_factor_meta,fields=factor_schema['normalized_fields'],raw_fields=factor_schema['raw_fields'],
        schema_adaptation={k:v for k,v in factor_schema.items() if k not in ('raw_fields','normalized_fields')})
    _validate_factor_rows(factor_rows, trade_date)
    if factor_meta.get("page_count") != 1:
        raise BaoStockDailyUpdateError("BAOSTOCK_FACTOR_BATCH_PAGINATION_UNEXPECTED")
    if factor_meta.get("provider_date") != trade_date:
        raise BaoStockDailyUpdateError("BAOSTOCK_FACTOR_PROVIDER_DATE_MISMATCH")
    daily_digest = _canonical_rows_digest(daily_rows)
    factor_digest = _canonical_rows_digest(factor_rows)
    raw_factor_digest = _canonical_rows_digest(raw_factor_rows)
    adapter_digest=factor_schema.get('adapter_sha256') or hashlib.sha256(b'BAOSTOCK_FACTOR_NATIVE_REQUIRED_SCHEMA_V1').hexdigest()
    composite = hashlib.sha256(f"{trade_date}\0{daily_digest}\0{raw_factor_digest}\0{factor_digest}\0{adapter_digest}".encode()).hexdigest()
    snapshot_id = "sha256-" + composite
    folder = snapshot_root / "baostock" / trade_date.replace("-", "") / snapshot_id
    ensure_outside_tdx(folder, tdx_root)
    existing = folder / "daily_update.json"
    previous = _revision_paths(snapshot_root, trade_date)
    revision = 1 + len([path for path in previous if path != folder])
    prior_payload = None
    if existing.is_file():
        try:
            prior_payload = json.loads(existing.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise BaoStockDailyUpdateError("BAOSTOCK_IMMUTABLE_SNAPSHOT_CORRUPT") from exc
        prior_ops = prior_payload.get("query_operations", [])
        if (prior_payload.get("trade_date") != trade_date or len(prior_ops) != 2
                or prior_ops[0].get("response_sha256") != daily_digest
                or prior_ops[1].get("response_sha256") != factor_digest):
            raise BaoStockDailyUpdateError("BAOSTOCK_IMMUTABLE_SNAPSHOT_COLLISION")
    status = "NOOP_SOURCE_ALREADY_FROZEN" if existing.is_file() else "BAOSTOCK_DAILY_SNAPSHOT_READY"
    payload: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "version": CONTRACT_VERSION,
        "status": status,
        "trade_date": trade_date,
        "provider_date": trade_date,
        "source_revision_id": f"{trade_date.replace('-', '')}-r{revision}",
        "snapshot_id": snapshot_id,
        "observed_at": parsed_observed.isoformat(),
        "received_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "provider_api_version": "DailyUpdates as documented by BaoStock Knowledge Base",
        "provider_api_docs_url": "https://www.baostock.com/mainContent?file=DailyUpdates.md",
        "provider_api_menu_url": "https://www.baostock.com/helpDocsHome",
        "sdk": sdk,
        "query_operations": [
            {"method": DAILY_METHOD, "params": {"date": trade_date}, "metadata": daily_meta,
             "row_count": len(daily_rows), "response_sha256": daily_digest},
            {"method": FACTOR_METHOD, "params": {"date": trade_date}, "metadata": factor_meta,
             "row_count": len(raw_factor_rows), "response_sha256": raw_factor_digest,
             "normalized_rows_sha256": factor_digest},
        ],
        "schema_adaptations": {"adjustment_factor": factor_schema},
        "daily_rows": daily_rows,
        "adjustment_factor_rows": factor_rows,
        "raw_daily_ohlc_authority": "TDX_ONLY",
        "bao_stock_ohlc_substitution_permitted": False,
        "adjustment_factor_role": "AUDIT_FACT_NOT_CANONICAL_QFQ_AUTHORITY",
        "request_count": 2,
        "date_level_query_count": 2,
        "tdx_root_write_count": 0,
    }
    if not existing.is_file():
        _atomic_json(existing, payload, tdx_root=tdx_root)
    return payload
