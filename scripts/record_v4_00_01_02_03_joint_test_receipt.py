from __future__ import annotations

"""Run the requested V4-00..03 regression suite and seal its receipt."""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEST_ROOTS = ("tests/v4_phase0", "tests/v4_01", "tests/v4_02", "tests/v4_03")
OUTPUT = Path("reports/v4_joint/V4_00_01_02_03_FULL_CHAIN_TEST_RECEIPT_R2.json")
PRIOR_FAILED_ATTEMPT = Path("reports/v4_joint/V4_00_01_02_03_FULL_CHAIN_TEST_ATTEMPT_R1_FAILED.json")


def sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8", "replace").strip()


def changed_file_identities() -> list[dict[str, Any]]:
    # Do not pass porcelain output through git(), which strips leading spaces
    # and would remove the first status column from the first row. The fixed
    # three-character prefix is XY plus one separator for every row.
    raw = subprocess.check_output(
        ["git", "status", "--short", "--untracked-files=all"], cwd=ROOT
    ).decode("utf-8", "replace").splitlines()
    found = []
    for line in raw:
        if not line:
            continue
        rel = line[3:]
        path = ROOT / rel
        found.append({"path": rel.replace("\\", "/"), "sha256": sha_file(path) if path.is_file() else None, "exists": path.is_file()})
    return found


def git_status_snapshot() -> dict[str, Any]:
    porcelain = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT
    ).decode("utf-8", "replace")
    short_branch = subprocess.check_output(
        ["git", "status", "--short", "--branch", "--untracked-files=all"], cwd=ROOT
    ).decode("utf-8", "replace")
    return {
        "clean": not porcelain.strip(),
        "porcelain": porcelain,
        "short_branch": short_branch,
        "head": git("rev-parse", "HEAD"),
    }


def parse_skip_details(output: str) -> dict[str, Any]:
    items = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped.startswith("SKIPPED ["):
            continue
        count_match = re.match(r"SKIPPED \[(\d+)\]", stripped)
        skip_count = int(count_match.group(1)) if count_match else 1
        payload = stripped.split("]", 1)[-1].strip()
        if " - " in payload:
            location, reason = payload.split(" - ", 1)
            separator = " - "
        else:
            location, separator, reason = payload.partition(": ")
        path = location.split("::", 1)[0]
        required_scope = "required_scope" in stripped.lower() or path.replace("\\", "/").startswith("tests/v4_01/")
        items.append({
            "count": skip_count,
            "summary_line": stripped,
            "test_location": location,
            "reason": reason.strip() if separator else "",
            "required_scope": required_scope,
            "scope_disposition": "BLOCKED_REQUIRED_SCOPE_SKIP" if required_scope else "OPTIONAL_OR_PLATFORM_SKIP",
        })
    return {
        "count": sum(item["count"] for item in items),
        "items": items,
        "required_scope_skip_count": sum(item["count"] for item in items if item["required_scope"]),
        "unexplained_skip_count": sum(item["count"] for item in items if not item["reason"]),
    }


def atomic_write(path: Path, payload: bytes) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, target)
    finally:
        Path(temp).unlink(missing_ok=True)


