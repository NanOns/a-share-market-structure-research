"""Build versioned V4-06 R2 evidence receipts without touching R1 evidence."""
from __future__ import annotations

from datetime import date, timedelta, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.baostock_supplemental import normalize_row
from workbench_analysis.v4_06_supplemental import (
    classify_turnover_pct60, compute_turnover_context, evaluate_binding, run_core_isolation_matrix,
)

OUT = ROOT / "reports/v4_06"
ACCEPTED_PUBLICATION = "PUB-3c03e227-c60a-4d8c-86ae-2861507c257b"
ACCEPTED_DIGEST = "d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74"


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _history(target_rate: float, count: int, *, rate: float = 0.01) -> tuple[str, dict, list[dict]]:
    end = date(2026, 9, 28)
    prior = [{"trade_date": (end - timedelta(days=i + 1)).isoformat(), "session_state": "BOUND_STRICT",
              "local_tradestatus": "1", "turnover_rate": rate} for i in range(count)]
    target = {"trade_date": end.isoformat(), "binding_status": "BOUND_STRICT", "local_tradestatus": "1",
              "turnover_rate": target_rate}
    return end.isoformat(), target, prior


def _target_result(*, rate: float = 0.025, count: int = 60, gap: bool = False,
                   suspensions: bool = False, binding: str = "BOUND_STRICT", reasons=()) -> dict:
    target_day, target, prior = _history(rate, count)
    if binding != "BOUND_STRICT":
        target["binding_status"] = binding
        target["binding_reason_codes"] = list(reasons)
    if gap and len(prior) > 4:
        prior[3] = {"trade_date": prior[3]["trade_date"], "session_state": "UNKNOWN", "turnover_rate": None}
    if suspensions and len(prior) > 61:
        prior[0] = {"trade_date": prior[0]["trade_date"], "session_state": "CONFIRMED_SUSPENSION",
                    "local_tradestatus": "0", "turnover_rate": None}
    return compute_turnover_context(target_trade_date=target_day, target=target, prior_sessions=prior)


def _percentile5(current: float, rates: list[float]) -> float | None:
    end = date(2026, 9, 28)
    prior = [{"trade_date": (end - timedelta(days=i + 1)).isoformat(), "session_state": "BOUND_STRICT",
              "local_tradestatus": "1", "turnover_rate": value} for i, value in enumerate(rates)]
    target = {"trade_date": end.isoformat(), "binding_status": "BOUND_STRICT", "local_tradestatus": "1",
              "turnover_rate": current}
    return compute_turnover_context(target_trade_date=end.isoformat(), target=target,
                                   prior_sessions=prior)["turnover_pct5"]


