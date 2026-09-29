"""Finalize hash-bound R4 stage records after remote LFS restoration succeeds."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/v4_05"
BASE = "9864939068a633e650de232f2f285681592a6528"
IMPLEMENTATION = "0e5b7585c5bd1e332ce6d11c6dfd1e4ff6cb6108"
ARTIFACT_COMMIT = "569b55862cd6115bc4456ccfb0ee7e98ee42da42"
PROTECTED = (
    "data/v4/V4_STAGE_ACCEPTED_HEAD.json", "data/v4/V4_01_ACCEPTED_HEAD.json",
    "data/v4/V4_02_ACCEPTED_HEAD.json", "data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json",
    "data/v4/V4_03_ACCEPTED_HEAD_AMENDED_R1.json", "data/v4/V4_04_ACCEPTED_HEAD.json",
)
REQUIRED = (
    "V4_05_R4_STAGE_ENTRY.md", "V4_05_R4_PERIOD_ASOF.json",
    "V4_05_R4_MARKET_SNAPSHOT_IDENTITY.json", "V4_05_R4_MARKET_REFERENCE.json",
    "V4_05_R4_MARKET_REFERENCE_INDEPENDENT_RECALC.json", "V4_05_R4_MARKET_PATH_CONTINUATION.json",
    "V4_05_R4_MARKET_PATH_COORDINATE_DIAGNOSTIC.json", "V4_05_R4_MARKET_REGIME.json",
    "V4_05_R4_REVISION_LEDGER_IDEMPOTENCY.json", "V4_05_R4_REMOTE_LFS_RESTORE.json",
    "V4_05_R4_INDEPENDENT_NUMERIC_POSTCHECK.json", "V4_05_R4_CORE_PROFILE_REPLAY.json",
    "V4_05_R4_R3_DIFF.json", "V4_05_R4_DETERMINISM.json", "V4_05_R4_CAPABILITY_GATE.json",
    "V4_05_R4_RUNTIME_TEST_RECEIPT.json", "V4_05_R4_INDEPENDENT_POSTCHECK.json", "V4_05_R4_CLOSURE.md",
    "V4_05_R4_TARGET_MARKET_SNAPSHOT.json", "V4_05_R4_FULL_SCOPE_FACTORS_RECEIPT.json",
    "V4_05_R4_DAILY_HISTORY_RECEIPT.json", "V4_05_R4_CALENDAR_RECEIPT.json",
)
LFS = (
    "staging/V4_05_R4_PERIOD_ASOF.jsonl.gz", "staging/V4_05_R4_FULL_SCOPE_FACTORS.jsonl.gz",
    "staging/V4_05_R4_FULL_MARKET_CORE_PROFILE.jsonl.gz",
)
SOURCE_DOCS = (
    "docs/evidence/V4_05_REPLAY_GATE_A_R4_CONTRACT_IDENTITY_REPAIR_TASK_20260929.md",
    "docs/evidence/V4_05_REPLAY_GATE_A_R3_EXTERNAL_AUDIT_20260929.md",
)


def file_sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_text(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def git_bytes(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True).stdout


def finalize() -> dict:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    remote = json.loads((REPORT / "V4_05_R4_REMOTE_LFS_RESTORE.json").read_text(encoding="utf-8"))
    if remote["status"] != "PASS" or remote["artifact_count"] != 8 or remote["verified_remote_commit"] != ARTIFACT_COMMIT:
        raise ValueError("fresh-clone LFS restore is missing or incomplete")

    stage_path = REPORT / "V4_05_R4_STAGE_ENTRY.md"
    stage = stage_path.read_text(encoding="utf-8")
    stage = stage.replace(
        "- Fresh-clone LFS recovery proof will be attached after the pushed artifact commit.",
        "- Fresh-clone Git LFS recovery passed for all 8 R3/R4 large artifacts after explicit fetch and checkout; pointer OIDs, expected/restored byte counts, and restored SHA256 all match the receipt.")
    atomic_text(stage_path, stage)

    closure_path = REPORT / "V4_05_R4_CLOSURE.md"
    closure = closure_path.read_text(encoding="utf-8")
    closure = closure.replace(
        "Remote LFS restore evidence is pending the fresh clone of the pushed artifact commit and will be bound in the final R4 candidate manifest.",
        f"Fresh-clone remote LFS recovery passed for all five R3 artifacts and all three new R4 LFS artifacts; every pointer OID, byte count, and restored SHA256 matched. The receipt records remote commit `{ARTIFACT_COMMIT}`.")
    atomic_text(closure_path, closure)

    independent_path = REPORT / "V4_05_R4_INDEPENDENT_POSTCHECK.json"
    independent = json.loads(independent_path.read_text(encoding="utf-8"))
    independent.update({"remote_lfs_restore_status": "PASS", "remote_lfs_artifact_count": 8,
                        "remote_lfs_verified_commit": ARTIFACT_COMMIT})
    independent["status"] = "PASS" if all(independent.get(key) == "PASS" for key in
                                           ("market_reference_status", "market_path_diagnostic_status", "numeric_postcheck_status")) else "FAIL"
    tmp = independent_path.with_suffix(independent_path.suffix + ".tmp")
    tmp.write_text(json.dumps(independent, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, independent_path)
    if independent["status"] != "PASS":
        raise ValueError("independent postcheck failed")

    heads = {}
    for rel in PROTECTED:
        baseline = git_bytes("show", f"{BASE}:{rel}").replace(b"\r\n", b"\n")
        current = (ROOT / rel).read_bytes().replace(b"\r\n", b"\n")
        before_sha, current_sha = sha256(baseline).hexdigest(), sha256(current).hexdigest()
        heads[rel] = {"starting_sha256": before_sha, "current_sha256": current_sha, "unchanged": before_sha == current_sha}
        if before_sha != current_sha:
            raise ValueError(f"protected Accepted Head changed: {rel}")
    absent_path = "data/v4/V4_05_ACCEPTED_HEAD.json"
    absent_at_start = subprocess.run(["git", "cat-file", "-e", f"{BASE}:{absent_path}"], cwd=ROOT, capture_output=True).returncode != 0
    if not absent_at_start or (ROOT / absent_path).exists():
        raise ValueError("V4-05 Accepted Head was created or modified")
    heads[absent_path] = {"starting_state": "ABSENT", "current_state": "ABSENT", "unchanged": True}

    artifacts = {}
    for name in REQUIRED:
        path = REPORT / name
        if not path.is_file():
            raise FileNotFoundError(path)
        artifacts[path.relative_to(ROOT).as_posix()] = {"byte_count": path.stat().st_size, "sha256": file_sha(path)}
    for name in LFS:
        path = REPORT / name
        artifacts[path.relative_to(ROOT).as_posix()] = {"byte_count": path.stat().st_size,
                                                        "sha256": file_sha(path), "storage": "git-lfs"}
    source_docs = {}
    for name in SOURCE_DOCS:
        path = ROOT / name
        source_docs[name] = {"byte_count": path.stat().st_size, "sha256": file_sha(path)}
    tool_path = ROOT / "scripts/finalize_v4_05_r4_candidate.py"
    tool = {"path": tool_path.relative_to(ROOT).as_posix(), "byte_count": tool_path.stat().st_size, "sha256": file_sha(tool_path)}

    diff = json.loads((REPORT / "V4_05_R4_R3_DIFF.json").read_text(encoding="utf-8"))
    determinism = json.loads((REPORT / "V4_05_R4_DETERMINISM.json").read_text(encoding="utf-8"))
    tests = json.loads((REPORT / "V4_05_R4_RUNTIME_TEST_RECEIPT.json").read_text(encoding="utf-8"))
    numeric = json.loads((REPORT / "V4_05_R4_INDEPENDENT_NUMERIC_POSTCHECK.json").read_text(encoding="utf-8"))
    ledger = json.loads((REPORT / "V4_05_R4_REVISION_LEDGER_IDEMPOTENCY.json").read_text(encoding="utf-8"))
    if diff["status"] != "PASS" or diff["unexpected_business_value_drift"] != 0 or determinism["status"] != "PASS":
        raise ValueError("profile diff or determinism gate failed")
    if tests["status"] != "PASS" or tests["implementation_commit"] != IMPLEMENTATION or numeric["status"] != "PASS" or ledger["status"] != "PASS":
        raise ValueError("runtime, numeric, or isolated-ledger gate failed")

    manifest = {
        "contract_id": "V4_05_R4_STAGE_CANDIDATE_MANIFEST_V1",
        "status": "V4_05_DATA_FACTOR_REPLAY_DEGRADED_PASS_CANDIDATE_R4",
        "stage": "V4-05 Replay Gate A R4 Contract Identity Repair",
        "branch": "codex/v4-system-reform", "starting_head": BASE,
        "implementation_commit": IMPLEMENTATION, "artifact_commit": ARTIFACT_COMMIT,
        "target_trade_date": "2026-09-28",
        "formal_publication_at": "2026-09-29T06:53:52+00:00",
        "stage_record": {"stage_contract": "V4_05_REPLAY_GATE_A_R4_CONTRACT_IDENTITY_REPAIR",
                          "acceptance_result": "DEGRADED_PASS_CURRENT_FORWARD_STOCK_CORE_CANDIDATE_R4; EXTERNAL_ACCEPTANCE_PENDING",
                          "evidence": "Hash-bound R4 contract and identity repairs, isolated revision-ledger replay, fresh-clone LFS restoration, independent numeric and market checks, deterministic replay, runtime tests, and protected-head checks.",
                          "next_stage": "INDEPENDENT_EXTERNAL_AUDIT_R4"},
        "data_factor_replay_pass": {"scope": "CURRENT_FORWARD_STOCK_CORE", "status": "DEGRADED_PASS"},
        "external_acceptance": "PENDING",
        "historical_as_recorded_adjusted_price": "BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE",
        "tdx_root_write_count": 0, "accepted_heads_unchanged": heads,
        "source_documents": source_docs, "evidence_generation_tool": tool, "artifacts": artifacts,
        "gates": {
            "runtime_tests": {"status": tests["status"], "passed": tests["passed"], "failed": tests["failed"],
                              "skipped": tests["skipped"], "implementation_commit": tests["implementation_commit"]},
            "independent_postcheck": independent["status"],
            "independent_numeric_postcheck": numeric["status"],
            "market_reference_independent_recalculation": json.loads((REPORT / "V4_05_R4_MARKET_REFERENCE_INDEPENDENT_RECALC.json").read_text(encoding="utf-8"))["status"],
            "revision_ledger": ledger["status"],
            "remote_lfs_restore": {"status": remote["status"], "artifact_count": remote["artifact_count"],
                                    "verified_remote_commit": remote["verified_remote_commit"]},
            "determinism": determinism["status"],
            "r3_r4_profile_diff": {"status": diff["status"], "row_set_same": diff["row_set"]["same_ordered_id_set"],
                                   "unexpected_business_value_drift": diff["unexpected_business_value_drift"]}},
        "created_at_utc": now,
    }
    manifest_path = REPORT / "V4_05_R4_STAGE_CANDIDATE_MANIFEST.json"
    tmp = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, manifest_path)
    return {"manifest": manifest_path.relative_to(ROOT).as_posix(), "manifest_sha256": file_sha(manifest_path),
            "artifact_count": len(artifacts), "accepted_heads_unchanged": all(row["unchanged"] for row in heads.values()),
            "remote_lfs_restore": remote["status"], "external_acceptance": "PENDING"}


if __name__ == "__main__":
    print(json.dumps(finalize(), ensure_ascii=False, sort_keys=True))
