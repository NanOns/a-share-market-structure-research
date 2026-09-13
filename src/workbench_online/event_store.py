"""Transactional close-event writer for the V3 online event tables."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import duckdb

from .event_batch import EVENT_BATCH_CONTRACT_VERSION, EventBatchReadResult


EVENT_STORAGE_CONTRACT_VERSION = "v3-online-event-storage-v1.0"
CLOSE_EVENT_STATUS = "CLOSE_DEGRADED"


class EventStoreError(ValueError):
    """Raised when a close-event batch is not safe to archive."""


def _db_timestamp(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _trade_date(value: str) -> str:
    if not isinstance(value, str) or len(value) != 8 or not value.isdigit():
        raise EventStoreError("INVALID_TRADE_DATE")
    return f"{value[:4]}-{value[4:6]}-{value[6:]}"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _logical_hash(result: EventBatchReadResult) -> str:
    material = {
        "contract_version": result.contract_version,
        "source_id": result.source_id,
        "dataset": result.dataset,
        "trade_date": result.trade_date,
        "batch_id": result.batch_id,
        "coverage": dict(result.coverage),
        "rows": [row.to_record() for row in result.rows],
        "header": result.header.to_record() if result.header else None,
    }
    return hashlib.sha256(_json(material).encode("utf-8")).hexdigest()


def _bundle_id(result: EventBatchReadResult) -> str:
    material = f"{result.source_id}|{result.dataset}|{result.trade_date}|{result.batch_id}"
    return "v3bundle-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def _validate_archivable(result: EventBatchReadResult) -> None:
    if result.status not in {"AVAILABLE", "DEGRADED"}:
        raise EventStoreError("CLOSE_BATCH_STATUS_NOT_ARCHIVABLE")
    if not result.batch_id or result.header is None:
        raise EventStoreError("CLOSE_BATCH_ID_OR_HEADER_MISSING")
    if result.coverage.get("complete_pagination") is not True:
        raise EventStoreError("CLOSE_BATCH_COVERAGE_INCOMPLETE")
    if result.failure_codes:
        raise EventStoreError("CLOSE_BATCH_HAS_FAILURES")
    if result.conflict_count:
        raise EventStoreError("CLOSE_BATCH_HAS_DUPLICATE_CONFLICT")
    if result.header.batch_id != result.batch_id:
        raise EventStoreError("CLOSE_HEADER_BATCH_MISMATCH")
    for row in result.rows:
        if row.batch_id != result.batch_id:
            raise EventStoreError("CLOSE_ROW_BATCH_MISMATCH")
        if ":" not in row.source_code:
            raise EventStoreError("SOURCE_CODE_NAMESPACE_MISSING")


def _existing_batch_state(connection: duckdb.DuckDBPyConnection, result: EventBatchReadResult, logical_hash: str, bundle_id: str) -> str | None:
    row = connection.execute(
        "SELECT dataset, trade_date, logical_hash, adapter_version FROM online_batches WHERE batch_id=?",
        [result.batch_id],
    ).fetchone()
    if row is None:
        return None
    expected_date = _trade_date(result.trade_date)
    if tuple(str(value) if value is not None else None for value in row) != (
        result.dataset,
        expected_date,
        logical_hash,
        result.adapter_version,
    ):
        raise EventStoreError("CLOSE_BATCH_ID_CONFLICT")
    header_count = connection.execute("SELECT count(*) FROM online_event_header WHERE batch_id=?", [result.batch_id]).fetchone()[0]
    row_count = connection.execute("SELECT count(*) FROM online_pool_entries WHERE batch_id=?", [result.batch_id]).fetchone()[0]
    bundle_count = connection.execute(
        "SELECT count(*) FROM online_event_bundles WHERE bundle_id=?", [bundle_id]
    ).fetchone()[0]
    if header_count != 1 or row_count != len(result.rows) or bundle_count != 1:
        raise EventStoreError("CLOSE_BATCH_EXISTING_PARTIAL_WRITE")
    return "ALREADY_STORED"


def _ensure_source_registered(connection: duckdb.DuckDBPyConnection, source_id: str) -> None:
    if connection.execute("SELECT count(*) FROM data_sources WHERE source_id=?", [source_id]).fetchone()[0] != 1:
        raise EventStoreError("SOURCE_NOT_REGISTERED")


def store_close_event_batch(
    connection: duckdb.DuckDBPyConnection,
    result: EventBatchReadResult,
    *,
    fetch_id: str,
    requested_at: datetime | str | None = None,
    http_status: int | None = 200,
) -> dict[str, Any]:
    """Persist one complete close-event batch atomically, without raw payloads."""
    _validate_archivable(result)
    if not isinstance(fetch_id, str) or not fetch_id.strip():
        raise EventStoreError("FETCH_ID_REQUIRED")
    _trade_date(result.trade_date)
    bundle_id = _bundle_id(result)
    observed_at = _db_timestamp(result.header.observed_at)
    requested = _db_timestamp(requested_at) or observed_at
    received = observed_at
    source_as_of = _db_timestamp(result.header.source_as_of)

    try:
        connection.execute("BEGIN TRANSACTION")
        _ensure_source_registered(connection, result.source_id)
        logical_hash = _logical_hash(result)
        existing = _existing_batch_state(connection, result, logical_hash, bundle_id)
        if existing:
            connection.execute("COMMIT")
            return {
                "status": existing,
                "contract_version": EVENT_STORAGE_CONTRACT_VERSION,
                "batch_id": result.batch_id,
                "bundle_id": bundle_id,
                "inserted": False,
                "row_count": len(result.rows),
                "raw_payload_persisted": False,
            }

        existing_fetch = connection.execute(
            "SELECT source_id, dataset, adapter_version FROM online_fetch_runs WHERE fetch_id=?", [fetch_id]
        ).fetchone()
        if existing_fetch is not None and tuple(existing_fetch) != (result.source_id, result.dataset, result.adapter_version):
            raise EventStoreError("FETCH_ID_CONFLICT")
        if existing_fetch is None:
            connection.execute(
                "INSERT INTO online_fetch_runs (fetch_id,source_id,dataset,requested_at,received_at,status,error_code,http_status,raw_hash,adapter_version) VALUES (?,?,?,?,?,?,?,?,?,?)",
                [fetch_id, result.source_id, result.dataset, requested, received, CLOSE_EVENT_STATUS, None, http_status, None, result.adapter_version],
            )
        connection.execute(
            "INSERT INTO online_batches (batch_id,fetch_id,dataset,trade_date,source_as_of,observed_at,first_seen_at,status,row_count,logical_hash,adapter_version) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [result.batch_id, fetch_id, result.dataset, _trade_date(result.trade_date), source_as_of, received, received, CLOSE_EVENT_STATUS, len(result.rows), logical_hash, result.adapter_version],
        )
        header = result.header
        connection.execute(
            "INSERT INTO online_event_header (batch_id,counts,rates,scope,source_notice) VALUES (?,?,?,?,?)",
            [result.batch_id, _json(header.counts), _json(header.rates), _json(header.scope), header.source_notice],
        )
        for row in result.rows:
            connection.execute(
                "INSERT INTO online_pool_entries (batch_id,pool_type,source_code,security_id,event_state,consecutive_limit_days,m_days,n_boards,first_limit_time,last_limit_time,last_break_time,price,amount,seal_amount,ret1,turnover,float_market_cap,open_count,source_reason,source_fields,quality_codes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [
                    result.batch_id,
                    row.pool_type,
                    row.source_code,
                    row.security_id,
                    row.event_state,
                    row.consecutive_limit_days,
                    row.m_days,
                    row.n_boards,
                    _db_timestamp(row.first_limit_time),
                    _db_timestamp(row.last_limit_time),
                    _db_timestamp(row.last_break_time),
                    row.price,
                    row.amount,
                    row.seal_amount,
                    row.ret1,
                    row.turnover,
                    row.float_market_cap,
                    row.open_count,
                    row.source_reason,
                    _json(row.source_fields),
                    _json(list(row.quality_codes)),
                ],
            )
        connection.execute(
            "INSERT INTO online_event_bundles (bundle_id,trade_date,source_batch_bindings,source_statuses,observed_at,coverage) VALUES (?,?,?,?,?,?)",
            [bundle_id, _trade_date(result.trade_date), _json({result.source_id: result.batch_id}), _json({result.source_id: result.status}), received, _json(result.coverage)],
        )
        connection.execute("COMMIT")
    except EventStoreError:
        try:
            connection.execute("ROLLBACK")
        except Exception:
            pass
        raise
    except Exception as exc:
        try:
            connection.execute("ROLLBACK")
        except Exception:
            pass
        raise EventStoreError(f"CLOSE_BATCH_WRITE_FAILED:{type(exc).__name__}:{exc}") from exc
    return {
        "status": "STORED",
        "contract_version": EVENT_STORAGE_CONTRACT_VERSION,
        "batch_id": result.batch_id,
        "bundle_id": bundle_id,
        "inserted": True,
        "row_count": len(result.rows),
        "raw_payload_persisted": False,
        "source_status": result.status,
    }
