"""Bounded three-day, full-stock factor replay from RAW with target-day QFQ anchors."""

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
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from adjustment.tdx_adjustment import build_affine_factors, xrxd_from_gbbq  # noqa: E402
from tdx.gbbq_reader import read_gbbq  # noqa: E402
from workbench_analysis.today_research_factors_v3_3 import calculate_today_facts  # noqa: E402

PARQUET = ROOT / "data/normalized/adjusted_daily.parquet"
GBBQ = Path("D:/new_tdx/T0002/hq_cache/gbbq")
SPEC = ROOT / "docs/V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md"
OUT = ROOT / "reports/p12_02/three_day_factor_replay.json"
DATES = ("2026-03-31", "2026-06-30", "2026-09-14")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    events = defaultdict(list)
    for item in read_gbbq(GBBQ):
        if item.category == 1:
            events[item.security_id].append(xrxd_from_gbbq(item))
    with duckdb.connect(database=":memory:") as con:
        sessions = [row[0].isoformat() for row in con.execute(
            "SELECT DISTINCT date FROM read_parquet(?) WHERE date BETWEEN '2026-01-01' AND '2026-09-14' ORDER BY date",
            [str(PARQUET)]).fetchall()]
        windows = {day: sessions[sessions.index(day) - 21:sessions.index(day) + 1] for day in DATES}
        if any(len(window) != 22 for window in windows.values()):
            raise RuntimeError("Insufficient master sessions")
        raw = con.execute("""
            SELECT security_id,date,raw_open,raw_high,raw_low,raw_close,
                   raw_amount,raw_volume,has_actual_bar,is_synthetic_fill,
                   adj_open,adj_high,adj_low,adj_close
            FROM read_parquet(?) WHERE date BETWEEN ? AND ? ORDER BY security_id,date
        """, [str(PARQUET), min(w[0] for w in windows.values()), max(DATES)]).fetchall()
    by_stock = defaultdict(dict)
    for row in raw:
        by_stock[row[0]][row[1].isoformat()] = row
    master_index = {day: i for i, day in enumerate(sessions)}
    results = []
    for target in DATES:
        cutoff = int(target.replace("-", ""))
        window_dates = windows[target]
        factor_rows = []
        mismatches = 0
        for sid in sorted(by_stock):
            bars = by_stock[sid]
            available = [int(day.replace("-", "")) for day in window_dates
                         if day in bars and bars[day][8] is True]
            factors = build_affine_factors(available, [event for event in events[sid] if event.ex_day <= cutoff]) if available else {}
            window = []
            for day in window_dates:
                row = bars.get(day)
                base = {"date": day, "session_index": master_index[day],
                        "anchor_cutoff": target, "price_basis": "TDX_NATIVE_AFFINE_QFQ"}
                if row is None or row[8] is not True:
                    window.append({**base, "has_actual_bar": False})
                    continue
                factor = factors[int(day.replace("-", ""))]
                adj = {key: float(factor.qfq_price(row[idx]))
                       for key, idx in (("open", 2), ("high", 3), ("low", 4), ("close", 5))}
                if target == DATES[-1]:
                    mismatches += sum(adj[key] != float(row[idx]) for key, idx in
                                      (("open", 10), ("high", 11), ("low", 12), ("close", 13)))
                window.append({**base, "has_actual_bar": True,
                               "is_synthetic_fill": bool(row[9]), **adj,
                               "raw_open": float(row[2]), "raw_close": float(row[5]),
                               "amount": float(row[6]), "volume": float(row[7])})
            facts = calculate_today_facts(window)
            factor_rows.append({"security_id": sid, "date": target,
                                "history_basis": "RECONSTRUCTED_CURRENT_SOURCE",
                                **facts})
        frame = pd.DataFrame(factor_rows).sort_values("security_id").reset_index(drop=True)
        frame["market_group"] = frame["security_id"].str[:2]
        valid_sigma = frame["sigma20_prior"].dropna()
        sigma_edges = [float(valid_sigma.quantile(q)) for q in (0.25, 0.5, 0.75)]
        def sigma_group(value):
            if pd.isna(value):
                return "UNKNOWN"
            return "Q1" if value <= sigma_edges[0] else "Q2" if value <= sigma_edges[1] else "Q3" if value <= sigma_edges[2] else "Q4"
        frame["sigma_group"] = frame["sigma20_prior"].map(sigma_group)
        risk_distribution = []
        for (market, group), subset in frame.groupby(["market_group", "sigma_group"], sort=True):
            risk_distribution.append({"market": market, "sigma_group": group,
                                      "stocks": len(subset),
                                      "severe_drop_true": int(subset["severe_drop"].eq(True).sum()),
                                      "severe_drop_false": int(subset["severe_drop"].eq(False).sum()),
                                      "severe_drop_unknown": int(subset["severe_drop"].isna().sum())})
        measurements = []
        for _ in range(2):
            fd, name = tempfile.mkstemp(prefix="p12_02_factor_", suffix=".parquet", dir=OUT.parent)
            os.close(fd)
            try:
                frame.to_parquet(name, index=False, compression="zstd")
                measurements.append({"sha256": sha256(Path(name)), "bytes": os.path.getsize(name)})
            finally:
                os.unlink(name)
        results.append({"date": target, "stocks": len(frame),
                        "ready": int((frame["quality"] == "READY").sum()),
                        "sigma20_prior_quartile_edges": sigma_edges,
                        "risk_distribution_by_market_and_prior_sigma": risk_distribution,
                        "latest_adj_ohlc_mismatch": mismatches if target == DATES[-1] else None,
                        "measurements": measurements,
                        "repeat_identical": measurements[0] == measurements[1]})
    result = {"stage_contract": "P12-02_THREE_DAY_FACTOR_REPLAY_V1",
              "captured_at_utc": datetime.now(timezone.utc).isoformat(),
              "consulted_spec_sha256": sha256(SPEC),
              "input_identity": {"adjusted_daily_sha256": sha256(PARQUET),
                                 "current_gbbq_sha256": sha256(GBBQ)},
              "history_basis": "RECONSTRUCTED_CURRENT_SOURCE",
              "dates": results, "temporary_shards_removed": True,
              "acceptance_result": "DEGRADED_PASS" if all(
                  x["stocks"] == 6182 and x["repeat_identical"] and
                  (x["latest_adj_ohlc_mismatch"] in (None, 0)) for x in results) else "BLOCKED",
              "acceptance_scope": "Three-date full-stock factor replay and temporary shard repeatability; historic PIT and publication excluded",
              "next_stage": "P12-02_FACTOR_V3_3_CONTINUE"}
    fd, name = tempfile.mkstemp(prefix="three_day_factor_", suffix=".tmp", dir=OUT.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, OUT)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    if result["acceptance_result"] == "BLOCKED":
        raise RuntimeError("Three-day replay failed")
    print(OUT)


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    main()
