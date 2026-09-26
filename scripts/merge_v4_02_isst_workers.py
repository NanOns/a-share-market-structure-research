from __future__ import annotations

"""Validate and atomically merge the four full-market dated isST shards."""

import argparse
import gzip
import hashlib
import heapq
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(value, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def next_item(stream):
    line = stream.readline()
    if not line:
        return None
    obj = json.loads(line)
    return (str(obj["trade_date"]), str(obj["source_security_key"]).lower()), obj


def merge(args) -> int:
    universe = ROOT / args.universe
    output = ROOT / args.output
    receipt_path = ROOT / args.receipt
    ledger_path = ROOT / args.ledger
    shard_dir = ROOT / args.shard_dir
    worker_report_dir = ROOT / args.worker_report_dir
    worker_ledger_dir = ROOT / args.worker_ledger_dir
    worker_receipts, worker_artifacts, worker_ledgers = [], [], []
    for index in range(args.workers):
        receipt_path_i = worker_report_dir / f"worker_{index}.json"
        artifact_path_i = shard_dir / f"worker_{index}.jsonl.gz"
        ledger_path_i = worker_ledger_dir / f"worker_{index}.json"
        receipt = json.loads(receipt_path_i.read_text(encoding="utf-8"))
        if receipt.get("worker_index") != index or receipt.get("worker_count") != args.workers:
            raise SystemExit("ISST_WORKER_RECEIPT_PARTITION_MISMATCH")
        if receipt.get("artifact", {}).get("sha256") != sha(artifact_path_i):
            raise SystemExit("ISST_WORKER_ARTIFACT_HASH_MISMATCH")
        worker_receipts.append(receipt)
        worker_artifacts.append(artifact_path_i)
        worker_ledgers.append(ledger_path_i)
    if len(worker_receipts) != args.workers:
        raise SystemExit("ISST_WORKER_RECEIPT_COUNT_MISMATCH")

    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=output.name + ".", suffix=".tmp", dir=output.parent)
    os.close(fd)
    temp = Path(temp_name)
    counts: Counter[str] = Counter()
    digest = hashlib.sha256()
    row_count = 0
    streams = [gzip.open(path, "rt", encoding="utf-8") for path in worker_artifacts]
    heap = []
    try:
        for worker_id, stream in enumerate(streams):
            item = next_item(stream)
            if item:
                heapq.heappush(heap, (item[0], worker_id, item[1]))
        prior_key = None
        with gzip.open(temp, "wt", encoding="utf-8", newline="\n", compresslevel=6) as target:
            while heap:
                sort_key, worker_id, row = heapq.heappop(heap)
                if sort_key == prior_key:
                    raise RuntimeError("ISST_DUPLICATE_SECURITY_DATE")
                prior_key = sort_key
                text = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                target.write(text)
                digest.update(text.encode("utf-8"))
                row_count += 1
                if row.get("is_st") in {"0", "1"}:
                    counts["IS_ST_" + row["is_st"]] += 1
                else:
                    counts[str(row.get("binding_quality"))] += 1
                following = next_item(streams[worker_id])
                if following:
                    heapq.heappush(heap, (following[0], worker_id, following[1]))
        with temp.open("rb+") as f:
            f.flush()
            os.fsync(f.fileno())
        if row_count != 4036121:
            raise RuntimeError(f"ISST_ROWS_MISMATCH:{row_count}")
        # Independent primary-key/coverage reconciliation against the accepted universe.
        seen = 0
        with gzip.open(universe, "rt", encoding="utf-8") as expected, gzip.open(temp, "rt", encoding="utf-8") as actual:
            for exp_line, got_line in zip(expected, actual, strict=True):
                exp, got = json.loads(exp_line), json.loads(got_line)
                if (exp["security_id"] != got["security_id"] or exp["source_security_key"] != got["source_security_key"]
                        or exp["trade_date"] != got["trade_date"]):
                    raise RuntimeError("ISST_UNIVERSE_BINDING_MISMATCH")
                seen += 1
        if seen != row_count:
            raise RuntimeError("ISST_UNIVERSE_RECONCILIATION_COUNT_MISMATCH")
        os.replace(temp, output)
    finally:
        for stream in streams:
            stream.close()
        if temp.exists():
            temp.unlink()

    # Merge isolated worker budgets into the central durable request ledger after workers stop.
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    day_entry = ledger.setdefault("by_shanghai_date", {}).setdefault(today, {"count": 0, "operations": {}})
    aggregation = {}
    added_count = 0
    for index, path in enumerate(worker_ledgers):
        value = json.loads(path.read_text(encoding="utf-8"))
        entry = value.get("by_shanghai_date", {}).get(today)
        if not entry:
            raise RuntimeError("WORKER_REQUEST_LEDGER_DATE_MISSING")
        added_count += int(entry.get("count", 0))
        for operation, count in entry.get("operations", {}).items():
            day_entry.setdefault("operations", {})[operation] = int(day_entry["operations"].get(operation, 0)) + int(count)
        aggregation[f"worker_{index}"] = {"request_count": int(entry["count"]), "sha256": sha(path)}
    day_entry["count"] = int(day_entry.get("count", 0)) + added_count
    ledger["last_updated_at_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    ledger["full_market_isst_worker_aggregation"] = aggregation
    atomic_json(ledger_path, ledger)

    unknown = row_count - counts["IS_ST_0"] - counts["IS_ST_1"]
    failures = [failure for receipt in worker_receipts for failure in receipt.get("query_failures", [])]
    sessions = [row["trade_date"] for receipt in worker_receipts for row in receipt.get("query_receipts", [])]
    if len(sessions) != 786 or len(set(sessions)) != 786:
        raise RuntimeError("ISST_QUERY_SESSION_COVERAGE_MISMATCH")
    receipt = {
        "contract_id": "V4_02_DATED_ST_STATUS_V1",
        "version": "1.0.0",
        "stage": "V4-02 / FINAL CLOSURE PACK",
        "status": "DATED_ST_STATUS_PASS" if not unknown and not failures and len(sessions) == 786 else "DATED_ST_STATUS_WITH_UNKNOWN",
        "stage_contract": "V4_02_FULL_MARKET_DATED_ISST_V1",
        "source_cutoff": "2026-09-24",
        "session_count": len(sessions),
        "membership_rows": row_count,
        "is_st_value_counts": {"0": counts["IS_ST_0"], "1": counts["IS_ST_1"], "UNKNOWN": unknown},
        "binding_quality_counts": {key: value for key, value in counts.items() if key not in {"IS_ST_0", "IS_ST_1"}},
        "query_failure_count": len(failures),
        "query_failures": failures,
        "query_receipt_count": len(sessions),
        "query_receipts": sorted([q for r in worker_receipts for q in r.get("query_receipts", [])], key=lambda x: x["trade_date"]),
        "artifact": {"path": args.output, "row_count": row_count, "sha256": sha(output)},
        "normalized_output_sha256": digest.hexdigest(),
        "input_hashes": {"universe_sha256": sha(universe), "worker_receipt_hashes": [sha(worker_report_dir / f"worker_{i}.json") for i in range(args.workers)]},
        "worker_ledgers": aggregation,
        "request_ledger_sha256": sha(ledger_path),
        "execution_identity": {"merge_script_sha256": sha(Path(__file__).resolve()),
                               "worker_script_sha256": sha(ROOT / "scripts/build_v4_02_isst_worker.py"),
                               "finished_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat()},
        "next_stage": "PRICE_LIMIT_RULE_V1_AND_WHOLE_STAGE_FINAL_PUBLICATION",
        "limitations": ["BaoStock is a supplemental status source, not a price authority.",
                        "Missing or invalid provider rows remain UNKNOWN; no status is inferred from a local bar."],
    }
    atomic_json(receipt_path, receipt)
    print(json.dumps({"status": receipt["status"], "rows": row_count, "sessions": len(sessions),
                      "unknown": unknown, "failures": len(failures), "artifact_sha256": receipt["artifact"]["sha256"]}, ensure_ascii=False))
    return 0 if receipt["status"] == "DATED_ST_STATUS_PASS" else 2


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--universe", default="data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R6_2_20260926.jsonl.gz")
    p.add_argument("--output", default="data/v4/artifact_store/v4_02/V4_02_DATED_ST_STATUS_V1_R6_2_20260926.jsonl.gz")
    p.add_argument("--receipt", default="reports/v4_02/V4_02_DATED_ST_STATUS_V1_R6_2_20260926.json")
    p.add_argument("--ledger", default="reports/v4_baostock/request_ledger.json")
    p.add_argument("--shard-dir", default="data/v4/artifact_store/v4_02/.isst_workers")
    p.add_argument("--worker-report-dir", default="reports/v4_02/.isst_workers")
    p.add_argument("--worker-ledger-dir", default="reports/v4_baostock/.isst_worker_ledgers")
    return merge(p.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
