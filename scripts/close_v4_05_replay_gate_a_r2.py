"""Record independently scoped R2 outcomes without promoting unbuilt capabilities."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/v4_05"
TARGET = "2026-09-28"
BLOCK = "TARGET_DATE_ACCEPTED_INPUT_SERIES_NOT_MATERIALIZED"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write(name: str, value: dict) -> None:
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def read(name: str) -> dict:
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def main() -> None:
    daily = read("V4_05_R2_DAILY_DETERMINISM.json")
    adjustment = read("V4_05_R2_ADJUSTMENT_REPRODUCIBILITY.json")
    if daily["status"] != "PASS" or adjustment["current_forward_status"] != "PASS":
        raise ValueError("forward daily gate not passed")
    if daily["first_digest"] != daily["second_digest"]:
        raise ValueError("daily drift")
    blocked = {"status": "BLOCKED", "reason": BLOCK, "target_trade_date": TARGET, "no_pass_claim": True}
    for name, gate, detail in (
        ("V4_05_R2_PERIOD_ASOF.json", "G05", "Target-date weekly and monthly accepted-input periods have not been rebuilt; semantic fixtures alone cannot prove production replay."),
        ("V4_05_R2_FACTOR_SOURCE_TIME.json", "G06", "Sep-28 Pure-Core factors and per-provider source timestamps have not been rebuilt; Sep-24 factors are ineligible."),
        ("V4_05_R2_MARKET_REFERENCE_REGIME.json", "B9", "Sep-28 benchmark/index inputs and market regime have not been rebuilt; Sep-24 regime is ineligible."),
        ("V4_05_R2_CORE_PROFILE_REPLAY.json", "G07", "Sep-28 full-market Core Profile has not been rebuilt; 27 upstream adjusted-unavailable identities must remain UNKNOWN."),
        ("V4_05_R2_REVISION_IDEMPOTENCY.json", "G08", "Daily source rebuild is deterministic, but no Sep-28 factor/profile publication revision exists for idempotency verification."),
        ("V4_05_R2_TEMPORAL_LEAKAGE.json", "TEMPORAL", "Daily maximum source date passed; period, factor, reference and profile negative cases remain unexecuted."),
    ):
        write(name, {"contract_id": name.removesuffix(".json").upper(), "gate": gate, **blocked, "detail": detail, "daily_evidence": "V4_05_R2_DAILY_DETERMINISM.json"})
    cases = {name: {"status": status, "evidence": evidence} for name, status, evidence in (
        ("sep28_current_forward", "PASS_DAILY_ONLY", "V4_05_R2_DAILY_DETERMINISM.json"),
        ("monday_weekly_asof", "BLOCKED_UNEXECUTED", "V4_05_R2_PERIOD_ASOF.json"),
        ("incomplete_month", "BLOCKED_UNEXECUTED", "V4_05_R2_PERIOD_ASOF.json"),
        ("no_t0_bar", "PASS_QUALITY_PROPAGATION", "V4_05_R2_ADJUSTMENT_REPRODUCIBILITY.json"),
        ("unsupported_adjustment", "PASS_QUALITY_PROPAGATION", "V4_05_R2_ADJUSTMENT_REPRODUCIBILITY.json"),
        ("code_change_identity", "PASS_UPSTREAM_ACCEPTED_R3", "reports/v4_02/V4_02_GO_FORWARD_ADJUSTMENT_SAMPLES_R3.json"),
        ("synthetic_valid_new_listing", "PASS_UPSTREAM_ACCEPTED_R3", "tests/v4_02/test_go_forward_r3.py"),
        ("synthetic_unresolved_new_key", "PASS_UPSTREAM_ACCEPTED_R3", "tests/v4_02/test_go_forward_r3.py"),
        ("later_gbbq_revision", "BLOCKED_UNEXECUTED_R2", "V4_05_R2_TEMPORAL_LEAKAGE.json"),
        ("future_raw_row", "BLOCKED_UNEXECUTED_R2", "V4_05_R2_TEMPORAL_LEAKAGE.json"),
    )}
    write("V4_05_R2_REPLAY_CASE_MATRIX.json", {"contract_id": "V4_05_REPLAY_CASE_MATRIX_R2", "target_trade_date": TARGET, "cases": cases})
    scopes = {
        "CURRENT_FORWARD_STOCK_CORE": ("BLOCKED", ["weekly/monthly, factor and Core Profile replay not complete"], ["V4_05_R2_FACTOR_SOURCE_TIME.json", "V4_05_R2_CORE_PROFILE_REPLAY.json"]),
        "HISTORICAL_AS_RECORDED_ADJUSTED_PRICE": ("BLOCKED", ["BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE"], ["V4_05_R2_ADJUSTMENT_REPRODUCIBILITY.json"]),
        "WEEKLY_PERIOD": ("BLOCKED", [BLOCK], ["V4_05_R2_PERIOD_ASOF.json"]),
        "MONTHLY_PERIOD": ("BLOCKED", [BLOCK], ["V4_05_R2_PERIOD_ASOF.json"]),
        "MARKET_REFERENCE": ("BLOCKED", [BLOCK], ["V4_05_R2_MARKET_REFERENCE_REGIME.json"]),
        "MARKET_REGIME": ("BLOCKED", [BLOCK], ["V4_05_R2_MARKET_REFERENCE_REGIME.json"]),
        "CURRENT_FORWARD_ADJUSTED_PRICE": ("FULL_PASS", [], ["V4_05_R2_ADJUSTMENT_REPRODUCIBILITY.json", "V4_05_R2_DAILY_DETERMINISM.json"]),
    }
    matrix = []
    for scope, (status, reasons, evidence) in scopes.items():
        matrix.append({"capability_scope": scope, "status": status, "affected_dates": [TARGET] if not scope.startswith("HISTORICAL") else ["pre-project historical dates"], "affected_entities": 5222 if scope != "HISTORICAL_AS_RECORDED_ADJUSTED_PRICE" else "historical accepted universe", "affected_fields": ["qfq_ohlc"] if "ADJUSTED_PRICE" in scope else [scope], "reasons": reasons, "evidence": evidence})
    write("V4_05_R2_CAPABILITY_GATE.json", {"contract_id": "V4_05_CAPABILITY_GATE_R2", "status": "BLOCKED_REQUIRED_CURRENT_FORWARD_STOCK_CORE", "target_trade_date": TARGET, "capabilities": matrix, "data_factor_replay_pass": [], "historical_as_recorded_adjusted_price": "BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE", "next_stage": "COMPLETE_TARGET_DATE_SERIES_FACTORS_REFERENCE_AND_PROFILE_BEFORE_EXTERNAL_AUDIT"})
    head = ROOT / "data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json"
    global_head = json.loads((ROOT / "data/v4/V4_STAGE_ACCEPTED_HEAD.json").read_text(encoding="utf-8"))
    checks = {
        "promotion_pass": json.loads((ROOT / "reports/v4_joint/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json").read_text(encoding="utf-8"))["status"] == "PASS",
        "accepted_binding": global_head["v4_02_go_forward_pit_binding"]["sha256"] == sha(head),
        "daily_rebuild_twice": daily["status"] == "PASS" and daily["first_digest"] == daily["second_digest"],
        "source_date": daily["max_source_trade_date"] <= 20260928,
        "unknown_27": adjustment["unknown"] == 27,
        "historical_block": global_head["historical_as_recorded_adjusted_price"] == "BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE",
        "v4_08_block": global_head["v4_08_sector_entry"] == "BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION",
        "no_unqualified_replay_pass": not read("V4_05_R2_CAPABILITY_GATE.json")["data_factor_replay_pass"],
    }
    write("V4_05_R2_INDEPENDENT_POSTCHECK.json", {"contract_id": "V4_05_R2_INDEPENDENT_POSTCHECK", "status": "PASS_SCOPED_BLOCKED_CANDIDATE" if all(checks.values()) else "FAIL", "checks": checks, "unverified_gates": ["G05", "G06", "B9", "G07", "G08", "temporal negatives"]})
    if not all(checks.values()):
        raise ValueError("postcheck failed")
    print("PASS_SCOPED_BLOCKED_CANDIDATE")


if __name__ == "__main__":
    main()
