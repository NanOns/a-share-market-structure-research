"""Evidence gate for the bounded P12-02 factor stage; no production publication."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/p12_02/p12_02_stage_gate.json"
SPEC = ROOT / "docs/V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md"
SOURCES = ("src/workbench_analysis/today_research_factors_v3_3.py",
           "src/workbench_analysis/pullback_episode_v1.py",
           "src/workbench_analysis/stock_attention.py",
           "config/research_attention_v3.yaml")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load(name: str) -> dict:
    return json.loads((ROOT / "reports/p12_02" / f"{name}.json").read_text(encoding="utf-8"))


def head_sha(name: str) -> str | None:
    result = subprocess.run(["git", "show", f"HEAD:{name}"], cwd=ROOT,
                            capture_output=True, check=False)
    return hashlib.sha256(result.stdout).hexdigest() if result.returncode == 0 else None


def recoverable_from_head(name: str, expected: str) -> bool:
    if head_sha(name) == expected:
        return True
    # A checkout may apply Git's configured CRLF conversion to text files.
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "--", name],
                             cwd=ROOT, capture_output=True, check=False).returncode == 0
    clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", name],
                           cwd=ROOT, capture_output=True, check=False).returncode == 0
    return tracked and clean


def main() -> None:
    pilot = load("historical_input_pilot")
    reanchor = load("reanchor_pilot")
    rps = load("rps_population_pilot")
    static = load("remaining_history_validation")
    replay = load("three_day_factor_replay")
    lock = load("dependency_lock_probe")
    baseline = json.loads((ROOT / "reports/p12_01/baseline_v2.json").read_text(encoding="utf-8"))
    receipts = {name: item["acceptance_result"] for name, item in
                (("historical_input_pilot", pilot), ("reanchor_pilot", reanchor),
                 ("rps_population_pilot", rps), ("remaining_history_validation", static),
                 ("three_day_factor_replay", replay), ("dependency_lock_probe", lock))}
    source_hashes = {name: sha256(ROOT / name) for name in SOURCES}
    source_recoverable = {name: recoverable_from_head(name, value) for name, value in source_hashes.items()}
    replay_checks = all(
        day["stocks"] == 6182 and day["repeat_identical"] and
        sum(group["stocks"] for group in day["risk_distribution_by_market_and_prior_sigma"]) == 6182 and
        sum(group["severe_drop_true"] + group["severe_drop_false"] + group["severe_drop_unknown"]
            for group in day["risk_distribution_by_market_and_prior_sigma"]) == 6182 and
        day["latest_adj_ohlc_mismatch"] in (None, 0)
        for day in replay["dates"])
    latest = replay["dates"][-1]
    checks = {
        "phase0_terminal_full_pass": baseline["phase0"]["final_status"] == "FULL_PASS_TDX_NATIVE"
            and baseline["phase0"]["phase0_closed"] is True,
        "all_subreceipts_degraded_pass": all(value == "DEGRADED_PASS" for value in receipts.values()),
        "candidate_sources_recoverable_from_head": all(source_recoverable.values()),
        "pilot_lock_canonical_and_tamper_rejected": lock["canonical_matches"] and lock["tamper_rejected"],
        "three_day_full_stock_replay_and_group_counts": replay_checks,
        "latest_ready_count_agrees_with_input_pilot": latest["ready"] == pilot["current_factor_distribution"]["ready"],
        "no_historic_pit_claim": replay["history_basis"] == "RECONSTRUCTED_CURRENT_SOURCE"
            and not lock["historical_source_availability_proven"],
    }
    result = {
        "stage_contract": "P12-02_FACTOR_V3_3_ACCEPTANCE_V1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "consulted_versions": {"upgrade_spec": "v2.1", "upgrade_spec_sha256": sha256(SPEC),
                               "phase0_source": "docs/P12_01_BASELINE_V2_ACCEPTANCE_20260914.md"},
        "input_identity": {"source_sha256": source_hashes,
                           "source_recoverable_from_head": source_recoverable,
                           "adjusted_daily_sha256": replay["input_identity"]["adjusted_daily_sha256"],
                           "current_gbbq_sha256": replay["input_identity"]["current_gbbq_sha256"]},
        "subreceipts": receipts, "checks": checks,
        "legacy_predicate_contract": {
            "implementation": "STOCK_ATTENTION_PREVIEW_1",
            "source": "src/workbench_analysis/stock_attention.py:classify_stock_attention",
            "declared_but_not_consumed_in_legacy_classifier": [
                "BREAKOUT.requires_position_fields", "SETUP.requires_position_fields",
                "RECOVERY.requires_position_fields",
                "RECOVERY.requires_previous_close_below_ma5",
                "TREND_BACKGROUND.close_gte_ma20", "TREND_BACKGROUND.ma20_delta5_gt",
                "STRUCTURE_BREAK.consecutive_valid_sessions"],
            "disposition": "Do not assert these config flags are active; P12-03 must bind actual predicates or register revised contract"},
        "capability_limits": ["CURRENT_GBBQ_ONLY_RECONSTRUCTED_HISTORIC_PRICES",
                              "HISTORIC_UNIVERSE_PIT_UNAVAILABLE",
                              "HISTORIC_FROZEN_SEED_NOT_AVAILABLE",
                              "PRODUCTION_RUN_BUNDLE_LOCK_DEFERRED_TO_P12_06"],
        "acceptance_result": "DEGRADED_PASS" if all(checks.values()) else "BLOCKED",
        "acceptance_scope": "P12-02 factor, risk, pullback-state and RPS comparability contracts; historic PIT and production publication excluded",
        "next_stage": "P12-03_SCANNER_V3_3" if all(checks.values()) else "P12-02_REPAIR",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="p12_02_stage_gate_", suffix=".tmp", dir=REPORT.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, REPORT)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    if result["acceptance_result"] == "BLOCKED":
        raise RuntimeError("P12-02 stage gate blocked")
    print(REPORT)


if __name__ == "__main__":
    main()