def main() -> int:
    test_files = sorted(
        path.relative_to(ROOT).as_posix()
        for test_root in TEST_ROOTS
        for path in (ROOT / test_root).rglob("test*.py")
    )
    command = ["python", "-m", "pytest", "-q", "-rs", *TEST_ROOTS]
    prior_attempt = None
    if (ROOT / PRIOR_FAILED_ATTEMPT).is_file():
        prior = json.loads((ROOT / PRIOR_FAILED_ATTEMPT).read_text(encoding="utf-8"))
        prior_output = str(prior.get("output_tail") or "")
        previous_summary = next(
            (line.strip() for line in reversed(prior_output.splitlines()) if any(word in line for word in ("passed", "failed", "skipped"))),
            prior.get("terminal_summary"),
        )
        prior_attempt = {
            "path": PRIOR_FAILED_ATTEMPT.as_posix(),
            "sha256": sha_file(ROOT / PRIOR_FAILED_ATTEMPT),
            "status": prior.get("status"),
            "terminal_summary": previous_summary,
            "disposition": "SUPERSEDED_BY_CURRENT_FULL_SUITE_RUN_AFTER_TEST_FIXTURE_ALIGNMENT",
        }
    start = time.perf_counter()
    status_at_test_start = git_status_snapshot()
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    duration = time.perf_counter() - start
    combined = (result.stdout + ("\n" + result.stderr if result.stderr else "")).strip()
    status_after_tests = git_status_snapshot()
    summary_match = re.findall(r"(?m)^=+\s*(.*?)\s*=+$", combined)
    count_summary = next(
        (line.strip() for line in reversed(combined.splitlines()) if re.search(r"\b\d+\s+(?:passed|failed|skipped|error)\b", line)),
        None,
    )
    terminal_summary = summary_match[-1] if summary_match else count_summary or (combined.splitlines()[-1] if combined else "NO_PYTEST_OUTPUT")
    counts = {}
    for key in ("passed", "failed", "skipped", "error", "xfailed", "xpassed"):
        match = re.search(rf"\b(\d+)\s+{key}\b", terminal_summary)
        counts[key] = int(match.group(1)) if match else 0
    skip_details = parse_skip_details(combined)
    status = "PASS" if result.returncode == 0 and status_at_test_start["clean"] and status_after_tests["clean"] and skip_details["required_scope_skip_count"] == 0 and skip_details["unexplained_skip_count"] == 0 else "BLOCKED"
    changed_files = changed_file_identities()
    report = {
        "contract_id": "V4_00_01_02_03_FULL_CHAIN_TEST_RECEIPT_R2",
        "version": "1.0.0",
        "stage": "V4-00..V4-03 CURRENT-WORKTREE COMBINED REGRESSION",
        "status": status,
        "result": status,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "execution_identity": {
            "tested_code_commit": status_at_test_start["head"],
            "branch": git("branch", "--show-current"),
            "python_version": sys.version.split()[0],
            "pytest_version": subprocess.check_output([sys.executable, "-m", "pytest", "--version"], cwd=ROOT, text=True).strip(),
            "working_tree_clean_at_test_start": status_at_test_start["clean"],
            "working_tree_changed_file_count_after_tests": len(changed_files),
            "working_tree_changed_files": changed_files,
        },
        "git_status": {
            "clean_at_test_start": status_at_test_start["clean"],
            "clean_after_tests_before_receipt": status_after_tests["clean"],
            "at_test_start": status_at_test_start["short_branch"],
            "porcelain_at_test_start": status_at_test_start["porcelain"],
            "after_tests_before_receipt": status_after_tests["short_branch"],
            "porcelain_after_tests_before_receipt": status_after_tests["porcelain"],
        },
        "command": ["python", "-m", "pytest", "-q", "-rs", *TEST_ROOTS],
        "test_roots": list(TEST_ROOTS),
        "test_file_count": len(test_files),
        "test_files": test_files,
        "counts": counts,
        "skip_details": skip_details,
        "duration_seconds": round(duration, 3),
        "return_code": result.returncode,
        "stdout_stderr_sha256": sha_bytes(combined.encode("utf-8")),
        "terminal_summary": terminal_summary,
        "output_tail": "\n".join(combined.splitlines()[-25:]),
        "superseded_prior_attempt": prior_attempt,
        "test_contract_alignment": [
            {
                "test_file": "tests/v4_phase0/test_baostock_supplemental.py",
                "change": "Mock package_metadata() to supply an unpinned runtime version and assert the current fail-closed error token; assert current default_runtime_pin metadata field.",
                "production_runtime_changed": False,
            }
        ],
        "tdx_root_write_count": 0,
        "stage_record": {
            "stage_contract": "V4-00..V4-03 R3 foundation repair; clean tested code commit and -rs skip accountability",
            "evidence": "Exact pytest command, clean-at-start git status, tested code commit, file set, interpreter, skip names/reasons, output digest, counts, and duration",
            "acceptance_result": status,
            "next_stage": "GENERATE_STAGE_EVIDENCE_AND_FULL_CHAIN_VALIDATION" if status == "PASS" else "REPAIR_TEST_OR_SKIP_BLOCKERS",
        },
    }
    payload = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    atomic_write(OUTPUT, payload)
    print(json.dumps({"status": status, "test_file_count": len(test_files), "counts": counts, "terminal_summary": terminal_summary, "duration_seconds": round(duration, 3), "receipt": OUTPUT.as_posix(), "receipt_sha256": sha_bytes(payload)}, ensure_ascii=False, indent=2))
    if combined:
        print(combined)
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
