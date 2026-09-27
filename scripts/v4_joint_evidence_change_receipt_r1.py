from __future__ import annotations

"""Bind evidence-only seal files to the tested business-code commit."""

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402

OUTPUT = Path("reports/v4_joint/V4_00_01_02_EVIDENCE_CHANGE_RECEIPT_R1_20260928.json")
EVIDENCE_FILES = (
    "reports/v4_01/V4_01_HISTORICAL_CODE_CHANGE_ALIAS_COMPLETENESS_R8.json",
    "reports/v4_01/V4_01_R8_IDENTITY_UNIVERSE_POSTCHECK_20260928.json",
    "reports/v4_01/v4_01_final_stage_receipt_R8_20260928.json",
    "reports/v4_01/V4_01_R8_FINAL_EXTERNAL_ACCEPTANCE_20260928.json",
    "docs/evidence/V4_01_R8_FINAL_EXTERNAL_ACCEPTANCE_20260928.md",
    "reports/v4_phase0/V4_PHASE0_STAGE_RECEIPTS_R5_20260928.json",
    "reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json",
    "reports/v4_02/V4_02_R8_CROSS_STAGE_POSTCHECK_20260928.json",
    "reports/v4_joint/V4_00_01_02_JOINT_TEST_RECEIPT_R1_20260928.json",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> int:
    head = git("rev-parse", "HEAD")
    test_receipt = json.loads((ROOT / EVIDENCE_FILES[-1]).read_text(encoding="utf-8"))
    changed_code = git("diff", "--name-only", head, "--", "src", "scripts", "config", "tests").splitlines()
    untracked_code = git("ls-files", "--others", "--exclude-standard", "--", "src", "scripts", "config", "tests").splitlines()
    changed_code_files = sorted(set(changed_code) | set(untracked_code))
    files = []
    missing = []
    for name in EVIDENCE_FILES:
        path = ROOT / name
        if not path.is_file():
            missing.append(name)
            continue
        files.append({"path": name, "sha256": sha256(path), "bytes": path.stat().st_size})
    status = "PASS" if not changed_code_files and not missing and test_receipt.get("execution_commit") == head else "BLOCKED"
    receipt = {
        "contract_id": "V4_00_01_02_EVIDENCE_CHANGE_RECEIPT_R1",
        "version": "1.0.0",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "tested_business_code_head": test_receipt.get("execution_commit"),
        "evidence_base_head": head,
        "business_code_changed_after_tested_head": bool(changed_code_files),
        "business_code_changed_files": changed_code_files,
        "evidence_files": files,
        "missing_expected_evidence_files": missing,
        "joint_receipt_is_created_after_this_inventory": True,
        "next_stage": "JOINT_FINAL_RECEIPT" if status == "PASS" else "BLOCKED_TESTED_CODE_HEAD_MISMATCH_OR_POST_TEST_CODE_CHANGE",
    }
    _atomic_json(ROOT / OUTPUT, receipt)
    print(json.dumps({"status": status, "evidence_files": len(files), "business_code_changed_files": changed_code_files,
                      "receipt": OUTPUT.as_posix()}, ensure_ascii=False))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
