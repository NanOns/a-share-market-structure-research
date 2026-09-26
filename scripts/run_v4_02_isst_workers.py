from __future__ import annotations

"""Run four bounded anonymous BaoStock workers and retain per-worker logs."""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--python", default="runtime/v4_baostock_093/Scripts/python.exe")
    args = p.parse_args()
    if args.workers != 4:
        raise SystemExit("V4_02_ISST_WORKER_COUNT_FROZEN_AT_4")
    worker_python = ROOT / args.python
    worker_script = ROOT / "scripts/build_v4_02_isst_worker.py"
    artifact_dir = ROOT / "data/v4/artifact_store/v4_02/.isst_workers"
    report_dir = ROOT / "reports/v4_02/.isst_workers"
    ledger_dir = ROOT / "reports/v4_baostock/.isst_worker_ledgers"
    for directory in (artifact_dir, report_dir, ledger_dir):
        directory.mkdir(parents=True, exist_ok=True)
    children = []
    log_handles = []
    for index in range(args.workers):
        output = artifact_dir / f"worker_{index}.jsonl.gz"
        receipt = report_dir / f"worker_{index}.json"
        ledger = ledger_dir / f"worker_{index}.json"
        log_path = report_dir / f"worker_{index}.log"
        if receipt.exists() or output.exists():
            raise SystemExit(f"WORKER_OUTPUT_ALREADY_EXISTS:{index}")
        log = log_path.open("wb")
        log_handles.append(log)
        child = subprocess.Popen(
            [str(worker_python), str(worker_script), "--worker-index", str(index), "--worker-count", str(args.workers),
             "--output", str(output.relative_to(ROOT)).replace("\\", "/"),
             "--receipt", str(receipt.relative_to(ROOT)).replace("\\", "/"),
             "--ledger", str(ledger.relative_to(ROOT)).replace("\\", "/")],
            cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        children.append((index, child, log_path))
        print(f"worker={index} pid={child.pid} log={log_path.relative_to(ROOT)}", flush=True)
    try:
        last_report = 0.0
        while any(child.poll() is None for _, child, _ in children):
            now = time.monotonic()
            if now - last_report >= 30:
                state = [{"worker": i, "pid": child.pid, "exit_code": child.poll(), "log_bytes": log.stat().st_size}
                         for i, child, log in children]
                print(state, flush=True)
                last_report = now
            time.sleep(5)
        results = [{"worker": i, "pid": child.pid, "exit_code": child.returncode, "log": str(log.relative_to(ROOT))}
                   for i, child, log in children]
        print(results, flush=True)
        return 0 if all(item["exit_code"] == 0 for item in results) else 2
    finally:
        for handle in log_handles:
            handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
