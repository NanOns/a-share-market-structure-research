"""R6 contract for binding an existing daily producer result to a publication.

The module validates and stores rows supplied by the existing V4 producer; it
does not calculate prices, moving averages, profiles, or signals. R6 deliberately
keeps publishability blocked while the live PG producer, its completeness
thresholds, and an independent database readback are absent.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
import math
import re
from typing import Any, Mapping, Sequence


CONTRACT_ID = "V4_DAILY_CORE_RESULT_BINDING_R6"
CONTRACT_VERSION = "1.0.0"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MAX_ROWS = 20_000
_PRICE_FIELDS = ("open", "high", "low", "close", "volume", "amount", "turnover_rate")
_PROFILE_FIELDS = ("ma5", "ma20", "ma60")


class CoreResultError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _date(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if not isinstance(value, str):
        raise CoreResultError("CORE_RESULT_T0_INVALID")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise CoreResultError("CORE_RESULT_T0_INVALID") from exc
    if parsed.isoformat() != value:
        raise CoreResultError("CORE_RESULT_T0_NONCANONICAL")
    return value


def _number(value: Any, field: str, *, nullable: bool = True) -> float | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool):
        raise CoreResultError("CORE_RESULT_VALUE_INVALID:" + field)
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise CoreResultError("CORE_RESULT_VALUE_INVALID:" + field) from exc
    if not math.isfinite(number) or number < 0:
        raise CoreResultError("CORE_RESULT_VALUE_INVALID:" + field)
    return number


def build_daily_core_result_plan(
    *,
    publication_id: str,
    publication_revision: int,
    trade_date: str,
    source_manifest_sha256: str,
    producer_contract_id: str,
    producer_sha256: str,
    producer_receipt: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    completeness_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a deterministic plan from actual producer rows, never computed here."""
    target = _date(trade_date)
    if (not isinstance(publication_id, str) or not publication_id.strip()
            or isinstance(publication_revision, bool) or not isinstance(publication_revision, int)
            or publication_revision <= 0):
        raise CoreResultError("CORE_RESULT_PUBLICATION_IDENTITY_INVALID")
    if not _SHA256.fullmatch(str(source_manifest_sha256)) or not _SHA256.fullmatch(str(producer_sha256)):
        raise CoreResultError("CORE_RESULT_DIGEST_INVALID")
    if not isinstance(producer_contract_id, str) or not producer_contract_id.strip():
        raise CoreResultError("CORE_RESULT_PRODUCER_CONTRACT_REQUIRED")
    if not isinstance(producer_receipt, Mapping):
        raise CoreResultError("CORE_RESULT_PRODUCER_RECEIPT_REQUIRED")
    receipt = dict(producer_receipt)
    receipt_digest = receipt.pop("receipt_sha256", None)
    if (receipt_digest != _sha(receipt)
            or receipt.get("trade_date") != target
            or receipt.get("producer_contract_id") != producer_contract_id
            or receipt.get("producer_sha256") != producer_sha256
            or receipt.get("publication_id") != publication_id
            or receipt.get("publication_revision") != publication_revision
            or receipt.get("source_manifest_sha256") != source_manifest_sha256):
        raise CoreResultError("CORE_RESULT_PRODUCER_RECEIPT_BINDING_MISMATCH")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows or len(rows) > _MAX_ROWS:
        raise CoreResultError("CORE_RESULT_ROWS_EMPTY_OR_LIMIT_EXCEEDED")

    normalized = []
    seen = set()
    missing_price = 0
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise CoreResultError("CORE_RESULT_ROW_INVALID")
        security = str(raw.get("security_id") or "").strip().upper()
        if not security or security in seen or _date(raw.get("trade_date")) != target:
            raise CoreResultError("CORE_RESULT_ROW_IDENTITY_INVALID")
        seen.add(security)
        security_type = raw.get("security_type")
        if not isinstance(security_type, str) or security_type not in {"STOCK", "INDEX", "FUND", "UNKNOWN"}:
            raise CoreResultError("CORE_RESULT_SECURITY_TYPE_INVALID")
        trade_status = raw.get("trade_status")
        if trade_status not in {"TRADING", "SUSPENDED", "DELISTED", "UNKNOWN"}:
            raise CoreResultError("CORE_RESULT_TRADE_STATUS_INVALID")
        values = {field: _number(raw.get(field), field) for field in (*_PRICE_FIELDS, *_PROFILE_FIELDS)}
        if trade_status == "TRADING" and any(values[field] is None for field in ("open", "high", "low", "close")):
            raise CoreResultError("CORE_RESULT_TRADING_PRICE_MISSING")
        if (values["high"] is not None and any(values[field] is not None for field in ("open", "low", "close"))
                and values["high"] < max(values[field] for field in ("open", "low", "close") if values[field] is not None)):
            raise CoreResultError("CORE_RESULT_OHLC_RANGE_INVALID")
        if (values["low"] is not None and any(values[field] is not None for field in ("open", "high", "close"))
                and values["low"] > min(values[field] for field in ("open", "high", "close") if values[field] is not None)):
            raise CoreResultError("CORE_RESULT_OHLC_RANGE_INVALID")
        if values["close"] is None:
            missing_price += 1
        if raw.get("price_basis") != "TDX_GBBQ_UNCHANGED":
            raise CoreResultError("CORE_RESULT_PRICE_BASIS_UNSUPPORTED")
        turnover_status = raw.get("turnover_status")
        if turnover_status not in {"AVAILABLE", "TURNOVER_UNAVAILABLE"}:
            raise CoreResultError("CORE_RESULT_TURNOVER_STATUS_REQUIRED")
        if (turnover_status == "AVAILABLE") != (values["turnover_rate"] is not None):
            raise CoreResultError("CORE_RESULT_TURNOVER_STATUS_VALUE_MISMATCH")
        history_status = raw.get("history_status")
        if history_status not in {"SUFFICIENT", "INSUFFICIENT_NEW_LISTING_HISTORY", "HISTORY_UNKNOWN"}:
            raise CoreResultError("CORE_RESULT_HISTORY_STATUS_REQUIRED")
        source_revision_id = raw.get("source_revision_id")
        if not isinstance(source_revision_id, str) or not source_revision_id.strip():
            raise CoreResultError("CORE_RESULT_SOURCE_REVISION_MISSING")
        row = {
            "trade_date": target, "security_id": security, "security_type": security_type,
            "trade_status": trade_status, **values, "price_basis": "TDX_GBBQ_UNCHANGED",
            "turnover_status": turnover_status, "history_status": history_status,
            "source_revision_id": source_revision_id,
            "profile_payload": dict(raw.get("profile_payload") or {}),
            "quality_status": str(raw.get("quality_status") or "UNKNOWN"),
        }
        row["row_sha256"] = _sha(row)
        normalized.append(row)
    normalized.sort(key=lambda row: row["security_id"].encode("utf-8"))

    if completeness_contract is None:
        completeness_contract_id = "UNRESOLVED"
        completeness_contract_version = "UNRESOLVED"
        completeness_status = "CONTRACT_UNRESOLVED"
        publishability = "BLOCKED_COMPLETENESS_CONTRACT_UNRESOLVED"
    else:
        # No threshold is inferred here. This is a sentinel until the active,
        # versioned operational contract is supplied and independently audited.
        completeness_contract_id = str(completeness_contract.get("contract_id") or "UNRESOLVED")
        completeness_contract_version = str(completeness_contract.get("version") or "UNRESOLVED")
        completeness_status = "CONTRACT_UNRESOLVED"
        publishability = "BLOCKED_COMPLETENESS_CONTRACT_UNRESOLVED"
    material = {
        "contract_id": CONTRACT_ID, "contract_version": CONTRACT_VERSION,
        "publication_id": publication_id, "publication_revision": publication_revision,
        "trade_date": target, "source_manifest_sha256": source_manifest_sha256,
        "producer_contract_id": producer_contract_id, "producer_sha256": producer_sha256,
        "producer_receipt_sha256": receipt_digest, "rows": normalized,
    }
    result_sha = _sha(material)
    result_identity = "v4-core-r6-" + _sha({
        "publication_id": publication_id, "publication_revision": publication_revision,
        "trade_date": target, "source_manifest_sha256": source_manifest_sha256,
        "producer_contract_id": producer_contract_id, "producer_sha256": producer_sha256,
        "result_sha256": result_sha,
    })
    return {
        "contract_id": CONTRACT_ID, "contract_version": CONTRACT_VERSION,
        "publication_id": publication_id, "publication_revision": publication_revision,
        "trade_date": target, "result_identity": result_identity,
        "result_contract_id": CONTRACT_ID, "producer_contract_id": producer_contract_id,
        "producer_sha256": producer_sha256, "source_manifest_sha256": source_manifest_sha256,
        "result_sha256": result_sha, "row_count": len(normalized),
        "missing_price_rows": missing_price, "completeness_contract_id": completeness_contract_id,
        "completeness_contract_version": completeness_contract_version,
        "completeness_status": completeness_status, "publishability_status": publishability,
        "quality_status": "CORE_RESULT_ROWS_VERIFIED_CANDIDATE",
        "rows": normalized, "write_mode": "PLAN_ONLY_NO_DATABASE_IO",
    }