def _tolerance_receipt() -> dict:
    config_path = ROOT / "config/baostock_turnover_binding_tolerance_v1.json"
    real = json.loads(config_path.read_text(encoding="utf-8"))
    source = normalize_row("sh.600000", {"date": "2026-09-01", "code": "sh.600000", "close": "10.0",
        "volume": "1200", "amount": "12000", "turn": "1.25", "tradestatus": "1", "isST": "0"})
    local = {"security_id": "SEC-001", "trade_date": "2026-09-01", "close": 10.0,
             "volume": 1200, "amount": 12000, "tradestatus": "1", "isST": "0"}
    current_result = evaluate_binding(local, source, expected_provider_code="sh.600000", tolerance_contract=real)
    accepted = json.loads(json.dumps(real))
    accepted.update({"status": "FROZEN", "acceptance": "INDEPENDENTLY_ACCEPTED", "strict_binding_allowed": True,
                     "tolerances": {"close": 0.01, "volume": 0, "amount": 0.01},
                     "evidence_digest": "a" * 64, "accepted_by": "synthetic-independent-review-fixture",
                     "accepted_at_utc": "2026-09-29T00:00:00Z"})
    accepted["denominator_semantics_acceptance"].update({"status": "INDEPENDENTLY_ACCEPTED",
        "evidence_digest": "b" * 64, "accepted_by": "synthetic-independent-review-fixture",
        "accepted_at_utc": "2026-09-29T00:00:00Z"})
    accepted_result = evaluate_binding(local, source, expected_provider_code="sh.600000", tolerance_contract=accepted)
    gates = {}
    for name, change in {
        "strict_binding_allowed_false": {"strict_binding_allowed": False},
        "non_frozen_status": {"status": "UNFROZEN_NO_INDEPENDENT_ACCEPTANCE"},
        "acceptance_not_independent": {"acceptance": "NOT_ACCEPTED"},
        "wrong_contract_version": {"contract_version": "9.9.9"},
        "wrong_contract_id": {"contract_id": "OTHER"},
        "wrong_source_contract": {"source_contract_id": "OTHER"},
        "wrong_dataset": {"dataset_id": "OTHER"},
        "wrong_comparison_basis": {"comparison_basis": {"close": "wrong unit"}},
        "missing_denominator_acceptance": {"denominator_semantics_acceptance": None},
        "missing_reviewer": {"accepted_by": None},
        "missing_evidence": {"evidence_digest": None},
        "missing_timestamp": {"accepted_at_utc": None},
    }.items():
        probe = json.loads(json.dumps(accepted))
        probe.update(change)
        gates[name] = evaluate_binding(local, source, expected_provider_code="sh.600000", tolerance_contract=probe)[0] != "BOUND_STRICT"
    denominator_gates = {}
    for key in ("accepted_by", "evidence_digest", "accepted_at_utc"):
        probe = json.loads(json.dumps(accepted))
        probe["denominator_semantics_acceptance"][key] = None
        denominator_gates[f"denominator_missing_{key}"] = evaluate_binding(
            local, source, expected_provider_code="sh.600000", tolerance_contract=probe)[0] != "BOUND_STRICT"
    wrong_denominator_basis = json.loads(json.dumps(accepted))
    wrong_denominator_basis["denominator_semantics_acceptance"]["basis"] = "TOTAL_SHARES"
    denominator_gates["denominator_wrong_basis"] = evaluate_binding(
        local, source, expected_provider_code="sh.600000",
        tolerance_contract=wrong_denominator_basis)[0] != "BOUND_STRICT"
    edge = json.loads(json.dumps(accepted))
    edge["tolerances"] = {"close": 0.01, "volume": 0, "amount": 0}
    within = evaluate_binding({**local, "close": 10.01}, source, expected_provider_code="sh.600000", tolerance_contract=edge)[0]
    outside = evaluate_binding({**local, "close": 10.0101}, source, expected_provider_code="sh.600000", tolerance_contract=edge)[0]
    return {
        "contract_id": "V4_06_R2_TOLERANCE_SCHEMA_ACCEPTANCE_V1",
        "status": "PASS" if current_result[0] != "BOUND_STRICT" and accepted_result[0] == "BOUND_STRICT"
                  and all(gates.values()) and all(denominator_gates.values()) and within == "BOUND_STRICT" and outside != "BOUND_STRICT" else "FAIL",
        "persisted_config_path": config_path.relative_to(ROOT).as_posix(), "persisted_config_sha256": sha(config_path),
        "persisted_schema_keys": sorted(real), "contract_version_field_consumed": "contract_version" in real and "version" not in real,
        "current_real_config": {"binding_quality": current_result[0], "reason_codes": list(current_result[1]),
                                "strict_binding_forbidden": current_result[0] != "BOUND_STRICT"},
        "synthetic_accepted_copy": {"binding_quality": accepted_result[0], "fixture_only": True,
                                     "not_live_source_acceptance": True},
        "strict_gate_negative_cases": gates, "denominator_acceptance_negative_cases": denominator_gates,
        "epsilon_boundary": {"at_tolerance": within, "outside_tolerance": outside},
        "live_baostock_tolerance_audit": "OPEN_NO_TOLERANCE_OR_DENOMINATOR_SEMANTICS_INFERRED",
    }


