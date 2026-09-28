"""Replay frozen V4-03 candidate producers and compare artifact bytes."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = {
    "core": ROOT / "reports/v4_03/staging/V4_03_CORE_REQUIRED_SCOPE_DIAGNOSTIC_R1.jsonl.gz",
    "full_scope": ROOT / "reports/v4_03/staging/V4_03_FULL_SCOPE_CANDIDATE_R1.jsonl.gz",
    "market_references": ROOT / "reports/v4_03/V4_03_MARKET_REFERENCE_CANDIDATE_R1.json",
    "market_path": ROOT / "reports/v4_03/staging/V4_03_MARKET_REFERENCE_PATH_CANDIDATE_R1.jsonl.gz",
}
OUTPUT = ROOT / "reports/v4_03/V4_03_DETERMINISM_REPLAY_R1.json"
COMMANDS = ["scripts.run_v4_03_core_frozen_diagnostic",
            "scripts.run_v4_03_market_path_candidate",
            "scripts.run_v4_03_full_scope_candidate"]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    started = time.monotonic()
    before = {name: sha(path) for name, path in ARTIFACTS.items()}
    run_log = []
    for module in COMMANDS:
        result = subprocess.run([sys.executable, "-m", module], cwd=ROOT, check=False,
                                capture_output=True, text=True)
        run_log.append({"module": module, "exit_code": result.returncode,
                        "stdout": result.stdout.strip(), "stderr": result.stderr[-4000:]})
        if result.returncode:
            break
    after = {name: sha(path) for name, path in ARTIFACTS.items()}
    differences = {name: {"before": before[name], "after": after[name]}
                   for name in before if before[name] != after[name]}
    status = "PASS" if len(run_log) == len(COMMANDS) and all(x["exit_code"] == 0 for x in run_log) and not differences else "FAIL"
    report = {"contract_id": "V4_03_DETERMINISM_REPLAY_R1", "status": status,
              "baseline": "V4_DEV_BASELINE_HEAD@2026-09-24", "commands": run_log,
              "artifact_sha256_before": before, "artifact_sha256_after": after,
              "differences": differences, "elapsed_seconds": round(time.monotonic() - started, 3),
              "scanner_run_count": 0, "trading_run_count": 0, "tdx_root_write_count": 0,
              "cache_state": "OS_AND_DUCKDB_CACHE_NOT_CONTROLLED_OR_CLEARED"}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, OUTPUT)
    print(json.dumps({"status": status, "artifact_count": len(after),
                      "differences": len(differences), "elapsed_seconds": report["elapsed_seconds"]}))
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
