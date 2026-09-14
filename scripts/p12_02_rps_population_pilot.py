"""Read-only RPS5 population comparability probe for three 2026 date pairs."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.today_research_factors_v3_3 import comparable_rps_delta  # noqa: E402
PARQUET = ROOT / "data/normalized/adjusted_daily.parquet"
OUT = ROOT / "reports/p12_02/rps_population_pilot.json"
TARGETS = ("2026-03-31", "2026-06-30", "2026-09-14")
SAMPLES = ("SZ.000001", "SZ.000009")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    baseline = json.loads((ROOT / "reports/p12_01/baseline_v2.json").read_text(encoding="utf-8"))
    strength_slice = next(
        item[2] for item in baseline["input_identity"]["dependency_bindings"]["analysis_slices"]
        if item[0] == "strength" and item[1] == "2026-09-14"
    )
    with duckdb.connect(str(ROOT / "data/database/market_research.duckdb"), read_only=True) as con:
        dates = [row[0].isoformat() for row in con.execute("""
            SELECT DISTINCT date FROM read_parquet(?)
            WHERE date BETWEEN '2026-01-01' AND '2026-09-14' ORDER BY date
        """, [str(PARQUET)]).fetchall()]
        pairs = [(target, dates[dates.index(target) - 3]) for target in TARGETS]
        selected = sorted({day for pair in pairs for day in pair})
        # Every stock has a master-session slot. Six actual closes are needed
        # for RET5; missing rows remain missing rather than shifting the window.
        result_rows = con.execute("""
            WITH indexed AS (
                SELECT security_id,date,adj_close,has_actual_bar,universe_status,
                       dense_rank() OVER (ORDER BY date) AS session_index
                FROM read_parquet(?)
                WHERE date BETWEEN '2025-12-01' AND '2026-09-14'
            ), bars AS (
                SELECT security_id,date,adj_close,has_actual_bar,universe_status,session_index,
                       lag(adj_close,5) OVER w AS prior5,
                       lag(session_index,5) OVER w AS prior_session_index,
                       sum(CASE WHEN has_actual_bar AND adj_close>0 THEN 1 ELSE 0 END)
                           OVER (PARTITION BY security_id ORDER BY date ROWS BETWEEN 5 PRECEDING AND CURRENT ROW) AS valid6
                FROM indexed
                WINDOW w AS (PARTITION BY security_id ORDER BY date)
            ), eligible AS (
                SELECT security_id,date,adj_close/prior5-1 AS ret5
                FROM bars WHERE date IN (?,?,?,?,?,?)
                  AND universe_status='IN_NORMAL_UNIVERSE'
                  AND has_actual_bar AND valid6=6 AND prior5>0
                  AND session_index-prior_session_index=5
            ), ranked AS (
                SELECT security_id,date,ret5,
                       rank() OVER (PARTITION BY date ORDER BY ret5) AS first_rank,
                       count(*) OVER (PARTITION BY date,ret5) AS tie_count,
                       count(*) OVER (PARTITION BY date) AS n
                FROM eligible
            )
            SELECT security_id,date,ret5,(first_rank+(tie_count-1)/2.0)/n AS rps5,n
            FROM ranked ORDER BY date,security_id
        """, [str(PARQUET), *selected]).fetchall()
        official = con.execute("""
            SELECT security_id,ret5,rps5,rps_valid_universe_count5
            FROM strength_result_daily WHERE slice_id=?
        """, [strength_slice]).fetchall()

    by_date = {day: {} for day in selected}
    for sid, day, ret5, rps5, n in result_rows:
        by_date[day.isoformat()][sid] = {"ret5": ret5, "rps5": rps5, "n": n}
    latest = by_date["2026-09-14"]
    official_nonnull = {sid: (ret5, rps5, n) for sid, ret5, rps5, n in official if rps5 is not None}
    mismatches = [sid for sid, values in latest.items()
                  if sid not in official_nonnull
                  or abs(values["rps5"] - official_nonnull[sid][1]) > 1e-12
                  or abs(values["ret5"] - official_nonnull[sid][0]) > 1e-12
                  or values["n"] != official_nonnull[sid][2]]
    population_mismatch = len(set(latest) ^ set(official_nonnull))
    pairs_out = []
    for today, prior in pairs:
        current = set(by_date[today])
        previous = set(by_date[prior])
        union = current | previous
        nmax = max(len(current), len(previous))
        size_change = abs(len(current) - len(previous)) / nmax if nmax else None
        jaccard = len(current & previous) / len(union) if union else None
        population_comparable = bool(nmax >= 100 and size_change <= 0.10 and jaccard >= 0.90)
        samples = {}
        for sid in SAMPLES:
            current_row = by_date[today].get(sid)
            prior_row = by_date[prior].get(sid)
            gated = comparable_rps_delta(
                current_row["rps5"] if current_row else None,
                prior_row["rps5"] if prior_row else None,
                current, previous,
                today_basis="LATEST_CUTOFF_DIAGNOSTIC",
                prior_basis="LATEST_CUTOFF_DIAGNOSTIC",
            )
            samples[sid] = {"today_rps5": current_row["rps5"] if current_row else None,
                            "prior_rps5": prior_row["rps5"] if prior_row else None,
                            "diagnostic_delta": gated["diagnostic_delta"],
                            "formal_delta": gated["delta"]}
        pairs_out.append({"today": today, "prior_t_minus_3": prior,
                          "today_valid_n": len(current), "prior_valid_n": len(previous),
                          "intersection": len(current & previous), "union": len(union),
                          "size_change": size_change, "jaccard": jaccard,
                          "population_comparable": population_comparable,
                          "formal_comparable": False,
                          "samples": samples})
    result = {
        "stage_contract": "P12-02_RPS_POPULATION_PILOT_V1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "consulted_spec_sha256": sha256(ROOT / "docs/V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md"),
        "input_identity": {"adjusted_daily_sha256": sha256(PARQUET),
                           "basis": "LATEST_CUTOFF_QFQ_AND_CURRENT_CUTOFF_UNIVERSE",
                           "required_history_basis": "PIT_ASOF_FOR_FORMAL_DELTA"},
        "pairs": pairs_out,
        "official_latest_strength_check": {"slice_id": strength_slice,
                                           "diagnostic_valid_rows": len(latest),
                                           "official_valid_rows": len(official_nonnull),
                                           "population_mismatch": population_mismatch,
                                           "value_mismatch": len(mismatches),
                                           "tolerance": 1e-12},
        "acceptance_result": "DEGRADED_PASS",
        "acceptance_scope": "Population arithmetic and exact calendar t-3 diagnostic only; formal RPS delta unavailable",
        "next_stage": "P12-02_FACTOR_V3_3_CONTINUE",
    }
    if population_mismatch or mismatches:
        result["acceptance_result"] = "BLOCKED"
        result["next_stage"] = "P12-02_RPS_POPULATION_REPAIR"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="rps_population_pilot.", suffix=".tmp", dir=OUT.parent)
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
