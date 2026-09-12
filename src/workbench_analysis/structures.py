"""Deterministic historical five-structure adapter (M8B-02)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from shadow_v2.breakout_prep import classify as classify_breakout
from shadow_v2.breakout_prep import range_status, vol_status
from shadow_v2.early_mover import classify as classify_early
from shadow_v2.early_mover import position_support, sector_context, trend_support
from shadow_v2.queue_ranking import SPECS, rank_queues
from shadow_v2.research_priority import MAPPINGS, queue_tier, research_band
from shadow_v2.sector_leader import classify as classify_leader
from shadow_v2.sector_leader import quality_class, semantic_category
from shadow_v2.strong_pullback import classify as classify_pullback
from shadow_v2.strong_pullback import depth_status, segment_status, volume_status
from shadow_v2.steady_trend import classify as classify_steady
from shadow_v2.steady_trend import continuity_class, pulse_class
from .immutable import immutable_slice_state
from workbench_service.result_objects import result_value_hash


CONTRACT_VERSION = "HISTORICAL_STRUCTURE_V2_1_RECONSTRUCTED"
STRUCTURE_BASIS = "RECONSTRUCTED"
QUEUE_NAMES = ("STEADY_QUEUE", "PULLBACK_QUEUE", "BREAKOUT_QUEUE", "LEADER_QUEUE", "EARLY_QUEUE")
QUEUE_KEYS = {"STEADY_QUEUE": "steady", "PULLBACK_QUEUE": "pullback", "BREAKOUT_QUEUE": "breakout", "LEADER_QUEUE": "leader", "EARLY_QUEUE": "early"}
STRUCTURE_RESULT_SCHEMA_VERSION = "structure-result-rows-v1"
STRUCTURE_RESULT_SEMANTIC_CONTRACT = "STRUCTURE_RESULT_V3"
STRUCTURE_RESULT_PRIMARY_KEY = ("security_id", "trade_date", "queue_name")
STRUCTURE_RESULT_COLUMNS = (
    "security_id", "trade_date", "queue_name", "hit", "tier", "source_class", "research_band",
    "queue_rank", "tier_rank", "transition", "structure_basis", "contract_id", "evidence", "quality_codes",
)


class StructureAdapterError(ValueError):
    pass


def _storage(value: Any) -> Any:
    if value is None:
        return None
    try:
        if bool(pd.isna(value)):
            return None
    except (TypeError, ValueError):
        pass
    return value.item() if hasattr(value, "item") else value


def _value(row: pd.Series, *names: str) -> Any:
    for name in names:
        value = row.get(name)
        if value is None:
            continue
        if isinstance(value, (list, tuple, dict, set)):
            return value
        missing = pd.isna(value)
        if not bool(missing):
            return value
    return None


def _bool(value: Any) -> bool | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized in {"TRUE", "1", "YES"}:
            return True
        if normalized in {"FALSE", "0", "NO"}:
            return False
        return None
    return bool(value)


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if pd.isna(value) if not isinstance(value, (dict, list, tuple, set)) else False:
        return None
    return value.item() if hasattr(value, "item") else value


def _v1(row: pd.Series, *names: str) -> bool | None:
    return _bool(_value(row, *names))


def _tri(class_name: str, hit: bool) -> bool | None:
    return None if "DATA_INSUFFICIENT" in class_name else bool(hit)


def _classify_row(row: pd.Series) -> dict[str, dict[str, Any]]:
    steady_v1 = _v1(row, "v1_steady_trend", "steady_trend", "steady_hit")
    continuity = _value(row, "continuity_class") or continuity_class(_value(row, "continuity_value"), _value(row, "continuity_valid_count"), _value(row, "continuity_valid_ratio"))
    pulse = _value(row, "pulse_class") or pulse_class(_value(row, "pulse_value"))
    steady_class, steady_hit = classify_steady(steady_v1, continuity, pulse) if steady_v1 is not None else ("DATA_INSUFFICIENT", False)

    pullback_v1 = _v1(row, "v1_strong_pullback", "strong_pullback", "pullback_hit")
    segment = _value(row, "pullback_segment") or segment_status(_value(row, "days_since_peak"))
    depth = _value(row, "pullback_depth") or depth_status(_value(row, "drawdown"))
    volume = _value(row, "pullback_volume") or volume_status(_value(row, "advance_mean"), _value(row, "pullback_mean"), _value(row, "pullback_volume_ratio"))
    pullback_class, pullback_hit, pullback_core = classify_pullback(pullback_v1, segment, depth, volume) if pullback_v1 is not None else ("DATA_INSUFFICIENT", False, False)

    breakout_v1 = _v1(row, "v1_breakout_prep", "breakout_prep", "breakout_hit")
    range_evidence = _value(row, "breakout_range") or range_status(_value(row, "range_recent"), _value(row, "range_prior"), _value(row, "range_ratio"))
    vol_evidence = _value(row, "breakout_volume") or vol_status(_value(row, "volume_recent"), _value(row, "volume_prior"), _value(row, "volume_ratio"))
    breakout_class, breakout_hit = classify_breakout(breakout_v1, range_evidence, vol_evidence) if breakout_v1 is not None else ("DATA_INSUFFICIENT", False)

    leader_v1 = _v1(row, "v1_sector_leader", "sector_leader", "leader_hit")
    semantic = _value(row, "sector_semantic") or semantic_category(str(_value(row, "sector_type") or "").upper(), _value(row, "style_class"))
    classes = _value(row, "leader_quality_classes")
    if isinstance(classes, str):
        try:
            classes = json.loads(classes)
        except json.JSONDecodeError:
            classes = [item for item in classes.split("|") if item]
    if not isinstance(classes, (list, tuple)):
        classes = [
            quality_class(_value(row, "sector_rs20_support"), _value(row, "sector_rs20_valid_count"), _value(row, "sector_rs20_valid_ratio")),
            quality_class(_value(row, "sector_breadth_support"), _value(row, "sector_breadth_valid_count"), _value(row, "sector_breadth_valid_ratio")),
        ]
    leader_class, leader_hit = classify_leader(leader_v1, semantic, classes) if leader_v1 is not None else ("DATA_INSUFFICIENT", False)

    early_v1 = _v1(row, "v1_early_mover", "early_mover", "early_hit")
    context = _value(row, "early_sector_context") or sector_context(bool(_value(row, "has_economic_sector")), bool(_value(row, "economic_sector_stabilizing")), bool(_value(row, "price_style_only")), bool(_value(row, "unknown_sector_only")))
    trend = _value(row, "early_trend_class") or trend_support(_value(row, "trend_support_value"))
    early_continuity = _value(row, "early_continuity_class") or continuity
    early_pulse = _value(row, "early_pulse_class") or pulse
    position = _value(row, "early_position_class") or position_support(_value(row, "position_support_value"))
    early_class, early_hit = classify_early(early_v1, context, trend, early_continuity, early_pulse, position) if early_v1 is not None else ("DATA_INSUFFICIENT", False)

    return {
        "STEADY_QUEUE": {"source_class": steady_class, "hit": _tri(steady_class, steady_hit), "evidence": {"v1": steady_v1, "continuity": continuity, "pulse": pulse}},
        "PULLBACK_QUEUE": {"source_class": pullback_class, "hit": _tri(pullback_class, pullback_hit), "evidence": {"v1": pullback_v1, "segment": segment, "depth": depth, "volume": volume, "core": pullback_core}},
        "BREAKOUT_QUEUE": {"source_class": breakout_class, "hit": _tri(breakout_class, breakout_hit), "evidence": {"v1": breakout_v1, "range": range_evidence, "volume": vol_evidence}},
        "LEADER_QUEUE": {"source_class": leader_class, "hit": _tri(leader_class, leader_hit), "evidence": {"v1": leader_v1, "semantic": semantic, "quality_classes": list(classes)}},
        "EARLY_QUEUE": {"source_class": early_class, "hit": _tri(early_class, early_hit), "evidence": {"v1": early_v1, "context": context, "trend": trend, "continuity": early_continuity, "pulse": early_pulse, "position": position}},
    }


def _ranking_input(row: pd.Series, key: str) -> dict[str, Any]:
    aliases = {
        "up_day_ratio20": ("up_day_ratio20",), "trend_r2_20": ("trend_r2_20", "TREND_R2_20"), "trend_r2_60": ("trend_r2_60", "TREND_R2_60"), "mdd20": ("mdd20", "MDD20"), "rs20": ("rs20", "RS20"),
        "v2_pullback_volume_confirmed": ("v2_pullback_volume_confirmed",), "pullback_amount_ratio": ("pullback_amount_ratio",), "RS60": ("RS60", "rs60"), "DIST_HIGH20": ("DIST_HIGH20", "dist_high20"),
        "range_contraction_ratio": ("range_contraction_ratio",), "realized_vol_contraction_ratio": ("realized_vol_contraction_ratio",), "POS60": ("POS60", "pos60"),
        "quality_dimension_strong_support_count": ("quality_dimension_strong_support_count",), "member_rs20_pct": ("member_rs20_pct",), "member_trend_r2_20_pct": ("member_trend_r2_20_pct",), "member_mdd20_quality_pct": ("member_mdd20_quality_pct",), "sector_rs20_pct": ("sector_rs20_pct",),
    }
    return {field: _value(row, *aliases.get(field, (field,))) for field, _ in SPECS[key]}


def _rank_date_rows(rows: list[dict[str, Any]], source: pd.DataFrame) -> list[dict[str, Any]]:
    if not rows:
        return rows
    board = pd.DataFrame(rows)
    board = board[["security_id"] + [f"{key}_queue_tier" for key in QUEUE_KEYS.values()]].drop_duplicates("security_id")
    details = {key: pd.DataFrame([{"security_id": row["security_id"], **_ranking_input(source.loc[row["_source_index"]], key)} for row in rows if row["queue_name"] == f"{key.upper()}_QUEUE"]).drop_duplicates("security_id") for key in QUEUE_KEYS.values()}
    ranks = rank_queues(board, details)
    for queue, key in QUEUE_KEYS.items():
        rank_map = ranks.set_index("security_id")[f"{key}_queue_rank"].to_dict()
        tier_map = ranks.set_index("security_id")[f"{key}_tier_rank"].to_dict()
        for row in rows:
            if row["queue_name"] == queue:
                row["queue_rank"] = rank_map.get(row["security_id"])
                row["tier_rank"] = tier_map.get(row["security_id"])
    return rows


def build_historical_structure_rows(frame: pd.DataFrame, *, cutoff: Any | None = None) -> pd.DataFrame:
    """Return one immutable-style row per security/date/queue."""
    required = {"security_id", "trade_date"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise StructureAdapterError("STRUCTURE_INPUT_COLUMNS_MISSING:" + ",".join(missing))
    source = frame.copy()
    source["trade_date"] = pd.to_datetime(source["trade_date"], errors="raise").dt.date
    if cutoff is not None and (source["trade_date"] > pd.Timestamp(cutoff).date()).any():
        raise StructureAdapterError("FUTURE_STRUCTURE_INPUT")
    if source[["security_id", "trade_date"]].duplicated().any():
        raise StructureAdapterError("STRUCTURE_DUPLICATE_SECURITY_DATE")
    output: list[dict[str, Any]] = []
    for index, row in source.sort_values(["trade_date", "security_id"], kind="mergesort").iterrows():
        classified = _classify_row(row)
        tiers = []
        for queue in QUEUE_NAMES:
            item = classified[queue]
            key = QUEUE_KEYS[queue]
            tier = queue_tier(queue, item["source_class"]) if item["hit"] is True else None
            tiers.append(tier)
            output.append({"_source_index": index, "trade_date": row["trade_date"], "security_id": str(row["security_id"]), "queue_name": queue, "hit": item["hit"], "tier": tier, "source_class": item["source_class"], "research_band": None, "queue_rank": None, "tier_rank": None, "transition": None, "structure_basis": STRUCTURE_BASIS, "contract_id": CONTRACT_VERSION, "evidence": item["evidence"], "quality_codes": [] if item["hit"] is not None else ["DATA_INSUFFICIENT"], f"{key}_queue_tier": tier})
        band = research_band(tiers)
        for item in output[-len(QUEUE_NAMES):]:
            item["research_band"] = band
    result_rows: list[dict[str, Any]] = []
    for _, group in pd.DataFrame(output).groupby("trade_date", sort=True):
        ranked = _rank_date_rows(group.to_dict("records"), source)
        result_rows.extend(ranked)
    result = pd.DataFrame(result_rows).drop(columns=["_source_index"] + [f"{key}_queue_tier" for key in QUEUE_KEYS.values()], errors="ignore")
    return result.sort_values(["trade_date", "queue_name", "queue_rank", "security_id"], na_position="last", kind="mergesort").reset_index(drop=True)


def build_structure_summary(structures: pd.DataFrame) -> pd.DataFrame:
    """Create per-security/date summary; unknown rows never count as misses."""
    if structures.empty:
        return pd.DataFrame(columns=["trade_date", "security_id", "queues_json", "research_band", "research_band_quality", "unique_hit_count", "queue_contract"])
    rows = []
    for (trade_date, security_id), group in structures.groupby(["trade_date", "security_id"], sort=True):
        known = group[group.hit.notna()]
        hits = known[known.hit.eq(True)]
        unknown = group.hit.isna().any()
        band = next((value for value in group.research_band.dropna()), "DIAGNOSTIC_ONLY")
        rows.append({"trade_date": trade_date, "security_id": security_id, "queues_json": json.dumps({row.queue_name: {"hit": row.hit, "tier": row.tier, "source_class": row.source_class, "queue_rank": row.queue_rank} for row in group.itertuples()}, ensure_ascii=False, sort_keys=True), "research_band": band, "research_band_quality": "DATA_INSUFFICIENT" if unknown else "AVAILABLE", "unique_hit_count": int(len(hits)), "queue_contract": "research-priority-v2-shadow-v1.0"})
    return pd.DataFrame(rows).sort_values(["trade_date", "security_id"], kind="mergesort").reset_index(drop=True)


def calculate_historical_structures(frame: pd.DataFrame, *, cutoff: Any | None = None) -> dict[str, Any]:
    structures = build_historical_structure_rows(frame, cutoff=cutoff)
    summary = build_structure_summary(structures)
    return {"contract_id": CONTRACT_VERSION, "structure_basis": STRUCTURE_BASIS, "structures": structures, "summary": summary, "queue_mappings": MAPPINGS, "audit": {"unknown_is_not_false": True, "formal_observations_written": False, "formal_outcomes_written": False}}


def rows_for_storage(frame: pd.DataFrame, slice_id: str) -> list[tuple[Any, ...]]:
    return [tuple(_storage(value) for value in (slice_id, row.security_id, row.trade_date, row.queue_name, row.hit, row.tier, row.source_class, row.research_band, row.queue_rank, row.tier_rank, row.transition, row.structure_basis, row.contract_id, json.dumps(_jsonable(row.evidence), ensure_ascii=False, sort_keys=True), json.dumps(_jsonable(row.quality_codes), ensure_ascii=False))) for row in frame.itertuples()]


def insert_historical_structure_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    rows = rows_for_storage(frame, slice_id)
    existing = connection.execute("select * from historical_structure_daily where slice_id=?", [slice_id]).fetchall()
    try:
        already_present = immutable_slice_state(existing, rows, key_indexes=(1, 2, 3), conflict_code="STRUCTURE_SLICE_IDENTITY_CONFLICT")
    except ValueError as exc:
        raise StructureAdapterError(str(exc)) from exc
    if already_present:
        return len(rows)
    connection.executemany("insert into historical_structure_daily values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


def _structure_result_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    names = ("slice_id",) + STRUCTURE_RESULT_COLUMNS
    records: list[dict[str, Any]] = []
    for values in rows_for_storage(frame, "__v3_result_object__"):
        record = dict(zip(names, values))
        record.pop("slice_id", None)
        record["trade_date"] = pd.Timestamp(record["trade_date"]).date()
        records.append(record)
    return records


def _structure_json_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _structure_value_semantics(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    return {
        "null_policy": "EXPLICIT_NULLS_PRESERVED",
        "legacy_nan_policy": "HASH_AS_NULL_PRESERVE_LEGACY_STORAGE",
        "json_policy": "SORTED_COMPACT_JSON",
        "business_key": list(STRUCTURE_RESULT_PRIMARY_KEY),
        "contract_ids": sorted({str(row["contract_id"]) for row in rows}),
        "structure_bases": sorted({str(row["structure_basis"]) for row in rows}),
        "queue_names": list(QUEUE_NAMES),
        "quality_field": "quality_codes",
        "evidence_field": "evidence",
        "evidence_semantics": "QUEUE_CLASSIFICATION_AND_RANKING_FACTS",
        "unknown_hit_policy": "UNKNOWN_IS_NOT_FALSE",
        "rank_semantics": "QUEUE_RANK_AND_TIER_RANK_WITHIN_TRADE_DATE",
        "research_band_semantics": "RESEARCH_PRIORITY_V2_SHADOW",
    }


def _structure_hash(records: list[dict[str, Any]]) -> tuple[str, int, dict[str, Any]]:
    semantics = _structure_value_semantics(records)
    canonical_records = []
    for record in records:
        canonical = dict(record)
        for column in ("queue_rank", "tier_rank"):
            value = canonical.get(column)
            if isinstance(value, (float, np.floating)) and not np.isfinite(float(value)):
                canonical[column] = None
            elif isinstance(value, (float, np.floating)) and float(value).is_integer():
                canonical[column] = int(value)
        canonical_records.append(canonical)
    value_hash, _, row_count = result_value_hash(
        domain="structure",
        schema_version=STRUCTURE_RESULT_SCHEMA_VERSION,
        semantic_contract=STRUCTURE_RESULT_SEMANTIC_CONTRACT,
        columns=STRUCTURE_RESULT_COLUMNS,
        primary_key=STRUCTURE_RESULT_PRIMARY_KEY,
        rows=canonical_records,
        value_semantics=semantics,
    )
    return value_hash, row_count, semantics


def _structure_records_from_db(connection: Any, result_object_id: str) -> list[dict[str, Any]]:
    columns = ",".join(STRUCTURE_RESULT_COLUMNS)
    rows = connection.execute(
        f"SELECT {columns} FROM structure_result_rows WHERE result_object_id=? ORDER BY security_id, trade_date, queue_name",
        [result_object_id],
    ).fetchall()
    return [dict(zip(STRUCTURE_RESULT_COLUMNS, row)) for row in rows]


def _register_structure_result_rows(
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
        raise ValueError(f"STRUCTURE_SLICE_NOT_FOUND:{slice_id}")
    if metadata[0] != "structure":
        raise ValueError("STRUCTURE_SLICE_DOMAIN_MISMATCH")
    if int(metadata[6]) != len(records):
        raise ValueError("STRUCTURE_RESULT_ROW_COUNT_MISMATCH")
    if len({(row["security_id"], row["trade_date"], row["queue_name"]) for row in records}) != len(records):
        raise ValueError("STRUCTURE_RESULT_PRIMARY_KEY_DUPLICATE")
    for record in records:
        record["evidence"] = _structure_json_text(record["evidence"])
        record["quality_codes"] = _structure_json_text(record["quality_codes"])
    value_hash, row_count, semantics = _structure_hash(records)
    result_object_id = "result-obj-" + value_hash[:32]
    now = datetime.now(timezone.utc)
    existing_object = connection.execute(
        "SELECT domain, schema_version, semantic_contract, value_hash, row_count, storage_kind FROM analysis_result_objects WHERE result_object_id=?",
        [result_object_id],
    ).fetchone()
    expected_object = (
        "structure", STRUCTURE_RESULT_SCHEMA_VERSION,
        STRUCTURE_RESULT_SEMANTIC_CONTRACT, value_hash, row_count, "DUCKDB",
    )
    if existing_object and tuple(existing_object) != expected_object:
        raise ValueError("STRUCTURE_RESULT_OBJECT_IDENTITY_CONFLICT")
    connection.execute(
        "INSERT INTO analysis_result_objects VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(result_object_id) DO NOTHING",
        [result_object_id, *expected_object[0:3], value_hash, row_count, "DUCKDB", now],
    )
    stored_rows = _structure_records_from_db(connection, result_object_id)
    if stored_rows:
        stored_hash, stored_count, stored_semantics = _structure_hash(stored_rows)
        if stored_count != row_count or stored_hash != value_hash or stored_semantics != semantics:
            raise ValueError("STRUCTURE_RESULT_VALUE_HASH_MISMATCH")
    else:
        columns = ["result_object_id", *STRUCTURE_RESULT_COLUMNS]
        placeholders = ",".join("?" for _ in columns)
        connection.executemany(
            f"INSERT INTO structure_result_rows VALUES ({placeholders})",
            [[result_object_id, *[record[column] for column in STRUCTURE_RESULT_COLUMNS]] for record in records],
        )
    storage_payload = {
        "storage_object_id": result_object_id,
        "result_object_id": result_object_id,
        "kind": "STRUCTURE_RESULT_ROWS",
        "storage_kind": "DUCKDB",
        "table": "structure_result_rows",
        "domain": "structure",
        "schema_version": STRUCTURE_RESULT_SCHEMA_VERSION,
        "semantic_contract": STRUCTURE_RESULT_SEMANTIC_CONTRACT,
        "value_hash": value_hash,
        "primary_key": list(STRUCTURE_RESULT_PRIMARY_KEY),
        "columns": list(STRUCTURE_RESULT_COLUMNS),
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
    if not connection.execute("SELECT 1 FROM storage_objects WHERE storage_object_id=?", [result_object_id]).fetchone():
        raise ValueError("STRUCTURE_RESULT_STORAGE_OBJECT_MISSING")
    if metadata[9] not in (None, result_object_id):
        raise ValueError("STRUCTURE_SLICE_STORAGE_OBJECT_CONFLICT")
    connection.execute(
        "UPDATE analysis_slices SET storage_object_id=? WHERE slice_id=? AND storage_object_id IS NULL",
        [result_object_id, slice_id],
    )
    basis = metadata[5] if isinstance(metadata[5], dict) else json.loads(metadata[5])
    evidence = {
        "contract_version": "v3-p03-03-structure-migration-v1",
        "migration_source": migration_source,
        "source_table": "historical_structure_daily",
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
        "result_schema_version": STRUCTURE_RESULT_SCHEMA_VERSION,
        "result_semantic_contract": STRUCTURE_RESULT_SEMANTIC_CONTRACT,
        "result_primary_key": list(STRUCTURE_RESULT_PRIMARY_KEY),
        "result_columns": list(STRUCTURE_RESULT_COLUMNS),
        "result_value_semantics": semantics,
    }
    existing_binding = connection.execute(
        "SELECT result_object_id FROM analysis_slice_result_bindings WHERE slice_id=?", [slice_id]
    ).fetchone()
    if existing_binding:
        if existing_binding[0] != result_object_id:
            raise ValueError("STRUCTURE_SLICE_RESULT_BINDING_CONFLICT")
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


def insert_structure_result_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    """Write one structure slice to the V3 result-object row store only."""
    records = _structure_result_records(frame)
    _register_structure_result_rows(connection, slice_id, records, migration_source="STRUCTURE_WRITER_V3")
    return len(records)


def migrate_structure_slice(connection: Any, slice_id: str) -> dict[str, Any]:
    """Import one immutable legacy structure slice into the V3 row store."""
    columns = ",".join(STRUCTURE_RESULT_COLUMNS)
    rows = connection.execute(
        f"SELECT {columns} FROM historical_structure_daily WHERE slice_id=? ORDER BY security_id, trade_date, queue_name",
        [slice_id],
    ).fetchall()
    records = [dict(zip(STRUCTURE_RESULT_COLUMNS, row)) for row in rows]
    return _register_structure_result_rows(connection, slice_id, records, migration_source="LEGACY_010_IMPORT")


def summary_rows_for_storage(frame: pd.DataFrame, slice_id: str) -> list[tuple[Any, ...]]:
    return [tuple(_storage(value) for value in (slice_id, row.security_id, row.trade_date, row.queues_json, row.research_band, row.research_band_quality, int(row.unique_hit_count), row.queue_contract)) for row in frame.itertuples()]


def insert_structure_summary_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    rows = summary_rows_for_storage(frame, slice_id)
    existing = connection.execute("select * from stock_structure_summary_daily where slice_id=?", [slice_id]).fetchall()
    try:
        present = immutable_slice_state(existing, rows, key_indexes=(1, 2), conflict_code="STRUCTURE_SUMMARY_SLICE_IDENTITY_CONFLICT")
    except ValueError as exc:
        raise StructureAdapterError(str(exc)) from exc
    if present:
        return len(rows)
    connection.executemany("insert into stock_structure_summary_daily values (?,?,?,?,?,?,?,?)", rows)
    return len(rows)
