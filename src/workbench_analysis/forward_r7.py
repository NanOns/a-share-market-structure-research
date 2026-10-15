"""R7 independent full-universe Forward research pipeline.

The producer is intentionally separated from Focus/Radar and does not issue
orders, model probabilities, or production admission. Historical callers must
pass the actual accepted per-day owner rows and label the output retrospective.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable


CONTRACT_ID = "V4_FORWARD_PIPELINE_R7_R1"
DEFINITIONS_PATH = Path("config/v4_forward_signal_definitions_r7.json")
HORIZONS = (1, 3, 5)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _field(row: dict, key: str):
    fields = row.get("fields", {})
    value = fields.get(key)
    if isinstance(value, dict):
        return value.get("value"), value.get("quality_state", value.get("quality")), value
    return value, "OBSERVED" if value is not None else "UNKNOWN", {}


def _known(row: dict, key: str):
    value, quality, meta = _field(row, key)
    return value is not None and quality not in ("UNKNOWN", "SOURCE_INCOMPLETE", "NOT_IMPLEMENTED", "MISSING"), value, meta


def _source_hashes(bindings: dict[str, dict]) -> dict[str, str]:
    result = {}
    for key, binding in sorted(bindings.items()):
        if binding and isinstance(binding.get("sha256"), str):
            result[key] = binding["sha256"]
    return result


def _quality_codes(*values):
    return all(v is not None for v in values)


def build_daily_universe(*, trade_date: str, stock_rows: list[dict], raw_rows: list[dict],
                         sector_rows: list[dict], prior_stock_rows: list[dict] | None,
                         prior_raw_rows: list[dict] | None, prior_sector_rows: list[dict] | None,
                         bindings: dict[str, dict],
                         captured_at: str, lane: str,
                         membership_basis: str) -> list[dict]:
    """Evaluate every stock and sector identity, retaining UNKNOWN and NO_MATCH."""
    if lane not in ("LIVE_OOS", "RETROSPECTIVE_RESEARCH"):
        raise ValueError("FORWARD_EVIDENCE_LANE_REQUIRED")
    if membership_basis not in ("AS_RECORDED", "MEMBERSHIP_RETRO", "RECONSTRUCTED"):
        raise ValueError("FORWARD_MEMBERSHIP_BASIS_REQUIRED")
    evidence = "LIVE_OOS" if lane == "LIVE_OOS" else "RETROSPECTIVE_RESEARCH"
    if lane == "LIVE_OOS" and membership_basis != "AS_RECORDED":
        evidence = "LATE_OBSERVED_NOT_PIT"
    hashes = _source_hashes(bindings)
    raw_by_id = {r.get("security_id"): r for r in raw_rows if r.get("security_id")}
    prior_raw_by_id = {r.get("security_id"): r for r in (prior_raw_rows or []) if r.get("security_id")}
    prior_stock = {r.get("security_id"): r for r in prior_stock_rows or []}
    current_stock = {r.get("security_id"): r for r in stock_rows if r.get("security_id")}
    out: list[dict] = []
    for entity_id in sorted(current_stock):
        core = current_stock[entity_id]
        raw = raw_by_id.get(entity_id)
        missing = []
        reasons = []
        if raw is None:
            missing.append("current_ohlcv")
        else:
            for name in ("open","high","low","close","volume"):
                if raw.get(name) is None:
                    missing.append(name)
        required = {}
        for name in ("prior_high20", "prior_low20", "ma20", "core_price_damage", "rps5", "rps20"):
            ok, value, meta = _known(core, name)
            required[name] = value if ok else None
            if not ok:
                missing.append(name)
            if name.startswith("prior_") and ok and meta.get("actual_count", 20) < 20:
                missing.append(name + ".minimum_20_observations")
        event = "NO_MATCH"
        status = "NO_MATCH"
        if missing:
            status, event = "UNKNOWN", "UNKNOWN"
            reasons.append("REQUIRED_INPUT_MISSING_OR_UNKNOWN")
        else:
            previous = prior_stock.get(entity_id)
            previous_breakout = False
            if previous:
                p_high_ok, p_high, _ = _known(previous, "prior_high20")
                p_raw = prior_raw_by_id.get(entity_id, {})
                previous_breakout = bool(p_raw.get("close") is not None and p_high_ok and p_raw["close"] > p_high)
            close = raw.get("close")
            prior_high = required["prior_high20"]
            if close is None:
                status, event = "UNKNOWN", "UNKNOWN"
                missing.append("close")
            elif previous_breakout and required["core_price_damage"] is False:
                low = raw.get("low")
                if low is None:
                    status, event = "UNKNOWN", "UNKNOWN"
                    missing.append("low")
                elif low <= prior_high * 1.02 and close >= prior_high:
                    status, event = "MATCH", "PULLBACK_CONFIRMATION_OBSERVED"
                elif close > prior_high:
                    status, event = "MATCH", "BREAKOUT_OBSERVED"
                else:
                    reasons.append("PULLBACK_CONFIRMATION_PREDICATE_FALSE")
            elif close > prior_high:
                status, event = "MATCH", "BREAKOUT_OBSERVED"
            else:
                reasons.append("BREAKOUT_PREDICATE_FALSE")
        out.append(dict(
            rule_id="STOCK_RIGHT_STRUCTURE_EVENT_R1", rule_version="1.0.0",
            T0=trade_date, entity_type="STOCK", entity_id=entity_id,
            symbol=core.get("source_security_key"), board_scope=core.get("board_scope"),
            sector_id=core.get("primary_industry"), status=status, event_code=event,
            reason_codes=reasons, missing_inputs=sorted(set(missing)),
            input_cutoff=trade_date + "T15:00:00+08:00", membership_basis=membership_basis,
            evidence_class=evidence, source_hashes=hashes, captured_at=captured_at,
            values=dict(open=raw.get("open") if raw else None, high=raw.get("high") if raw else None,
                        low=raw.get("low") if raw else None, close=raw.get("close") if raw else None,
                        volume=raw.get("volume") if raw else None, **required),
            source_security_key=core.get("source_security_key")))

    prior_sector = {r.get("sector_id"): r for r in prior_sector_rows or []}
    for sector in sorted(sector_rows, key=lambda r: r.get("sector_id", "")):
        sector_id = sector.get("sector_id")
        vals = {}
        missing = []
        for name in ("sector_rs5", "sector_rs20", "breadth_ret5", "breadth_ret20", "sector_quote_coverage"):
            ok, value, _ = _known(sector, name)
            vals[name] = value if ok else None
            if not ok:
                missing.append(name)
        prior = prior_sector.get(sector_id)
        current_membership = sector.get("membership_snapshot_id") or sector.get("member_set_asof")
        prior_membership = (prior or {}).get("membership_snapshot_id") or (prior or {}).get("member_set_asof")
        if prior is None:
            missing.append("prior_comparable_state")
        elif not current_membership or not prior_membership or current_membership != prior_membership:
            missing.append("comparable_membership_basis")
        status, event = "UNKNOWN", "UNKNOWN"
        reasons = []
        if not missing:
            score = sum(vals[k] > 0 for k in ("sector_rs5", "sector_rs20", "breadth_ret5", "breadth_ret20"))
            prior_score = sum(_known(prior, k)[0] and _known(prior, k)[1] > 0
                              for k in ("sector_rs5", "sector_rs20", "breadth_ret5", "breadth_ret20"))
            if vals["sector_quote_coverage"] < 0.8:
                status, event = "UNKNOWN", "UNKNOWN"
                reasons.append("QUOTE_COVERAGE_BELOW_0_8")
            elif all(vals[k] > 0 for k in ("sector_rs5", "sector_rs20", "breadth_ret5", "breadth_ret20")) and score > prior_score:
                status, event = "MATCH", "STRENGTHENING_OBSERVED"
            else:
                status, event = "NO_MATCH", "NO_MATCH"
                reasons.append("STRENGTHENING_PREDICATE_FALSE")
        else:
            reasons.append("NO_COMPARABLE_OR_COMPLETE_SECTOR_INPUTS")
        out.append(dict(
            rule_id="SECTOR_STRENGTH_TRANSITION_R1", rule_version="1.0.0",
            T0=trade_date, entity_type="SECTOR", entity_id=sector_id,
            sector_id=sector_id, status=status, event_code=event,
            reason_codes=reasons, missing_inputs=sorted(set(missing)),
            input_cutoff=trade_date + "T15:00:00+08:00",
            membership_basis=("RECONSTRUCTED" if membership_basis == "MEMBERSHIP_RETRO" else membership_basis),
            evidence_class=evidence, source_hashes=hashes, captured_at=captured_at,
            values=vals, membership_snapshot_id=current_membership))
    return out


def make_observation_id(row: dict) -> str:
    return sha256([row["rule_id"], row["rule_version"], row["T0"], row["entity_id"]])


def scheduled_sessions(trade_date: str, sessions: list[str]) -> dict[int, str | None]:
    ordered = sorted(set(d for d in sessions if d <= trade_date))
    if not ordered or ordered[-1] != trade_date:
        raise ValueError("T0_NOT_IN_ACCEPTED_SESSION_CALENDAR")
    index = ordered.index(trade_date)
    # Callers may pass future official sessions after the T0 boundary.
    all_sessions = sorted(set(sessions))
    index = all_sessions.index(trade_date)
    return {n: all_sessions[index + n] if index + n < len(all_sessions) else None for n in HORIZONS}


def compute_nominal_settlement(*, observation: dict, due_date: str,
                               prices_by_date: dict[str, dict[str, dict]],
                               settlement_at: str, due_source_accepted: bool = True) -> dict:
    """Settle only accepted source dates; absent due dates are not quote failures."""
    if observation.get("entity_type") != "STOCK" or observation.get("status") != "MATCH":
        return dict(status="SOURCE_GAP", reason="NO_TRADABLE_STOCK_MATCH")
    if not due_source_accepted:
        return dict(status="DUE_SOURCE_NOT_ACCEPTED", reason="DUE_SESSION_NOT_IN_ACCEPTED_HEAD", due_date=due_date)
    t0_row = prices_by_date.get(observation["T0"], {}).get(observation["entity_id"], {})
    due_row = prices_by_date.get(due_date, {}).get(observation["entity_id"], {})
    t0_price = t0_row.get("close")
    due_price = due_row.get("close")
    if t0_price is None or float(t0_price) <= 0:
        return dict(status="SOURCE_GAP", reason="ACCEPTED_T0_RAW_CLOSE_MISSING", due_date=due_date)
    source_status = due_row.get("source_status") or due_row.get("quote_status")
    if source_status in ("NO_QUOTE", "SUSPENDED"):
        if due_price is not None:
            return dict(status="SOURCE_GAP", reason="QUOTE_STATUS_CONFLICTS_WITH_ACCEPTED_PRICE", due_date=due_date)
        return dict(status=source_status, reason="SECURITY_LEVEL_ACCEPTED_SOURCE_FACT",
                    due_date=due_date, source_fact=source_status,
                    source_hash=due_row.get("source_hash"))
    if due_price is None:
        return dict(status="SOURCE_GAP", reason="ACCEPTED_DUE_SESSION_SECURITY_ROW_MISSING", due_date=due_date)
    return dict(status="SETTLED", T0_close=float(t0_price), due_close=float(due_price),
                nominal_return=float(due_price) / float(t0_price) - 1.0,
                price_basis="NOMINAL_UNADJUSTED_CLOSE",
                corporate_action_adjustment="NOT_APPLIED",
                settlement_at=settlement_at,
                source_hashes=observation.get("source_hashes", {}),
                calculation_version="V4_FORWARD_NOMINAL_CLOSE_RETURN_R1")


def summarize_universe(rows: list[dict]) -> dict:
    groups = {}
    for row in rows:
        key = (row["rule_id"], row["rule_version"], row["entity_type"], row["status"], row["evidence_class"])
        group = groups.setdefault(key, dict(rule_id=key[0], rule_version=key[1], entity_type=key[2],
                                            status=key[3], evidence_class=key[4], count=0,
                                            match_count=0, no_match_count=0, unknown_count=0))
        group["count"] += 1
        group[{"MATCH": "match_count", "NO_MATCH": "no_match_count", "UNKNOWN": "unknown_count"}[row["status"]]] += 1
    return dict(contract_id="V4_FORWARD_AGGREGATE_R7_R1", total=len(rows), groups=list(groups.values()),
                rule_versions=sorted({r["rule_id"] + ":" + r["rule_version"] for r in rows}))


def load_definitions(root: str | Path) -> tuple[dict, str]:
    path = Path(root) / DEFINITIONS_PATH
    if not path.is_file():
        path = Path(__file__).resolve().parents[2] / DEFINITIONS_PATH
    raw = path.read_bytes()
    value = json.loads(raw)
    if value.get("contract_id") != "V4_FORWARD_SIGNAL_DEFINITIONS_R7" or value.get("version") != "R1":
        raise ValueError("R7_SIGNAL_DEFINITION_CONTRACT_MISMATCH")
    ids = [r.get("rule_id") for r in value.get("rules", [])]
    if ids != ["STOCK_RIGHT_STRUCTURE_EVENT_R1", "SECTOR_STRENGTH_TRANSITION_R1"]:
        raise ValueError("R7_RULE_SET_INCOMPLETE")
    return value, hashlib.sha256(raw).hexdigest()
