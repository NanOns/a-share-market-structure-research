"""Assemble capability-scoped R3 stage outcome after executed replay gates."""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/v4_05"
TARGET = "2026-09-28"


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def write(name, value):
    path = OUT / name
    temp = path.with_suffix(".tmp")
    temp.write_bytes((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
    os.replace(temp, path)


def row(scope, status, entities, fields, reasons, evidence):
    return {"capability_scope": scope, "status": status, "affected_dates": [TARGET] if not scope.startswith("HISTORICAL") else ["pre-project historical sessions"],
            "affected_entities": entities, "affected_fields": fields, "reasons": reasons, "evidence": evidence}


def main():
    daily = read("V4_05_R3_DAILY_HISTORY_RECEIPT.json")
    period = read("V4_05_R3_PERIOD_ASOF.json")
    factor = read("V4_05_R3_FULL_SCOPE_FACTORS_RECEIPT.json")
    market = read("V4_05_R3_MARKET_REFERENCE.json")
    regime = read("V4_05_R3_MARKET_REGIME.json")
    profile = read("V4_05_R3_CORE_PROFILE_REPLAY.json")
    deterministic = read("V4_05_R3_DETERMINISM.json")
    revision = read("V4_05_R3_REVISION_IDEMPOTENCY.json")
    temporal = read("V4_05_R3_TEMPORAL_LEAKAGE.json")
    if (daily["counts"]["entities"] != 5222 or profile["row_count"] != 5222 or
            deterministic["status"] != "PASS" or temporal["status"] != "PASS" or
            revision["status"] != "PASS_CANDIDATE_IDENTITY"):
        raise ValueError("R3 replay execution gates incomplete")
    if market["status"] != "PASS" or regime["regime_ui"]["value"] != "UNKNOWN":
        raise ValueError("market scope status mismatch")
    capabilities = [
        row("CURRENT_FORWARD_ADJUSTED_PRICE", "FULL_PASS", 5222, ["T0 QFQ OHLC"], [], ["reports/v4_05/V4_05_R2_ADJUSTMENT_REPRODUCIBILITY.json", "V4_05_R3_DAILY_HISTORY_RECEIPT.json"]),
        row("WEEKLY_PERIOD", "DEGRADED_PASS", 5222, ["RAW", "QFQ", "CLOSED_ONLY", "AS_OF_PARTIAL"], ["Field-local UNKNOWN for no-bar, unsupported adjustment or unexplained historical gap"], ["V4_05_R3_PERIOD_ASOF.json", "V4_05_R3_TEMPORAL_LEAKAGE.json"]),
        row("MONTHLY_PERIOD", "DEGRADED_PASS", 5222, ["RAW", "QFQ", "CLOSED_ONLY", "AS_OF_PARTIAL"], ["Field-local UNKNOWN for no-bar, unsupported adjustment or unexplained historical gap"], ["V4_05_R3_PERIOD_ASOF.json", "V4_05_R3_TEMPORAL_LEAKAGE.json"]),
        row("PURE_CORE_FACTORS", "DEGRADED_PASS", 5222, ["39 CORE_FACTOR_V1 fields", "8 relative fields"], ["Prior-RPS delta fields require first-forward bootstrap and remain UNKNOWN"], ["V4_05_R3_FACTOR_SOURCE_TIME.json", "V4_05_R3_FULL_SCOPE_FACTORS_RECEIPT.json"]),
        row("MARKET_REFERENCE", "FULL_PASS", 5222, ["equal-weight 1/3/5-session reference"], [], ["V4_05_R3_MARKET_REFERENCE.json"]),
        row("MARKET_REGIME", "DEGRADED_PASS", 5222, ["breadth_axis", "participation_axis", "stress_level", "stress_change", "trend_axis", "regime_ui"], ["No accepted Sep-28 price-limit facts for stress; breadth prior comparable set not materialized; UI UNKNOWN"], ["V4_05_R3_MARKET_REGIME.json"]),
        row("CURRENT_FORWARD_STOCK_CORE", "DEGRADED_PASS", 5222, ["V4-04 full-market Core Profile"], ["27 adjusted-unavailable identities retained; prior-RPS and market-regime dependent fields remain UNKNOWN"], ["V4_05_R3_CORE_PROFILE_REPLAY.json", "V4_05_R3_DETERMINISM.json", "V4_05_R3_REVISION_IDEMPOTENCY.json"]),
        row("HISTORICAL_AS_RECORDED_ADJUSTED_PRICE", "BLOCKED", "historical accepted universe", ["historical QFQ OHLC"], ["BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE"], ["data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json"]),
    ]
    gate = {"contract_id": "V4_05_R3_CAPABILITY_GATE_V1", "status": "V4_05_DATA_FACTOR_REPLAY_DEGRADED_PASS_CANDIDATE_R3",
            "target_trade_date": TARGET, "capabilities": capabilities,
            "data_factor_replay_pass": [{"alias": "DATA_FACTOR_REPLAY_PASS", "scope": "CURRENT_FORWARD_STOCK_CORE", "status": "DEGRADED_PASS", "evidence": "V4_05_R3_CORE_PROFILE_REPLAY.json"}],
            "historical_as_recorded_adjusted_price": "BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE", "external_acceptance": "PENDING",
            "next_stage": "INDEPENDENT_EXTERNAL_AUDIT_R3"}
    write("V4_05_R3_CAPABILITY_GATE.json", gate)
    print(gate["status"])


if __name__ == "__main__":
    main()
