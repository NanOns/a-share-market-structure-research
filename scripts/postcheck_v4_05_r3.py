"""Independent byte and semantic audit of the R3 replay candidate."""
from __future__ import annotations

from collections import Counter
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/v4_05"
TARGET = 20260928


def sha(path):
    h = sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def scan(name, *, nested=False):
    receipt = read(name)
    path = ROOT / receipt["artifact_path"]
    if sha(path) != receipt["artifact_sha256"]:
        raise ValueError(f"artifact mismatch: {name}")
    logical = sha256()
    rows = 0
    target_rows = {}
    max_date = 0
    quality = Counter()
    with gzip.open(path, "rb") as stream:
        for line in stream:
            logical.update(line)
            value = json.loads(line)
            rows += 1
            maximum = value.get("max_source_trade_date", value.get("trade_date", 0))
            if isinstance(maximum, str):
                maximum = int(maximum.replace("-", ""))
            max_date = max(max_date, maximum)
            if value.get("trade_date") == TARGET or value.get("trade_date") == "2026-09-28":
                target_rows[value["security_id"]] = value
            if "profile_quality" in value:
                quality[value["profile_quality"]] += 1
            if nested and "fields" in value:
                for item in value["fields"].values():
                    if item["max_source_trade_date"] > TARGET or item["available_at"] > value["formal_publication_at"]:
                        raise ValueError("factor future input")
    if logical.hexdigest() != receipt["logical_digest"] or max_date > TARGET:
        raise ValueError(f"logical/source date mismatch: {name}")
    return rows, target_rows, quality


