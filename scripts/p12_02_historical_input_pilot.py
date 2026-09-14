"""Read-only three-date historical input pilot; never publishes research rows."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy
import pandas

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from adjustment.tdx_adjustment import build_affine_factors, xrxd_from_gbbq  # noqa: E402
from tdx.gbbq_reader import read_gbbq  # noqa: E402
from workbench_analysis.pullback_episode_v1 import CONTRACT_ID as EPISODE_CONTRACT  # noqa: E402
from workbench_analysis.today_research_factors_v3_3 import (  # noqa: E402
    CONTRACT_ID as FACTOR_CONTRACT,
    calculate_today_facts,
)

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
        baseline = json.loads((ROOT / "reports/p12_01/baseline_v2.json").read_text(encoding="utf-8"))
        bound_run_id = baseline["input_identity"]["run_id"]
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
        current_window = sessions[-22:]
        current_rows = con.execute("""
            SELECT security_id,date,adj_open,adj_high,adj_low,adj_close,
                   raw_open,raw_close,raw_amount,raw_volume,has_actual_bar,is_synthetic_fill
            FROM read_parquet(?) WHERE date BETWEEN ? AND ?
            ORDER BY security_id,date
        """, [str(PARQUET), current_window[0], current_window[-1]]).fetchall()
        p05_rows = con.execute("""
            SELECT security_id,bias20,sigma20,extension_z20,dist_high20
            FROM research_stock_states WHERE run_id=?
        """, [bound_run_id]).fetchall()

    by_symbol = defaultdict(dict)
    master_index = {day: index for index, day in enumerate(sessions)}
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
    factor_examples = []
    for sid in SYMBOLS:
        for cutoff in DATES:
            available = [d for d in by_symbol[sid] if d <= cutoff]
            if not available:
                raise RuntimeError(f"Missing sample: {sid} {cutoff}")
            integers = [int(d.replace("-", "")) for d in sorted(available)]
            factors = build_affine_factors(integers, [e for e in events[sid] if e.ex_day <= int(cutoff.replace("-", ""))])
            full_source_factors = build_affine_factors(integers, events[sid])
            row = by_symbol[sid][cutoff]
            cutoff_close = float(factors[int(cutoff.replace("-", ""))].qfq_price(row[5]))
            future_events_ignored = all(
                factors[d].qfq_mul == full_source_factors[d].qfq_mul
                and factors[d].qfq_add == full_source_factors[d].qfq_add for d in integers
            )
            if not future_events_ignored:
                raise RuntimeError(f"Future event leaked into cutoff adjustment: {sid} {cutoff}")
            samples.append({
                "security_id": sid, "cutoff": cutoff,
                "raw_close": float(row[5]), "latest_parquet_adj_close": float(row[6]),
                "recomputed_cutoff_adj_close": cutoff_close,
                "latest_minus_cutoff_adj_close": round(float(row[6]) - cutoff_close, 4),
                "effective_xrxd_event_count_to_cutoff": sum(e.ex_day <= int(cutoff.replace("-", "")) for e in events[sid]),
                "later_xrxd_event_count_ignored": sum(e.ex_day > int(cutoff.replace("-", "")) for e in events[sid]),
                "future_event_exclusion_verified": future_events_ignored,
                "source_availability": "CURRENT_GBBQ_SOURCE_ONLY_RECONSTRUCTED",
            })
            target_index = sessions.index(cutoff)
            window_dates = sessions[target_index - 21:target_index + 1]
            fact_input = []
            for session in window_dates:
                source = by_symbol[sid].get(session)
                if source is None or not source[9]:
                    fact_input.append({"date": session, "price_basis": "TDX_NATIVE_AFFINE_QFQ",
                                       "anchor_cutoff": cutoff, "session_index": master_index[session],
                                       "has_actual_bar": False})
                    continue
                factor = factors[int(session.replace("-", ""))]
                fact_input.append({
                    "date": session, "price_basis": "TDX_NATIVE_AFFINE_QFQ",
                    "anchor_cutoff": cutoff, "session_index": master_index[session],
                    "has_actual_bar": True, "is_synthetic_fill": False,
                    "open": float(factor.qfq_price(source[2])),
                    "high": float(factor.qfq_price(source[3])),
                    "low": float(factor.qfq_price(source[4])),
                    "close": float(factor.qfq_price(source[5])),
                    "raw_open": float(source[2]), "raw_close": float(source[5]),
                    "amount": float(source[7]), "volume": float(source[8]),
                })
            facts = calculate_today_facts(fact_input)
            complete = len(fact_input) == 22 and all(row.get("has_actual_bar") for row in fact_input)
            manual_phc = max(row["close"] for row in fact_input[1:-1]) if complete else None
            manual_phh = max(row["high"] for row in fact_input[1:-1]) if complete else None
            manual_amr = fact_input[-1]["amount"] / (sum(row["amount"] for row in fact_input[1:-1]) / 20) if complete else None
            if complete and (facts["phc20"] != manual_phc or facts["phh20"] != manual_phh or
                             abs(facts["amr20_mean_prior"] - manual_amr) > 1e-12):
                raise RuntimeError(f"Manual factor mismatch: {sid} {cutoff}")
            factor_examples.append({"security_id": sid, "cutoff": cutoff,
                                    "window_sessions": len(fact_input), "window_complete": complete,
                                    "phc20": facts["phc20"], "phh20": facts["phh20"],
                                    "amr20_mean_prior": facts["amr20_mean_prior"],
                                    "sigma20_v3": facts["sigma20_v3"],
                                    "vol20_sample": facts["vol20_sample"],
                                    "severe_drop": facts["severe_drop"],
                                    "manual_phc20": manual_phc, "manual_phh20": manual_phh,
                                    "manual_amr20_mean_prior": manual_amr})
    current_by_symbol = defaultdict(dict)
    for row in current_rows:
        current_by_symbol[row[0]][row[1].isoformat()] = row
    current_distribution = {"stocks": 0, "ready": 0, "phc20_nonnull": 0,
                            "amr20_nonnull": 0, "sigma20_prior_nonnull": 0,
                            "severe_drop_true": 0, "severe_drop_false": 0,
                            "severe_drop_unknown": 0, "first_day_damage_true": 0,
                            "first_day_damage_unknown": 0}
    current_factor_rows = []
    for sid, records in current_by_symbol.items():
        window = []
        for session in current_window:
            source = records.get(session)
            if source is None or not source[10]:
                window.append({"date": session, "price_basis": "TDX_NATIVE_AFFINE_QFQ",
                               "anchor_cutoff": current_window[-1], "session_index": master_index[session],
                               "has_actual_bar": False})
            else:
                window.append({"date": session, "price_basis": "TDX_NATIVE_AFFINE_QFQ",
                               "anchor_cutoff": current_window[-1], "session_index": master_index[session],
                               "has_actual_bar": True, "is_synthetic_fill": bool(source[11]),
                               "open": source[2], "high": source[3], "low": source[4],
                               "close": source[5], "raw_open": source[6],
                               "raw_close": source[7], "amount": source[8], "volume": source[9]})
        facts = calculate_today_facts(window)
        current_factor_rows.append({"security_id": sid, **facts})
        current_distribution["stocks"] += 1
        current_distribution["ready"] += facts["quality"] == "READY"
        current_distribution["phc20_nonnull"] += facts["phc20"] is not None
        current_distribution["amr20_nonnull"] += facts["amr20_mean_prior"] is not None
        current_distribution["sigma20_prior_nonnull"] += facts["sigma20_prior"] is not None
        current_distribution[f"severe_drop_{'unknown' if facts['severe_drop'] is None else str(facts['severe_drop']).lower()}"] += 1
        current_distribution["first_day_damage_true"] += facts["first_day_damage"] is True
        current_distribution["first_day_damage_unknown"] += facts["first_day_damage"] is None
    p05 = {row[0]: row[1:] for row in p05_rows}
    comparisons = {}
    for field, column in (("bias20", 0), ("sigma20_v3", 1),
                          ("extension_z20", 2), ("break_margin_close20", 3)):
        counts = {"both_nonnull": 0, "numeric_mismatch": 0,
                  "candidate_only": 0, "p05_only": 0}
        for row in current_factor_rows:
            new = row[field]
            old = p05[row["security_id"]][column]
            if new is not None and old is not None:
                counts["both_nonnull"] += 1
                counts["numeric_mismatch"] += abs(new - old) > 1e-10
            elif new is not None:
                counts["candidate_only"] += 1
            elif old is not None:
                counts["p05_only"] += 1
        comparisons[field] = counts
    OUT.parent.mkdir(parents=True, exist_ok=True)
    factor_fd, factor_tmp = tempfile.mkstemp(prefix="factor_size_probe.", suffix=".parquet", dir=OUT.parent)
    os.close(factor_fd)
    try:
        pandas.DataFrame(current_factor_rows).to_parquet(factor_tmp, index=False, compression="zstd")
        factor_shard_bytes = os.path.getsize(factor_tmp)
    finally:
        os.unlink(factor_tmp)
    dependency_lock = {
        "scope": "P12_02_PILOT_PARTIAL",
        "factor_contract": FACTOR_CONTRACT,
        "episode_contract": EPISODE_CONTRACT,
        "spec_sha256": sha256(SPEC),
        "adjusted_daily_sha256": sha256(PARQUET),
        "gbbq_current_sha256": gbbq_sha,
        "source_hashes": {
            name: sha256(ROOT / name) for name in (
                "src/workbench_analysis/today_research_factors_v3_3.py",
                "src/workbench_analysis/pullback_episode_v1.py",
                "src/adjustment/tdx_adjustment.py",
                "src/tdx/gbbq_reader.py",
            )
        },
        "risk_parameters": {"drop_floor_pct": 0.04, "drop_cap_pct": 0.08, "drop_z": 2.0},
        "runtime": {"python": platform.python_version(), "duckdb": duckdb.__version__,
                    "numpy": numpy.__version__, "pandas": pandas.__version__},
        "historical_source_availability": "CURRENT_GBBQ_SOURCE_ONLY_RECONSTRUCTED",
    }
    lock_hash = hashlib.sha256(json.dumps(dependency_lock, sort_keys=True, separators=(",", ":"),
                                          ensure_ascii=False).encode("utf-8")).hexdigest()
    result = {
        "stage_contract": "P12-02_HISTORICAL_INPUT_PILOT_V1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "consulted_spec_sha256": sha256(SPEC),
        "dependency_lock_draft": dependency_lock,
        "dependency_lock_draft_sha256": lock_hash,
        "dependency_lock_status": "PILOT_ONLY_SOURCE_RECOVERY_AND_PRODUCTION_RUN_BINDING_PENDING",
        "factor_contract": {"contract_id": FACTOR_CONTRACT,
                            "implementation_sha256": sha256(ROOT / "src/workbench_analysis/today_research_factors_v3_3.py"),
                            "risk_parameters": {"drop_floor_pct": 0.04, "drop_cap_pct": 0.08, "drop_z": 2.0}},
        "episode_contract": {"contract_id": EPISODE_CONTRACT,
                             "implementation_sha256": sha256(ROOT / "src/workbench_analysis/pullback_episode_v1.py"),
                             "manual_counterexample_tests": "tests/upgrade_v3/test_p12_02_pullback_episode.py"},
        "input_identity": {"adjusted_daily_sha256": sha256(PARQUET), "gbbq_current_sha256": gbbq_sha,
                           "gbbq_path": str(GBBQ), "sample_symbols": SYMBOLS},
        "year_2026_available": {"sessions": full_year[0], "rows": full_year[1],
                                "first": full_year[2].isoformat(), "last": full_year[3].isoformat()},
        "date_coverage": date_rows, "cutoff_adjustment_samples": samples,
        "factor_examples": factor_examples,
        "current_factor_distribution": current_distribution,
        "current_p05_numeric_comparison": {"run_id": bound_run_id,
                                           "tolerance": 1e-10, "fields": comparisons},
        "resource_probe": {"single_day_6182_stock_factor_parquet_zstd_bytes": factor_shard_bytes,
                           "ephemeral_probe_removed": True,
                           "excludes_sector_roles_runs_evidence_and_source_history": True},
        "history_basis": "RECONSTRUCTED_CURRENT_SOURCE",
        "pit_member_status": "UNAVAILABLE",
        "storage_decision": "NO_170_DAY_MATERIALIZATION_BEFORE_FACTOR_AND_DEPENDENCY_LOCK_ACCEPTANCE",
        "acceptance_result": "DEGRADED_PASS",
        "acceptance_scope": "Three-date raw-input coverage, cutoff-adjustment and three candidate factor cross-checks; no historical PIT or complete P12-02 acceptance",
        "next_stage": "P12-02_FACTOR_V3_3_CONTINUE",
    }
    if (len(date_rows) != len(DATES)
            or any(x["raw_ohlc_order_errors"] for x in date_rows.values())
            or any(item["numeric_mismatch"] or item["candidate_only"] or item["p05_only"]
                   for item in comparisons.values())):
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
