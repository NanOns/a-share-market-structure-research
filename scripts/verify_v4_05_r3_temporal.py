"""Execute all required R3 temporal negative tests and record their identities."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / "tests/v4_05/test_replay_gate_a_r3.py"
OUT = ROOT / "reports/v4_05/V4_05_R3_TEMPORAL_LEAKAGE.json"
CASES = {
    "A_T_PLUS_ONE_RAW": "test_future_raw_price_does_not_enter_t0_history",
    "B_LATER_WEEK_SESSION": "test_future_sessions_cannot_change_monday_or_month_asof[WEEKLY]",
    "C_FUTURE_MONTH_END": "test_future_sessions_cannot_change_monday_or_month_asof[MONTHLY]",
    "D_FUTURE_IDENTITY": "test_future_identity_metadata_cannot_change_target_membership",
    "E_LATER_GBBQ_REVISION": "test_later_gbbq_revision_cannot_replace_accepted_snapshot",
    "F_LATE_PROVIDER": "test_late_provider_is_excluded",
    "G_FUTURE_FACTOR_SOURCE": "test_future_factor_source_is_hard_blocked",
    "H_FUTURE_MARKET_INPUT": "test_future_market_regime_input_is_hard_blocked",
}


def main():
    command = [sys.executable, "-m", "pytest", "-q", str(TEST)]
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if run.returncode != 0 or "10 passed" not in run.stdout:
        raise RuntimeError(run.stdout + run.stderr)
    result = {"contract_id": "V4_05_R3_TEMPORAL_NEGATIVE_SUITE_V1", "status": "PASS", "command": "python -m pytest -q tests/v4_05/test_replay_gate_a_r3.py", "exit_code": run.returncode,
              "test_file_sha256": sha256(TEST.read_bytes()).hexdigest(), "cases": {key: {"test": name, "status": "PASS"} for key, name in CASES.items()},
              "additional_positive_checks": 2, "pytest_summary": run.stdout.strip().splitlines()[-1]}
    tmp = OUT.with_suffix(".tmp")
    tmp.write_bytes((json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
    os.replace(tmp, OUT)
    print(result["pytest_summary"])


if __name__ == "__main__":
    main()
