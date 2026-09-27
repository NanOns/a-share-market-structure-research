from __future__ import annotations

"""Run all affected 00/01/02 and joint tests and bind their exact source tree."""

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402

OUTPUT = Path("reports/v4_joint/V4_00_01_02_JOINT_TEST_RECEIPT_R1_20260928.json")
TEST_DIRS = ("tests/v4_phase0", "tests/v4_01", "tests/v4_02", "tests/v4_joint")
SOURCE_FILES = (
    "config/v4_01_historical_code_change_alias_completeness_v1.json",
    "config/v4_02_r8_cross_stage_postcheck_v1.json",
    "config/v4_joint_final_gate_r1.json",
    "src/workbench_analysis/baostock_supplemental.py",
    "src/workbench_analysis/dated_security_alias.py",
    "src/workbench_analysis/v4_01_required_scope.py",
    "src/workbench_analysis/v4_01_alias_completeness.py",
    "src/workbench_analysis/v4_joint_receipt.py",
    "src/workbench_analysis/special_price_phases.py",
    "src/v4/contracts/algorithm_contract.py",
    "scripts/v4_01_historical_code_change_alias_completeness_r8.py",
    "scripts/v4_01_r8_identity_universe_postcheck.py",
    "scripts/v4_02_r8_cross_stage_postcheck.py",
    "scripts/v4_joint_run_test_gate_r1.py",
    "scripts/v4_joint_seal_receipts_r1.py",
    "scripts/v4_joint_evidence_change_receipt_r1.py",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_digest() -> tuple[str, list[dict[str, str]]]:
    files: list[dict[str, str]] = []
    for directory in TEST_DIRS:
        for path in sorted((ROOT / directory).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            rel = path.relative_to(ROOT).as_posix()
            files.append({"path": rel, "sha256": sha256(path)})
    root_hash = hashlib.sha256(
        "\n".join(f"{row['path']}:{row['sha256']}" for row in files).encode("utf-8")
    ).hexdigest()
    return root_hash, files


def main() -> int:
    command = [sys.executable, "-m", "pytest", "-q", *TEST_DIRS]
    started = time.perf_counter()
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    duration = time.perf_counter() - started
    output = (result.stdout or "") + (result.stderr or "")
    import re

    # Use the final pytest summary line only.
    summary_lines = [line for line in output.splitlines() if " passed" in line or " failed" in line or " skipped" in line]
    summary_line = summary_lines[-1] if summary_lines else ""
    passed_match = re.search(r"(\d+) passed", summary_line)
    failed_match = re.search(r"(\d+) failed", summary_line)
    skipped_match = re.search(r"(\d+) skipped", summary_line)
    passed = int(passed_match.group(1)) if passed_match else 0
    failed = int(failed_match.group(1)) if failed_match else (1 if result.returncode else 0)
    skipped = int(skipped_match.group(1)) if skipped_match else 0
    digest, test_files = tree_digest()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    source_hashes = {name: sha256(ROOT / name) for name in SOURCE_FILES if (ROOT / name).is_file()}
    status = "PASS" if result.returncode == 0 and failed == 0 and passed > 0 else "BLOCKED"
    receipt = {
        "contract_id": "V4_00_01_02_JOINT_TEST_RECEIPT_R1",
        "version": "1.0.0",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "command": "python -m pytest -q tests/v4_phase0 tests/v4_01 tests/v4_02 tests/v4_joint",
        "input_commit": "1a70c8c733096936da4fa250a3f4def501ccfd1d",
        "execution_commit": head,
        "test_scope": list(TEST_DIRS),
        "test_tree_digest": digest,
        "test_files": test_files,
        "test_summary": {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration_seconds": round(duration, 3),
            "python_version": sys.version.split()[0],
            "pytest_version": subprocess.check_output(
                [sys.executable, "-m", "pytest", "--version"], cwd=ROOT, text=True
            ).strip(),
            "summary_line": summary_line,
        },
        "affected_source_digests": source_hashes,
        "input_files": {"task_card_sha256": sha256(ROOT / "docs/evidence/V4_PRE03_JOINT_FINAL_SEAL_TASK_R1_20260927.md"),
                        "rev2_sha256": sha256(ROOT / "docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md")},
        "test_exit_code": result.returncode,
        "output_tail": output[-4000:],
    }
    _atomic_json(ROOT / OUTPUT, receipt)
    print(json.dumps({"status": status, "summary": receipt["test_summary"], "test_tree_digest": digest,
                      "receipt": OUTPUT.as_posix()}, ensure_ascii=False))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