def read_daily_core_result(pg: Any, *, publication_id: str, publication_revision: int,
                           trade_date: str, source_manifest_sha256: str) -> dict[str, Any]:
    """Independently read back and hash a publication-bound core result in PG."""
    target = _date(trade_date)
    snapshot = pg.execute(
        """SELECT trade_date,result_identity,result_contract_id,producer_contract_id,
                  producer_sha256,producer_receipt_sha256,source_manifest_sha256,result_sha256,row_count,
                  missing_price_rows,completeness_contract_id,completeness_contract_version,
                  completeness_status,quality_status
             FROM v4.daily_core_result_snapshots
            WHERE publication_id=%s AND publication_revision=%s""",
        (publication_id, publication_revision),
    ).fetchone()
    if snapshot is None:
        raise CoreResultError("CORE_RESULT_PG_ROW_MISSING")
    if (snapshot[0].isoformat() != target or str(snapshot[6]).strip() != source_manifest_sha256
            or snapshot[2] != CONTRACT_ID):
        raise CoreResultError("CORE_RESULT_PG_PUBLICATION_IDENTITY_MISMATCH")
    rows = pg.execute(
        """SELECT trade_date,security_id,security_type,trade_status,open,high,low,close,
                  volume,amount,turnover_rate,turnover_status,ma5,ma20,ma60,history_status,price_basis,source_revision_id,
                  profile_payload,quality_status,row_sha256
             FROM v4.daily_core_result_rows
            WHERE publication_id=%s AND publication_revision=%s
            ORDER BY security_id COLLATE "C""",
        (publication_id, publication_revision),
    ).fetchall()
    columns = ("trade_date", "security_id", "security_type", "trade_status", *_PRICE_FIELDS,
               "turnover_status", *_PROFILE_FIELDS, "history_status", "price_basis", "source_revision_id",
               "profile_payload", "quality_status", "row_sha256")
    material_rows = []
    missing_price = 0
    for values in rows:
        item = dict(zip(columns, values))
        if item["trade_date"].isoformat() != target or item["price_basis"] != "TDX_GBBQ_UNCHANGED":
            raise CoreResultError("CORE_RESULT_PG_ROW_IDENTITY_MISMATCH")
        row_sha = item.pop("row_sha256")
        # Date and scalar conversions are canonicalized to match the producer plan.
        item["trade_date"] = item["trade_date"].isoformat()
        if _sha(item) != str(row_sha).strip():
            raise CoreResultError("CORE_RESULT_PG_ROW_DIGEST_MISMATCH")
        if item["close"] is None:
            missing_price += 1
        material_rows.append({**item, "row_sha256": str(row_sha).strip()})
    if len(rows) != int(snapshot[8]) or missing_price != int(snapshot[9]):
        raise CoreResultError("CORE_RESULT_PG_ROWSET_COUNT_MISMATCH")
    material = {
        "contract_id": CONTRACT_ID, "contract_version": CONTRACT_VERSION,
        "publication_id": publication_id, "publication_revision": publication_revision,
        "trade_date": target, "source_manifest_sha256": source_manifest_sha256,
        "producer_contract_id": snapshot[3], "producer_sha256": str(snapshot[4]).strip(),
        "producer_receipt_sha256": str(snapshot[5]).strip(), "rows": material_rows,
    }
    result_sha = _sha(material)
    if result_sha != str(snapshot[7]).strip():
        raise CoreResultError("CORE_RESULT_PG_AGGREGATE_DIGEST_MISMATCH")
    expected_identity = "v4-core-r6-" + _sha({
        "publication_id": publication_id, "publication_revision": publication_revision,
        "trade_date": target, "source_manifest_sha256": source_manifest_sha256,
        "producer_contract_id": snapshot[3], "producer_sha256": str(snapshot[4]).strip(),
        "result_sha256": result_sha,
    })
    if expected_identity != snapshot[1]:
        raise CoreResultError("CORE_RESULT_PG_RESULT_IDENTITY_MISMATCH")
    return {
        "publication_id": publication_id, "publication_revision": publication_revision,
        "trade_date": target, "result_identity": snapshot[1], "result_sha256": result_sha,
        "row_count": len(rows), "missing_price_rows": missing_price,
        "completeness_status": snapshot[12], "quality_status": snapshot[13],
        "publishable": snapshot[12] == "PASS",
    }
