from __future__ import annotations

"""Run and bind the V4-01 Phase 0 regression suite to the current R6.2 code head."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402

CODE_FILES = (
    "scripts/v4_01_lifecycle_boundary_resolution_r6_2.py",
    "scripts/v4_01_materialize_lifecycle_boundaries_r6_2.py",
    "scripts/v4_01_historical_universe_r6_2.py",
    "scripts/v4_01_final_stage_receipt_r6_2.py",
    "scripts/apply_v4_phase0_schema.py",
    "scripts/v4_01_test_receipt_r6_2.py",
    "src/workbench_analysis/v4_01_required_scope.py",
    "src/workbench_db/migrations/v4_postgres/011_security_membership_interval_r6_2.sql",
    "src/workbench_db/migrations/v4_postgres/012_provider_lifecycle_fact_r6_2.sql",
    "tests/v4_phase0/test_v4_01_required_scope_r6.py",
    "tests/v4_phase0/test_postgres_schema.py",
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="reports/v4_01/v4_01_test_receipt_R6_2_20260926.json")
    args = ap.parse_args()
    test = subprocess.run([sys.executable, "-m", "pytest", "tests/v4_phase0", "-q"], cwd=ROOT,
                          text=True, capture_output=True)
    compile_result = subprocess.run(
        [sys.executable, "-m", "py_compile", *CODE_FILES[:6]], cwd=ROOT,
        text=True, capture_output=True,
    )
    output = (test.stdout or "") + (test.stderr or "")
    match = re.search(r"(\d+) passed(?:, (\d+) skipped)?(?:, (\d+) failed)?", output)
    sha = lambda name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    status = "PASS" if test.returncode == 0 and compile_result.returncode == 0 and match else "BLOCKED"
    receipt = {
        "stage": "V4-01-R6_2-REQUIRED-SCOPE-REGRESSION-TESTS",
        "contract_id": "V4_01_TEST_RECEIPT_R6_2_V1",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "tested_head": head,
        "test_scope": "tests/v4_phase0",
        "test_command": "python -m pytest tests/v4_phase0 -q",
        "test_summary": {"passed": int(match.group(1)) if match else None,
                         "skipped": int(match.group(2) or 0) if match else None,
                         "failed": int(match.group(3) or 0) if match else None},
        "py_compile_status": "PASS" if compile_result.returncode == 0 else "BLOCKED",
        "py_compile_files": list(CODE_FILES[:6]),
        "test_exit_code": test.returncode,
        "py_compile_exit_code": compile_result.returncode,
        "test_output_tail": output[-2400:],
        "implementation_sha256": {name: sha(name) for name in CODE_FILES},
        "execution_identity": {"tested_head": head},
    }
    _atomic_json(ROOT / args.output, receipt)
    print(json.dumps({"status": status, "tested_head": head, "test_summary": receipt["test_summary"],
                      "py_compile_status": receipt["py_compile_status"], "receipt": args.output}, ensure_ascii=False))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
