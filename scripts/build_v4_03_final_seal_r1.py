"""Seal externally accepted V4-03 governance state without running V4-04 work."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_COMMIT = "e19bd4f376d9e47ae14610ad5c93247f3513c4bd"
TASK = "docs/audits/V4_03_FINAL_SEAL_AND_V4_04_ENTRY_TASK_20260928.md"
ACCEPTANCE = "docs/evidence/V4_03_EXTERNAL_ACCEPTANCE_PASS_20260928.md"
RECEIPT_REL = "reports/v4_03/V4_03_FINAL_STAGE_RECEIPT_R1_20260928.json"
V403_HEAD_REL = "data/v4/V4_03_ACCEPTED_HEAD.json"
GLOBAL_HEAD_REL = "data/v4/V4_STAGE_ACCEPTED_HEAD.json"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def file_hashes(paths: list[str]) -> dict:
    result = {}
    for relative in paths:
        path = ROOT / relative
        if not path.is_file():
            raise RuntimeError(f"seal input is missing: {relative}")
        result[relative] = sha(path)
    return result


def main() -> None:
    current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if current != CANDIDATE_COMMIT:
        raise RuntimeError(f"candidate commit must remain {CANDIDATE_COMMIT}, got {current}")

    disposition = load("reports/v4_03/V4_03_STAGE_DISPOSITION_R3.json")
    determinism = load("reports/v4_03/V4_03_DETERMINISM_REPLAY_R3.json")
    native = load("reports/v4_03/V4_03_NATIVE_CONTRACT_ACCEPTANCE_R3.json")
    if disposition.get("status") != "CAPABILITY_SCOPED_PASS_CANDIDATE_NOT_FINAL_ACCEPTANCE":
        raise RuntimeError("V4-03 candidate disposition is not sealable")
    if disposition.get("artifact_hashes", {}).get("full_scope") is None or determinism.get("status") != "PASS":
        raise RuntimeError("V4-03 artifact or determinism evidence is incomplete")
    if native.get("status") != "PASS" or native.get("market_regime_raw_derivation_covered") is not True:
        raise RuntimeError("V4-03 native contract evidence is incomplete")
    expected_candidate = {"STOCK_CORE": "PASS_CANDIDATE", "RELATIVE_RPS": "PASS_CANDIDATE",
                          "MARKET_REFERENCE": "PASS_CANDIDATE", "MARKET_REGIME": "PASS_CANDIDATE",
                          "SECTOR_NATIVE": "BLOCKED"}
    if {key: value.get("status") for key, value in disposition["capabilities"].items()} != expected_candidate:
        raise RuntimeError("V4-03 scoped capability disposition differs from the external acceptance")
    for relative in ("reports/v4_03/V4_03_PRIOR_RPS_INDEPENDENT_POSTCHECK_R3.json",
                     "reports/v4_03/V4_03_MARKET_REFERENCE_PATH_INDEPENDENT_POSTCHECK_R3.json",
                     "reports/v4_03/V4_03_MARKET_REGIME_NATIVE_INDEPENDENT_POSTCHECK_R3.json",
                     "reports/v4_03/V4_03_INDEPENDENT_POSTCHECK_R3.json",
                     "reports/v4_03/V4_03_CONTRACT_PRODUCER_CONSISTENCY_R3.json",
                     "reports/v4_03/V4_03_AST_GOLDEN_VECTOR_ACCEPTANCE_R3.json"):
        if load(relative).get("status") != "PASS":
            raise RuntimeError(f"required V4-03 evidence is not PASS: {relative}")
    regime_postcheck = load("reports/v4_03/V4_03_MARKET_REGIME_NATIVE_INDEPENDENT_POSTCHECK_R3.json")
    if regime_postcheck.get("contract_conformance") != "PASS":
        raise RuntimeError("Market Regime REV2 formula conformance evidence is missing")
    for result in determinism["results"].values():
        digests = result.get("replay_sha256", [])
        if not result.get("deterministic") or len(digests) != 2 or any(x != result.get("baseline_sha256") for x in digests):
            raise RuntimeError("V4-03 deterministic replay does not match baseline")

    evidence_text = (ROOT / ACCEPTANCE).read_text(encoding="utf-8")
    required_acceptance_tokens = ("EXTERNAL_ACCEPTANCE_PASS_WITH_CAPABILITY_SCOPE",
                                  CANDIDATE_COMMIT,
                                  "V4_03_STOCK_CORE = PASS", "V4_03_SECTOR_NATIVE = DEGRADED_BLOCKED")
    if not all(token in evidence_text for token in required_acceptance_tokens):
        raise RuntimeError("archived external acceptance does not match the requested scoped PASS")

    upstream_head_path = ROOT / GLOBAL_HEAD_REL
    live_global_head = load(GLOBAL_HEAD_REL)
    original_global_text = subprocess.check_output(
        ["git", "show", f"{CANDIDATE_COMMIT}:{GLOBAL_HEAD_REL}"], cwd=ROOT, text=True, encoding="utf-8")
    original_global_head = json.loads(original_global_text)
    added_keys = {"v4_03_binding", "v4_03_status", "v4_04_stock_core_entry",
                  "v4_08_sector_entry", "incremental_update"}
    if {k: v for k, v in live_global_head.items() if k not in added_keys} != original_global_head:
        raise RuntimeError("global accepted head has unrelated changes after the candidate commit")
    global_head = original_global_head
    old_global_hash = hashlib.sha256(original_global_text.encode("utf-8")).hexdigest()
    dev_head = load("data/v4/V4_DEV_BASELINE_HEAD.json")
    bootstrap = load(dev_head["bootstrap_manifest"]["path"])
    manifest_ref = bootstrap["parent_artifacts"]["v4_02_manifest"]
    manifest = load(manifest_ref["path"])
    if sha(ROOT / manifest_ref["path"]) != manifest_ref["sha256"]:
        raise RuntimeError("V4-02 manifest identity changed")
    v401_universe = bootstrap["parent_artifacts"]["v4_01_universe"]
    if sha(ROOT / v401_universe["path"]) != v401_universe["sha256"]:
        raise RuntimeError("V4-01 universe identity changed")
    v402_head = global_head["bindings"]["v4_02_accepted_head"]
    if sha(ROOT / v402_head["path"]) != v402_head["sha256"]:
        raise RuntimeError("V4-02 accepted head identity changed")
    if global_head["source_cutoffs"].get("V4-02") != "2026-09-24":
        raise RuntimeError("source cutoff differs from the external acceptance")
    if manifest.get("scope", {}).get("source_cutoff") != "2026-09-24":
        raise RuntimeError("accepted V4-02 manifest cutoff differs from the task")
    if dev_head.get("accepted_data_cutoff") != "2026-09-24":
        raise RuntimeError("immutable development baseline cutoff differs from the task")
    for key in ("DAILY_R7", "CALENDAR", "FROZEN_R3_BASE"):
        ref = manifest["components"][key]
        if sha(ROOT / ref["path"]) != ref["sha256"]:
            raise RuntimeError(f"V4-02 accepted component identity mismatch: {key}")
    for binding in global_head["bindings"].values():
        if "path" in binding and "sha256" in binding and sha(ROOT / binding["path"]) != binding["sha256"]:
            raise RuntimeError(f"existing global binding mismatch: {binding['path']}")

    source_paths = ["data/v4/V4_DEV_BASELINE_HEAD.json", v401_universe["path"],
                    global_head["bindings"]["v4_01_identity_map"]["path"], v402_head["path"],
                    manifest_ref["path"]]
    for key in ("DAILY_R7", "CALENDAR", "FROZEN_R3_BASE"):
        source_paths.append(manifest["components"][key]["path"])
    contract_paths = ["config/v4_03_algorithm_contracts_v1.json", "config/v4_03_native_rule_contracts_r3.json",
                      "config/v4_03_native_contract_registry_v1.json", "config/v4_03_native_scope_map_v1.json",
                      "config/v4_03_output_schema_v1.json", "config/v4_03_parameter_registry_v1.json",
                      "config/v4_03_parameter_set_v1.json"]
    artifact_paths = ["reports/v4_03/staging/V4_03_PRIOR_RPS_STAGING_R3.json",
                      "reports/v4_03/staging/V4_03_FULL_SCOPE_CANDIDATE_R3.jsonl.gz",
                      "reports/v4_03/staging/V4_03_MARKET_REFERENCE_PATH_CANDIDATE_R3.jsonl.gz",
                      "reports/v4_03/staging/V4_03_MARKET_REGIME_NATIVE_CANDIDATE_R3.jsonl.gz"]
    evidence_paths = ["reports/v4_03/V4_03_STAGE_DISPOSITION_R3.json",
                      "reports/v4_03/V4_03_DETERMINISM_REPLAY_R3.json",
                      "reports/v4_03/V4_03_NATIVE_CONTRACT_ACCEPTANCE_R3.json",
                      "reports/v4_03/V4_03_AST_GOLDEN_VECTOR_ACCEPTANCE_R3.json",
                      "reports/v4_03/V4_03_PRIOR_RPS_INDEPENDENT_POSTCHECK_R3.json",
                      "reports/v4_03/V4_03_MARKET_REFERENCE_PATH_INDEPENDENT_POSTCHECK_R3.json",
                      "reports/v4_03/V4_03_MARKET_REGIME_NATIVE_INDEPENDENT_POSTCHECK_R3.json",
                      "reports/v4_03/V4_03_INDEPENDENT_POSTCHECK_R3.json",
                      "reports/v4_03/V4_03_CONTRACT_PRODUCER_CONSISTENCY_R3.json", ACCEPTANCE, TASK,
                      "docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md"]
    all_paths = sorted(set(source_paths + contract_paths + artifact_paths + evidence_paths))
    hashes = file_hashes(all_paths)

    capability_status = {
        "STOCK_CORE": "PASS", "RELATIVE_RPS": "PASS", "MARKET_REFERENCE": "PASS",
        "MARKET_REGIME": "PASS", "SECTOR_NATIVE": "BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP",
    }
    receipt = {
        "contract_id": "V4_03_FINAL_STAGE_RECEIPT_R1_20260928",
        "stage": "V4-03", "status": "PASS_WITH_SECTOR_SCOPE_DEGRADED",
        "stage_contract": {"task": TASK,
                           "technical_baseline": "docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md §27",
                           "scope": "final governance seal and V4-04 Stock Core entry authorization only"},
        "external_acceptance": "PASS_WITH_CAPABILITY_SCOPE",
        "external_acceptance_document": ACCEPTANCE,
        "accepted_candidate_commit": CANDIDATE_COMMIT,
        "source_cutoff": "2026-09-24", "capabilities": capability_status,
        "deferred_non_blocking": ["INCREMENTAL_UPDATE"],
        "authorized_successor": "V4_04_STOCK_CORE",
        "next_stage": "V4-04 Full-Market Core Profile; entry authorized, no business calculation started by this seal task",
        "blocked_successor": "V4_08_SECTOR",
        "authorization": {"V4_04_STOCK_CORE_ENTRY": "AUTHORIZED",
                          "V4_08_SECTOR_ENTRY": "BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP"},
        "scanner_run_count": 0, "trading_run_count": 0, "tdx_root_write_count": 0,
        "v4_04_business_calculation_started": False,
        "upstream_identities": {
            "v4_01_identity_map": {"path": global_head["bindings"]["v4_01_identity_map"]["path"],
                                    "sha256": global_head["bindings"]["v4_01_identity_map"]["sha256"]},
            "v4_01_universe": v401_universe,
            "v4_02_accepted_head": v402_head,
            "v4_02_manifest": manifest_ref,
        },
        "hashes": {"source": file_hashes(source_paths), "contracts": file_hashes(contract_paths),
                   "artifacts": file_hashes(artifact_paths), "evidence": file_hashes(evidence_paths)},
        "previous_global_accepted_head_sha256": old_global_hash,
    }
    receipt_path = ROOT / RECEIPT_REL
    atomic_json(receipt_path, receipt)
    receipt_sha = sha(receipt_path)

    accepted_head = {
        "contract_id": "V4_03_ACCEPTED_HEAD_V1", "stage": "V4-03",
        "status": "PASS_WITH_SECTOR_SCOPE_DEGRADED", "source_cutoff": "2026-09-24",
        "accepted_candidate_commit": CANDIDATE_COMMIT,
        "final_stage_receipt": {"path": RECEIPT_REL, "sha256": receipt_sha},
        "capabilities": capability_status,
        "upstream_identities": receipt["upstream_identities"],
        "v4_04_stock_core_authorization": "AUTHORIZED",
        "v4_08_sector": "BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP",
        "incremental_update": "DEFERRED_NON_BLOCKING",
    }
    accepted_head_path = ROOT / V403_HEAD_REL
    atomic_json(accepted_head_path, accepted_head)
    accepted_head_sha = sha(accepted_head_path)

    # Append only V4-03 and its authorized/blocked successors; preserve every
    # pre-existing V4-01/V4-02/global field exactly as read above.
    global_head["v4_03_binding"] = {"path": V403_HEAD_REL, "sha256": accepted_head_sha}
    global_head["v4_03_status"] = "PASS_WITH_SECTOR_SCOPE_DEGRADED"
    global_head["v4_04_stock_core_entry"] = "AUTHORIZED"
    global_head["v4_08_sector_entry"] = "BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP"
    atomic_json(upstream_head_path, global_head)
    print(json.dumps({"status": receipt["status"], "receipt_sha256": receipt_sha,
                      "v4_03_accepted_head_sha256": accepted_head_sha,
                      "v4_stage_accepted_head_sha256": sha(upstream_head_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
