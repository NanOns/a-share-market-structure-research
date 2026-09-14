"""Read-only three-date historical input pilot; never publishes research rows."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from adjustment.tdx_adjustment import build_affine_factors, xrxd_from_gbbq  # noqa: E402
from tdx.gbbq_reader import read_gbbq  # noqa: E402

PARQUET = ROOT / "data/normalized/adjusted_daily.parquet"
GBBQ = Path("D:/new_tdx/T0002/hq_cache/gbbq")
OUT = ROOT / "reports/p12_02/historical_input_pilot.json"
DATES = ("2026-03-31", "2026-06-30", "2026-09-14")
SYMBOLS = ("SZ.000001", "SZ.000009")
SPEC = ROOT / "docs/V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    if not GBBQ.is_file():
        raise RuntimeError("Configured TDX GBBQ input is unavailable")
    gbbq_sha = sha256(GBBQ)
    events = defaultdict(list)
    for record in read_gbbq(GBBQ):
        if record.category == 1 and record.security_id in SYMBOLS:
            events[record.security_id].append(xrxd_from_gbbq(record))

    with duckdb.connect(str(ROOT / "data/database/market_research.duckdb"), read_only=True) as con:
        sessions = [row[0].isoformat() for row in con.execute(
            "SELECT DISTINCT date FROM read_parquet(?) WHERE date BETWEEN '2025-01-01' AND '2026-09-14' ORDER BY date",
            [str(PARQUET)],
        ).fetchall()]
        aggregates = con.execute("""
            SELECT date, count(*), count_if(has_actual_bar),
                   count_if(universe_status='IN_NORMAL_UNIVERSE'),
                   count_if(has_actual_bar AND raw_open IS NOT NULL AND raw_high IS NOT NULL
                       AND raw_low IS NOT NULL AND raw_close IS NOT NULL AND raw_amount>0
                       AND raw_volume>0),
                   count_if(has_actual_bar AND (raw_high<greatest(raw_open,raw_close,raw_low)
                       OR raw_low>least(raw_open,raw_close,raw_high)))
            FROM read_parquet(?) WHERE date IN (?,?,?) GROUP BY date ORDER BY date
        """, [str(PARQUET), *DATES]).fetchall()
        sample = con.execute("""
            SELECT security_id,date,raw_open,raw_high,raw_low,raw_close,
                   adj_close,raw_amount,raw_volume,has_actual_bar
            FROM read_parquet(?) WHERE security_id IN (?,?) AND date<='2026-09-14'
            ORDER BY security_id,date
        """, [str(PARQUET), *SYMBOLS]).fetchall()
        full_year = con.execute("""
            SELECT count(DISTINCT date), count(*), min(date), max(date)
            FROM read_parquet(?) WHERE date BETWEEN '2026-01-01' AND '2026-12-31'
        """, [str(PARQUET)]).fetchone()

    by_symbol = defaultdict(dict)
    for row in sample:
        by_symbol[row[0]][row[1].isoformat()] = row
    date_rows = {}
    for day, rows, actual, normal, valid, bad_ohlc in aggregates:
        key = day.isoformat()
        window = sessions[max(0, sessions.index(key) - 119):sessions.index(key) + 1]
        date_rows[key] = {
            "rows": rows, "actual_bar": actual, "current_cutoff_normal_universe": normal,
            "complete_raw_ohlc_positive_amount_volume": valid,
            "raw_ohlc_order_errors": bad_ohlc,
            "master_session_120_window": len(window),
            "sample_120_actual_counts": {sid: sum(bool(by_symbol[sid].get(d, (None,) * 10)[9]) for d in window)
                                          for sid in SYMBOLS},
        }
    samples = []
    for sid in SYMBOLS:
        for cutoff in DATES:
            available = [d for d in by_symbol[sid] if d <= cutoff]
            if not available:
                raise RuntimeError(f"Missing sample: {sid} {cutoff}")
            integers = [int(d.replace("-", "")) for d in sorted(available)]
            factors = build_affine_factors(integers, [e for e in events[sid] if e.ex_day <= int(cutoff.replace("-", ""))])
            row = by_symbol[sid][cutoff]
            cutoff_close = float(factors[int(cutoff.replace("-", ""))].qfq_price(row[5]))
            samples.append({
                "security_id": sid, "cutoff": cutoff,
                "raw_close": float(row[5]), "latest_parquet_adj_close": float(row[6]),
                "recomputed_cutoff_adj_close": cutoff_close,
                "latest_minus_cutoff_adj_close": round(float(row[6]) - cutoff_close, 4),
                "effective_xrxd_event_count_to_cutoff": sum(e.ex_day <= int(cutoff.replace("-", "")) for e in events[sid]),
                "source_availability": "CURRENT_GBBQ_SOURCE_ONLY_RECONSTRUCTED",
            })
    result = {
        "stage_contract": "P12-02_HISTORICAL_INPUT_PILOT_V1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "consulted_spec_sha256": sha256(SPEC),
        "input_identity": {"adjusted_daily_sha256": sha256(PARQUET), "gbbq_current_sha256": gbbq_sha,
                           "gbbq_path": str(GBBQ), "sample_symbols": SYMBOLS},
        "year_2026_available": {"sessions": full_year[0], "rows": full_year[1],
                                "first": full_year[2].isoformat(), "last": full_year[3].isoformat()},
        "date_coverage": date_rows, "cutoff_adjustment_samples": samples,
        "history_basis": "RECONSTRUCTED_CURRENT_SOURCE",
        "pit_member_status": "UNAVAILABLE",
        "storage_decision": "NO_170_DAY_MATERIALIZATION_BEFORE_FACTOR_AND_DEPENDENCY_LOCK_ACCEPTANCE",
        "acceptance_result": "DEGRADED_PASS",
        "acceptance_scope": "Three-date raw-input coverage and cutoff-adjustment feasibility only; no historical PIT or new-factor acceptance",
        "next_stage": "P12-02_FACTOR_V3_3_CONTINUE",
    }
    if len(date_rows) != len(DATES) or any(x["raw_ohlc_order_errors"] for x in date_rows.values()):
        result["acceptance_result"] = "BLOCKED"
        result["next_stage"] = "P12-02_HISTORICAL_INPUT_PILOT_REPAIR"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="historical_input_pilot.", suffix=".tmp", dir=OUT.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, OUT)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    print(OUT)


if __name__ == "__main__":
    main()
