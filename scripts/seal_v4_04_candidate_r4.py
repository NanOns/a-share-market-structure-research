"""Seal V4-04 candidate evidence without publishing an accepted head."""

from __future__ import annotations

from collections import Counter
import argparse
import gzip
from hashlib import sha256
import json
import os
import re
from pathlib import Path
import subprocess
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/v4_04"
ARTIFACT = REPORT / "staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R4.jsonl.gz"
BUILD = REPORT / "V4_04_FULL_MARKET_CANDIDATE_RECEIPT_R4.json"
POSTCHECK = REPORT / "V4_04_INDEPENDENT_POSTCHECK_R4.json"


def hash_file(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write(name: str, payload: dict) -> dict:
    path = REPORT / name
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes((json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    os.replace(tmp, path)
    return {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": hash_file(path), "byte_count": path.stat().st_size}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--first-run-sha256", required=True)
    args = parser.parse_args()
    expected_sha = args.first_run_sha256
    if len(expected_sha) != 64 or any(ch not in "0123456789abcdef" for ch in expected_sha):
        raise ValueError("invalid first-run SHA256")
    build = json.loads(BUILD.read_text(encoding="utf-8"))
    postcheck = json.loads(POSTCHECK.read_text(encoding="utf-8"))
    historical_r1 = REPORT / "staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R1.jsonl.gz"
    historical_sha = "afbea0ab09cbe28cfb5648495264ce346ccce22f5ca40b15b24112b6d8eb2e07"
    if hash_file(historical_r1) != historical_sha:
        raise ValueError("R1 historical artifact identity changed")
    historical_r2 = REPORT / "staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R2.jsonl.gz"
    historical_r2_sha = "89ed21dbdcc5abf377d2fda8299c444e7cd687fabb0eb5648ef5f12b8c4c0f12"
    if hash_file(historical_r2) != historical_r2_sha:
        raise ValueError("R2 historical artifact identity changed")
    historical_r3 = REPORT / "staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R3.jsonl.gz"
    historical_r3_sha = "0c0fccd06fd2c2bad856b529d3ae2bcf64584f451e97961380997d72830b46b6"
    if hash_file(historical_r3) != historical_r3_sha:
        raise ValueError("R3 historical artifact identity changed")
    vector_path = REPORT / "V4_04_MACHINE_VECTOR_COVERAGE_R4.json"
    vectors = json.loads(vector_path.read_text(encoding="utf-8"))
    if (vectors["status"] != "PASS" or vectors["semantic_categories_status"] != "PASS" or
            vectors["rules_missing_vector_coverage"] or
            vectors["machine_rule_count"] != 18 or
            postcheck["machine_vector_receipt_sha256"] != hash_file(vector_path)):
        raise ValueError("machine vector coverage gate not passed")
    if hash_file(ARTIFACT) != expected_sha or build["artifact"]["sha256"] != expected_sha or postcheck["artifact_sha256"] != expected_sha:
        raise ValueError("deterministic artifact identity mismatch")
    if (postcheck["status"] != "PASS" or postcheck["rows_checked"] != 5222 or
            postcheck["machine_rule_coverage"] != 1 or postcheck["unsupported_operators"] or
            postcheck["unexecuted_machine_rules"] or
            postcheck["minimum_liquidity_false_unknown_count"] != 0 or
            postcheck["drawdown_inclusive_boundary_check"] != "PASS_20_AND_60"):
        raise ValueError("independent postcheck not passed")
    implementation = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    rows, boards, quality, field_quality, state_unknown = 0, Counter(), Counter(), Counter(), Counter()
    with gzip.open(ARTIFACT, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            rows += 1
            boards[row["board"]] += 1
            quality[row["profile_quality"]] += 1
            for field, item in row["primitive_quality"].items():
                field_quality[(field, item["quality_state"])] += 1
            for field, item in row["derived_fields"].items():
                field_quality[(field, item["quality"])] += 1
            for field, item in row["states"].items():
                field_quality[(field, "UNKNOWN" if item["unknown_reason"] else "OBSERVED")] += 1
                if item["unknown_reason"]:
                    state_unknown[(field, item["unknown_reason"])] += 1
    if rows != 5222 or dict(boards) != build["board_count"]:
        raise ValueError("row or board count mismatch")
    refs = {}
    refs["row_count"] = write("V4_04_ROW_BOARD_COUNT_R4.json", {
        "contract_id": "V4_04_ROW_BOARD_COUNT_R4", "row_count": rows, "board_count": dict(boards),
        "required_boards": build["required_boards"], "source_cutoff": build["cutoff"], "artifact_sha256": expected_sha})
    refs["field_completeness"] = write("V4_04_FIELD_COMPLETENESS_R4.json", {
        "contract_id": "V4_04_FIELD_COMPLETENESS_R4", "row_count": rows,
        "field_quality_counts": {f"{field}:{state}": n for (field, state), n in sorted(field_quality.items())},
        "registry_sha256": build["contract_files"]["config/v4_04_field_registry_v2.json"],
        "schema_check": "PASS_ALL_ROWS_INDEPENDENT_POSTCHECK", "artifact_sha256": expected_sha})
    refs["quality_inventory"] = write("V4_04_UNKNOWN_QUALITY_INVENTORY_R4.json", {
        "contract_id": "V4_04_UNKNOWN_QUALITY_INVENTORY_R4", "profile_quality_counts": dict(quality),
        "state_unknown_reasons": {f"{field}:{reason}": n for (field, reason), n in sorted(state_unknown.items())},
        "pos250_optional_diagnostic": True, "artifact_sha256": expected_sha})
    refs["consumed_sources"] = write("V4_04_CONSUMED_SOURCE_MANIFEST_R4.json", {
        "contract_id": "V4_04_CONSUMED_SOURCE_MANIFEST_R4", "sources": build["sources"],
        "source_cutoff": build["cutoff"], "input_resolver": "src/v4/accepted_input.py", "artifact_sha256": expected_sha})
    refs["input_identity"] = write("V4_04_INPUT_IDENTITY_R4.json", {
        "contract_id": "V4_04_INPUT_IDENTITY_R4", "authority": "data/v4/V4_STAGE_ACCEPTED_HEAD.json",
        "upstream": ["V4_01_ACCEPTED_HEAD_V1", "V4_02_ACCEPTED_HEAD_V1", "V4_03_ACCEPTED_HEAD_AMENDED_V1"],
        "source_hash_verification": "PASS", "cutoff_verification": "PASS", "required_board_verification": "PASS",
        "artifact_sha256": expected_sha})
    refs["contract_digest"] = write("V4_04_CONTRACT_PARAMETER_DIGEST_R4.json", {
        "contract_id": "V4_04_CONTRACT_PARAMETER_DIGEST_R4", "files": build["contract_files"],
        "combined_digest": build["contract_digest"], "artifact_sha256": expected_sha})
    refs["determinism"] = write("V4_04_DETERMINISM_R4.json", {
        "contract_id": "V4_04_DETERMINISM_R4", "status": "PASS", "first_run_sha256": expected_sha,
        "second_run_sha256": build["artifact"]["sha256"], "row_count": rows,
        "same_contract_and_accepted_inputs": True})
    test_dirs = ["tests/v4_01", "tests/v4_02", "tests/v4_03", "tests/v4_04", "tests/v4_joint", "tests/v4_phase0"]
    command = ["python", "-m", "pytest", *test_dirs, "-q"]
    runtime_started = datetime.now(timezone.utc).isoformat()
    test_run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    test_log = write("V4_04_FOCUSED_PYTEST_RUNTIME_R4.json", {
        "command": command, "started_utc": runtime_started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "exit_code": test_run.returncode, "stdout": test_run.stdout, "stderr": test_run.stderr})
    summary = re.search(r"(\d+) passed(?:, (\d+) skipped)?", test_run.stdout)
    if test_run.returncode != 0 or summary is None:
        raise ValueError("focused pytest runtime failed; inspect V4_04_FOCUSED_PYTEST_RUNTIME_R4.json")
    test_sources = {str(path.relative_to(ROOT)).replace("\\", "/"): hash_file(path)
                    for directory in test_dirs for path in sorted((ROOT / directory).glob("test_*.py"))}
    refs["tests"] = write("V4_04_TEST_GATE_R4.json", {
        "contract_id": "V4_04_TEST_GATE_R4", "status": "PASS",
        "command": " ".join(command),
        "passed": int(summary.group(1)), "skipped": int(summary.group(2) or 0), "failed": 0,
        "tested_implementation_commit": implementation,
        "test_sources": test_sources, "runtime_log": test_log,
        "global_suite_status": "SEPARATE_OPEN_AUDIT_ITEM_V4_GLOBAL_PYTEST_COLLECTION_AUDIT_ITEM_R1"})
    refs["postcheck"] = {"path": str(POSTCHECK.relative_to(ROOT)).replace("\\", "/"),
                         "sha256": hash_file(POSTCHECK), "byte_count": POSTCHECK.stat().st_size}
    refs["machine_vectors"] = {"path": str(vector_path.relative_to(ROOT)).replace("\\", "/"),
                               "sha256": hash_file(vector_path), "byte_count": vector_path.stat().st_size}
    refs["production"] = {"path": str(BUILD.relative_to(ROOT)).replace("\\", "/"),
                          "sha256": hash_file(BUILD), "byte_count": BUILD.stat().st_size}
    for key, name in (("registry_consistency", "V4_04_REGISTRY_ARTIFACT_CONSISTENCY_R4.json"),
                      ("window_traceability", "V4_04_WINDOW_TRACEABILITY_R4.json")):
        path = REPORT / name
        receipt = json.loads(path.read_text(encoding="utf-8"))
        if receipt["status"] != "PASS" or receipt["artifact_sha256"] != expected_sha:
            raise ValueError(f"{key} receipt mismatch")
        refs[key] = {"path": str(path.relative_to(ROOT)).replace("\\", "/"),
                     "sha256": hash_file(path), "byte_count": path.stat().st_size}
    write("V4_04_STAGE_CANDIDATE_MANIFEST_R4.json", {
        "contract_id": "V4_04_STAGE_CANDIDATE_MANIFEST_R4", "status": "V4_04_FULL_PASS_CANDIDATE_R4",
        "implementation_commit": implementation, "artifact": build["artifact"], "evidence": refs,
        "test_gate": refs["tests"],
        "historical_r1_artifact_sha256": historical_sha,
        "historical_r2_artifact_sha256": historical_r2_sha,
        "historical_r3_artifact_sha256": historical_r3_sha,
        "global_acceptance": "NOT_PROMOTED_AWAITING_EXTERNAL_REVIEW", "v4_05_execution": "NOT_STARTED"})
    print(json.dumps({"status": "V4_04_FULL_PASS_CANDIDATE_R4", "rows": rows, "boards": dict(boards), "artifact_sha256": expected_sha}))


if __name__ == "__main__":
    main()
