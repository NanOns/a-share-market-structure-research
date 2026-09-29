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
OUTPUT = Path("reports/v4_joint/V4_00_01_02_03_FULL_CHAIN_TEST_RECEIPT_R1.json")
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
    raw = git("status", "--short", "--untracked-files=all").splitlines()
    found = []
    for line in raw:
        rel = line[3:].strip()
        path = ROOT / rel
        found.append({"path": rel.replace("\\", "/"), "sha256": sha_file(path) if path.is_file() else None, "exists": path.is_file()})
    return found


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
    command = [sys.executable, "-m", "pytest", "-q", *TEST_ROOTS]
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
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    duration = time.perf_counter() - start
    combined = (result.stdout + ("\n" + result.stderr if result.stderr else "")).strip()
    summary_match = re.findall(r"(?m)^=+\s*(.*?)\s*=+$", combined)
    terminal_summary = summary_match[-1] if summary_match else combined.splitlines()[-1] if combined else "NO_PYTEST_OUTPUT"
    counts = {}
    for key in ("passed", "failed", "skipped", "error", "xfailed", "xpassed"):
        match = re.search(rf"\b(\d+)\s+{key}\b", terminal_summary)
        counts[key] = int(match.group(1)) if match else 0
    status = "PASS" if result.returncode == 0 else "FAIL"
    changed_files = changed_file_identities()
    report = {
        "contract_id": "V4_00_01_02_03_FULL_CHAIN_TEST_RECEIPT_R1",
        "version": "1.0.0",
        "stage": "V4-00..V4-03 CURRENT-WORKTREE COMBINED REGRESSION",
        "status": status,
        "result": status,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "execution_identity": {
            "tested_commit": git("rev-parse", "HEAD"),
            "branch": git("branch", "--show-current"),
            "python_version": sys.version.split()[0],
            "pytest_version": subprocess.check_output([sys.executable, "-m", "pytest", "--version"], cwd=ROOT, text=True).strip(),
            "working_tree_changed_file_count": len(changed_files),
            "working_tree_changed_files": changed_files,
        },
        "command": ["python", "-m", "pytest", "-q", *TEST_ROOTS],
        "test_roots": list(TEST_ROOTS),
        "test_file_count": len(test_files),
        "test_files": test_files,
        "counts": counts,
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
            "stage_contract": "V4-00..V4-03 R2 foundation closure task combined current-HEAD regression",
            "evidence": "Exact pytest command, file set, interpreter, output digest, counts, and duration",
            "acceptance_result": status,
            "next_stage": "RUN_CANDIDATE_FULL_CHAIN_VALIDATOR" if status == "PASS" else "REPAIR_TEST_FAILURES",
        },
    }
    payload = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    atomic_write(OUTPUT, payload)
    print(json.dumps({"status": status, "test_file_count": len(test_files), "counts": counts, "terminal_summary": terminal_summary, "duration_seconds": round(duration, 3), "receipt": OUTPUT.as_posix(), "receipt_sha256": sha_bytes(payload)}, ensure_ascii=False, indent=2))
    if combined:
        print(combined)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
