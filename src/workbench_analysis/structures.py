"""Deterministic historical five-structure adapter (M8B-02)."""

from __future__ import annotations

import json
from typing import Any

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


CONTRACT_VERSION = "HISTORICAL_STRUCTURE_V2_1_RECONSTRUCTED"
STRUCTURE_BASIS = "RECONSTRUCTED"
QUEUE_NAMES = ("STEADY_QUEUE", "PULLBACK_QUEUE", "BREAKOUT_QUEUE", "LEADER_QUEUE", "EARLY_QUEUE")
QUEUE_KEYS = {"STEADY_QUEUE": "steady", "PULLBACK_QUEUE": "pullback", "BREAKOUT_QUEUE": "breakout", "LEADER_QUEUE": "leader", "EARLY_QUEUE": "early"}


class StructureAdapterError(ValueError):
    pass


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
        if value.upper() in {"TRUE", "1", "YES"}:
            return True
        if value.upper() in {"FALSE", "0", "NO"}:
            return False
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
    return [(slice_id, row.security_id, row.trade_date, row.queue_name, row.hit, row.tier, row.source_class, row.research_band, row.queue_rank, row.tier_rank, row.transition, row.structure_basis, row.contract_id, json.dumps(_jsonable(row.evidence), ensure_ascii=False, sort_keys=True), json.dumps(_jsonable(row.quality_codes), ensure_ascii=False)) for row in frame.itertuples()]


def insert_historical_structure_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    rows = rows_for_storage(frame, slice_id)
    existing = connection.execute("select security_id,trade_date,queue_name from historical_structure_daily where slice_id=?", [slice_id]).fetchall()
    expected = {(str(row[1]), str(row[2]), str(row[3])) for row in rows}
    actual = {(str(row[0]), str(row[1]), str(row[2])) for row in existing}
    if actual and actual != expected:
        raise StructureAdapterError("STRUCTURE_SLICE_IDENTITY_CONFLICT")
    if actual:
        return len(rows)
    connection.executemany("insert into historical_structure_daily values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)
