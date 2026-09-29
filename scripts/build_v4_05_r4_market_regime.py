"""Fail closed on target path continuity while binding corrected R4 identities."""
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
from src.v4.factors.native import market_axis_primitives
from src.v4.market_regime_ui import project
from src.v4.replay_r4_identity import digest

TARGET = "2026-09-28"
OUT = ROOT / "reports/v4_05/V4_05_R4_MARKET_REGIME.json"


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> dict:
    ref_path = ROOT / "reports/v4_05/V4_05_R4_MARKET_REFERENCE.json"
    identity_path = ROOT / "reports/v4_05/V4_05_R4_MARKET_SNAPSHOT_IDENTITY.json"
    snapshot_path = ROOT / "reports/v4_05/V4_05_R4_TARGET_MARKET_SNAPSHOT.json"
    factor_receipt_path = ROOT / "reports/v4_05/V4_05_R4_FULL_SCOPE_FACTORS_RECEIPT.json"
    ref = json.loads(ref_path.read_text(encoding="utf-8"))
    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    factors_receipt = json.loads(factor_receipt_path.read_text(encoding="utf-8"))
    calendar_receipt = json.loads((ROOT / "reports/v4_05/V4_05_R3_CALENDAR_RECEIPT.json").read_text(encoding="utf-8"))
    factors_path = ROOT / factors_receipt["artifact_path"]
    amounts = []
    with gzip.open(factors_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            item = row["fields"]["amount_ratio20"]
            if item["quality_state"] == "OBSERVED":
                amounts.append(item["value"])
    market_identity = {
        "trade_date": TARGET,
        "market_calendar_id": ref["market_calendar_id"],
        "market_snapshot_id": identity["target_market_snapshot_id"],
        "adjustment_basis_id": identity["target_adjustment_basis_id"],
        "input_source_digest": digest({"market_reference": sha(ref_path), "snapshot": sha(snapshot_path),
                                        "factor_file": sha(factors_path), "candidate": factors_receipt}),
        "path_series_identity": "V4_03_MARKET_REFERENCE_PATH_V1:UNKNOWN_SUFFIX_UNTIL_NEW_SERIES_VERSION",
        "parameter_set_id": "V4_03_CORE_FACTOR_PARAMETER_SET_V1",
    }
    axes = market_axis_primitives(breadth=None,
                                  participation=statistics.median(amounts) if amounts else None,
                                  limit_coverage=None, stress_ratio=None, prior_stress_ratio=None,
                                  **{k: market_identity[k] for k in ("trade_date", "market_calendar_id", "market_snapshot_id", "adjustment_basis_id", "input_source_digest")})
    # No accepted target path row or approved series migration exists; the target trend must stay UNKNOWN.
    trend = {"contract_id": "MARKET_REGIME_TREND_WEAK_ERRATUM_V1", "contract_version": "1.0.0",
             "quality_state": "UNKNOWN", "trend_axis": "UNKNOWN",
             "unknown_reason": "PATH_CONTINUATION_UNPROVEN_UNTIL_NEW_SERIES_VERSION",
             "identity": market_identity,
             "input_digest": digest({"continuation": "OPTION_C_FAIL_CLOSED", "reference_1": ref["horizons"]["1"]["output_digest"]})}
    trend["output_digest"] = digest(trend)
    target_row = {"trade_date": TARGET, "breadth_axis": axes["breadth_axis"],
                  "participation_axis": axes["participation_axis"], "stress_level": axes["stress_level"],
                  "stress_change": axes["stress_change"], "trend_axis": "UNKNOWN",
                  "output_digest": digest([axes["output_digest"], trend["output_digest"]])}
    old_regime_path = ROOT / "reports/v4_03/staging/V4_03_MARKET_REGIME_NATIVE_CANDIDATE_R3.jsonl.gz"
    historical = [json.loads(line) for line in gzip.open(old_regime_path, "rt", encoding="utf-8")]
    if historical[-1]["trade_date"] != "2026-09-24":
        raise ValueError("accepted candidate regime cutoff changed")
    projection = project([*historical, target_row])[TARGET]
    result = {"contract_id": "V4_05_R4_MARKET_REGIME_REPLAY_V1", "status": "DEGRADED_PASS",
              "target_trade_date": TARGET, "target_row": target_row, "axes": axes, "trend": trend,
              "regime_ui": {"value": projection.value, "unknown_reason": projection.unknown_reason,
                            "evidence": projection.evidence}, "identity": market_identity,
              "market_snapshot_artifact_sha256": sha(snapshot_path), "target_amount_evaluable_count": len(amounts),
              "target_limit_status": "UNKNOWN_NO_ACCEPTED_SEP28_PRICE_LIMIT_FACTS",
              "path_continuation_policy": "OPTION_C_FAIL_CLOSED", "target_path_row_published": False,
              "target_coordinate_diagnostic_is_not_accepted_path": True,
              "formal_publication_at": "2026-09-29T06:53:52+00:00", "max_source_trade_date": 20260928,
              "historical_as_recorded_claim": False}
    temp = OUT.with_suffix(OUT.suffix + ".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, OUT)
    return result


if __name__ == "__main__":
    result = main()
    print(json.dumps({"status": result["status"], "trend_axis": result["target_row"]["trend_axis"],
                      "participation_axis": result["target_row"]["participation_axis"],
                      "regime_ui": result["regime_ui"]["value"]}, ensure_ascii=False))
