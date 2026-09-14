"""M8A-01 technical history contract and deterministic factor producer."""

from __future__ import annotations

import json
import math
from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from .immutable import immutable_slice_state
from workbench_service.result_objects import result_value_hash


CONTRACT_VERSION = "TECHNICAL_HISTORY_V2_1_PREVIEW"
PRICE_BASIS = "TDX_NATIVE_QFQ"
WINDOWS = (5, 10, 20, 60)
TECHNICAL_RESULT_SCHEMA_VERSION = "technical-result-rows-v1"
TECHNICAL_RESULT_SEMANTIC_CONTRACT = "TECHNICAL_RESULT_V3"
TECHNICAL_RESULT_PRIMARY_KEY = ("security_id", "trade_date")
TECHNICAL_RESULT_COLUMNS = (
    "security_id", "trade_date", "contract_id", "price_basis",
    "raw_close", "adj_close", "quote_ret1", "raw_amount", "raw_volume",
    "ma5", "ma10", "ma20", "ma60", "ret5", "ret10", "ret20", "ret60",
    "rs5", "rs10", "rs20", "rs60", "amount_ma5", "amount_ma10", "amount_ma20",
    "amount_ratio20", "amount_vs_prior20", "volume_vs_prior20", "amount_class",
    "ma_alignment", "validity", "quality_codes", "basis_json",
)