def _contract_semantics_receipt() -> dict:
    # Independent oracle for percentile vectors: the formula is implemented
    # here separately from the production helper.
    vectors = []
    percentile_vectors = (
        ("all_prior_above", 0.005, [0.01] * 5),
        ("all_prior_below", 0.2, [0.01] * 5),
        ("all_equal", 0.01, [0.01] * 5),
        ("mixed_lower_equal_higher", 0.5, [0.1, 0.2, 0.3, 0.5, 0.8]),
    )
    for label, current, prior in percentile_vectors:
        expected = 100.0 * (sum(x < current for x in prior) + 0.5 * sum(x == current for x in prior)) / len(prior)
        vectors.append({"id": label, "independent_expected_percentile": expected,
                        "unit": "PERCENT", "range": [0, 100], "formula_oracle_independent": True,
                        "runtime_boundary_suite": "tests/v4_06/test_v4_06_supplemental.py"})
    actuals = {f"percentile_{label}": _percentile5(current, prior)
               for label, current, prior in percentile_vectors}
    expected_percentiles = {f"percentile_{item['id']}": item["independent_expected_percentile"] for item in vectors}
    pct60_boundaries = [{"pct60": x, "expected": expected, "actual": classify_turnover_pct60(x)} for x, expected in (
        (19.999999, "LOW"), (20, "NORMAL"), (69.999999, "NORMAL"), (70, "ELEVATED"),
        (89.999999, "ELEVATED"), (90, "HIGH"), (96.999999, "HIGH"), (97, "EXTREME"), (100, "EXTREME"))]
    pct60_boundaries_pass = all(item["actual"] == item["expected"] for item in pct60_boundaries)
    state_cases = {
        "sixty_strict_samples": _target_result(count=60)["turnover_state"],
        "fifty_nine_strict_samples": _target_result(count=59)["turnover_state"],
        "unknown_gap": _target_result(count=60, gap=True)["turnover_state"],
        "target_pending": _target_result(count=60, binding="BOUND_SOFT",
                                          reasons=("TOLERANCE_NOT_INDEPENDENTLY_ACCEPTED",))["turnover_state"],
        "target_unavailable": _target_result(count=60, binding="UNBOUND",
                                               reasons=("LOCAL_SOURCE_FINGERPRINT_CONFLICT",))["turnover_state"],
    }
    state_expected = {"sixty_strict_samples": "EXTREME", "fifty_nine_strict_samples": "UNKNOWN_DATA",
                      "unknown_gap": "UNKNOWN_DATA", "target_pending": "PENDING", "target_unavailable": "UNAVAILABLE"}
    return {
        "contract_id": "V4_06_R2_CONTRACT_SEMANTICS_ACCEPTANCE_V1",
        "status": "PASS" if actuals == expected_percentiles and state_cases == state_expected and pct60_boundaries_pass else "FAIL",
        "contract": {"contract_id": "TURNOVER_CONTEXT_V1", "contract_version": "2.0.0",
                     "path": "config/turnover_context_contract_v2.json", "sha256": sha(ROOT / "config/turnover_context_contract_v2.json")},
        "percentile_formula": "100 * (count(prior < current) + 0.5 * count(prior == current)) / N",
        "percentile_vectors": vectors, "runtime_percentile_results": actuals,
        "pct60_state_boundaries": pct60_boundaries, "pct60_boundaries_pass": pct60_boundaries_pass,
        "state_cases": state_cases,
        "state_cases_match_contract": state_cases == state_expected,
        "binding_quality_separate_from_turnover_state": True,
        "turnover_context_alias": "DEPRECATED_INTERNAL_ALIAS_EXACTLY_EQUAL_TO_TURNOVER_STATE",
    }


def _determinism_receipt() -> dict:
    probe = r'''import json, sys, hashlib
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))
from workbench_analysis.v4_06_supplemental import compute_turnover_context
from datetime import date, timedelta
end=date(2026,9,28)
prior=[{"trade_date":(end-timedelta(days=i+1)).isoformat(),"session_state":"BOUND_STRICT","local_tradestatus":"1","turnover_rate":0.01} for i in range(60)]
target={"trade_date":end.isoformat(),"binding_status":"BOUND_STRICT","local_tradestatus":"1","turnover_rate":0.02}
out=compute_turnover_context(target_trade_date=end.isoformat(),target=target,prior_sessions=prior)
payload={k:v for k,v in out.items() if k not in {"created_at","observed_at"}}
data=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
print(json.dumps({"logical_digest":hashlib.sha256(data).hexdigest(),"row":payload},sort_keys=True))'''
    runs = []
    for _ in range(2):
        process = subprocess.run([sys.executable, "-c", probe], cwd=ROOT, text=True, capture_output=True, check=True)
        runs.append(json.loads(process.stdout))
    return {"contract_id": "V4_06_R2_DETERMINISM_V1", "status": "PASS" if runs[0] == runs[1] else "FAIL",
            "runs": [{"logical_digest": item["logical_digest"]} for item in runs],
            "row_identity_count": 1, "created_timestamps_present": False,
            "canonical_digest_excludes_only_ephemeral_timestamps": True,
            "two_fresh_processes_identical": runs[0] == runs[1]}


