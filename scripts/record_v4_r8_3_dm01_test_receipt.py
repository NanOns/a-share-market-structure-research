from __future__ import annotations

"""Run the authorized R8.3/DM-01 gate tests and atomically record evidence."""

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports/v4_joint/V4_R8_3_DM01_TEST_RECEIPT_R1_20260928.json"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    command = [sys.executable, "-m", "pytest", "-q", "tests/v4_01", "tests/v4_dm01"]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    output = completed.stdout + completed.stderr
    summary_lines = [line for line in output.splitlines()
                     if " in " in line and re.search(r"\b(passed|failed|skipped|error)\b", line)]
    summary_line = summary_lines[-1] if summary_lines else ""
    counts = {"passed": 0, "failed": 0, "skipped": 0, "error": 0, "errors": 0}
    for count, label in re.findall(r"(\d+)\s+(passed|failed|skipped|errors?)\b", summary_line):
        key = "error" if label.startswith("error") else label
        counts[key] += int(count)
    status = "PASS" if completed.returncode == 0 and counts["failed"] == 0 else "BLOCKED"
    test_files = sorted([*ROOT.glob("tests/v4_01/test_*.py"), *ROOT.glob("tests/v4_dm01/test_*.py")])
    receipt = {
        "contract_id": "V4_R8_3_DM01_TEST_RECEIPT_R1",
        "version": "1.0.0",
        "status": status,
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "command": command[1:],
        "exit_code": completed.returncode,
        "counts": counts,
        "test_file_count": len(test_files),
        "test_files": [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)} for path in test_files],
        "stdout_tail": output[-4000:],
        "next_stage": "R8_3_INDEPENDENT_POSTCHECK_AND_GATE_SEAL" if status == "PASS" else "REPAIR_GATE_TEST_FAILURES",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    data = (json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with temporary.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(OUTPUT)
    print(json.dumps({"status": status, "counts": counts, "test_file_count": len(test_files),
                      "receipt": OUTPUT.relative_to(ROOT).as_posix()}, ensure_ascii=False))
    if output and status != "PASS":
        print(output)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
