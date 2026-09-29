"""Verify frozen Accepted Head bindings and emit the V4-05 R4.1 hash policy."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.v4.canonical_governance_hash import (
    CANONICAL_JSON_SHA256_V1,
    CANONICAL_TEXT_SHA256_V1,
    canonical_json_file_sha256,
)

REPORT = ROOT / "reports/v4_05"
BASE = "e751c9dc63ba6e6325b50daa15e849091e18f5dc"
FROZEN_GO_FORWARD_BINDING = "83fa37ded40337d69ff0e447a0b6a3bc293d2ca95ea9c8aa009f0f104776c4be"
GO_FORWARD = "data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json"
STAGE_HEAD = "data/v4/V4_STAGE_ACCEPTED_HEAD.json"
PROTECTED = (
    STAGE_HEAD,
    "data/v4/V4_01_ACCEPTED_HEAD.json",
    "data/v4/V4_02_ACCEPTED_HEAD.json",
    GO_FORWARD,
    "data/v4/V4_03_ACCEPTED_HEAD_AMENDED_R1.json",
    "data/v4/V4_04_ACCEPTED_HEAD.json",
)


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True).stdout


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def canonical_lf_sha(path: Path) -> str:
    raw = path.read_bytes()
    return sha256(raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    os.replace(temp, path)


def build() -> dict:
    global_head = json.loads((ROOT / STAGE_HEAD).read_text("utf-8"))
    binding = global_head.get("v4_02_go_forward_pit_binding", {})
    go_forward_path = ROOT / GO_FORWARD
    raw_sha = file_sha(go_forward_path)
    json_sha = canonical_json_file_sha256(go_forward_path)
    base_blob = git("rev-parse", f"{BASE}:{GO_FORWARD}").decode().strip()
    current_blob = git("rev-parse", f"HEAD:{GO_FORWARD}").decode().strip()
    repository_bytes = git("show", f"HEAD:{GO_FORWARD}")
    repository_lf = repository_bytes.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    repository_lf_sha = sha256(repository_lf).hexdigest()
    reconstructed_crlf = repository_lf.replace(b"\n", b"\r\n")
    reconstructed_crlf_sha = sha256(reconstructed_crlf).hexdigest()
    working_tree_diff_clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", GO_FORWARD], cwd=ROOT).returncode == 0
    protected = {}
    for relative in PROTECTED:
        before = git("rev-parse", f"{BASE}:{relative}").decode().strip()
        current = git("rev-parse", f"HEAD:{relative}").decode().strip()
        diff_clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", relative], cwd=ROOT).returncode == 0
        protected[relative] = {"starting_git_blob": before, "current_git_blob": current,
                               "worktree_diff_clean": diff_clean,
                               "unchanged": before == current and diff_clean,
                               "canonical_json_sha256": canonical_json_file_sha256(ROOT / relative)}
    absent = "data/v4/V4_05_ACCEPTED_HEAD.json"
    absent_at_base = subprocess.run(["git", "cat-file", "-e", f"{BASE}:{absent}"], cwd=ROOT,
                                    capture_output=True).returncode != 0
    absent_now = not (ROOT / absent).exists()
    go_forward_valid = (
        base_blob == current_blob
        and reconstructed_crlf_sha == FROZEN_GO_FORWARD_BINDING
        and binding.get("path") == GO_FORWARD
        and binding.get("sha256") == reconstructed_crlf_sha
        and binding.get("byte_count") == len(reconstructed_crlf)
        and working_tree_diff_clean
    )
    all_protected = all(row["unchanged"] for row in protected.values())
    validation = {
        "contract_id": "V4_05_R4_1_ACCEPTED_HEAD_HASH_VALIDATION_V1",
        "status": "PASS" if go_forward_valid and all_protected and absent_at_base and absent_now else "FAIL",
        "starting_head": BASE,
        "go_forward_head": {
            "path": GO_FORWARD,
            "starting_git_blob": base_blob,
            "current_git_blob": current_blob,
            "git_blob_unchanged": base_blob == current_blob,
            "working_tree_raw_sha256": raw_sha,
            "repository_canonical_lf_sha256": repository_lf_sha,
            "reconstructed_frozen_crlf_sha256": reconstructed_crlf_sha,
            "reconstructed_frozen_crlf_byte_count": len(reconstructed_crlf),
            "working_tree_diff_clean": working_tree_diff_clean,
            "canonical_json_sha256": json_sha,
            "global_stage_binding_sha256": binding.get("sha256"),
            "global_stage_binding_byte_count": binding.get("byte_count"),
            "repository_lf_sha_matches_frozen_sha": repository_lf_sha == FROZEN_GO_FORWARD_BINDING,
            "frozen_representation_matches_global_stage_binding": binding.get("sha256") == reconstructed_crlf_sha,
            "frozen_promotion_sha256": FROZEN_GO_FORWARD_BINDING,
            "canonical_json_identity_is_separate_from_frozen_binding": json_sha != FROZEN_GO_FORWARD_BINDING,
        },
        "protected_heads": protected,
        "v4_05_accepted_head": {"absent_at_start": absent_at_base, "absent_now": absent_now},
        "head_files_changed": 0,
        "stage_record": {
            "stage_contract": "V4_05_REPLAY_GATE_A_R4_1_POSTGRES_HASH_CLOSURE",
            "acceptance_result": "PASS" if go_forward_valid and all_protected and absent_at_base and absent_now else "FAIL",
            "evidence": "Unchanged Git blob, recreated frozen CRLF-byte promotion binding, parsed canonical JSON identity, clean tracked path, and unchanged protected heads.",
            "next_stage": "INDEPENDENT_EXTERNAL_AUDIT_R4_1",
        },
    }
    policy = {
        "contract_id": "V4_05_R4_1_CANONICAL_HASH_POLICY_V1",
        "status": validation["status"],
        "stage_contract": "V4_05_REPLAY_GATE_A_R4_1_POSTGRES_HASH_CLOSURE",
        "governance_json_identity": {
            "algorithm_id": CANONICAL_JSON_SHA256_V1,
            "parse": "UTF-8 JSON (optional BOM), parsed as JSON values",
            "serialize": "UTF-8; ensure_ascii=false; sort_keys=true; separators=(',',':'); allow_nan=false; no newline",
            "use": "Business/source identity for JSON governance heads and JSON report inputs; independent of file whitespace and line endings.",
        },
        "ordinary_governance_text_identity": {
            "algorithm_id": CANONICAL_TEXT_SHA256_V1,
            "normalize": "UTF-8 without BOM; CRLF and CR normalized to LF",
        },
        "frozen_promotion_binding_compatibility": {
            "algorithm_id": "FROZEN_ACCEPTED_HEAD_SHA256_V1",
            "scope": GO_FORWARD,
            "reason": "Preserve the externally promoted immutable binding by recreating its original CRLF file representation from the unchanged Git LF blob. Downstream business identities use CANONICAL_JSON_SHA256_V1.",
            "frozen_promotion_sha256": FROZEN_GO_FORWARD_BINDING,
            "repository_canonical_lf_sha256": repository_lf_sha,
            "reconstructed_frozen_crlf_sha256": reconstructed_crlf_sha,
            "global_stage_binding_sha256": binding.get("sha256"),
            "binding_valid": go_forward_valid,
            "canonical_json_sha256": json_sha,
        },
        "binary_artifact_identity": "SHA256 of raw bytes for gzip, parquet, zip, and GBBQ payloads.",
        "prohibited_identity_input": "OS working-tree raw-byte SHA for governance files.",
        "newline_negative_test": {
            "test": "tests/v4_05/test_v4_05_r4_1_canonical_hash.py",
            "lf_crlf_raw_hashes_may_differ": True,
            "canonical_governance_sha_and_downstream_identity_must_match": True,
        },
    }
    atomic_json(REPORT / "V4_05_R4_1_CANONICAL_HASH_POLICY.json", policy)
    atomic_json(REPORT / "V4_05_R4_1_ACCEPTED_HEAD_HASH_VALIDATION.json", validation)
    if validation["status"] != "PASS":
        raise RuntimeError("protected accepted-head binding validation failed")
    return {"status": validation["status"], "canonical_json_sha256": json_sha,
            "repository_lf_sha256": repository_lf_sha,
            "reconstructed_frozen_binding_sha256": reconstructed_crlf_sha,
            "global_binding_matches": go_forward_valid,
            "protected_heads_unchanged": all_protected}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, sort_keys=True))
