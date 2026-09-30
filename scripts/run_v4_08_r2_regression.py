from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FAMILIES = [
    "tests/v4_01", "tests/v4_02", "tests/v4_03", "tests/v4_04", "tests/v4_05",
    "tests/v4_06", "tests/v4_07", "tests/v4_08", "tests/v4_joint", "tests/v4_phase0",
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, default=ROOT / "reports/v4_08/V4_08_R2_REQUIRED_REGRESSION.json")
    args = parser.parse_args()
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="v4_08_r2_regression_") as temp:
        junit = Path(temp) / "junit.xml"
        command = [sys.executable, "-m", "pytest", "-q", *REQUIRED_FAMILIES, f"--junitxml={junit}"]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, encoding="utf-8", errors="replace")
        report = None
        if junit.exists():
            tree = ET.parse(junit)
            suite_nodes = list(tree.getroot().iter("testsuite"))
            tests = sum(int(node.attrib.get("tests", "0")) for node in suite_nodes)
            failures = sum(int(node.attrib.get("failures", "0")) for node in suite_nodes)
            errors = sum(int(node.attrib.get("errors", "0")) for node in suite_nodes)
            skipped = sum(int(node.attrib.get("skipped", "0")) for node in suite_nodes)
            report = {"tests": tests, "passed": tests - failures - errors - skipped,
                      "failures": failures, "errors": errors, "skipped": skipped,
                      "suite_count": len(suite_nodes)}
            junit_bytes = junit.read_bytes()
        else:
            junit_bytes = b""
    evidence = {
        "contract_id": "V4_08_R2_REQUIRED_REGRESSION_V1",
        "status": "PASS" if result.returncode == 0 and report and report["failures"] == 0 and report["errors"] == 0 else "FAIL",
        "required_families": REQUIRED_FAMILIES,
        "command": command,
        "summary": report,
        "junit_xml_sha256": sha(junit_bytes) if junit_bytes else None,
        "pytest_return_code": result.returncode,
        "stdout": result.stdout[-16000:],
        "stderr": result.stderr[-8000:],
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    destination = args.evidence if args.evidence.is_absolute() else ROOT / args.evidence
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    temp_path.write_text(json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temp_path, destination)
    print(json.dumps({"status": evidence["status"], "summary": report, "elapsed_seconds": evidence["elapsed_seconds"]}, sort_keys=True))
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
