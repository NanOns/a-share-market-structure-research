"""M8A-02 close-based new-high states."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from .immutable import immutable_slice_state
from workbench_service.result_objects import result_value_hash


CONTRACT_VERSION = "TECHNICAL_HISTORY_V2_1_PREVIEW"
PRICE_BASIS = "TDX_NATIVE_QFQ"
WINDOWS = (20, 30, 60, 100)
HIGH_RESULT_SCHEMA_VERSION = "high-result-rows-v1"
HIGH_RESULT_SEMANTIC_CONTRACT = "HIGH_RESULT_V3"
HIGH_RESULT_PRIMARY_KEY = ("security_id", "trade_date", "window")
HIGH_RESULT_COLUMNS = (
    "security_id", "trade_date", "window", "contract_id", "price_basis",
    "prior_max_close", "new_high", "at_prior_high", "streak",
    "is_left_censored", "dist_prior_high", "valid_n", "quality_codes", "basis_json",
)


def _finite(value: Any) -> bool:
    try:
        return bool(pd.notna(value) and np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def calculate_high_daily(frame: pd.DataFrame, *, cutoff: Any | None = None) -> pd.DataFrame:
    """Calculate strict prior-window close highs without using the current bar."""
    required = {"security_id", "date", "adj_close"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError("HIGH_INPUT_COLUMNS_MISSING:" + ",".join(missing))
    work = frame.copy()
    work["date"] = pd.to_datetime(work["date"]).dt.date
    if cutoff is not None and (work["date"] > pd.Timestamp(cutoff).date()).any():
        raise ValueError("FUTURE_HIGH_INPUT")
    work = work.sort_values(["security_id", "date"], kind="mergesort").reset_index(drop=True)
    outputs: list[pd.DataFrame] = []
    for security_id, group in work.groupby("security_id", sort=False, dropna=False):
        group = group.copy().reset_index(drop=True)
        close = pd.to_numeric(group["adj_close"], errors="coerce")
        for width in WINDOWS:
            prior = close.shift(1).rolling(width, min_periods=width).max()
            valid_n = close.shift(1).rolling(width, min_periods=0).count().astype(int)
            complete = valid_n.eq(width) & close.notna() & prior.notna()
            new_high = (close > prior).where(complete)
            at_prior_high = (close == prior).where(complete)
            streak: list[int | None] = []
            for index, is_new in enumerate(new_high.tolist()):
                if is_new is not True:
                    streak.append(0 if is_new is False else None)
                    continue
                previous = streak[index - 1] if index else None
                previous_new = bool(new_high.iloc[index - 1]) if index else False
                streak.append(int(previous) + 1 if previous_new and previous is not None else 1)
            group[f"prior_max_close_{width}"] = prior
            group[f"new_high_{width}"] = new_high
            group[f"at_prior_high_{width}"] = at_prior_high
            group[f"high_streak_{width}"] = streak
            group[f"is_left_censored_{width}"] = ~complete & (valid_n < width)
            group[f"dist_prior_high_{width}"] = (close / prior - 1).where(complete & (prior > 0))
            group[f"high_valid_n_{width}"] = valid_n
        group["security_id"] = security_id
        outputs.append(group)
    result = pd.concat(outputs, ignore_index=True) if outputs else work.copy()
    result["high_contract_id"] = CONTRACT_VERSION
    result["high_price_basis"] = PRICE_BASIS
    return result.sort_values(["date", "security_id"], kind="mergesort").reset_index(drop=True)


def high_rows_for_storage(frame: pd.DataFrame, slice_id: str) -> list[tuple[Any, ...]]:
    rows = []
    for _, row in frame.iterrows():
        for width in WINDOWS:
            values = [row.get(f"prior_max_close_{width}"), row.get(f"dist_prior_high_{width}")]
            values = [None if not _finite(value) else float(value) for value in values]
            valid_n = int(row.get(f"high_valid_n_{width}") or 0)
            quality = [] if valid_n == width and _finite(row.get("adj_close")) else ["INSUFFICIENT_HISTORY"]
            rows.append((
                slice_id, row["security_id"], row["date"], width, CONTRACT_VERSION, PRICE_BASIS,
                values[0], None if pd.isna(row.get(f"new_high_{width}")) else bool(row[f"new_high_{width}"]),
                None if pd.isna(row.get(f"at_prior_high_{width}")) else bool(row[f"at_prior_high_{width}"]),
                None if pd.isna(row.get(f"high_streak_{width}")) else int(row[f"high_streak_{width}" ]),
                bool(row[f"is_left_censored_{width}"]), values[1], valid_n,
                json.dumps(quality), json.dumps({
                    "contract_id": CONTRACT_VERSION, "price_basis": PRICE_BASIS,
                    "comparison": "ADJ_CLOSE_T_GREATER_THAN_PRIOR_N_CLOSES",
                    "ties_are_not_new_high": True, "window": width,
                }, sort_keys=True),
            ))
    return rows


def insert_high_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    rows = high_rows_for_storage(frame, slice_id)
    existing = connection.execute('select * from stock_high_daily where slice_id=?', [slice_id]).fetchall()
    if immutable_slice_state(existing, rows, key_indexes=(1, 2, 3), conflict_code="HIGH_SLICE_IDENTITY_CONFLICT"):
        return len(rows)
    connection.executemany("insert into stock_high_daily values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


def _json_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _high_result_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    names = ("slice_id",) + HIGH_RESULT_COLUMNS
    records: list[dict[str, Any]] = []
    for values in high_rows_for_storage(frame, "__v3_result_object__"):
        record = dict(zip(names, values))
        record.pop("slice_id", None)
        record["trade_date"] = pd.Timestamp(record["trade_date"]).date()
        records.append(record)
    return records


def _high_value_semantics(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    return {
        "null_policy": "EXPLICIT_NULLS_PRESERVED",
        "json_policy": "SORTED_COMPACT_JSON",
        "business_key": list(HIGH_RESULT_PRIMARY_KEY),
        "contract_ids": sorted({str(row["contract_id"]) for row in rows}),
        "price_bases": sorted({str(row["price_basis"]) for row in rows}),
        "quality_field": "quality_codes",
        "basis_field": "basis_json",
        "windows": list(WINDOWS),
        "comparison": "ADJ_CLOSE_T_GREATER_THAN_PRIOR_N_CLOSES",
        "ties_are_not_new_high": True,
    }


def _high_hash(records: list[dict[str, Any]]) -> tuple[str, int, dict[str, Any]]:
    semantics = _high_value_semantics(records)
    value_hash, _, row_count = result_value_hash(
        domain="high",
        schema_version=HIGH_RESULT_SCHEMA_VERSION,
        semantic_contract=HIGH_RESULT_SEMANTIC_CONTRACT,
        columns=HIGH_RESULT_COLUMNS,
        primary_key=HIGH_RESULT_PRIMARY_KEY,
        rows=records,
        value_semantics=semantics,
    )
    return value_hash, row_count, semantics


def _high_records_from_db(connection: Any, result_object_id: str) -> list[dict[str, Any]]:
    columns = ",".join('"window"' if column == "window" else column for column in HIGH_RESULT_COLUMNS)
    rows = connection.execute(
        f'SELECT {columns} FROM high_result_rows WHERE result_object_id=? ORDER BY security_id, trade_date, "window"',
        [result_object_id],
    ).fetchall()
    return [dict(zip(HIGH_RESULT_COLUMNS, row)) for row in rows]


def _register_high_result_rows(
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
        raise ValueError(f"HIGH_SLICE_NOT_FOUND:{slice_id}")
    if metadata[0] != "high":
        raise ValueError("HIGH_SLICE_DOMAIN_MISMATCH")
    declared_row_count = int(metadata[6])
    if migration_source == "LEGACY_008_IMPORT":
        if declared_row_count == len(records):
            source_storage_multiplier = 1
        elif declared_row_count * len(WINDOWS) == len(records):
            source_storage_multiplier = len(WINDOWS)
        else:
            raise ValueError("HIGH_RESULT_ROW_COUNT_MISMATCH")
    else:
        if declared_row_count != len(records):
            raise ValueError("HIGH_RESULT_ROW_COUNT_MISMATCH")
        source_storage_multiplier = 1
    expected_physical_row_count = len(records)
    if expected_physical_row_count <= 0:
        raise ValueError("HIGH_RESULT_ROW_COUNT_MISMATCH")
    if len({(row["security_id"], row["trade_date"], row["window"]) for row in records}) != len(records):
        raise ValueError("HIGH_RESULT_PRIMARY_KEY_DUPLICATE")
    for record in records:
        record["quality_codes"] = _json_text(record["quality_codes"])
        record["basis_json"] = _json_text(record["basis_json"])
    value_hash, row_count, semantics = _high_hash(records)
    result_object_id = "result-obj-" + value_hash[:32]
    now = datetime.now(timezone.utc)
    existing_object = connection.execute(
        "SELECT domain, schema_version, semantic_contract, value_hash, row_count, storage_kind FROM analysis_result_objects WHERE result_object_id=?",
        [result_object_id],
    ).fetchone()
    expected_object = (
        "high", HIGH_RESULT_SCHEMA_VERSION,
        HIGH_RESULT_SEMANTIC_CONTRACT, value_hash, row_count, "DUCKDB",
    )
    if existing_object and tuple(existing_object) != expected_object:
        raise ValueError("HIGH_RESULT_OBJECT_IDENTITY_CONFLICT")
    connection.execute(
        "INSERT INTO analysis_result_objects VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(result_object_id) DO NOTHING",
        [result_object_id, *expected_object[0:3], value_hash, row_count, "DUCKDB", now],
    )
    stored_rows = _high_records_from_db(connection, result_object_id)
    if stored_rows:
        stored_hash, stored_count, stored_semantics = _high_hash(stored_rows)
        if stored_count != row_count or stored_hash != value_hash or stored_semantics != semantics:
            raise ValueError("HIGH_RESULT_VALUE_HASH_MISMATCH")
    else:
        columns = ["result_object_id", *HIGH_RESULT_COLUMNS]
        placeholders = ",".join("?" for _ in columns)
        connection.executemany(
            f"INSERT INTO high_result_rows VALUES ({placeholders})",
            [[result_object_id, *[record[column] for column in HIGH_RESULT_COLUMNS]] for record in records],
        )
    storage_payload = {
        "storage_object_id": result_object_id,
        "result_object_id": result_object_id,
        "kind": "HIGH_RESULT_ROWS",
        "storage_kind": "DUCKDB",
        "table": "high_result_rows",
        "domain": "high",
        "schema_version": HIGH_RESULT_SCHEMA_VERSION,
        "semantic_contract": HIGH_RESULT_SEMANTIC_CONTRACT,
        "value_hash": value_hash,
        "primary_key": list(HIGH_RESULT_PRIMARY_KEY),
        "columns": list(HIGH_RESULT_COLUMNS),
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
    if not connection.execute(
        "SELECT 1 FROM storage_objects WHERE storage_object_id=?", [result_object_id]
    ).fetchone():
        raise ValueError("HIGH_RESULT_STORAGE_OBJECT_MISSING")
    if metadata[9] not in (None, result_object_id):
        raise ValueError("HIGH_SLICE_STORAGE_OBJECT_CONFLICT")
    connection.execute(
        "UPDATE analysis_slices SET storage_object_id=? WHERE slice_id=? AND storage_object_id IS NULL",
        [result_object_id, slice_id],
    )
    basis = metadata[5] if isinstance(metadata[5], dict) else json.loads(metadata[5])
    evidence = {
        "contract_version": "v3-p03-02-high-migration-v1",
        "migration_source": migration_source,
        "source_table": "stock_high_daily",
        "source_slice_id": slice_id,
        "source_trade_date": str(metadata[1]),
        "source_contract_id": metadata[2],
        "source_input_hash": metadata[3],
        "source_dependency_hash": metadata[4],
        "source_basis": basis,
        "source_logical_hash": metadata[7],
        "source_row_count": int(metadata[6]),
        "source_storage_multiplier": source_storage_multiplier,
        "source_physical_row_count": expected_physical_row_count,
        "result_object_id": result_object_id,
        "result_value_hash": value_hash,
        "result_schema_version": HIGH_RESULT_SCHEMA_VERSION,
        "result_semantic_contract": HIGH_RESULT_SEMANTIC_CONTRACT,
        "result_primary_key": list(HIGH_RESULT_PRIMARY_KEY),
        "result_columns": list(HIGH_RESULT_COLUMNS),
        "result_value_semantics": semantics,
    }
    existing_binding = connection.execute(
        "SELECT result_object_id FROM analysis_slice_result_bindings WHERE slice_id=?",
        [slice_id],
    ).fetchone()
    if existing_binding:
        if existing_binding[0] != result_object_id:
            raise ValueError("HIGH_SLICE_RESULT_BINDING_CONFLICT")
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


def insert_high_result_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    """Write one high slice to the V3 result-object row store only."""
    records = _high_result_records(frame)
    _register_high_result_rows(
        connection, slice_id, records, migration_source="HIGH_WRITER_V3"
    )
    return len(records)


def migrate_high_slice(connection: Any, slice_id: str) -> dict[str, Any]:
    """Import one immutable legacy high slice into the V3 row store."""
    columns = ",".join('"window"' if column == "window" else column for column in HIGH_RESULT_COLUMNS)
    rows = connection.execute(
        f'SELECT {columns} FROM stock_high_daily WHERE slice_id=? ORDER BY security_id, trade_date, "window"',
        [slice_id],
    ).fetchall()
    records = [dict(zip(HIGH_RESULT_COLUMNS, row)) for row in rows]
    return _register_high_result_rows(
        connection, slice_id, records, migration_source="LEGACY_008_IMPORT"
    )