def main():
    checks = {}
    global_head = json.loads((ROOT / "data/v4/V4_STAGE_ACCEPTED_HEAD.json").read_text(encoding="utf-8"))
    accepted = ROOT / "data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json"
    checks["accepted_head_binding"] = global_head["v4_02_go_forward_pit_binding"]["sha256"] == sha(accepted)
    head = json.loads(accepted.read_text(encoding="utf-8"))
    for name in ("official_tdx_package", "gbbq_snapshot"):
        binding = head["evidence_bindings"][name]
        checks[f"source:{name}"] = sha(ROOT / binding["path"]) == binding["sha256"]
    calendar = read("V4_05_R3_CALENDAR_RECEIPT.json")
    for market, binding in calendar["calendar_bindings"].items():
        path = ROOT / binding["path"]
        sessions = json.loads(path.read_text(encoding="utf-8"))["session_dates"]
        checks[f"calendar:{market}"] = sha(path) == binding["sha256"] and "2026-09-28" in sessions and "2026-09-29" in sessions and "2026-09-30" in sessions
    daily_n, daily_t0, _ = scan("V4_05_R3_DAILY_HISTORY_RECEIPT.json")
    checks["daily_history"] = daily_n == read("V4_05_R3_DAILY_HISTORY_RECEIPT.json")["counts"]["rows"]
    candidate = {row["security_id"]: row for row in (json.loads(line) for line in gzip.open(ROOT / head["candidate_path"], "rt", encoding="utf-8"))}
    checks["target_row_set"] = set(candidate) == set(daily_t0) | {sid for sid, row in candidate.items() if row["adjusted_quality"] == "ADJUSTED_UNAVAILABLE_NO_T0_RAW"}
    checks["target_coordinates"] = all(daily_t0[sid]["qfq_ohlc"] == row["qfq_ohlc"] for sid, row in candidate.items() if row["adjusted_quality"] == "ADJUSTED_READY")
    checks["unknown_no_bar"] = sum(row["adjusted_quality"] == "ADJUSTED_UNAVAILABLE_NO_T0_RAW" for row in candidate.values()) == 12
    period_receipt = read("V4_05_R3_PERIOD_ASOF.json")
    period_path = ROOT / period_receipt["artifact_path"]
    checks["period_hash"] = sha(period_path) == period_receipt["artifact_sha256"]
    period_logical = sha256()
    current_period = Counter()
    with gzip.open(period_path, "rb") as stream:
        for line in stream:
            period_logical.update(line)
            row = json.loads(line)
            if row["max_source_trade_date"] > TARGET:
                raise ValueError("future period source")
            if row["period_key"] in ("2026-W40", "2026-09"):
                if row["period_view"] == "CLOSED_ONLY":
                    raise ValueError("future week/month marked closed")
                current_period[(row["period_type"], row["price_basis"])] += 1
    checks["period_digest"] = period_logical.hexdigest() == period_receipt["logical_digest"]
    checks["period_target_coverage"] = all(current_period[(kind, basis)] == 5222 for kind in ("WEEKLY", "MONTHLY") for basis in ("RAW", "QFQ"))
    factor_n, factor_rows, _ = scan("V4_05_R3_FULL_SCOPE_FACTORS_RECEIPT.json", nested=True)
    checks["factor_row_set"] = factor_n == 5222 and set(factor_rows) == set(candidate)
    checks["prior_rps_bootstrap"] = all(row["fields"]["rps5_delta1"]["unknown_reason"] == "BOOTSTRAP_INSUFFICIENT_FORWARD_HISTORY" for row in factor_rows.values())
    reference = read("V4_05_R3_MARKET_REFERENCE.json")
    checks["market_reference"] = all(row["quality_state"] == "OBSERVED" and row["end_session"] == "2026-09-28" and row["max_source_trade_date"] == TARGET for row in reference["horizons"].values())
    regime = read("V4_05_R3_MARKET_REGIME.json")
    checks["market_regime"] = regime["target_row"]["trade_date"] == "2026-09-28" and regime["regime_ui"]["value"] == "UNKNOWN" and regime["trend"]["quality_state"] == "OBSERVED"
    profile_n, profile_rows, profile_quality = scan("V4_05_R3_CORE_PROFILE_REPLAY.json")
    checks["profile_row_set"] = profile_n == 5222 and set(profile_rows) == set(candidate)
    checks["profile_quality"] = dict(profile_quality) == read("V4_05_R3_CORE_PROFILE_REPLAY.json")["quality_counts"]
    unavailable = {sid for sid, row in candidate.items() if row["adjusted_quality"] != "ADJUSTED_READY"}
    checks["unknown_propagation"] = len(unavailable) == 27 and all(profile_rows[sid]["states"]["trend_state"]["unknown_reason"] for sid in unavailable)
    deterministic = read("V4_05_R3_DETERMINISM.json")
    revision = read("V4_05_R3_REVISION_IDEMPOTENCY.json")
    temporal = read("V4_05_R3_TEMPORAL_LEAKAGE.json")
    checks["determinism"] = deterministic["first"] == deterministic["second"] and deterministic["first"]["artifact_sha256"] == read("V4_05_R3_CORE_PROFILE_REPLAY.json")["artifact_sha256"]
    checks["revision"] = revision["first_revision_id"] == revision["second_revision_id"] != revision["controlled_changed_source_revision_id"]
    checks["temporal"] = len(temporal["cases"]) == 8 and all(row["status"] == "PASS" for row in temporal["cases"].values())
    gate = read("V4_05_R3_CAPABILITY_GATE.json")
    scope = {row["capability_scope"]: row["status"] for row in gate["capabilities"]}
    checks["capability_scope"] = scope["CURRENT_FORWARD_STOCK_CORE"] == "DEGRADED_PASS" and scope["HISTORICAL_AS_RECORDED_ADJUSTED_PRICE"] == "BLOCKED"
    checks["historical_block"] = head["historical_as_recorded_adjusted_price"] == "BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE"
    checks["v4_08_block"] = global_head["v4_08_sector_entry"] == "BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION"
    receipt = {"contract_id": "V4_05_R3_INDEPENDENT_POSTCHECK_V1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "daily_rows_scanned": daily_n, "factor_rows_scanned": factor_n, "profile_rows_scanned": profile_n, "period_current_counts": {f"{a}:{b}": n for (a, b), n in current_period.items()}}
    path = OUT / "V4_05_R3_INDEPENDENT_POSTCHECK.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes((json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
    os.replace(tmp, path)
    if not all(checks.values()):
        raise ValueError({k: v for k, v in checks.items() if not v})
    print("PASS", len(checks))


if __name__ == "__main__":
    main()
