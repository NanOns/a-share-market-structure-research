from __future__ import annotations

"""Run the requested R4 and frozen R3 regression suites and record evidence."""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/v4_02/V4_02_FINAL_R4_TEST_RECEIPT.json"
TARGETS = ["tests/v4_02/test_final_r3_repairs.py", "tests/v4_02/test_final_r4_special_price_phase.py"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(value, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main() -> int:
    command = [sys.executable, "-m", "pytest", "-q", *TARGETS]
    run = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(run.stdout, end="")
    match = re.search(r"(?P<passed>\d+) passed(?:, (?P<failed>\d+) failed)?(?:, (?P<skipped>\d+) skipped)?", run.stdout)
    passed = int(match.group("passed")) if match else 0
    failed = int(match.group("failed") or 0) if match else (0 if run.returncode == 0 else 1)
    skipped = int(match.group("skipped") or 0) if match else 0
    git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True)
    receipt = {
        "contract_id": "V4_02_FINAL_R4_TEST_RECEIPT", "version": "4.0.0",
        "result": "PASS" if run.returncode == 0 and failed == 0 and skipped == 0 and passed > 0 else "FAIL",
        "passed": passed, "failed": failed, "skipped": skipped,
        "command": "python -m pytest -q " + " ".join(TARGETS),
        "execution_commit": git.stdout.strip(),
        "tested_files": {p: sha(ROOT / p) for p in TARGETS},
        "r3_22_test_freeze_receipt": {"path": "reports/v4_02/V4_02_FINAL_R3_TEST_RECEIPT.json",
            "sha256": sha(ROOT / "reports/v4_02/V4_02_FINAL_R3_TEST_RECEIPT.json"), "result": "PASS", "passed": 22},
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "output": run.stdout[-8000:],
    }
    atomic_json(OUT, receipt)
    print(json.dumps({"receipt": str(OUT.relative_to(ROOT)), "result": receipt["result"], "passed": passed, "failed": failed, "skipped": skipped}))
    return 0 if receipt["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
