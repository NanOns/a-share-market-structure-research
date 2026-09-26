from __future__ import annotations

"""One bounded worker for the full-market dated isST collection."""

import argparse
import gzip
import hashlib
import importlib.metadata
import json
import os
import socket
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.baostock_supplemental import BaoStockClient, RequestBudget  # noqa: E402


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
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


def atomic_gzip(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    os.close(fd)
    return Path(name)


def digest_rows(rows: list[dict[str, str]]) -> str:
    h = hashlib.sha256()
    for row in sorted(rows, key=lambda x: x["code"]):
        h.update(f"{row['date']}\t{row['code']}\t{row['tradestatus']}\t{row['isST']}\n".encode("ascii"))
    return h.hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--worker-index", type=int, required=True)
    p.add_argument("--worker-count", type=int, required=True)
    p.add_argument("--universe", default="data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R6_2_20260926.jsonl.gz")
    p.add_argument("--contract", default="config/v4_02_full_market_isst_contract_v1.json")
    p.add_argument("--output", required=True)
    p.add_argument("--receipt", required=True)
    p.add_argument("--ledger", required=True)
    args = p.parse_args()
    if args.worker_count < 1 or not (0 <= args.worker_index < args.worker_count):
        raise SystemExit("WORKER_PARTITION_INVALID")
    universe_path, contract_path = ROOT / args.universe, ROOT / args.contract
    output_path, receipt_path, ledger_path = ROOT / args.output, ROOT / args.receipt, ROOT / args.ledger
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    expected_fields = contract["provider"]["expected_fields"]
    failures, receipts = [], []
    counts: Counter[str] = Counter()
    membership_rows = 0
    observed_start = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    temp_path = atomic_gzip(output_path)
    source = gzip.open(universe_path, "rt", encoding="utf-8")
    prior_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(45)
    session = None
    day_index = -1
    day = None
    members: list[dict] = []

    def flush_day(current_day: str, current_members: list[dict], client: BaoStockClient) -> None:
        nonlocal membership_rows
        if (day_index % args.worker_count) != args.worker_index:
            return
        started = time.monotonic()
        normalized: list[dict[str, str]] = []
        err = None
        try:
            rows, meta = client.query_rows("query_daily_history_k_AStock", "query_daily_history_k_AStock",
                                           date=current_day, max_rows=20000, max_pages=1)
            if meta.get("fields") != expected_fields:
                raise RuntimeError("UNEXPECTED_FULL_MARKET_FIELDS")
            seen = set()
            for row in rows:
                code = str(row.get("code", "")).strip().lower()
                row_day = str(row.get("date", ""))
                tradestatus, is_st = str(row.get("tradestatus", "")).strip(), str(row.get("isST", "")).strip()
                if row_day != current_day or not code or code in seen:
                    raise RuntimeError("INVALID_OR_DUPLICATE_PROVIDER_KEY")
                seen.add(code)
                if tradestatus in {"0", "1"} and is_st in {"0", "1"}:
                    normalized.append({"date": current_day, "code": code, "tradestatus": tradestatus, "isST": is_st})
            provider = {row["code"]: row for row in normalized}
            source_revision = "sha256:" + digest_rows(normalized)
            for member in current_members:
                key = str(member["source_security_key"]).lower()
                fact = provider.get(key)
                result = {"security_id": member["security_id"], "source_security_key": member["source_security_key"],
                          "trade_date": current_day, "is_st": fact["isST"] if fact else None,
                          "source_provider": "BAOSTOCK_PUBLIC_ANONYMOUS_QUERY_DAILY_HISTORY_K_ASTOCK",
                          "binding_quality": "DIRECT_CODE_DATE" if fact else "UNKNOWN_NO_VALID_PROVIDER_ROW",
                          "source_revision": source_revision if fact else None}
                line = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                target.write(line)
                counts[result["binding_quality"]] += 1
                counts["IS_ST_" + str(result["is_st"])] += 1
            receipts.append({"trade_date": current_day, "partition_index": args.worker_index,
                             "required_membership_rows": len(current_members), "provider_row_count": len(rows),
                             "normalized_full_market_status_rows": len(normalized),
                             "normalized_full_market_status_sha256": source_revision.removeprefix("sha256:"),
                             "provider_error_code": meta.get("error_code"), "page_count": meta.get("page_count"),
                             "elapsed_seconds": round(time.monotonic() - started, 3), "status": "PASS"})
        except Exception as exc:
            err = type(exc).__name__ + ":" + str(exc)[:180]
            failures.append({"trade_date": current_day, "error": err})
            for member in current_members:
                result = {"security_id": member["security_id"], "source_security_key": member["source_security_key"],
                          "trade_date": current_day, "is_st": None,
                          "source_provider": "BAOSTOCK_PUBLIC_ANONYMOUS_QUERY_DAILY_HISTORY_K_ASTOCK",
                          "binding_quality": "UNKNOWN_QUERY_FAILURE", "source_revision": None}
                target.write(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
                counts["UNKNOWN_QUERY_FAILURE"] += 1
            receipts.append({"trade_date": current_day, "partition_index": args.worker_index,
                             "required_membership_rows": len(current_members), "status": "UNKNOWN", "error": err})
        membership_rows += len(current_members)
        if len(receipts) % 25 == 0:
            print(json.dumps({"worker": args.worker_index, "days": len(receipts), "rows": membership_rows,
                              "unknown": counts["UNKNOWN_NO_VALID_PROVIDER_ROW"] + counts["UNKNOWN_QUERY_FAILURE"]}, ensure_ascii=False), flush=True)

    try:
        with gzip.open(temp_path, "wt", encoding="utf-8", newline="\n", compresslevel=6) as target:
            with BaoStockClient(RequestBudget(ledger_path), auth_mode="PUBLIC_ANONYMOUS", timeout=45) as client:
                if importlib.metadata.version("baostock") != "0.9.3":
                    raise SystemExit("FULL_MARKET_ISST_REQUIRES_ISOLATED_BAOSTOCK_0_9_3")
                session = client
                for line in source:
                    row = json.loads(line)
                    current_day = str(row["trade_date"])
                    if day is None:
                        day, members = current_day, [row]
                    elif current_day != day:
                        day_index += 1
                        flush_day(day, members, client)
                        if day_index % args.worker_count == args.worker_index:
                            print(json.dumps({"worker": args.worker_index, "sessions_completed": len(receipts),
                                              "last_date": day, "failures": len(failures)}, ensure_ascii=False), flush=True)
                        day, members = current_day, [row]
                    else:
                        members.append(row)
                if day is not None:
                    day_index += 1
                    flush_day(day, members, client)
            with temp_path.open("rb+") as f:
                f.flush()
                os.fsync(f.fileno())
        os.replace(temp_path, output_path)
    finally:
        source.close()
        socket.setdefaulttimeout(prior_timeout)
        if temp_path.exists():
            temp_path.unlink()

    observed_end = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    receipt = {"contract_id": "V4_02_FULL_MARKET_ISST_WORKER_RECEIPT_V1", "worker_index": args.worker_index,
               "worker_count": args.worker_count, "status": "PASS" if not failures and counts["UNKNOWN_NO_VALID_PROVIDER_ROW"] == 0 else "WITH_UNKNOWN",
               "expected_session_count": (786 + args.worker_count - 1 - args.worker_index) // args.worker_count,
               "queried_session_count": len(receipts), "membership_rows": membership_rows,
               "unknown_count": counts["UNKNOWN_NO_VALID_PROVIDER_ROW"] + counts["UNKNOWN_QUERY_FAILURE"],
               "is_st_counts": {"0": counts["IS_ST_0"], "1": counts["IS_ST_1"]},
               "query_failures": failures, "query_receipts": receipts,
               "artifact": {"path": args.output, "sha256": sha(output_path), "membership_rows": membership_rows},
               "input_hashes": {"universe": sha(universe_path), "contract": sha(contract_path)},
               "observed_start_utc": observed_start, "observed_end_utc": observed_end,
               "request_ledger": {"path": args.ledger, "sha256": sha(ledger_path)}}
    atomic_json(receipt_path, receipt)
    print(json.dumps({"worker": args.worker_index, "status": receipt["status"], "days": len(receipts),
                      "rows": membership_rows, "unknown": receipt["unknown_count"]}, ensure_ascii=False), flush=True)
    return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
