from __future__ import annotations

"""Capture exact dated BaoStock roster membership for the bounded V4-01 window."""

import argparse
import contextlib
import gzip
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.baostock_supplemental import (  # noqa: E402
    BaoStockClient,
    BaoStockError,
    RequestBudget,
    _atomic_json,
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-receipt", default="reports/v4_01/historical_evaluable_universe_receipt_R4_20260925.json")
    parser.add_argument("--ledger", default="reports/v4_baostock/request_ledger.json")
    parser.add_argument("--output", default="data/v4/artifact_store/v4_01/baostock_dated_rosters_R5_20260925.jsonl.gz")
    parser.add_argument("--receipt", default="reports/v4_01/baostock_dated_roster_receipt_R5_20260925.json")
    parser.add_argument("--max-rows-per-day", type=int, default=10_000)
    parser.add_argument("--max-pages-per-day", type=int, default=10)
    parser.add_argument("--progress-every", type=int, default=25)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--end-index", type=int)
    parser.add_argument("--budget-soft-limit", type=int, default=40_000)
    parser.add_argument("--budget-hard-limit", type=int, default=45_000)
    args = parser.parse_args()

    candidate_path = ROOT / args.candidate_receipt
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    all_sessions = [item["trade_date"] for item in candidate["daily_reconstructed_universe"]["days"]]
    if not all_sessions or all_sessions != sorted(set(all_sessions)):
        raise SystemExit("CANDIDATE_SESSION_LIST_INVALID")
    if all_sessions[0] != candidate["formal_window"]["warmup_first_session"] or all_sessions[-1] != candidate["formal_window"]["last_session"]:
        raise SystemExit("CANDIDATE_SESSION_WINDOW_BINDING_INVALID")
    end_index = args.end_index if args.end_index is not None else len(all_sessions)
    if not 0 <= args.start_index < end_index <= len(all_sessions):
        raise SystemExit("DATED_ROSTER_SESSION_SLICE_INVALID")
    sessions = all_sessions[args.start_index:end_index]
    if not 0 < args.budget_soft_limit <= args.budget_hard_limit <= 45_000:
        raise SystemExit("DATED_ROSTER_BUDGET_SLICE_INVALID")

    ledger_path = ROOT / args.ledger
    output_path = ROOT / args.output
    partial_path = output_path.with_name(output_path.name + ".partial")
    receipt_path = ROOT / args.receipt
    output_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    roster_digest = hashlib.sha256()
    total_rows = 0
    daily_counts: list[dict[str, object]] = []
    failure: dict[str, str] | None = None
    failed_trade_date: str | None = None
    query_failures = 0
    before_doc = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    before_calls = sum(int(value.get("count", 0)) for value in before_doc.get("by_shanghai_date", {}).values())

    if partial_path.exists():
        with gzip.open(partial_path, "rt", encoding="utf-8") as stream:
            for line in stream:
                record = json.loads(line)
                expected_index = len(daily_counts)
                if (expected_index >= len(sessions) or record.get("trade_date") != sessions[expected_index]
                        or record.get("contract_id") != "BAOSTOCK_DATED_ROSTER_SNAPSHOT_V1"):
                    raise SystemExit("DATED_ROSTER_PARTIAL_CHECKPOINT_ORDER_OR_CONTRACT_INVALID")
                codes = record.get("source_codes", [])
                if (codes != sorted(set(codes)) or record.get("row_count") != len(codes)
                        or hashlib.sha256("\n".join(codes).encode("ascii")).hexdigest() != record.get("codes_sha256")):
                    raise SystemExit("DATED_ROSTER_PARTIAL_CHECKPOINT_DIGEST_INVALID")
                daily_counts.append({"trade_date": record["trade_date"], "row_count": len(codes),
                                     "page_count": record.get("page_count"), "codes_sha256": record["codes_sha256"]})
                total_rows += len(codes)
                roster_digest.update(f"{record['trade_date']}\0{len(codes)}\0{record['codes_sha256']}\n".encode("ascii"))

    try:
        mode = "at" if partial_path.exists() else "wt"
        with gzip.open(partial_path, mode, encoding="utf-8", newline="\n", compresslevel=6) as stream:
            client = BaoStockClient(RequestBudget(ledger_path, hard_limit=args.budget_hard_limit,
                                                  soft_limit=args.budget_soft_limit),
                                    auth_mode="PUBLIC_ANONYMOUS", timeout=30)
            client.__enter__()
            try:
                for index in range(len(daily_counts), len(sessions)):
                    trade_date = sessions[index]
                    index += 1
                    rows = None
                    meta = None
                    for attempt in range(3):
                        try:
                            rows, meta = client.query_rows(
                                "query_all_stock", "query_all_stock", day=trade_date,
                                max_rows=args.max_rows_per_day, max_pages=args.max_pages_per_day,
                            )
                            break
                        except BaoStockError as exc:
                            query_failures += 1
                            transient_provider_error = bool(exc.provider_code and (
                                exc.provider_code.startswith("10002") or exc.provider_code == "10001001"))
                            if attempt >= 2 or (exc.provider_code and not transient_provider_error):
                                failed_trade_date = trade_date
                                raise
                            client.__exit__(type(exc), exc, exc.__traceback__)
                            time.sleep(min(2 ** attempt, 4))
                            client = BaoStockClient(RequestBudget(ledger_path, hard_limit=args.budget_hard_limit,
                                                                  soft_limit=args.budget_soft_limit),
                                                    auth_mode="PUBLIC_ANONYMOUS", timeout=30)
                            client.__enter__()
                    if rows is None or meta is None:
                        failed_trade_date = trade_date
                        raise BaoStockError("DATED_ROSTER_QUERY_DID_NOT_RETURN")
                    codes = [str(row.get("code", "")).strip().lower() for row in rows]
                    if any(not code.startswith(("sh.", "sz.", "bj.")) or len(code) != 9 for code in codes):
                        raise BaoStockError("DATED_ROSTER_CODE_FORMAT_INVALID")
                    if len(codes) != len(set(codes)):
                        raise BaoStockError("DATED_ROSTER_DUPLICATE_CODE")
                    codes.sort()
                    day_digest = hashlib.sha256("\n".join(codes).encode("ascii")).hexdigest()
                    record = {
                        "contract_id": "BAOSTOCK_DATED_ROSTER_SNAPSHOT_V1",
                        "trade_date": trade_date,
                        "row_count": len(codes),
                        "page_count": meta["page_count"],
                        "codes_sha256": day_digest,
                        "source_codes": codes,
                    }
                    stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
                    roster_digest.update(f"{trade_date}\0{len(codes)}\0{day_digest}\n".encode("ascii"))
                    total_rows += len(codes)
                    daily_counts.append({"trade_date": trade_date, "row_count": len(codes),
                                         "page_count": meta["page_count"], "codes_sha256": day_digest})
                    if index % args.progress_every == 0 or index == len(sessions):
                        print(json.dumps({"completed_sessions": index, "total_sessions": len(sessions),
                                          "total_rows": total_rows, "last_session": trade_date}, ensure_ascii=False), flush=True)
            finally:
                client.__exit__(None, None, None)
    except Exception as exc:
        failure = {"code": str(exc)[:120], "provider_code": getattr(exc, "provider_code", None),
                   "provider_message": getattr(exc, "provider_message", None),
                   "trade_date": failed_trade_date}
    if failure is None and len(daily_counts) == len(sessions):
        with partial_path.open("rb+") as stream:
            os.fsync(stream.fileno())
        os.replace(partial_path, output_path)
        published = True
    else:
        published = False

    after_doc = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    after_calls = sum(int(value.get("count", 0)) for value in after_doc.get("by_shanghai_date", {}).values())
    receipt = {
        "stage": "V4-01-BAOSTOCK-DATED-ROSTERS-R5",
        "contract_id": "BAOSTOCK_DATED_ROSTER_SNAPSHOT_V1",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "BUILT" if published else "BLOCKED",
        "stage_completion_authorized": False,
        "source": {"provider": "BaoStock", "method": "query_all_stock(day)",
                   "auth_mode": "PUBLIC_ANONYMOUS", "source_document": "https://www.baostock.com/mainContent?file=pythonAPI.md"},
        "input": {"candidate_receipt": args.candidate_receipt,
                  "candidate_receipt_sha256": file_sha256(candidate_path),
                  "session_basis": candidate["formal_window"]["session_basis"],
                  "first_session": sessions[0], "last_session": sessions[-1], "session_count": len(sessions),
                  "full_session_count": len(all_sessions), "slice_start_index": args.start_index,
                  "slice_end_index_exclusive": end_index},
        "output": ({"path": args.output, "sha256": file_sha256(output_path),
                    "byte_count": output_path.stat().st_size, "format": "GZIP_JSONL",
                    "total_roster_rows": total_rows, "daily_roster_digest_root": roster_digest.hexdigest()}
                   if published else None),
        "partial_checkpoint": ({"path": str(partial_path.relative_to(ROOT).as_posix()),
                                "sha256": file_sha256(partial_path), "completed_sessions": len(daily_counts),
                                "byte_count": partial_path.stat().st_size}
                               if partial_path.exists() else None),
        "daily_counts": daily_counts,
        "request_budget": {"ledger_path": args.ledger, "before_total_count": before_calls, "after_total_count": after_calls,
                           "request_count_delta": after_calls - before_calls,
                           "configured_soft_cap": args.budget_soft_limit, "configured_hard_cap": args.budget_hard_limit,
                           "provider_limit": 50_000},
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "query_failure_count": query_failures,
        "execution_identity": {"input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                               "script_sha256": file_sha256(Path(__file__))},
        "failures": failure or {},
        "next_stage": "V4_01_STABLE_IDENTITY_AND_BSE_LIFECYCLE_R5",
    }
    _atomic_json(receipt_path, receipt)
    print(json.dumps({"status": receipt["status"], "session_count": len(daily_counts),
                      "total_rows": total_rows, "request_count_delta": after_calls - before_calls,
                      "failure": failure, "receipt": args.receipt}, ensure_ascii=False))
    return 0 if published else 2


if __name__ == "__main__":
    raise SystemExit(main())
