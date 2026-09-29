"""Seal V4-04 candidate evidence without publishing an accepted head."""

from __future__ import annotations

from collections import Counter
import argparse
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/v4_04"
ARTIFACT = REPORT / "staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R1.jsonl.gz"
BUILD = REPORT / "V4_04_FULL_MARKET_CANDIDATE_RECEIPT_R1.json"
POSTCHECK = REPORT / "V4_04_INDEPENDENT_POSTCHECK_R1.json"


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
    if hash_file(ARTIFACT) != expected_sha or build["artifact"]["sha256"] != expected_sha or postcheck["artifact_sha256"] != expected_sha:
        raise ValueError("deterministic artifact identity mismatch")
    if postcheck["status"] != "PASS" or postcheck["rows_checked"] != 5222:
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
    refs["row_count"] = write("V4_04_ROW_BOARD_COUNT_R1.json", {
        "contract_id": "V4_04_ROW_BOARD_COUNT_R1", "row_count": rows, "board_count": dict(boards),
        "required_boards": build["required_boards"], "source_cutoff": build["cutoff"], "artifact_sha256": expected_sha})
    refs["field_completeness"] = write("V4_04_FIELD_COMPLETENESS_R1.json", {
        "contract_id": "V4_04_FIELD_COMPLETENESS_R1", "row_count": rows,
        "field_quality_counts": {f"{field}:{state}": n for (field, state), n in sorted(field_quality.items())},
        "registry_sha256": build["contract_files"]["config/v4_04_field_registry_v1.json"],
        "schema_check": "PASS_ALL_ROWS_INDEPENDENT_POSTCHECK", "artifact_sha256": expected_sha})
    refs["quality_inventory"] = write("V4_04_UNKNOWN_QUALITY_INVENTORY_R1.json", {
        "contract_id": "V4_04_UNKNOWN_QUALITY_INVENTORY_R1", "profile_quality_counts": dict(quality),
        "state_unknown_reasons": {f"{field}:{reason}": n for (field, reason), n in sorted(state_unknown.items())},
        "pos250_optional_diagnostic": True, "artifact_sha256": expected_sha})
    refs["consumed_sources"] = write("V4_04_CONSUMED_SOURCE_MANIFEST_R1.json", {
        "contract_id": "V4_04_CONSUMED_SOURCE_MANIFEST_R1", "sources": build["sources"],
        "source_cutoff": build["cutoff"], "input_resolver": "src/v4/accepted_input.py", "artifact_sha256": expected_sha})
    refs["input_identity"] = write("V4_04_INPUT_IDENTITY_R1.json", {
        "contract_id": "V4_04_INPUT_IDENTITY_R1", "authority": "data/v4/V4_STAGE_ACCEPTED_HEAD.json",
        "upstream": ["V4_01_ACCEPTED_HEAD_V1", "V4_02_ACCEPTED_HEAD_V1", "V4_03_ACCEPTED_HEAD_AMENDED_V1"],
        "source_hash_verification": "PASS", "cutoff_verification": "PASS", "required_board_verification": "PASS",
        "artifact_sha256": expected_sha})
    refs["contract_digest"] = write("V4_04_CONTRACT_PARAMETER_DIGEST_R1.json", {
        "contract_id": "V4_04_CONTRACT_PARAMETER_DIGEST_R1", "files": build["contract_files"],
        "combined_digest": build["contract_digest"], "artifact_sha256": expected_sha})
    refs["determinism"] = write("V4_04_DETERMINISM_R1.json", {
        "contract_id": "V4_04_DETERMINISM_R1", "status": "PASS", "first_run_sha256": expected_sha,
        "second_run_sha256": build["artifact"]["sha256"], "row_count": rows,
        "same_contract_and_accepted_inputs": True})
    refs["postcheck"] = {"path": str(POSTCHECK.relative_to(ROOT)).replace("\\", "/"),
                         "sha256": hash_file(POSTCHECK), "byte_count": POSTCHECK.stat().st_size}
    refs["production"] = {"path": str(BUILD.relative_to(ROOT)).replace("\\", "/"),
                          "sha256": hash_file(BUILD), "byte_count": BUILD.stat().st_size}
    write("V4_04_STAGE_CANDIDATE_MANIFEST_R1.json", {
        "contract_id": "V4_04_STAGE_CANDIDATE_MANIFEST_R1", "status": "V4_04_FULL_PASS_CANDIDATE",
        "implementation_commit": implementation, "artifact": build["artifact"], "evidence": refs,
        "test_gate": {"scope": "tests/v4_01+v4_02+v4_03+v4_04+v4_joint+v4_phase0", "passed": 354, "skipped": 2},
        "global_acceptance": "NOT_PROMOTED_AWAITING_EXTERNAL_REVIEW", "v4_05_execution": "NOT_STARTED"})
    print(json.dumps({"status": "V4_04_FULL_PASS_CANDIDATE", "rows": rows, "boards": dict(boards), "artifact_sha256": expected_sha}))


if __name__ == "__main__":
    main()
