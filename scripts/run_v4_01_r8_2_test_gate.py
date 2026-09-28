from __future__ import annotations

"""Run the R8.2 and DM01 regression scope and record its exact evidence."""

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.daily_data_head import write_json_atomic  # noqa: E402

OUTPUT = Path("reports/v4_joint/V4_R8_2_DM01_TEST_RECEIPT_R1_20260928.json")
TEST_ROOTS = (Path("tests/v4_01"), Path("tests/v4_dm01"))


def sha(path: Path) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main() -> int:
    command = [sys.executable, "-m", "pytest", "-q", *(root.as_posix() for root in TEST_ROOTS)]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    output = (completed.stdout + completed.stderr).strip()
    summary = output.splitlines()[-1] if output else ""
    counts = {key: int(match.group(1)) if (match := re.search(rf"(\d+) {key}", summary)) else 0
              for key in ("passed", "failed", "skipped", "error", "errors")}
    test_files = sorted(path.relative_to(ROOT).as_posix() for test_root in TEST_ROOTS
                        for path in (ROOT / test_root).rglob("test_*.py"))
    status = "PASS" if completed.returncode == 0 and counts["failed"] == 0 and counts["errors"] == 0 else "BLOCKED"
    receipt = {
        "contract_id": "V4_R8_2_DM01_TEST_RECEIPT_R1",
        "version": "1.0.0",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "command": command[1:],
        "exit_code": completed.returncode,
        "counts": counts,
        "summary": summary,
        "test_file_count": len(test_files),
        "test_files": [{"path": name, "sha256": sha(Path(name))} for name in test_files],
        "runner_sha256": sha(Path(__file__).resolve().relative_to(ROOT)),
        "next_stage": "R8_2_INDEPENDENT_POLICY_POSTCHECK" if status == "PASS" else "REPAIR_TEST_FAILURES",
    }
    write_json_atomic(ROOT / OUTPUT, receipt, tdx_root=Path("D:/new_tdx"))
    print(json.dumps({"status": status, "counts": counts, "summary": summary,
                      "receipt": OUTPUT.as_posix()}, ensure_ascii=False))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
