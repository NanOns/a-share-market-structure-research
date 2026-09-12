"""M8A-02 cross-sectional RS/RPS calculations."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from .technical import CONTRACT_VERSION, PRICE_BASIS, WINDOWS, calculate_technical_daily
from .immutable import immutable_slice_state
from workbench_service.result_objects import result_value_hash


STRENGTH_RESULT_SCHEMA_VERSION = "strength-result-rows-v1"
STRENGTH_RESULT_SEMANTIC_CONTRACT = "STRENGTH_RESULT_V3"
STRENGTH_RESULT_PRIMARY_KEY = ("security_id", "trade_date")
STRENGTH_RESULT_COLUMNS = (
    "security_id", "trade_date", "contract_id", "price_basis",
    "ret5", "ret10", "ret20", "ret60", "rs5", "rs10", "rs20", "rs60",
    "rps5", "rps10", "rps20", "rps60", "rps_valid_universe_count5",
    "rps_valid_universe_count10", "rps_valid_universe_count20",
    "rps_valid_universe_count60", "quality_codes", "basis_json",
)


def average_rank_percentile(values: pd.Series) -> pd.Series:
    """Average-tie rank divided by N, as required by the public contract."""
    return values.rank(method="average", ascending=True, na_option="keep") / values.notna().sum()


def calculate_strength_daily(frame: pd.DataFrame, *, cutoff: Any | None = None, min_universe: int = 100) -> pd.DataFrame:
    """Add RS and RPS using only same-date eligible securities."""
    result = calculate_technical_daily(frame, cutoff=cutoff)
    for width in WINDOWS:
        ret = f"ret{width}"
        rs = f"rs{width}"
        rps = f"rps{width}"
        count_name = f"rps_valid_universe_count{width}"
        result[count_name] = 0
        result[rps] = np.nan
        result[rs] = np.nan
        for trade_date, indexes in result.groupby("date", sort=False).groups.items():
            subset = result.loc[list(indexes)]
            if "universe_status" in subset:
                eligible = subset["universe_status"].eq("IN_NORMAL_UNIVERSE")
            else:
                eligible = pd.Series(True, index=subset.index)
            eligible &= subset[ret].notna()
            valid = subset.loc[eligible, ret]
            count = int(valid.notna().sum())
            result.loc[list(indexes), count_name] = count
            if count < min_universe:
                continue
            median = float(valid.median())
            result.loc[valid.index, rs] = valid - median
            result.loc[valid.index, rps] = average_rank_percentile(valid)
    result["strength_contract_id"] = CONTRACT_VERSION
    result["strength_price_basis"] = PRICE_BASIS
    result["strength_quality_codes"] = result.apply(lambda row: [f"INSUFFICIENT_RPS_UNIVERSE_{width}" for width in WINDOWS if int(row[f"rps_valid_universe_count{width}"]) < min_universe], axis=1)
    result["strength_basis_json"] = result.apply(lambda row: {
        "contract_id": CONTRACT_VERSION, "price_basis": PRICE_BASIS,
        "rps": "AVERAGE_TIE_RANK_DIVIDED_BY_SAME_DATE_VALID_N",
        "rps_min_universe": min_universe, "rs": "RET_MINUS_SAME_DATE_VALID_MEDIAN",
    }, axis=1)
    return result


def strength_rows_for_storage(frame: pd.DataFrame, slice_id: str) -> list[tuple[Any, ...]]:
    rows = []
    factor_names = tuple(f"ret{n}" for n in WINDOWS) + tuple(f"rs{n}" for n in WINDOWS) + tuple(f"rps{n}" for n in WINDOWS)
    for _, row in frame.iterrows():
        values = [None if pd.isna(row.get(name)) else float(row[name]) for name in factor_names]
        counts = [int(row.get(f"rps_valid_universe_count{n}") or 0) for n in WINDOWS]
        rows.append(tuple(
            [slice_id, row["security_id"], row["date"], CONTRACT_VERSION, PRICE_BASIS]
            + values + counts
            + [json.dumps(row["strength_quality_codes"], ensure_ascii=False), json.dumps(row["strength_basis_json"], ensure_ascii=False, sort_keys=True)]
        ))
    return rows


def insert_strength_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    """Insert a legacy 008 strength row set for compatibility fixtures."""
    rows = strength_rows_for_storage(frame, slice_id)
    existing = connection.execute("select * from stock_strength_daily where slice_id=?", [slice_id]).fetchall()
    if immutable_slice_state(existing, rows, key_indexes=(1, 2), conflict_code="STRENGTH_SLICE_IDENTITY_CONFLICT"):
        return len(rows)
    connection.executemany("insert into stock_strength_daily values (?,?,?,?,? ,?,?,?,? ,?,?,?,? ,?,?,?,? ,?,?,?,? ,?,?)", rows)
    return len(rows)


def _json_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _strength_result_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    names = ("slice_id",) + STRENGTH_RESULT_COLUMNS
    records: list[dict[str, Any]] = []
    for values in strength_rows_for_storage(frame, "__v3_result_object__"):
        record = dict(zip(names, values))
        record.pop("slice_id", None)
        record["trade_date"] = pd.Timestamp(record["trade_date"]).date()
        records.append(record)
    return records


def _strength_value_semantics(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    return {
        "null_policy": "EXPLICIT_NULLS_PRESERVED",
        "json_policy": "SORTED_COMPACT_JSON",
        "business_key": list(STRENGTH_RESULT_PRIMARY_KEY),
        "contract_ids": sorted({str(row["contract_id"]) for row in rows}),
        "price_bases": sorted({str(row["price_basis"]) for row in rows}),
        "quality_field": "quality_codes",
        "basis_field": "basis_json",
        "rs_semantics": "RET_MINUS_SAME_DATE_VALID_MEDIAN",
        "rps_semantics": "AVERAGE_TIE_RANK_DIVIDED_BY_SAME_DATE_VALID_N",
        "rps_denominator_fields": [f"rps_valid_universe_count{width}" for width in WINDOWS],
    }


def _strength_hash(records: list[dict[str, Any]]) -> tuple[str, int, dict[str, Any]]:
    semantics = _strength_value_semantics(records)
    value_hash, _, row_count = result_value_hash(
        domain="strength",
        schema_version=STRENGTH_RESULT_SCHEMA_VERSION,
        semantic_contract=STRENGTH_RESULT_SEMANTIC_CONTRACT,
        columns=STRENGTH_RESULT_COLUMNS,
        primary_key=STRENGTH_RESULT_PRIMARY_KEY,
        rows=records,
        value_semantics=semantics,
    )
    return value_hash, row_count, semantics


def _strength_records_from_db(connection: Any, result_object_id: str) -> list[dict[str, Any]]:
    columns = ",".join(STRENGTH_RESULT_COLUMNS)
    rows = connection.execute(
        f"SELECT {columns} FROM strength_result_rows WHERE result_object_id=? ORDER BY security_id, trade_date",
        [result_object_id],
    ).fetchall()
    return [dict(zip(STRENGTH_RESULT_COLUMNS, row)) for row in rows]


def _register_strength_result_rows(
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
        raise ValueError(f"STRENGTH_SLICE_NOT_FOUND:{slice_id}")
    if metadata[0] != "strength":
        raise ValueError("STRENGTH_SLICE_DOMAIN_MISMATCH")
    if int(metadata[6]) != len(records):
        raise ValueError("STRENGTH_RESULT_ROW_COUNT_MISMATCH")
    if len({(row["security_id"], row["trade_date"]) for row in records}) != len(records):
        raise ValueError("STRENGTH_RESULT_PRIMARY_KEY_DUPLICATE")
    for record in records:
        record["quality_codes"] = _json_text(record["quality_codes"])
        record["basis_json"] = _json_text(record["basis_json"])
    value_hash, row_count, semantics = _strength_hash(records)
    result_object_id = "result-obj-" + value_hash[:32]
    now = datetime.now(timezone.utc)
    existing_object = connection.execute(
        "SELECT domain, schema_version, semantic_contract, value_hash, row_count, storage_kind FROM analysis_result_objects WHERE result_object_id=?",
        [result_object_id],
    ).fetchone()
    expected_object = (
        "strength", STRENGTH_RESULT_SCHEMA_VERSION,
        STRENGTH_RESULT_SEMANTIC_CONTRACT, value_hash, row_count, "DUCKDB",
    )
    if existing_object and tuple(existing_object) != expected_object:
        raise ValueError("STRENGTH_RESULT_OBJECT_IDENTITY_CONFLICT")
    connection.execute(
        "INSERT INTO analysis_result_objects VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(result_object_id) DO NOTHING",
        [result_object_id, *expected_object[0:3], value_hash, row_count, "DUCKDB", now],
    )
    stored_rows = _strength_records_from_db(connection, result_object_id)
    if stored_rows:
        stored_hash, stored_count, stored_semantics = _strength_hash(stored_rows)
        if stored_count != row_count or stored_hash != value_hash or stored_semantics != semantics:
            raise ValueError("STRENGTH_RESULT_VALUE_HASH_MISMATCH")
    else:
        columns = ["result_object_id", *STRENGTH_RESULT_COLUMNS]
        placeholders = ",".join("?" for _ in columns)
        connection.executemany(
            f"INSERT INTO strength_result_rows VALUES ({placeholders})",
            [[result_object_id, *[record[column] for column in STRENGTH_RESULT_COLUMNS]] for record in records],
        )
    storage_payload = {
        "storage_object_id": result_object_id,
        "result_object_id": result_object_id,
        "kind": "STRENGTH_RESULT_ROWS",
        "storage_kind": "DUCKDB",
        "table": "strength_result_rows",
        "domain": "strength",
        "schema_version": STRENGTH_RESULT_SCHEMA_VERSION,
        "semantic_contract": STRENGTH_RESULT_SEMANTIC_CONTRACT,
        "value_hash": value_hash,
        "primary_key": list(STRENGTH_RESULT_PRIMARY_KEY),
        "columns": list(STRENGTH_RESULT_COLUMNS),
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
        raise ValueError("STRENGTH_RESULT_STORAGE_OBJECT_MISSING")
    if metadata[9] not in (None, result_object_id):
        raise ValueError("STRENGTH_SLICE_STORAGE_OBJECT_CONFLICT")
    connection.execute(
        "UPDATE analysis_slices SET storage_object_id=? WHERE slice_id=? AND storage_object_id IS NULL",
        [result_object_id, slice_id],
    )
    basis = metadata[5] if isinstance(metadata[5], dict) else json.loads(metadata[5])
    evidence = {
        "contract_version": "v3-p03-02-strength-migration-v1",
        "migration_source": migration_source,
        "source_table": "stock_strength_daily",
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
        "result_schema_version": STRENGTH_RESULT_SCHEMA_VERSION,
        "result_semantic_contract": STRENGTH_RESULT_SEMANTIC_CONTRACT,
        "result_primary_key": list(STRENGTH_RESULT_PRIMARY_KEY),
        "result_columns": list(STRENGTH_RESULT_COLUMNS),
        "result_value_semantics": semantics,
    }
    existing_binding = connection.execute(
        "SELECT result_object_id FROM analysis_slice_result_bindings WHERE slice_id=?",
        [slice_id],
    ).fetchone()
    if existing_binding:
        if existing_binding[0] != result_object_id:
            raise ValueError("STRENGTH_SLICE_RESULT_BINDING_CONFLICT")
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


def insert_strength_result_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    """Write one strength slice to the V3 result-object row store only."""
    records = _strength_result_records(frame)
    _register_strength_result_rows(
        connection, slice_id, records, migration_source="STRENGTH_WRITER_V3"
    )
    return len(records)


def migrate_strength_slice(connection: Any, slice_id: str) -> dict[str, Any]:
    """Import one immutable legacy strength slice into the V3 row store."""
    columns = ",".join(STRENGTH_RESULT_COLUMNS)
    rows = connection.execute(
        f"SELECT {columns} FROM stock_strength_daily WHERE slice_id=? ORDER BY security_id, trade_date",
        [slice_id],
    ).fetchall()
    records = [dict(zip(STRENGTH_RESULT_COLUMNS, row)) for row in rows]
    return _register_strength_result_rows(
        connection, slice_id, records, migration_source="LEGACY_008_IMPORT"
    )
