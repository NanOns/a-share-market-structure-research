"""M9-02 point-in-time strong-member states and comparison sets."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from .immutable import immutable_slice_state
from workbench_service.result_objects import result_value_hash


CONTRACT_VERSION = "SECTOR_MEMBER_STATE_V1_2_EXCLUDE_DIAGNOSTIC"
HISTORY_BASIS = "RECONSTRUCTED"
MEMBER_STATE_RESULT_SCHEMA_VERSION = "member-state-result-rows-v1"
MEMBER_STATE_RESULT_SEMANTIC_CONTRACT = "MEMBER_STATE_RESULT_V3"
MEMBER_STATE_RESULT_PRIMARY_KEY = ("sector_id", "security_id", "trade_date")
MEMBER_STATE_RESULT_COLUMNS = (
    "sector_id", "security_id", "trade_date", "member_present", "member_rank",
    "rank_valid_count", "member_percentile", "strong_state", "strong_predicates",
    "structure_hit", "high_hit", "member_change_kind", "strength_change_kind",
    "previous_rank", "rank_delta", "queue_refs", "high_refs", "history_basis", "contract_id",
)


class MemberStateError(ValueError):
    pass


def _finite(value: Any) -> bool:
    try:
        return value is not None and bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def _tri(value: Any) -> bool | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip().upper()
        if value in {"TRUE", "1", "YES"}:
            return True
        if value in {"FALSE", "0", "NO"}:
            return False
        return None
    return bool(value)


def _normalise(frame: pd.DataFrame, required: tuple[str, ...], label: str) -> pd.DataFrame:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise MemberStateError(f"{label}_COLUMNS_MISSING:" + ",".join(missing))
    result = frame.copy()
    result["trade_date"] = pd.to_datetime(result["trade_date"], errors="raise").dt.date
    result["security_id"] = result["security_id"].astype(str)
    return result


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _structure_state(frame: pd.DataFrame) -> dict[tuple[str, Any], bool | None]:
    if frame is None or frame.empty:
        return {}
    source = _normalise(frame, ("security_id", "trade_date", "hit", "research_band"), "STRUCTURE")
    result = {}
    for key, group in source.groupby(["security_id", "trade_date"], sort=False):
        unknown = False
        qualified_hit = False
        for _, row in group.iterrows():
            band = row["research_band"]
            band = str(band).strip().upper() if band is not None and not pd.isna(band) else None
            hit = _tri(row["hit"])
            if band in {"CORE_RESEARCH", "SUPPORTED_RESEARCH"}:
                if hit is True:
                    qualified_hit = True
                    break
                if hit is None:
                    unknown = True
            elif band == "DIAGNOSTIC_ONLY":
                # A diagnostic row is a known non-qualification, even if its
                # underlying shadow queue happened to report hit=True.
                continue
            else:
                unknown = True
        result[key] = True if qualified_hit else None if unknown else False
    return result


def _high_state(frame: pd.DataFrame) -> dict[tuple[str, Any], bool | None]:
    if frame is None or frame.empty:
        return {}
    source = _normalise(frame, ("security_id", "trade_date"), "HIGH")
    columns = [column for column in ("new_high_20", "new_high_30", "new_high_60", "new_high_100") if column in source]
    if not columns:
        raise MemberStateError("HIGH_COLUMNS_MISSING:new_high_20/new_high_30/new_high_60/new_high_100")
    result = {}
    for key, group in source.groupby(["security_id", "trade_date"], sort=False):
        values = [_tri(value) for value in group.iloc[0][columns]]
        result[key] = True if True in values else None if None in values else False
    return result


def build_sector_member_state_daily(
    technical: pd.DataFrame,
    memberships: pd.DataFrame,
    *,
    structures: pd.DataFrame | None = None,
    highs: pd.DataFrame | None = None,
    cutoff: Any | None = None,
    history_basis: str = HISTORY_BASIS,
) -> pd.DataFrame:
    """Return one state row for every sector/member/date in the union timeline."""
    if history_basis != HISTORY_BASIS:
        raise MemberStateError("MEMBER_STATE_REQUIRES_RECONSTRUCTED_HISTORY")
    tech = _normalise(technical, ("security_id", "trade_date"), "TECHNICAL")
    members = _normalise(memberships, ("sector_id", "security_id", "trade_date"), "MEMBERSHIP")
    if cutoff is not None:
        cutoff_date = pd.Timestamp(cutoff).date()
        if (tech.trade_date > cutoff_date).any() or (members.trade_date > cutoff_date).any():
            raise MemberStateError("FUTURE_MEMBER_STATE_INPUT")
    if tech.duplicated(["security_id", "trade_date"]).any():
        raise MemberStateError("TECHNICAL_DUPLICATE_SECURITY_DATE")
    key = ["sector_id", "security_id", "trade_date"]
    if members.duplicated(key).any():
        raise MemberStateError("MEMBERSHIP_DUPLICATE_CONFLICT")
    joined = members.merge(tech, on=["security_id", "trade_date"], how="left", suffixes=("", "_technical"))
    def numeric(*names: str) -> pd.Series:
        for name in names:
            if name in joined:
                return pd.to_numeric(joined[name], errors="coerce")
        return pd.Series(np.nan, index=joined.index, dtype="float64")
    ret20 = numeric("ret20", "RET20")
    rps20 = numeric("rps20", "rps20_pct")
    # M9 defines the within-sector member rank by RET20.  RS20 is a separate
    # factor and must not silently replace or backfill that ranking input.
    rank_metric = ret20
    joined["_rank_metric"] = rank_metric
    joined["_rps20"] = rps20
    joined["_ret20"] = ret20
    joined["_rank"] = joined.groupby(["sector_id", "trade_date"])["_rank_metric"].rank(method="average", ascending=False, na_option="keep")
    joined["_rank_valid_count"] = joined.groupby(["sector_id", "trade_date"])["_rank_metric"].transform(lambda values: int(values.notna().sum()))
    joined["_member_percentile"] = (joined["_rank_valid_count"] - joined["_rank"] + 1) / joined["_rank_valid_count"].replace(0, np.nan)
    structure = _structure_state(structures)
    high = _high_state(highs)
    rows: list[dict[str, Any]] = []
    for _, row in joined.iterrows():
        pair = (row.security_id, row.trade_date)
        data_valid = _finite(row._ret20)
        market_rps = _tri(float(row._rps20) >= .80) if _finite(row._rps20) else None
        sector_percentile = _tri(float(row._member_percentile) >= .80) if _finite(row._member_percentile) else None
        structure_hit = structure.get(pair)
        high_hit = high.get(pair)
        structure_or_high = True if structure_hit is True or high_hit is True else None if structure_hit is None or high_hit is None else False
        predicates = {"data_valid": data_valid, "market_rps20_ge_080": market_rps, "sector_member_percentile_ge_080": sector_percentile, "qualified_structure": structure_hit, "structure_qualification_basis": "CORE_RESEARCH_OR_SUPPORTED_RESEARCH_ONLY", "structure_or_high": structure_or_high}
        known = [value for value in predicates.values() if value is not None]
        strong = True if len(known) == len(predicates) and all(known) else False if len(known) == len(predicates) else None
        rows.append({"sector_id": str(row.sector_id), "security_id": str(row.security_id), "trade_date": row.trade_date, "member_present": True, "member_rank": float(row._rank) if _finite(row._rank) else None, "rank_valid_count": int(row._rank_valid_count), "member_percentile": float(row._member_percentile) if _finite(row._member_percentile) else None, "strong_state": strong, "strong_predicates": _json(predicates), "structure_hit": structure_hit, "high_hit": high_hit, "member_change_kind": None, "strength_change_kind": None, "previous_rank": None, "rank_delta": None, "queue_refs": _json([]), "high_refs": _json([]), "history_basis": history_basis, "contract_id": CONTRACT_VERSION})
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    dates = sorted(result.trade_date.unique())
    by_key = result.set_index(["sector_id", "security_id", "trade_date"])
    state_rows = []
    for current_date in dates:
        previous_date = dates[dates.index(current_date) - 1] if dates.index(current_date) else None
        current_keys = set(result.loc[result.trade_date == current_date, ["sector_id", "security_id"]].itertuples(index=False, name=None))
        previous_keys = set(result.loc[result.trade_date == previous_date, ["sector_id", "security_id"]].itertuples(index=False, name=None)) if previous_date else set()
        for sector_id, security_id in sorted(current_keys | previous_keys):
            current = by_key.loc[(sector_id, security_id, current_date)] if (sector_id, security_id, current_date) in by_key.index else None
            previous = by_key.loc[(sector_id, security_id, previous_date)] if previous_date and (sector_id, security_id, previous_date) in by_key.index else None
            if current is None:
                current = {"sector_id": sector_id, "security_id": security_id, "trade_date": current_date, "member_present": False, "member_rank": None, "rank_valid_count": 0, "member_percentile": None, "strong_state": None, "strong_predicates": _json({}), "structure_hit": None, "high_hit": None, "previous_rank": previous["member_rank"], "rank_delta": None, "queue_refs": _json([]), "high_refs": _json([]), "history_basis": HISTORY_BASIS, "contract_id": CONTRACT_VERSION}
            else:
                current = current.to_dict()
                current["sector_id"] = sector_id
                current["security_id"] = security_id
                current["trade_date"] = current_date
                current["previous_rank"] = previous["member_rank"] if previous is not None else None
                current["rank_delta"] = (current["previous_rank"] - current["member_rank"]) if _finite(current["previous_rank"]) and _finite(current["member_rank"]) else None
            if previous_date is None:
                change = "UNKNOWN"
            elif previous is None:
                change = "ADDED" if current["member_present"] else "REMOVED"
            elif not current["member_present"]:
                change = "REMOVED"
            elif not previous["member_present"]:
                change = "ADDED"
            elif current["strong_state"] is None or previous["strong_state"] is None:
                change = "UNKNOWN"
            elif current["strong_state"] and previous["strong_state"]:
                change = "RETAINED"
            elif current["strong_state"] and not previous["strong_state"]:
                change = "ENTERED"
            elif not current["strong_state"] and previous["strong_state"]:
                change = "EXITED"
            else:
                change = "UNCHANGED"
            current["member_change_kind"] = change
            current["strength_change_kind"] = change if change in {"RETAINED", "ENTERED", "EXITED", "UNKNOWN", "UNCHANGED"} else None
            state_rows.append(current)
    return pd.DataFrame(state_rows).sort_values(["trade_date", "sector_id", "member_rank", "security_id"], na_position="last", kind="mergesort").reset_index(drop=True)


def build_membership_changes(states: pd.DataFrame) -> pd.DataFrame:
    """Extract only actual set additions/removals; first observations are excluded."""
    if states.empty:
        return pd.DataFrame(columns=["sector_id", "security_id", "trade_date", "change_type", "basis_version", "reason"])
    result = states[states.member_change_kind.isin(["ADDED", "REMOVED"])].copy()
    result["change_type"] = result["member_change_kind"]
    result["basis_version"] = CONTRACT_VERSION
    result["reason"] = result["change_type"].map({"ADDED": "CURRENT_MEMBER_NOT_IN_PREVIOUS_DATE", "REMOVED": "PREVIOUS_MEMBER_NOT_IN_CURRENT_DATE"})
    return result[["sector_id", "security_id", "trade_date", "change_type", "basis_version", "reason"]].reset_index(drop=True)


def rows_for_storage(frame: pd.DataFrame, slice_id: str) -> list[tuple[Any, ...]]:
    columns = ("sector_id", "security_id", "trade_date", "member_present", "member_rank", "rank_valid_count", "member_percentile", "strong_state", "strong_predicates", "structure_hit", "high_hit", "member_change_kind", "strength_change_kind", "previous_rank", "rank_delta", "queue_refs", "high_refs", "history_basis", "contract_id")
    return [tuple([slice_id] + [row.get(column) for column in columns]) for _, row in frame.iterrows()]


def change_rows_for_storage(frame: pd.DataFrame, slice_id: str) -> list[tuple[Any, ...]]:
    return [(slice_id, row.sector_id, row.security_id, row.trade_date, row.change_type, row.basis_version, row.reason) for row in frame.itertuples()]


def insert_member_state_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    """Insert an immutable member-state slice, rejecting identity conflicts."""
    rows = rows_for_storage(frame, slice_id)
    existing = connection.execute(
        "select * from sector_member_state_daily where slice_id=?", [slice_id]
    ).fetchall()
    if immutable_slice_state(existing, rows, key_indexes=(1, 2, 3), conflict_code="MEMBER_STATE_SLICE_IDENTITY_CONFLICT"):
        return len(rows)
    connection.executemany(
        "insert into sector_member_state_daily values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    return len(rows)


def _json_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _member_state_result_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    names = ("slice_id",) + MEMBER_STATE_RESULT_COLUMNS
    records: list[dict[str, Any]] = []
    for values in rows_for_storage(frame, "__v3_result_object__"):
        record = dict(zip(names, values))
        record.pop("slice_id", None)
        record["trade_date"] = pd.Timestamp(record["trade_date"]).date()
        records.append(record)
    return records


def _member_state_value_semantics(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    return {
        "null_policy": "EXPLICIT_NULLS_PRESERVED",
        "legacy_nan_policy": "HASH_AS_NULL_PRESERVE_LEGACY_STORAGE",
        "json_policy": "SORTED_COMPACT_JSON",
        "business_key": list(MEMBER_STATE_RESULT_PRIMARY_KEY),
        "contract_ids": sorted({str(row["contract_id"]) for row in rows}),
        "history_bases": sorted({str(row["history_basis"]) for row in rows}),
        "rank_semantics": "RET20_DESC_AVERAGE_TIE_WITHIN_SECTOR_DATE",
        "rank_valid_count_semantics": "SAME_SECTOR_DATE_NON_NULL_RET20_COUNT",
        "percentile_semantics": "(RANK_VALID_COUNT-RANK+1)/RANK_VALID_COUNT",
        "strong_state_semantics": "TRI_STATE_ALL_EXPLICIT_PREDICATES",
        "json_value_fields": ["strong_predicates", "queue_refs", "high_refs"],
        "change_fields": ["member_change_kind", "strength_change_kind"],
        "static_attribute_source": "sector_base_daily",
    }


def _member_state_hash(records: list[dict[str, Any]]) -> tuple[str, int, dict[str, Any]]:
    semantics = _member_state_value_semantics(records)
    canonical_records = []
    numeric_columns = ("member_rank", "rank_valid_count", "member_percentile", "previous_rank", "rank_delta")
    for record in records:
        canonical = dict(record)
        for column in numeric_columns:
            value = canonical.get(column)
            if isinstance(value, (float, np.floating)) and not np.isfinite(float(value)):
                canonical[column] = None
        canonical_records.append(canonical)
    value_hash, _, row_count = result_value_hash(
        domain="member_state",
        schema_version=MEMBER_STATE_RESULT_SCHEMA_VERSION,
        semantic_contract=MEMBER_STATE_RESULT_SEMANTIC_CONTRACT,
        columns=MEMBER_STATE_RESULT_COLUMNS,
        primary_key=MEMBER_STATE_RESULT_PRIMARY_KEY,
        rows=canonical_records,
        value_semantics=semantics,
    )
    return value_hash, row_count, semantics


def _member_state_records_from_db(connection: Any, result_object_id: str) -> list[dict[str, Any]]:
    columns = ",".join(MEMBER_STATE_RESULT_COLUMNS)
    rows = connection.execute(
        f"SELECT {columns} FROM member_state_result_rows WHERE result_object_id=? ORDER BY sector_id, security_id, trade_date",
        [result_object_id],
    ).fetchall()
    return [dict(zip(MEMBER_STATE_RESULT_COLUMNS, row)) for row in rows]


def _register_member_state_result_rows(
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
        raise ValueError(f"MEMBER_STATE_SLICE_NOT_FOUND:{slice_id}")
    if metadata[0] != "member_state":
        raise ValueError("MEMBER_STATE_SLICE_DOMAIN_MISMATCH")
    if int(metadata[6]) != len(records):
        raise ValueError("MEMBER_STATE_RESULT_ROW_COUNT_MISMATCH")
    if len({(row["sector_id"], row["security_id"], row["trade_date"]) for row in records}) != len(records):
        raise ValueError("MEMBER_STATE_RESULT_PRIMARY_KEY_DUPLICATE")
    for record in records:
        record["strong_predicates"] = _json_text(record["strong_predicates"])
        record["queue_refs"] = _json_text(record["queue_refs"])
        record["high_refs"] = _json_text(record["high_refs"])
    value_hash, row_count, semantics = _member_state_hash(records)
    result_object_id = "result-obj-" + value_hash[:32]
    now = datetime.now(timezone.utc)
    existing_object = connection.execute(
        "SELECT domain, schema_version, semantic_contract, value_hash, row_count, storage_kind FROM analysis_result_objects WHERE result_object_id=?",
        [result_object_id],
    ).fetchone()
    expected_object = (
        "member_state", MEMBER_STATE_RESULT_SCHEMA_VERSION,
        MEMBER_STATE_RESULT_SEMANTIC_CONTRACT, value_hash, row_count, "DUCKDB",
    )
    if existing_object and tuple(existing_object) != expected_object:
        raise ValueError("MEMBER_STATE_RESULT_OBJECT_IDENTITY_CONFLICT")
    connection.execute(
        "INSERT INTO analysis_result_objects VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(result_object_id) DO NOTHING",
        [result_object_id, *expected_object[0:3], value_hash, row_count, "DUCKDB", now],
    )
    stored_rows = _member_state_records_from_db(connection, result_object_id)
    if stored_rows:
        stored_hash, stored_count, stored_semantics = _member_state_hash(stored_rows)
        if stored_count != row_count or stored_hash != value_hash or stored_semantics != semantics:
            raise ValueError("MEMBER_STATE_RESULT_VALUE_HASH_MISMATCH")
    else:
        columns = ["result_object_id", *MEMBER_STATE_RESULT_COLUMNS]
        placeholders = ",".join("?" for _ in columns)
        connection.executemany(
            f"INSERT INTO member_state_result_rows VALUES ({placeholders})",
            [[result_object_id, *[record[column] for column in MEMBER_STATE_RESULT_COLUMNS]] for record in records],
        )
    storage_payload = {
        "storage_object_id": result_object_id,
        "result_object_id": result_object_id,
        "kind": "MEMBER_STATE_RESULT_ROWS",
        "storage_kind": "DUCKDB",
        "table": "member_state_result_rows",
        "domain": "member_state",
        "schema_version": MEMBER_STATE_RESULT_SCHEMA_VERSION,
        "semantic_contract": MEMBER_STATE_RESULT_SEMANTIC_CONTRACT,
        "value_hash": value_hash,
        "primary_key": list(MEMBER_STATE_RESULT_PRIMARY_KEY),
        "columns": list(MEMBER_STATE_RESULT_COLUMNS),
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
        raise ValueError("MEMBER_STATE_RESULT_STORAGE_OBJECT_MISSING")
    if metadata[9] not in (None, result_object_id):
        raise ValueError("MEMBER_STATE_SLICE_STORAGE_OBJECT_CONFLICT")
    connection.execute(
        "UPDATE analysis_slices SET storage_object_id=? WHERE slice_id=? AND storage_object_id IS NULL",
        [result_object_id, slice_id],
    )
    basis = metadata[5] if isinstance(metadata[5], dict) else json.loads(metadata[5])
    evidence = {
        "contract_version": "v3-p03-03-member-state-migration-v1",
        "migration_source": migration_source,
        "source_table": "sector_member_state_daily",
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
        "result_schema_version": MEMBER_STATE_RESULT_SCHEMA_VERSION,
        "result_semantic_contract": MEMBER_STATE_RESULT_SEMANTIC_CONTRACT,
        "result_primary_key": list(MEMBER_STATE_RESULT_PRIMARY_KEY),
        "result_columns": list(MEMBER_STATE_RESULT_COLUMNS),
        "result_value_semantics": semantics,
    }
    existing_binding = connection.execute(
        "SELECT result_object_id FROM analysis_slice_result_bindings WHERE slice_id=?",
        [slice_id],
    ).fetchone()
    if existing_binding:
        if existing_binding[0] != result_object_id:
            raise ValueError("MEMBER_STATE_SLICE_RESULT_BINDING_CONFLICT")
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


def insert_member_state_result_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    """Write one member-state slice to the V3 result-object row store only."""
    records = _member_state_result_records(frame)
    _register_member_state_result_rows(
        connection, slice_id, records, migration_source="MEMBER_STATE_WRITER_V3"
    )
    return len(records)


def migrate_member_state_slice(connection: Any, slice_id: str) -> dict[str, Any]:
    """Import one immutable legacy member-state slice into the V3 row store."""
    columns = ",".join(MEMBER_STATE_RESULT_COLUMNS)
    rows = connection.execute(
        f"SELECT {columns} FROM sector_member_state_daily WHERE slice_id=? ORDER BY sector_id, security_id, trade_date",
        [slice_id],
    ).fetchall()
    records = [dict(zip(MEMBER_STATE_RESULT_COLUMNS, row)) for row in rows]
    return _register_member_state_result_rows(
        connection, slice_id, records, migration_source="LEGACY_012_IMPORT"
    )


def insert_membership_change_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    """Insert an immutable membership-change slice, rejecting identity conflicts."""
    rows = change_rows_for_storage(frame, slice_id)
    existing = connection.execute(
        "select * from sector_membership_changes where slice_id=?", [slice_id]
    ).fetchall()
    if immutable_slice_state(existing, rows, key_indexes=(1, 2, 3, 4), conflict_code="MEMBERSHIP_CHANGE_SLICE_IDENTITY_CONFLICT"):
        return len(rows)
    if not rows:
        return 0
    connection.executemany(
        "insert into sector_membership_changes values (?,?,?,?,?,?,?)",
        rows,
    )
    return len(rows)
