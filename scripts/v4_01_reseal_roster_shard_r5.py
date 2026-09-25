from __future__ import annotations

"""Repair gzip trailers for verified JSONL records after a safe interruption."""

import argparse
import gzip
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker-index", type=int, required=True)
    parser.add_argument("--start-index", type=int, required=True)
    parser.add_argument("--end-index", type=int, required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--partial", required=True)
    parser.add_argument("--attempt-receipt", required=True)
    parser.add_argument("--candidate-receipt", default="reports/v4_01/historical_evaluable_universe_receipt_R4_20260925.json")
    args = parser.parse_args()
    candidate_path = ROOT / args.candidate_receipt
    candidate = json.loads(candidate_path.read_text("utf-8"))
    all_sessions = [item["trade_date"] for item in candidate["daily_reconstructed_universe"]["days"]]
    if not 0 <= args.start_index < args.end_index <= len(all_sessions):
        raise SystemExit("ROSTER_SHARD_SLICE_INVALID")
    expected = all_sessions[args.start_index:args.end_index]
    partial_path = ROOT / args.partial
    records = []
    try:
        with gzip.open(partial_path, "rt", encoding="utf-8") as stream:
            for line in stream:
                records.append(json.loads(line))
    except (EOFError, OSError):
        pass
    if not records or len(records) > len(expected):
        raise SystemExit("ROSTER_SHARD_NO_RECOVERABLE_RECORDS_OR_TOO_MANY")
    daily = []
    total = 0
    root = hashlib.sha256()
    for index, record in enumerate(records):
        codes = record.get("source_codes", [])
        digest = hashlib.sha256("\n".join(codes).encode("ascii")).hexdigest()
        if (record.get("trade_date") != expected[index] or record.get("contract_id") != "BAOSTOCK_DATED_ROSTER_SNAPSHOT_V1"
                or codes != sorted(set(codes)) or record.get("row_count") != len(codes) or record.get("codes_sha256") != digest):
            raise SystemExit(f"ROSTER_SHARD_CHECKPOINT_INVALID:{index}")
        daily.append({"trade_date": record["trade_date"], "row_count": len(codes),
                      "page_count": record.get("page_count"), "codes_sha256": digest})
        total += len(codes)
        root.update(f"{record['trade_date']}\0{len(codes)}\0{digest}\n".encode("ascii"))
    fd, temp_name = tempfile.mkstemp(prefix=partial_path.name + ".", suffix=".tmp", dir=partial_path.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    with gzip.open(temp_path, "wt", encoding="utf-8", newline="\n", compresslevel=6) as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    with temp_path.open("rb+") as stream:
        os.fsync(stream.fileno())
    os.replace(temp_path, partial_path)
    ledger_path = ROOT / args.ledger
    ledger = json.loads(ledger_path.read_text("utf-8"))
    ledger_count = sum(int(value.get("count", 0)) for value in ledger.get("by_shanghai_date", {}).values())
    receipt = {"stage": "V4-01-BAOSTOCK-DATED-ROSTER-INTERRUPTED-CHECKPOINT-R5",
               "contract_id": "BAOSTOCK_DATED_ROSTER_SNAPSHOT_V1",
               "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
               "status": "PARTIAL_CHECKPOINT_RESEALED", "stage_completion_authorized": False,
               "interruption_reason": "Budget-date rollover; complete records retained and gzip trailer repaired after JSON, order, count, and daily-digest verification.",
               "input": {"candidate_receipt": args.candidate_receipt, "candidate_receipt_sha256": sha256(candidate_path),
                         "full_session_count": len(all_sessions), "slice_start_index": args.start_index,
                         "slice_end_index_exclusive": args.start_index + len(records), "requested_slice_end_index_exclusive": args.end_index,
                         "completed_sessions": len(records), "first_session": daily[0]["trade_date"],
                         "last_session": daily[-1]["trade_date"]},
               "partial_checkpoint": {"path": args.partial, "sha256": sha256(partial_path),
                                      "byte_count": partial_path.stat().st_size, "total_roster_rows": total,
                                      "daily_roster_digest_root": root.hexdigest()},
               "daily_counts": daily,
               "request_budget": {"ledger_path": args.ledger, "ledger_sha256": sha256(ledger_path),
                                  "requests_recorded_across_dates": ledger_count},
               "execution_identity": {"input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                                      "script_sha256": sha256(Path(__file__))},
               "next_stage": "V4_01_EXACT_DATED_ROSTERS_R5"}
    _atomic_json(ROOT / args.attempt_receipt, receipt)
    print(json.dumps({"status": receipt["status"], "worker": args.worker_index,
                      "completed_sessions": len(records), "last_session": daily[-1]["trade_date"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