def _finite(value: Any) -> bool:
    try:
        return bool(pd.notna(value) and np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def _window_complete(values: pd.Series, width: int) -> pd.Series:
    return values.rolling(width, min_periods=width).count().eq(width)


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    result = numerator / denominator
    return result.where(denominator > 0)


def amount_class(value: Any) -> str | None:
    if not _finite(value):
        return None
    value = float(value)
    if value < 1.5:
        return "NORMAL"
    if value < 2:
        return "INCREASED"
    if value < 3:
        return "NOTABLE"
    return "SIGNIFICANT"


def ma_alignment(values: Iterable[Any]) -> str | None:
    values = tuple(values)
    if any(not _finite(value) for value in values):
        return None
    ma5, ma10, ma20, ma60 = (float(value) for value in values)
    if ma5 > ma10 > ma20 > ma60:
        return "BULLISH"
    if ma5 < ma10 < ma20 < ma60:
        return "BEARISH"
    return "MIXED"


def _quality_for_row(row: pd.Series) -> list[str]:
    flags: set[str] = set()
    for name in ("ma5", "ma10", "ma20", "ma60", "ret5", "ret10", "ret20", "ret60"):
        if not _finite(row.get(name)):
            flags.add("INSUFFICIENT_HISTORY")
    if not _finite(row.get("raw_close")) or not _finite(row.get("adj_close")):
        flags.add("MISSING_CLOSE")
    quality = row.get("data_quality_flag")
    if quality not in (None, "", "OK"):
        flags.add(str(quality))
    if row.get("is_synthetic_fill") is True:
        flags.add("SYNTHETIC_INPUT_PRESENT")
    return sorted(flags)


def calculate_technical_daily(frame: pd.DataFrame, *, cutoff: Any | None = None) -> pd.DataFrame:
    """Calculate M8A-01 factors without skipping missing rows or future data."""
    required = {"security_id", "date", "adj_close", "raw_close", "raw_amount", "raw_volume"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError("TECHNICAL_INPUT_COLUMNS_MISSING:" + ",".join(missing))
    work = frame.copy()
    work["date"] = pd.to_datetime(work["date"]).dt.date
    if cutoff is not None:
        cutoff_date = pd.Timestamp(cutoff).date()
        if (work["date"] > cutoff_date).any():
            raise ValueError("FUTURE_TECHNICAL_INPUT")
    work = work.sort_values(["security_id", "date"], kind="mergesort").reset_index(drop=True)
    outputs: list[pd.DataFrame] = []
    for security_id, group in work.groupby("security_id", sort=False, dropna=False):
        group = group.copy().reset_index(drop=True)
        close = pd.to_numeric(group["adj_close"], errors="coerce")
        amount = pd.to_numeric(group["raw_amount"], errors="coerce")
        volume = pd.to_numeric(group["raw_volume"], errors="coerce")
        previous = pd.to_numeric(group["quote_prev_close"], errors="coerce") if "quote_prev_close" in group else pd.Series(np.nan, index=group.index)
        group["quote_ret1"] = pd.to_numeric(group["raw_close"], errors="coerce") / previous - 1
        for width in WINDOWS:
            group[f"ma{width}"] = close.rolling(width, min_periods=width).mean()
            group[f"ret{width}"] = close / close.shift(width) - 1
            group.loc[~_window_complete(close, width + 1), f"ret{width}"] = np.nan
            group[f"amount_ma{width}"] = amount.rolling(width, min_periods=width).mean()
        group["amount_ratio20"] = _safe_ratio(amount, group["amount_ma20"])
        group["amount_vs_prior20"] = _safe_ratio(amount, amount.shift(1).rolling(20, min_periods=20).mean())
        group["volume_vs_prior20"] = _safe_ratio(volume, volume.shift(1).rolling(20, min_periods=20).mean())
        group["amount_class"] = group["amount_vs_prior20"].map(amount_class)
        group["ma_alignment"] = group[[f"ma{n}" for n in WINDOWS]].apply(ma_alignment, axis=1)
        group["validity"] = "INSUFFICIENT"
        group.loc[group[[f"ma{n}" for n in WINDOWS]].notna().any(axis=1), "validity"] = "PARTIAL"
        group.loc[group[[f"ma{n}" for n in WINDOWS]].notna().all(axis=1), "validity"] = "VALID"
        group["security_id"] = security_id
        outputs.append(group)
    result = pd.concat(outputs, ignore_index=True) if outputs else work.copy()
    result["technical_contract_id"] = CONTRACT_VERSION
    result["price_basis"] = PRICE_BASIS
    result["quality_codes"] = result.apply(_quality_for_row, axis=1)
    result["basis_json"] = result.apply(lambda row: {
        "contract_id": CONTRACT_VERSION,
        "price_basis": PRICE_BASIS,
        "calendar_basis": "MASTER_TRADING_CALENDAR",
        "include_current_observation": True,
        "amount_ratio20": "CURRENT_DIVIDED_BY_CURRENT_INCLUSIVE_20_DAY_MEAN",
        "amount_vs_prior20": "CURRENT_DIVIDED_BY_PRIOR_EXCLUSIVE_20_DAY_MEAN",
        "volume_vs_prior20": "CURRENT_DIVIDED_BY_PRIOR_EXCLUSIVE_20_DAY_MEAN",
    }, axis=1)
    return result.sort_values(["date", "security_id"], kind="mergesort").reset_index(drop=True)


def rows_for_storage(frame: pd.DataFrame, slice_id: str) -> list[tuple[Any, ...]]:
    """Convert calculated rows into the immutable 008 table shape."""
    names = (
        "raw_close", "adj_close", "quote_ret1", "raw_amount", "raw_volume",
        "ma5", "ma10", "ma20", "ma60", "ret5", "ret10", "ret20", "ret60",
        "rs5", "rs10", "rs20", "rs60", "amount_ma5", "amount_ma10", "amount_ma20",
        "amount_ratio20", "amount_vs_prior20", "volume_vs_prior20",
    )
    rows = []
    for _, row in frame.iterrows():
        values = [None if not _finite(row.get(name)) else float(row[name]) for name in names]
        rows.append(tuple(
            [slice_id, row["security_id"], row["date"], CONTRACT_VERSION, PRICE_BASIS]
            + values
            + [row.get("amount_class"), row.get("ma_alignment"), row["validity"],
               json.dumps(row["quality_codes"], ensure_ascii=False),
               json.dumps(row["basis_json"], ensure_ascii=False, sort_keys=True)]
        ))
    return rows


def insert_technical_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    """Insert a legacy 008 row set for pre-V3 compatibility fixtures.

    Production preview builds use ``insert_technical_result_rows``.  Keeping
    this narrow adapter allows old M8 contract tests and unbound legacy slices
    to be read through the V3 compatibility view without writing both stores.
    """
    rows = rows_for_storage(frame, slice_id)
    existing = connection.execute(
        "select * from stock_technical_daily where slice_id=?", [slice_id]
    ).fetchall()
    if immutable_slice_state(existing, rows, key_indexes=(1, 2), conflict_code="TECHNICAL_SLICE_IDENTITY_CONFLICT"):
        return len(rows)
    connection.executemany(
        "insert into stock_technical_daily values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    return len(rows)


def _technical_result_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    legacy_names = ("slice_id",) + TECHNICAL_RESULT_COLUMNS
    records: list[dict[str, Any]] = []
    for values in rows_for_storage(frame, "__v3_result_object__"):
        record = dict(zip(legacy_names, values))
        record.pop("slice_id", None)
        record["trade_date"] = pd.Timestamp(record["trade_date"]).date()
        # Nullable categorical columns may arrive as pandas NaN even though
        # numeric factor columns are already normalised by rows_for_storage.
        for column, value in record.items():
            if isinstance(value, float) and not math.isfinite(value):
                record[column] = None
        records.append(record)
    return records


def _json_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _technical_value_semantics(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    return {
        "null_policy": "EXPLICIT_NULLS_PRESERVED",
        "json_policy": "SORTED_COMPACT_JSON",
        "business_key": list(TECHNICAL_RESULT_PRIMARY_KEY),
        "contract_ids": sorted({str(row["contract_id"]) for row in rows}),
        "price_bases": sorted({str(row["price_basis"]) for row in rows}),
        "quality_field": "quality_codes",
        "basis_field": "basis_json",
    }


def _technical_hash(records: list[dict[str, Any]]) -> tuple[str, int, dict[str, Any]]:
    semantics = _technical_value_semantics(records)
    value_hash, _, row_count = result_value_hash(
        domain="technical",
        schema_version=TECHNICAL_RESULT_SCHEMA_VERSION,
        semantic_contract=TECHNICAL_RESULT_SEMANTIC_CONTRACT,
        columns=TECHNICAL_RESULT_COLUMNS,
        primary_key=TECHNICAL_RESULT_PRIMARY_KEY,
        rows=records,
        value_semantics=semantics,
    )
    return value_hash, row_count, semantics


def _technical_records_from_db(connection: Any, result_object_id: str) -> list[dict[str, Any]]:
    columns = ",".join(TECHNICAL_RESULT_COLUMNS)
    rows = connection.execute(
        f"SELECT {columns} FROM technical_result_rows WHERE result_object_id=? ORDER BY security_id, trade_date",
        [result_object_id],
    ).fetchall()
    return [dict(zip(TECHNICAL_RESULT_COLUMNS, row)) for row in rows]


def _register_technical_result_rows(
    connection: Any,
    slice_id: str,
    records: list[dict[str, Any]],
    *,
    migration_source: str,
) -> dict[str, Any]:
    metadata = connection.execute(
        """
        SELECT domain, trade_date, contract_id, input_hash, dependency_hash,
               basis_json, row_count, logical_hash, storage_kind, storage_object_id
        FROM analysis_slices WHERE slice_id=?
        """,
        [slice_id],
    ).fetchone()
    if not metadata:
        raise ValueError(f"TECHNICAL_SLICE_NOT_FOUND:{slice_id}")
    if metadata[0] != "technical":
        raise ValueError("TECHNICAL_SLICE_DOMAIN_MISMATCH")
    if int(metadata[6]) != len(records):
        raise ValueError("TECHNICAL_RESULT_ROW_COUNT_MISMATCH")
    if len({(row["security_id"], row["trade_date"]) for row in records}) != len(records):
        raise ValueError("TECHNICAL_RESULT_PRIMARY_KEY_DUPLICATE")
    for record in records:
        record["quality_codes"] = _json_text(record["quality_codes"])
        record["basis_json"] = _json_text(record["basis_json"])
    value_hash, row_count, semantics = _technical_hash(records)
    result_object_id = "result-obj-" + value_hash[:32]
    now = datetime.now(timezone.utc)
    existing_object = connection.execute(
        "SELECT domain, schema_version, semantic_contract, value_hash, row_count, storage_kind FROM analysis_result_objects WHERE result_object_id=?",
        [result_object_id],
    ).fetchone()
    expected_object = (
        "technical", TECHNICAL_RESULT_SCHEMA_VERSION,
        TECHNICAL_RESULT_SEMANTIC_CONTRACT, value_hash, row_count, "DUCKDB",
    )
    if existing_object and tuple(existing_object) != expected_object:
        raise ValueError("TECHNICAL_RESULT_OBJECT_IDENTITY_CONFLICT")
    connection.execute(
        "INSERT INTO analysis_result_objects VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(result_object_id) DO NOTHING",
        [result_object_id, *expected_object[0:3], value_hash, row_count, "DUCKDB", now],
    )
    stored_rows = _technical_records_from_db(connection, result_object_id)
    if stored_rows:
        stored_hash, stored_count, stored_semantics = _technical_hash(stored_rows)
        if stored_count != row_count or stored_hash != value_hash or stored_semantics != semantics:
            raise ValueError("TECHNICAL_RESULT_VALUE_HASH_MISMATCH")
    else:
        columns = ["result_object_id", *TECHNICAL_RESULT_COLUMNS]
        placeholders = ",".join("?" for _ in columns)
        connection.executemany(
            f"INSERT INTO technical_result_rows VALUES ({placeholders})",
            [[result_object_id, *[record[column] for column in TECHNICAL_RESULT_COLUMNS]] for record in records],
        )
    storage_payload = {
        "storage_object_id": result_object_id,
        "result_object_id": result_object_id,
        "kind": "TECHNICAL_RESULT_ROWS",
        "storage_kind": "DUCKDB",
        "table": "technical_result_rows",
        "domain": "technical",
        "schema_version": TECHNICAL_RESULT_SCHEMA_VERSION,
        "semantic_contract": TECHNICAL_RESULT_SEMANTIC_CONTRACT,
        "value_hash": value_hash,
        "primary_key": list(TECHNICAL_RESULT_PRIMARY_KEY),
        "columns": list(TECHNICAL_RESULT_COLUMNS),
        "value_semantics": semantics,
        "row_count": row_count,
        "state": "ACTIVE",
        "referenced": True,
        "registered_at_utc": now.isoformat(),
    }
    connection.execute(
        "INSERT INTO storage_objects(storage_object_id,payload_json) VALUES (?, ?) ON CONFLICT(storage_object_id) DO NOTHING",
        [result_object_id, json.dumps(storage_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))],
    )
    stored_payload = connection.execute(
        "SELECT payload_json FROM storage_objects WHERE storage_object_id=?", [result_object_id]
    ).fetchone()
    if not stored_payload:
        raise ValueError("TECHNICAL_RESULT_STORAGE_OBJECT_MISSING")
    if metadata[9] not in (None, result_object_id):
        raise ValueError("TECHNICAL_SLICE_STORAGE_OBJECT_CONFLICT")
    connection.execute(
        "UPDATE analysis_slices SET storage_object_id=? WHERE slice_id=? AND storage_object_id IS NULL",
        [result_object_id, slice_id],
    )
    basis = metadata[5] if isinstance(metadata[5], dict) else json.loads(metadata[5])
    evidence = {
        "contract_version": "v3-p03-02-technical-migration-v1",
        "migration_source": migration_source,
        "source_table": "stock_technical_daily",
        "source_slice_id": slice_id,
        "source_trade_date": str(metadata[1]),
        "source_contract_id": metadata[2],
        "source_input_hash": metadata[3],
        "source_dependency_hash": metadata[4],
        "source_basis": basis,
        "source_logical_hash": metadata[7],
        "source_row_count": int(metadata[6]),
        "result_object_id": result_object_id,
        "result_value_hash": value_hash,
        "result_schema_version": TECHNICAL_RESULT_SCHEMA_VERSION,
        "result_semantic_contract": TECHNICAL_RESULT_SEMANTIC_CONTRACT,
        "result_primary_key": list(TECHNICAL_RESULT_PRIMARY_KEY),
        "result_columns": list(TECHNICAL_RESULT_COLUMNS),
        "result_value_semantics": semantics,
    }
    existing_binding = connection.execute(
        "SELECT result_object_id, identity_evidence FROM analysis_slice_result_bindings WHERE slice_id=?",
        [slice_id],
    ).fetchone()
    if existing_binding:
        if existing_binding[0] != result_object_id:
            raise ValueError("TECHNICAL_SLICE_RESULT_BINDING_CONFLICT")
    else:
        connection.execute(
            "INSERT INTO analysis_slice_result_bindings VALUES (?, ?, ?)",
            [slice_id, result_object_id, json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":"))],
        )
    return {
        "slice_id": slice_id,
        "result_object_id": result_object_id,
        "value_hash": value_hash,
        "row_count": row_count,
        "reused": bool(stored_rows),
    }


def insert_technical_result_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    """Write one technical slice to the V3 result-object row store only."""
    records = _technical_result_records(frame)
    _register_technical_result_rows(
        connection, slice_id, records, migration_source="TECHNICAL_WRITER_V3"
    )
    return len(records)


def migrate_technical_slice(connection: Any, slice_id: str) -> dict[str, Any]:
    """Import one immutable legacy technical slice into the V3 row store."""
    columns = ",".join(TECHNICAL_RESULT_COLUMNS)
    rows = connection.execute(
        f"SELECT {columns} FROM stock_technical_daily WHERE slice_id=? ORDER BY security_id, trade_date",
        [slice_id],
    ).fetchall()
    records = [dict(zip(TECHNICAL_RESULT_COLUMNS, row)) for row in rows]
    return _register_technical_result_rows(
        connection, slice_id, records, migration_source="LEGACY_008_IMPORT"
    )
