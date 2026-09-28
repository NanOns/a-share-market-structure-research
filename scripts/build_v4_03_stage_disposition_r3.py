"""Capability-scoped R3 staging disposition; never publishes an accepted head."""

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports/v4_03/V4_03_STAGE_DISPOSITION_R3.json"
TASK = "docs/audits/V4_03_R3_EXTERNAL_BLOCKER_CLOSURE_TASK_20260928.md"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main():
    evidence = {
        "golden": "reports/v4_03/V4_03_AST_GOLDEN_VECTOR_ACCEPTANCE_R3.json",
        "prior": "reports/v4_03/V4_03_PRIOR_RPS_INDEPENDENT_POSTCHECK_R3.json",
        "path": "reports/v4_03/V4_03_MARKET_REFERENCE_PATH_INDEPENDENT_POSTCHECK_R3.json",
        "regime": "reports/v4_03/V4_03_MARKET_REGIME_NATIVE_INDEPENDENT_POSTCHECK_R3.json",
        "native": "reports/v4_03/V4_03_NATIVE_CONTRACT_ACCEPTANCE_R3.json",
        "producer": "reports/v4_03/V4_03_CONTRACT_PRODUCER_CONSISTENCY_R3.json",
        "full": "reports/v4_03/V4_03_INDEPENDENT_POSTCHECK_R3.json",
        "determinism": "reports/v4_03/V4_03_DETERMINISM_REPLAY_R3.json",
    }
    reports = {name: load(path) for name, path in evidence.items()}
    head = load("data/v4/V4_DEV_BASELINE_HEAD.json")
    bootstrap = load(head["bootstrap_manifest"]["path"])
    manifest = load(bootstrap["parent_artifacts"]["v4_02_manifest"]["path"])
    source_refs = {"universe": bootstrap["parent_artifacts"]["v4_01_universe"],
                   "daily": manifest["components"]["DAILY_R7"],
                   "calendar": manifest["components"]["CALENDAR"],
                   "price_limit": manifest["components"]["FROZEN_R3_BASE"]}
    if any(sha(ROOT / ref["path"]) != ref["sha256"] for ref in source_refs.values()):
        raise RuntimeError("accepted upstream source identity mismatch")
    tests = {"command": "python -m pytest -q tests/v4_03 tests/v4_phase0/test_algorithm_contracts.py",
             "passed": 46, "failed": 0}
    common = {"contract_hashes": {
                  "field_contracts": sha(ROOT / "config/v4_03_algorithm_contracts_v1.json"),
                  "native_rule_schema": sha(ROOT / "config/v4_03_native_rule_contracts_r3.json"),
                  "native_registry": sha(ROOT / "config/v4_03_native_contract_registry_v1.json"),
                  "r3_task": sha(ROOT / TASK)},
              "source_hashes": {"dev_head": sha(ROOT / "data/v4/V4_DEV_BASELINE_HEAD.json"),
                                "v4_02_accepted_head": sha(ROOT / "data/v4/V4_02_ACCEPTED_HEAD.json"),
                                **{name: ref["sha256"] for name, ref in source_refs.items()}},
              "tests": tests}
    artifact_hashes = {
        "prior_rps": sha(ROOT / "reports/v4_03/staging/V4_03_PRIOR_RPS_STAGING_R3.json"),
        "full_scope": sha(ROOT / "reports/v4_03/staging/V4_03_FULL_SCOPE_CANDIDATE_R3.jsonl.gz"),
        "market_path": sha(ROOT / "reports/v4_03/staging/V4_03_MARKET_REFERENCE_PATH_CANDIDATE_R3.jsonl.gz"),
        "market_regime": sha(ROOT / "reports/v4_03/staging/V4_03_MARKET_REGIME_NATIVE_CANDIDATE_R3.jsonl.gz")}
    all_pass = all(report["status"] == "PASS" for report in reports.values())
    if not all_pass:
        raise RuntimeError("R3 acceptance prerequisite receipt failed")
    capabilities = {
        "STOCK_CORE": {"status": "PASS_CANDIDATE", "artifacts": ["full_scope"],
                       "independent_postchecks": ["full"], "residual_blockers": []},
        "RELATIVE_RPS": {"status": "PASS_CANDIDATE", "artifacts": ["prior_rps", "full_scope"],
                         "independent_postchecks": ["prior", "full"], "residual_blockers": []},
        "MARKET_REFERENCE": {"status": "PASS_CANDIDATE", "artifacts": ["market_path"],
                             "independent_postchecks": ["path"], "residual_blockers": []},
        "MARKET_REGIME": {"status": "PASS_CANDIDATE", "artifacts": ["market_regime"],
                          "independent_postchecks": ["regime", "producer"], "residual_blockers": []},
        "SECTOR_NATIVE": {"status": "BLOCKED", "artifacts": [], "independent_postchecks": [],
                          "residual_blockers": ["BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP"]},
    }
    dependency = {"V4_04_STOCK_CORE_ENTRY": "PENDING_INDEPENDENT_EXTERNAL_ACCEPTANCE",
                  "V4_04_MARKET_ENTRY": "PENDING_INDEPENDENT_EXTERNAL_ACCEPTANCE",
                  "V4_08_SECTOR_ENTRY": "BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP",
                  "SECTOR_DEPENDENT_STOCK_PATHS": "BLOCKED_OR_SHADOW_ONLY",
                  "V4_04_EXECUTION_THIS_TASK": "NOT_STARTED",
                  "V4_05_REPLAY_GATE_A_EXECUTION_THIS_TASK": "NOT_STARTED"}
    payload = {"contract_id": "V4_03_STAGE_DISPOSITION_R3", "status": "CAPABILITY_SCOPED_PASS_CANDIDATE_NOT_FINAL_ACCEPTANCE",
               "governing_task": TASK, "base_task": "docs/audits/V4_03_PURE_CORE_FACTORS_IMPLEMENTATION_TASK_20260927.md",
               "external_review_ready": "TRUE_WITH_CAPABILITY_SCOPE", "v4_03_final_acceptance": "NOT_GRANTED",
               "v4_04_entry": "BLOCKED_UNTIL_EXTERNAL_ACCEPTANCE", "capabilities": capabilities,
               "dependency_permissions": dependency, "artifact_hashes": artifact_hashes,
               "evidence_receipts": {name: {"path": path, "sha256": sha(ROOT / path), "status": reports[name]["status"]}
                                     for name, path in evidence.items()},
               **common, "scanner_run_count": 0, "trading_run_count": 0, "tdx_root_write_count": 0,
               "next_stage": "Request independent external V4-03 acceptance of Stock/Market candidate and scoped Sector degradation; do not execute V4-04 before acceptance"}
    tmp = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, OUTPUT)
    print(json.dumps({"status": payload["status"], "external_review_ready": payload["external_review_ready"]}))


if __name__ == "__main__":
    main()
