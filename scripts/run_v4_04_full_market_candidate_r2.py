"""Build a hash-bound V4-04 full-market staging candidate at the frozen cutoff."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, replace
import gzip
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import sys

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.v4.accepted_input import BOARDS, CUTOFF, resolve  # noqa: E402
from src.v4.profile_core import (closed_period_trend, compression, drawdown, extension_risk,
                                 ma_structure, near_high, participation, position, ratio_state,
                                 relative, severe_extension, trend, P)  # noqa: E402
from src.v4.profile_primitives import derive_closed_period, derive_daily  # noqa: E402
from src.v4.market_regime_ui import project as project_regime_ui  # noqa: E402
from src.v4.profile_status import component_status  # noqa: E402


OUT = ROOT / "reports/v4_04/staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R2.jsonl.gz"
RECEIPT = ROOT / "reports/v4_04/V4_04_FULL_MARKET_CANDIDATE_RECEIPT_R2.json"
CONTRACT_FILES = ("config/v4_04_field_registry_v2.json", "config/v4_04_output_schema_v2.json",
                  "config/v4_04_algorithm_contracts_v2.json", "config/v4_04_parameter_set_v1.json",
                  "config/v4_04_field_window_mapping_v1.json")


def iso_date(value: int | str) -> str:
    raw = str(value)
    return raw if "-" in raw else f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"


def digest(value: object) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _periods(connection: duckdb.DuckDBPyConnection, path: Path, limit: int) -> dict[str, list[dict]]:
    query = f"""
      SELECT canonical_security_id, period_last_session, period_view, period_status,
             price_basis, close, source_daily_digest
      FROM read_parquet(?)
      WHERE price_basis='QFQ' AND period_view='CLOSED_ONLY' AND period_last_session <= 20260924
      QUALIFY row_number() OVER (PARTITION BY canonical_security_id ORDER BY period_last_session DESC) <= {limit}
      ORDER BY canonical_security_id, period_last_session
    """
    rows = defaultdict(list)
    cur = connection.execute(query, [str(path)])
    for sid, date, view, status, basis, close, source_digest in cur.fetchall():
        rows[sid].append({"period_last_session": iso_date(date), "period_view": view,
                          "period_status": status, "price_basis": basis,
                          "close": float(close) if close is not None else None,
                          "source_daily_digest": source_digest})
    return rows


def _daily(connection: duckdb.DuckDBPyConnection, path: Path) -> dict[str, list[dict]]:
    query = f"""
      SELECT canonical_security_id, source_security_key, board_scope, trade_date,
             qfq_close, qfq_high, qfq_low, amount, adjusted_quality
      FROM read_parquet(?)
      WHERE trade_date <= 20260924 AND trading_status='ACTUAL_TRADED'
      QUALIFY row_number() OVER (PARTITION BY canonical_security_id ORDER BY trade_date DESC) <= {int(P['POS250_WINDOW']) + 1}
      ORDER BY canonical_security_id, trade_date
    """
    rows = defaultdict(list)
    cur = connection.execute(query, [str(path)])
    while batch := cur.fetchmany(20000):
        for sid, symbol, board, date, close, high, low, amount, quality in batch:
            rows[sid].append({"source_security_key": symbol, "board_scope": board,
                              "trade_date": iso_date(date), "qfq_close": float(close) if close is not None else None,
                              "qfq_high": float(high) if high is not None else None,
                              "qfq_low": float(low) if low is not None else None,
                              "amount": amount, "adjusted_quality": quality})
    return rows


def _cutoff_universe(path: Path) -> dict[str, dict]:
    rows = {}
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["trade_date"] == CUTOFF:
                sid = row["security_id"]
                if sid in rows:
                    raise ValueError("duplicate cutoff universe identity")
                rows[sid] = row
    return rows


def _statuses(path: Path, starts: dict[str, str]) -> dict[str, list[tuple[str, str]]]:
    result: dict[str, list[tuple[str, str]]] = defaultdict(list)
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            sid = row["security_id"]
            start = starts.get(sid)
            if start is not None and start <= row["trade_date"] <= CUTOFF:
                result[sid].append((row["trade_date"], row["status"]))
    for value in result.values():
        value.sort()
    return result


def _factor_values(fields: dict) -> dict:
    return {name: item["value"] if item["quality_state"] == "OBSERVED" else None for name, item in fields.items()}


def _state_payload(state, source_digest: str, contract_digest: str) -> dict:
    payload = asdict(state)
    payload["parameter_set_id"] = "V4_04_CORE_PROFILE_PARAMETER_SET_V1"
    payload["source_digest"] = source_digest
    payload["contract_digest"] = contract_digest
    payload["input_digest"] = digest(state.evidence)
    payload["output_digest"] = digest(payload)
    return payload


def build_row(factor_row: dict, bars: list[dict], weekly: list[dict], monthly: list[dict],
              statuses: list[tuple[str, str]], universe: dict, source_digest: str, contract_digest: str,
              calendar: list[str], regime_ui) -> dict:
    fields = factor_row["fields"]
    primitives = _factor_values(fields)
    pos_start = bars[-int(P["POS250_WINDOW"])]["trade_date"] if len(bars) >= P["POS250_WINDOW"] else None
    expected_sessions = {date for date in calendar if pos_start is not None and pos_start <= date <= CUTOFF}
    observed_sessions = {date for date, _ in statuses}
    status_values = statuses if pos_start is not None and observed_sessions == expected_sessions and len(statuses) == len(expected_sessions) else [(CUTOFF, "UNKNOWN")]
    derived = derive_daily(bars, fields, status_values, CUTOFF)
    for name, item in list(derived.items()):
        if item.window_start_trade_date is None:
            continue
        span = [status for date, status in statuses if item.window_start_trade_date <= date <= item.window_end_trade_date]
        if span:
            derived[name] = replace(item, calendar_span=len(span), suspended_count=span.count("SUSPENDED"))
    primitives.update({name: value.value for name, value in derived.items()})
    close = bars[-1]["qfq_close"] if bars and bars[-1]["trade_date"] == CUTOFF and bars[-1]["adjusted_quality"] == "READY" else None
    primitives["close"] = close
    primitives["ma10"] = derived["ma10"].value
    primitives["minimum_liquidity"] = derived["minimum_liquidity"].value
    wk = derive_closed_period(weekly, int(P["WEEKLY_MA_WINDOW"]), CUTOFF)
    mo = derive_closed_period(monthly, int(P["MONTHLY_MA_WINDOW"]), CUTOFF)
    comp = compression(primitives)
    ma = ma_structure(primitives)
    risk = extension_risk(primitives)
    states = {
        "trend_state": trend(primitives),
        "weekly_trend_state": closed_period_trend(wk, "weekly"),
        "monthly_trend_state": closed_period_trend(mo, "monthly"),
        "position_state": position(primitives),
        "near_high20_state": near_high(primitives, 20),
        "near_high60_state": near_high(primitives, 60),
        "drawdown20_state": drawdown(primitives, 20),
        "drawdown60_state": drawdown(primitives, 60),
        "ma_structure_state": ma,
        "relative_market_state": relative(primitives, comp.value, ma.value),
        "compression_state": comp,
        "amount_state": ratio_state(primitives, "amount_ratio20"),
        "volume_state": ratio_state(primitives, "volume_ratio20"),
        "core_participation_result": participation(primitives),
        "core_extension_risk": risk,
        "severe_extension": severe_extension(risk),
    }
    states["regime_ui"] = regime_ui
    identity = {"security_id": factor_row["security_id"], "symbol": universe["source_security_key"],
                "trade_date": CUTOFF, "board": factor_row["board_scope"], "source_cutoff": CUTOFF,
                "publication_id": "V4_04_STAGING_R2"}
    state_rows = {key: _state_payload(value, source_digest, contract_digest) for key, value in states.items()}
    derived_rows = {}
    for key, value in derived.items():
        item = {**asdict(value), "source_digest": source_digest, "contract_digest": contract_digest}
        item["output_digest"] = digest(item)
        derived_rows[key] = item
    required_unknown = sum(value["unknown_reason"] is not None for value in state_rows.values())
    state_count = len(state_rows)
    mapping_path = ROOT / "config/v4_04_field_window_mapping_v1.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    upstream_mapping_digest = mapping["accepted_v4_03_mapping_sha256"]
    period_lineage = {}
    for name, periods in (("weekly_trend_state", weekly), ("monthly_trend_state", monthly)):
        used = periods[-(6 if name.startswith("weekly") else 4):]
        period_lineage[name] = {"window_identity": digest(used),
                                "period_last_session": used[-1]["period_last_session"] if used else None,
                                "period_view": used[-1]["period_view"] if used else "UNKNOWN",
                                "source_daily_digest": digest([x["source_daily_digest"] for x in used])}
    payload = {**identity, "states": state_rows,
               "derived_fields": derived_rows,
               "primitive_quality": {key: {k: value.get(k) for k in ("quality_state", "unknown_reason", "output_digest", "input_digest", "window_identity", "window_start_trade_date", "window_end_trade_date", "calendar_span", "actual_count", "suspended_count", "contract_id", "parameter_set_id")}
                                     for key, value in fields.items()},
               "profile_component_status": component_status(state_count - required_unknown, state_count),
               "profile_quality": "COMPLETE" if required_unknown == 0 else "PARTIAL_UNKNOWN",
               "source_asof": CUTOFF, "technical_window_identity": digest([value.window_identity for value in derived.values()]),
               "field_window_mapping_id": mapping["contract_id"],
               "field_window_mapping_digest": sha256(mapping_path.read_bytes()).hexdigest(),
               "accepted_v4_03_field_window_mapping_digest": upstream_mapping_digest,
               "period_lineage": period_lineage,
               "source_digest": source_digest, "contract_digest": contract_digest,
               "trading_status": statuses[-1][1] if statuses and statuses[-1][0] == CUTOFF else "UNKNOWN"}
    payload["output_digest"] = digest(payload)
    return payload


def main() -> None:
    sources = resolve(ROOT)
    calendars = {
        "SH": json.loads(sources["calendar"].path.read_text(encoding="utf-8"))["session_dates"],
        "SZ": json.loads(sources["calendar_szse"].path.read_text(encoding="utf-8"))["session_dates"],
    }
    contracts = {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in CONTRACT_FILES}
    contract_digest = digest(contracts)
    algorithm = json.loads((ROOT / CONTRACT_FILES[2]).read_text(encoding="utf-8"))
    if algorithm.get("parameter_set_id") != "V4_04_CORE_PROFILE_PARAMETER_SET_V1" or len(algorithm.get("rules", {})) < 8:
        raise ValueError("V4-04 machine contract incomplete")
    connection = duckdb.connect()
    daily = _daily(connection, sources["daily"].path)
    weekly = _periods(connection, sources["weekly"].path, int(P["WEEKLY_MA_WINDOW"]) + 1)
    monthly = _periods(connection, sources["monthly"].path, int(P["MONTHLY_MA_WINDOW"]) + 1)
    universe = _cutoff_universe(sources["universe"].path)
    with gzip.open(sources["factors"].path, "rt", encoding="utf-8") as stream:
        factor_rows = [json.loads(line) for line in stream]
    with gzip.open(sources["market_regime"].path, "rt", encoding="utf-8") as stream:
        regime_path = [json.loads(line) for line in stream]
    regime_by_date = project_regime_ui(regime_path)
    if CUTOFF not in regime_by_date or len(regime_by_date) != len(regime_path):
        raise ValueError("accepted market regime cutoff/path identity mismatch")
    if len(factor_rows) != len({x["security_id"] for x in factor_rows}):
        raise ValueError("duplicate factor identity")
    if set(x["board_scope"] for x in factor_rows) != set(BOARDS):
        raise ValueError("required board coverage mismatch")
    if any(x["trade_date"] != CUTOFF or x["security_id"] not in universe or
           x["board_scope"] != universe[x["security_id"]]["board_scope"] for x in factor_rows):
        raise ValueError("factor/universe cutoff identity mismatch")
    starts = {sid: (rows[-int(P["POS250_WINDOW"])] if len(rows) >= P["POS250_WINDOW"] else rows[0])["trade_date"]
              for sid, rows in daily.items() if rows}
    statuses = _statuses(sources["trading_status"].path, starts)
    source_digest = digest({key: value.sha256 for key, value in sorted(sources.items())})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(OUT.suffix + ".tmp")
    boards, quality = Counter(), Counter()
    with tmp.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0, compresslevel=6) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as text:
                for factor in sorted(factor_rows, key=lambda x: (x["board_scope"], x["security_id"])):
                    sid = factor["security_id"]
                    row = build_row(factor, daily.get(sid, []), weekly.get(sid, []), monthly.get(sid, []),
                                    statuses.get(sid, []), universe[sid], source_digest, contract_digest,
                                    calendars["SH" if factor["board_scope"] in ("SH_MAIN", "STAR") else "SZ"],
                                    regime_by_date[CUTOFF])
                    text.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
                    boards[row["board"]] += 1
                    quality[row["profile_quality"]] += 1
    os.replace(tmp, OUT)
    h = sha256(OUT.read_bytes()).hexdigest()
    receipt = {"contract_id": "V4_04_FULL_MARKET_CANDIDATE_RECEIPT_R2", "status": "STAGING_ONLY_NOT_ACCEPTED",
               "cutoff": CUTOFF, "required_boards": list(BOARDS), "board_count": dict(boards),
               "row_count": sum(boards.values()), "quality_count": dict(quality),
               "contract_files": contracts, "contract_digest": contract_digest,
               "sources": {key: {"path": str(value.path.relative_to(ROOT)).replace("\\", "/"),
                                  "sha256": value.sha256, "contract_id": value.contract_id}
                           for key, value in sources.items()},
               "artifact": {"path": str(OUT.relative_to(ROOT)).replace("\\", "/"), "sha256": h,
                            "byte_count": OUT.stat().st_size}}
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    receipt_tmp = RECEIPT.with_suffix(".json.tmp")
    receipt_tmp.write_bytes((json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    os.replace(receipt_tmp, RECEIPT)
    print(json.dumps({"rows": sum(boards.values()), "boards": boards, "quality": quality, "artifact_sha256": h}, default=dict))


if __name__ == "__main__":
    main()
