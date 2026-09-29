from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    command = [sys.executable, "-m", "pytest", "tests/v4_07", "-q"]
    environment = os.environ.copy()
    environment["V4_07_ACCEPTED_INPUTS_ROOT"] = str(
        Path(environment.get("V4_07_ACCEPTED_INPUTS_ROOT", str(ROOT))).resolve()
    )
    result = subprocess.run(command, cwd=ROOT, env=environment, text=True, capture_output=True, check=False)
    output = (result.stdout + result.stderr).strip()
    receipt = {
        "contract_id": "V4_07_R2_RUNTIME_TEST_RECEIPT_V1",
        "stage_contract": "V4_06_R2_CONTRACT_REPAIR_AND_V4_07_BASE_SEED_STAGE_TASK_20260929",
        "command": "python -m pytest tests/v4_07 -q",
        "exit_code": result.returncode,
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "test_scope": [
            "frozen BASE_SEED machine vectors",
            "parameter-set fixture perturbation synchronized across machine executor, production evaluator, and independent verifier",
            "production evaluator rejects threshold literal fallback",
            "accepted run context binds source publication, date, digest, identity count, and board scope",
            "T and T+1 synthetic accepted-context isolation with different row counts",
            "future-date rows do not affect prior-date output",
            "V4-06 forbidden-input isolation",
            "accepted-input determinism",
        ],
        "accepted_inputs_root": environment["V4_07_ACCEPTED_INPUTS_ROOT"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "output": output,
    }
    atomic_json(ROOT / "reports/v4_07/V4_07_R2_RUNTIME_TEST_RECEIPT.json", receipt)
    print(json.dumps({"status": receipt["status"], "summary": output.splitlines()[-1] if output else ""}, sort_keys=True))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
