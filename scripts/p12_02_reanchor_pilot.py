"""Read-only real XRXD cutoff-anchor comparison for frozen OHLC references."""

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
from workbench_analysis.today_research_factors_v3_3 import calculate_today_facts  # noqa: E402

PARQUET = ROOT / "data/normalized/adjusted_daily.parquet"
GBBQ = Path("D:/new_tdx/T0002/hq_cache/gbbq")
OUT = ROOT / "reports/p12_02/reanchor_pilot.json"
CASES = (
    ("SZ.000001", "2026-06-11", "2026-06-30"),
    ("SZ.000009", "2026-08-26", "2026-09-14"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    symbols = {case[0] for case in CASES}
    records = defaultdict(list)
    for item in read_gbbq(GBBQ):
        if item.category == 1 and item.security_id in symbols:
            records[item.security_id].append(xrxd_from_gbbq(item))
    with duckdb.connect(str(ROOT / "data/database/market_research.duckdb"), read_only=True) as con:
        cursor = con.execute("""
            SELECT security_id,date,raw_open,raw_high,raw_low,raw_close,
                   adj_open,adj_high,adj_low,adj_close,raw_amount,raw_volume,has_actual_bar
            FROM read_parquet(?) WHERE security_id IN (?,?) AND date BETWEEN '2026-01-01' AND '2026-09-14'
            ORDER BY security_id,date
        """, [str(PARQUET), *sorted(symbols)])
        columns = [item[0] for item in cursor.description]
        rows = cursor.fetchall()
        sessions = [row[0].isoformat() for row in con.execute("""
            SELECT DISTINCT date FROM read_parquet(?)
            WHERE date BETWEEN '2026-01-01' AND '2026-09-14' ORDER BY date
        """, [str(PARQUET)]).fetchall()]
    by_symbol = defaultdict(dict)
    for row in rows:
        item = dict(zip(columns, row))
        by_symbol[item["security_id"]][item["date"].isoformat()] = item
    cases = []
    for sid, reference, target in CASES:
        first_dates = [int(day.replace("-", "")) for day in by_symbol[sid] if day <= reference]
        target_dates = [int(day.replace("-", "")) for day in by_symbol[sid] if day <= target]
        first_cutoff = int(reference.replace("-", ""))
        target_cutoff = int(target.replace("-", ""))
        seed_factor = build_affine_factors(first_dates, records[sid])[first_cutoff]
        target_factors = build_affine_factors(target_dates, records[sid])
        target_factor = target_factors[first_cutoff]
        raw_reference = by_symbol[sid][reference]["raw_high"]
        frozen_at_reference = float(seed_factor.qfq_price(raw_reference))
        reanchored_reference = float(target_factor.qfq_price(raw_reference))
        current_parquet_reference = float(by_symbol[sid][reference]["adj_high"])
        if not by_symbol[sid][reference]["has_actual_bar"] or not by_symbol[sid][target]["has_actual_bar"]:
            raise RuntimeError(f"Actual source bar missing: {sid}")
        window_dates = sessions[sessions.index(target) - 21:sessions.index(target) + 1]
        window = []
        mismatches = []
        for j, session in enumerate(window_dates):
            source = by_symbol[sid].get(session)
            if source is None or not source["has_actual_bar"]:
                window.append({"date": session, "session_index": j,
                               "anchor_cutoff": target, "price_basis": "TDX_NATIVE_AFFINE_QFQ",
                               "has_actual_bar": False})
                continue
            factor = target_factors[int(session.replace("-", ""))]
            anchored = {field: float(factor.qfq_price(source[f"raw_{field}"]))
                        for field in ("open", "high", "low", "close")}
            for field, value in anchored.items():
                if value != float(source[f"adj_{field}"]):
                    mismatches.append(f"{session}:{field}")
            window.append({"date": session, "session_index": j,
                           "anchor_cutoff": target, "price_basis": "TDX_NATIVE_AFFINE_QFQ",
                           "has_actual_bar": True, "is_synthetic_fill": False,
                           **anchored, "raw_open": float(source["raw_open"]),
                           "raw_close": float(source["raw_close"]),
                           "amount": float(source["raw_amount"]),
                           "volume": float(source["raw_volume"])})
        facts = calculate_today_facts(window)
        cases.append({
            "security_id": sid, "reference_date": reference, "target_cutoff": target,
            "raw_reference_high": float(raw_reference),
            "frozen_reference_high_at_reference_anchor": frozen_at_reference,
            "reference_high_reanchored_to_target": reanchored_reference,
            "current_parquet_reference_high": current_parquet_reference,
            "anchor_difference": round(reanchored_reference - frozen_at_reference, 4),
            "target_adj_close": float(target_factors[target_cutoff].qfq_price(by_symbol[sid][target]["raw_close"])),
            "parquet_target_adj_close": float(by_symbol[sid][target]["adj_close"]),
            "window_sessions": len(window),
            "window_actual_bars": sum(item["has_actual_bar"] for item in window),
            "window_adjusted_ohlc_mismatch_count": len(mismatches),
            "window_factor_phh20": facts["phh20"],
            "window_factor_amr20": facts["amr20_mean_prior"],
            "historical_signal_status": "NOT_REEVALUATED_IN_THIS_PRICE_ONLY_PILOT",
            "source_availability": "CURRENT_GBBQ_SOURCE_ONLY_RECONSTRUCTED",
        })
    result = {
        "stage_contract": "P12-02_REANCHOR_PILOT_V1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "consulted_spec_sha256": sha256(ROOT / "docs/V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md"),
        "input_identity": {"adjusted_daily_sha256": sha256(PARQUET),
                           "current_gbbq_sha256": sha256(GBBQ)},
        "cases": cases,
        "acceptance_result": "DEGRADED_PASS",
        "acceptance_scope": "Real source reference-price reanchor at two XRXD boundaries; historical source availability not proven",
        "next_stage": "P12-02_FACTOR_V3_3_CONTINUE",
    }
    if any(case["anchor_difference"] == 0 or case["window_sessions"] != 22 or
           case["window_actual_bars"] != 22 or case["window_adjusted_ohlc_mismatch_count"] != 0 or
           case["target_adj_close"] != case["parquet_target_adj_close"] or
           case["reference_high_reanchored_to_target"] != case["current_parquet_reference_high"]
           for case in cases):
        result["acceptance_result"] = "BLOCKED"
        result["next_stage"] = "P12-02_REANCHOR_REPAIR"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="reanchor_pilot.", suffix=".tmp", dir=OUT.parent)
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
