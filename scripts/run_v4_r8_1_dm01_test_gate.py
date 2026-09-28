from __future__ import annotations

"""Run the requested 00/01/02/joint and DM01 regression gate with a receipt."""

import hashlib
import json
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.daily_data_head import write_json_atomic  # noqa: E402

TEST_ROOTS = ("tests/v4_phase0", "tests/v4_01", "tests/v4_02", "tests/v4_joint", "tests/v4_dm01")
BOUND_PATHS = (
    "config/security_identity_event_discovery_v1.json",
    "config/v4_continuous_data_maintenance_v1.json",
    "config/v4_data_accepted_head_v1.json",
    "config/v4_dm01_bridge_calendar_v1.json",
    "src/workbench_analysis/security_identity_event_discovery.py",
    "src/workbench_analysis/daily_source_freeze.py",
    "src/workbench_analysis/daily_data_head.py",
    "src/workbench_analysis/continuous_data_maintenance.py",
    "scripts/v4_01_identity_event_discovery_r8_1.py",
    "scripts/independent_v4_01_r8_1_postcheck.py",
    "scripts/run_v4_continuous_data_maintenance.py",
    "scripts/independent_v4_dm01_postcheck.py",
    "scripts/run_v4_r8_1_dm01_test_gate.py",
    "scripts/seal_v4_01_r8_1_gate_a.py",
)
OUTPUT = Path("reports/v4_joint/V4_R8_1_DM01_TEST_RECEIPT_R1_20260928.json")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with (ROOT / path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    test_files = sorted(path.relative_to(ROOT).as_posix()
                        for folder in TEST_ROOTS for path in (ROOT / folder).rglob("test_*.py"))
    started = time.perf_counter()
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *TEST_ROOTS],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    elapsed = round(time.perf_counter() - started, 3)
    output = (result.stdout + ("\n" + result.stderr if result.stderr else "")).strip()
    summary = output.splitlines()[-1] if output else ""
    counts = {name: 0 for name in ("passed", "failed", "skipped", "error", "xfailed", "xpassed")}
    for value, label in re.findall(r"\b(\d+)\s+(passed|failed|skipped|error|xfailed|xpassed)\b", summary):
        counts[label] = int(value)
    receipt = {
        "contract_id": "V4_R8_1_DM01_TEST_RECEIPT_R1",
        "version": "1.0.0",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "PASS" if result.returncode == 0 else "BLOCKED",
        "execution_head": head,
        "command": f"{Path(sys.executable).name} -m pytest -q {' '.join(TEST_ROOTS)}",
        "python_version": platform.python_version(),
        "pytest_version": subprocess.check_output([sys.executable, "-m", "pytest", "--version"],
                                                   cwd=ROOT, text=True).strip(),
        "elapsed_seconds": elapsed,
        "return_code": result.returncode,
        "counts": counts,
        "test_roots": list(TEST_ROOTS),
        "test_files": [{"path": name, "sha256": sha(Path(name))} for name in test_files],
        "test_tree_sha256": hashlib.sha256("\n".join(
            f"{row['path']}:{row['sha256']}" for row in
            [{"path": name, "sha256": sha(Path(name))} for name in test_files]
        ).encode("utf-8")).hexdigest(),
        "implementation_files": [{"path": name, "sha256": sha(Path(name))} for name in BOUND_PATHS],
        "output_tail": output.splitlines()[-30:],
        "next_stage": "RUN_R8_1_DISCOVERY_AND_INDEPENDENT_POSTCHECK" if result.returncode == 0
        else "REPAIR_TEST_GATE_FAILURES",
    }
    write_json_atomic(ROOT / OUTPUT, receipt, tdx_root=Path("D:/new_tdx"))
    print(json.dumps({"status": receipt["status"], "counts": counts, "elapsed_seconds": elapsed,
                      "receipt": OUTPUT.as_posix(), "summary": summary}, ensure_ascii=False))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
