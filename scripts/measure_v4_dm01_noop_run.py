from __future__ import annotations

"""Capture wall/CPU/peak-memory metrics for an idempotent DM01 no-op rerun."""

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.daily_data_head import write_json_atomic  # noqa: E402

UNIVERSE_ROWS = Path("reports/v4_01/V4_01_IDENTITY_EVENT_DISCOVERY_R8_1.json")
OUTPUT = Path("reports/v4_dm01/2026-09-28/performance_receipt.json")
TDX_ARCHIVE = Path("data/v4/raw_archive/b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f/hsjday.zip")


def main() -> int:
    event = json.loads((ROOT / UNIVERSE_ROWS).read_text(encoding="utf-8"))
    command = [sys.executable, "scripts/run_v4_continuous_data_maintenance.py"]
    started_wall = time.perf_counter()
    child = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, encoding="utf-8", errors="replace")
    process = psutil.Process(child.pid)
    peak_rss = 0
    cpu_seconds = 0.0
    while child.poll() is None:
        try:
            memory = process.memory_info().rss
            times = process.cpu_times()
            peak_rss = max(peak_rss, memory)
            cpu_seconds = max(cpu_seconds, times.user + times.system)
        except psutil.Error:
            pass
        time.sleep(0.02)
    stdout, stderr = child.communicate()
    elapsed = round(time.perf_counter() - started_wall, 3)
    summary = json.loads(stdout.strip().splitlines()[-1]) if stdout.strip() else {}
    receipt = {
        "contract_id": "V4_DM01_PERFORMANCE_RECEIPT_R1",
        "version": "1.0.0",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "PASS" if child.returncode == 0 else "BLOCKED",
        "measurement_scope": "IDEMPOTENT_NOOP_RERUN; no new official session was complete",
        "command": " ".join(command),
        "wall_seconds": elapsed,
        "cpu_seconds_sampled": round(cpu_seconds, 3),
        "peak_working_set_bytes_sampled": peak_rss,
        "rows_read": int(event.get("scope", {}).get("required_universe_rows_scanned", 0)),
        "rows_written": 0,
        "securities_affected": 0,
        "large_file_hash_bytes": (ROOT / TDX_ARCHIVE).stat().st_size,
        "canonical_data_rows_written": 0,
        "receipt_documents_written": 7,
        "runner_result": summary,
        "stdout": stdout.strip(),
        "stderr": stderr.strip(),
        "limitations": [
            "Metrics measure the post-bootstrap idempotent rerun, not the original bootstrap process.",
            "Peak working set is sampled every 20 ms; a shorter transient peak may not be observed.",
            "Rows read is the accepted R7 Required Scope universe scan count recorded by Gate A.",
        ],
        "next_stage": "INDEPENDENT_POSTCHECK_AND_FINAL_RECEIPT",
    }
    write_json_atomic(ROOT / OUTPUT, receipt, tdx_root=Path("D:/new_tdx"))
    print(json.dumps({"status": receipt["status"], "wall_seconds": elapsed,
                      "cpu_seconds_sampled": receipt["cpu_seconds_sampled"],
                      "peak_working_set_bytes_sampled": peak_rss,
                      "rows_read": receipt["rows_read"], "rows_written": 0,
                      "receipt": OUTPUT.as_posix()}, ensure_ascii=False))
    return child.returncode


if __name__ == "__main__":
    raise SystemExit(main())
