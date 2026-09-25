from __future__ import annotations

"""Validate and atomically publish disjoint bounded R5 dated-roster shards."""

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
from zoneinfo import ZoneInfo

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
    parser.add_argument("--candidate-receipt", default="reports/v4_01/historical_evaluable_universe_receipt_R4_20260925.json")
    parser.add_argument("--shard-receipts", nargs="+", required=True)
    parser.add_argument("--attempt-receipts", nargs="*", default=[])
    parser.add_argument("--central-ledger", default="reports/v4_baostock/request_ledger.json")
    parser.add_argument("--output", default="data/v4/artifact_store/v4_01/baostock_dated_rosters_R5_20260925.jsonl.gz")
    parser.add_argument("--receipt", default="reports/v4_01/baostock_dated_roster_receipt_R5_20260925.json")
    args = parser.parse_args()
    candidate_path = ROOT / args.candidate_receipt
    candidate = json.loads(candidate_path.read_text("utf-8"))
    sessions = [row["trade_date"] for row in candidate["daily_reconstructed_universe"]["days"]]
    shards = []
    for receipt_name in args.shard_receipts:
        receipt_path = ROOT / receipt_name
        receipt = json.loads(receipt_path.read_text("utf-8"))
        if receipt.get("status") != "BUILT" or receipt.get("failures"):
            raise SystemExit(f"ROSTER_SHARD_NOT_BUILT:{receipt_name}")
        out = ROOT / receipt["output"]["path"]
        if sha256(out) != receipt["output"]["sha256"]:
            raise SystemExit(f"ROSTER_SHARD_DIGEST_MISMATCH:{receipt_name}")
        shards.append((receipt_path, receipt, out))
    shards.sort(key=lambda item: item[1]["input"]["slice_start_index"])
    cursor = 0
    for _, receipt, _ in shards:
        info = receipt["input"]
        if (info.get("full_session_count") != len(sessions) or info.get("slice_start_index") != cursor
                or info.get("slice_end_index_exclusive") <= cursor):
            raise SystemExit("ROSTER_SHARD_COVERAGE_GAP_OR_OVERLAP")
        cursor = info["slice_end_index_exclusive"]
    if cursor != len(sessions):
        raise SystemExit("ROSTER_SHARD_COVERAGE_INCOMPLETE")

    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=output_path.name + ".", suffix=".tmp", dir=output_path.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    daily_counts = []
    digest_root = hashlib.sha256()
    total_rows = 0
    with gzip.open(temp_path, "wt", encoding="utf-8", newline="\n", compresslevel=6) as destination:
        for _, receipt, shard_path in shards:
            start = receipt["input"]["slice_start_index"]
            end = receipt["input"]["slice_end_index_exclusive"]
            expected_dates = sessions[start:end]
            local_daily = receipt["daily_counts"]
            if [row["trade_date"] for row in local_daily] != expected_dates:
                raise SystemExit("ROSTER_SHARD_DAILY_COUNT_DATE_MISMATCH")
            shard_digest = hashlib.sha256()
            count = 0
            with gzip.open(shard_path, "rt", encoding="utf-8") as source:
                for index, line in enumerate(source):
                    if index >= len(expected_dates):
                        raise SystemExit("ROSTER_SHARD_EXTRA_DAILY_ROWS")
                    record = json.loads(line)
                    day, codes = record["trade_date"], record["source_codes"]
                    summary = local_daily[index]
                    if (day != expected_dates[index] or record.get("contract_id") != "BAOSTOCK_DATED_ROSTER_SNAPSHOT_V1"
                            or codes != sorted(set(codes)) or record.get("row_count") != len(codes)
                            or hashlib.sha256("\n".join(codes).encode("ascii")).hexdigest() != record.get("codes_sha256")
                            or summary.get("codes_sha256") != record.get("codes_sha256")
                            or summary.get("row_count") != len(codes)):
                        raise SystemExit("ROSTER_SHARD_RECORD_VALIDATION_FAILED")
                    destination.write(line)
                    shard_digest.update(f"{day}\0{len(codes)}\0{record['codes_sha256']}\n".encode("ascii"))
                    digest_root.update(f"{day}\0{len(codes)}\0{record['codes_sha256']}\n".encode("ascii"))
                    total_rows += len(codes)
                    count += 1
            if count != len(expected_dates) or shard_digest.hexdigest() != receipt["output"].get("daily_roster_digest_root"):
                raise SystemExit("ROSTER_SHARD_COUNT_OR_ROOT_DIGEST_INVALID")
            daily_counts.extend(local_daily)
    with temp_path.open("rb+") as stream:
        os.fsync(stream.fileno())
    os.replace(temp_path, output_path)

    ledger_path = ROOT / args.central_ledger
    ledger = json.loads(ledger_path.read_text("utf-8")) if ledger_path.exists() else {"ledger_version": 1, "by_shanghai_date": {}}
    before_total = sum(int(item.get("count", 0)) for item in ledger["by_shanghai_date"].values())
    aggregate_delta = 0
    worker_ledgers = []
    rollover_adjustments = []
    for _, receipt, _ in shards:
        ledger_name = receipt.get("request_budget", {}).get("ledger_path")
        if not ledger_name:
            if not receipt.get("request_budget", {}).get("ledger_already_aggregated"):
                raise SystemExit("ROSTER_SHARD_LEDGER_BINDING_MISSING")
            continue
        worker_ledger_path = ROOT / ledger_name
        worker = json.loads(worker_ledger_path.read_text("utf-8"))
        worker_total = sum(int(item.get("count", 0)) for item in worker.get("by_shanghai_date", {}).values())
        aggregate_delta += worker_total
        worker_ledgers.append({"path": ledger_name, "sha256": sha256(worker_ledger_path),
                               "request_count": worker_total})
        rollover_adjustments.extend({"ledger": ledger_name, **item}
                                    for item in worker.get("rollover_adjustments", []))
        for day, day_doc in worker.get("by_shanghai_date", {}).items():
            target = ledger["by_shanghai_date"].setdefault(day, {"count": 0, "operations": {}})
            target["count"] = int(target.get("count", 0)) + int(day_doc.get("count", 0))
            for operation, amount in day_doc.get("operations", {}).items():
                target.setdefault("operations", {})[operation] = int(target["operations"].get(operation, 0)) + int(amount)
    after_total = before_total + aggregate_delta
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    today_total = int(ledger["by_shanghai_date"].get(today, {}).get("count", 0))
    if after_total > 45_000 or today_total > 40_000:
        raise SystemExit("AGGREGATED_REQUEST_BUDGET_EXCEEDED")
    ledger["last_updated_at_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    _atomic_json(ledger_path, ledger)
    attempts = []
    for name in args.attempt_receipts:
        path = ROOT / name
        attempt = json.loads(path.read_text("utf-8"))
        attempts.append({"path": name, "sha256": sha256(path), "status": attempt.get("status"),
                         "completed_sessions_before_retry": attempt.get("partial_checkpoint", {}).get("completed_sessions", 0),
                         "query_failure_count": attempt.get("query_failure_count", 0),
                         "failure": attempt.get("failures", {})})
    receipt_doc = {"stage": "V4-01-BAOSTOCK-DATED-ROSTERS-R5", "contract_id": "BAOSTOCK_DATED_ROSTER_SNAPSHOT_V1",
                   "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                   "status": "BUILT", "stage_completion_authorized": False,
                   "source": {"provider": "BaoStock", "method": "query_all_stock(day)", "auth_mode": "PUBLIC_ANONYMOUS",
                              "source_document": "https://www.baostock.com/mainContent?file=pythonAPI.md"},
                   "input": {"candidate_receipt": args.candidate_receipt, "candidate_receipt_sha256": sha256(candidate_path),
                             "session_basis": candidate["formal_window"]["session_basis"], "first_session": sessions[0],
                             "last_session": sessions[-1], "session_count": len(sessions)},
                   "output": {"path": args.output, "sha256": sha256(output_path), "byte_count": output_path.stat().st_size,
                              "format": "GZIP_JSONL", "total_roster_rows": total_rows,
                              "daily_roster_digest_root": digest_root.hexdigest()},
                   "daily_counts": daily_counts,
                   "request_budget": {"ledger_path": args.central_ledger, "before_total_count": before_total,
                                      "after_total_count": after_total, "request_count_delta": aggregate_delta,
                                      "configured_soft_cap": 40_000, "configured_hard_cap": 45_000,
                                      "provider_limit": 50_000, "shard_ledgers": worker_ledgers,
                                      "rollover_adjustments": rollover_adjustments},
                   "worker_receipts": [{"path": path, "sha256": sha256(ROOT / path)} for path, _, _ in shards],
                   "retry_attempts": attempts,
                   "query_failure_count_total": sum(int(row.get("query_failure_count", 0)) for row in attempts)
                                                + sum(int(receipt.get("query_failure_count", 0)) for _, receipt, _ in shards),
                   "execution_identity": {"input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                                          "script_sha256": sha256(Path(__file__))},
                   "next_stage": "V4_01_STABLE_IDENTITY_AND_BSE_LIFECYCLE_R5"}
    _atomic_json(ROOT / args.receipt, receipt_doc)
    print(json.dumps({"status": receipt_doc["status"], "session_count": len(daily_counts), "total_rows": total_rows,
                      "request_count_delta": aggregate_delta, "output_sha256": receipt_doc["output"]["sha256"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
