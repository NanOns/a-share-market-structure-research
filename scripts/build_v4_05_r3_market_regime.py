"""Rebuild Sep-28 market regime inputs, propagating unavailable target facts."""
from __future__ import annotations

from hashlib import sha256
import gzip
import json
import os
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.v4.factors.native import market_axis_primitives, market_trend_axis
from src.v4.market_regime_ui import project
from src.v4.replay_r3_guards import require_market_dates

OUT = ROOT / "reports/v4_05/V4_05_R3_MARKET_REGIME.json"
TARGET = "2026-09-28"


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def main():
    reference = json.loads((ROOT / "reports/v4_05/V4_05_R3_MARKET_REFERENCE.json").read_text(encoding="utf-8"))
    factors = json.loads((ROOT / "reports/v4_05/V4_05_R3_FACTOR_SOURCE_TIME.json").read_text(encoding="utf-8"))
    calendar = json.loads((ROOT / "reports/v4_05/V4_05_R3_CALENDAR_RECEIPT.json").read_text(encoding="utf-8"))
    old_path = ROOT / "reports/v4_03/staging/V4_03_MARKET_REFERENCE_PATH_CANDIDATE_R3.jsonl.gz"
    old_receipt = json.loads((ROOT / "reports/v4_03/V4_03_MARKET_REFERENCE_PATH_RECEIPT_R3.json").read_text(encoding="utf-8"))
    if sha256(old_path.read_bytes()).hexdigest() != old_receipt["output_sha256"]:
        raise ValueError("accepted market path changed")
    path = [json.loads(line) for line in gzip.open(old_path, "rt", encoding="utf-8")]
    if path[-1]["trade_date"] != "2026-09-24" or reference["horizons"]["1"]["start_session"] != "2026-09-24":
        raise ValueError("market path continuation mismatch")
    target_reference = reference["horizons"]["1"]
    level = path[-1]["level"] * (1 + target_reference["reference_return"]) if target_reference["reference_return"] is not None else None
    levels = [x["level"] for x in path[-24:]] + [level]
    ma20 = statistics.fmean(levels[-20:]) if all(x is not None for x in levels[-20:]) else None
    prior_ma20 = statistics.fmean(levels[-25:-5]) if all(x is not None for x in levels[-25:-5]) else None
    amounts = []
    with gzip.open(ROOT / factors["artifact_path"], "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            field = row["fields"]["amount_ratio20"]
            if field["quality_state"] == "OBSERVED":
                amounts.append(field["value"])
    identity = {"trade_date": TARGET, "market_calendar_id": f"V4_05_R3_CALENDAR:{calendar['calendar_bindings']['SSE']['sha256']}",
                "market_snapshot_id": target_reference["start_universe_snapshot_id"],
                "adjustment_basis_id": "T0_CURRENT_COORDINATE", "input_source_digest": digest([reference, factors["logical_digest"], old_receipt["output_sha256"]])}
    axes = market_axis_primitives(breadth=None, participation=statistics.median(amounts) if amounts else None,
                                  limit_coverage=None, stress_ratio=None, prior_stress_ratio=None, **identity)
    trend = market_trend_axis(index_close=level, index_ma20=ma20, index_ma20_t_minus_5=prior_ma20, **identity)
    target_row = {"trade_date": TARGET, "breadth_axis": axes["breadth_axis"], "participation_axis": axes["participation_axis"],
                  "stress_level": axes["stress_level"], "stress_change": axes["stress_change"], "trend_axis": trend["trend_axis"],
                  "output_digest": digest([axes["output_digest"], trend["output_digest"]])}
    require_market_dates([target_row])
    old_regime = ROOT / "reports/v4_03/staging/V4_03_MARKET_REGIME_NATIVE_CANDIDATE_R3.jsonl.gz"
    regime_rows = [json.loads(line) for line in gzip.open(old_regime, "rt", encoding="utf-8")]
    if regime_rows[-1]["trade_date"] != "2026-09-24":
        raise ValueError("accepted regime path cutoff mismatch")
    projection = project([*regime_rows, target_row])[TARGET]
    result = {"contract_id": "V4_05_R3_MARKET_REGIME_REPLAY_V1", "status": "DEGRADED_PASS_FIELD_LOCAL_UNKNOWN",
              "target_trade_date": TARGET, "target_row": target_row, "axes": axes, "trend": trend, "regime_ui": {"value": projection.value, "unknown_reason": projection.unknown_reason, "evidence": projection.evidence},
              "index_reference": {"path": old_path.relative_to(ROOT).as_posix(), "sha256": old_receipt["output_sha256"], "prior_level": path[-1]["level"], "target_daily_return": target_reference["reference_return"], "target_level": level, "ma20": ma20, "ma20_t_minus_5": prior_ma20},
              "target_index_input_source_digest": identity["input_source_digest"], "target_amount_evaluable_count": len(amounts),
              "target_limit_status": "UNKNOWN_NO_ACCEPTED_SEP28_PRICE_LIMIT_FACTS", "historical_as_recorded_claim": False,
              "max_source_trade_date": 20260928, "formal_publication_at": target_reference["formal_publication_at"]}
    tmp = OUT.with_suffix(".tmp")
    tmp.write_bytes((json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
    os.replace(tmp, OUT)
    print(json.dumps({"trend": trend["trend_axis"], "regime_ui": projection.value, "unknown_reason": projection.unknown_reason}))


if __name__ == "__main__":
    main()