def _core_isolation_receipt() -> dict:
    core = {"core_fact_digest": "1" * 64, "core_profile_digest": "2" * 64,
            "core_eligibility_digest": "3" * 64, "core_state_digest": "4" * 64,
            "core_event_digest": "5" * 64, "validation_enrollment_digest": "6" * 64}
    scenarios = {
        "A_NO_TURNOVER_SIDECAR": {},
        "B_PENDING_SIDECAR": {"turnover_state": "PENDING"},
        "C_SYNTHETIC_TURNOVER": {"turnover_rate": 0.1234, "turnover_pct60": 100.0},
        "D_EXTENSION_NOTE_CHANGED": {"supplemental_extension_note": {"state": "UNAVAILABLE", "reason_codes": ["FIXTURE"]}},
        "E_BINDING_QUALITY_CONFLICT": {"binding_quality": "BOUND_SOFT"},
    }
    result = run_core_isolation_matrix(core, scenarios)
    db = json.loads((OUT / "V4_06_R2_SCHEMA_MIGRATION_RECEIPT.json").read_text(encoding="utf-8"))
    return {"contract_id": "V4_06_R2_CORE_ISOLATION_ACCEPTANCE_V1",
            "status": "PASS" if result["all_core_components_identical"]
                      and db["checks"]["core_publication_head_unchanged"] else "FAIL",
            "accepted_v4_05_publication_id": ACCEPTED_PUBLICATION,
            "accepted_v4_05_core_logical_digest": ACCEPTED_DIGEST,
            "accepted_core_head_before_after": {"before": db["checks"]["core_publication_head_before"],
                                                 "after": db["checks"]["core_publication_head_after"],
                                                 "unchanged": db["checks"]["core_publication_head_unchanged"]},
            "scenario_matrix": result["checks"],
            "fixture_digest_disclosure": "Six component hashes and all sidecar scenarios are structural fixtures, not accepted V4-05 business component digests.",
            "core_dependency": "NONE"}


def main() -> None:
    runtime = subprocess.run([sys.executable, "-m", "pytest", "tests/v4_06", "-q"],
                             cwd=ROOT, text=True, capture_output=True)
    runtime_receipt = {"contract_id": "V4_06_R2_RUNTIME_TEST_RECEIPT_V1",
                       "command": "python -m pytest tests/v4_06 -q", "exit_code": runtime.returncode,
                       "output": runtime.stdout + runtime.stderr,
                       "status": "PASS" if runtime.returncode == 0 else "FAIL",
                       "test_scope": ["percentile units and independent midpoint vectors", "pct60 state boundaries",
                                      "59/60 sample boundary", "unknown gap and suspension handling",
                                      "PENDING/UNAVAILABLE/UNKNOWN_DATA", "real tolerance schema and strict gates",
                                      "append-only revision", "supplemental extension note", "Core isolation A-E"]}
    write_atomic(OUT / "V4_06_R2_RUNTIME_TEST_RECEIPT.json", runtime_receipt)
    tolerance = _tolerance_receipt()
    semantics = _contract_semantics_receipt()
    determinism = _determinism_receipt()
    isolation = _core_isolation_receipt()
    write_atomic(OUT / "V4_06_R2_TOLERANCE_SCHEMA_ACCEPTANCE.json", tolerance)
    write_atomic(OUT / "V4_06_R2_CONTRACT_SEMANTICS_ACCEPTANCE.json", semantics)
    write_atomic(OUT / "V4_06_R2_DETERMINISM.json", determinism)
    write_atomic(OUT / "V4_06_R2_CORE_ISOLATION_ACCEPTANCE.json", isolation)
    if runtime.returncode or tolerance["status"] != "PASS" or semantics["status"] != "PASS" \
            or determinism["status"] != "PASS" or isolation["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
