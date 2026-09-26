from __future__ import annotations

"""Retry only explicitly failed full-market isST dates, once, then publish a new artifact."""

import argparse
import gzip
import hashlib
import importlib.metadata
import json
import os
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.baostock_supplemental import BaoStockClient, RequestBudget  # noqa: E402


EXPECTED_FIELDS = ["date", "code", "open", "high", "low", "close", "preclose", "volume", "amount",
                   "adjustflag", "turn", "tradestatus", "pctChg", "peTTM", "pbMRQ", "psTTM",
                   "pcfNcfTTM", "isST"]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def atomic_gzip(path: Path, rows) -> tuple[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temp = Path(name)
    digest, count = hashlib.sha256(), 0
    try:
        with gzip.open(temp, "wt", encoding="utf-8", newline="\n", compresslevel=6) as out:
            for row in rows:
                line = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                out.write(line)
                digest.update(line.encode("utf-8"))
                count += 1
        with temp.open("rb+") as stream:
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()
    return digest.hexdigest(), count


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--contract", default="config/v4_02_isst_bounded_recovery_v1.json")
    p.add_argument("--base-receipt", default="reports/v4_02/V4_02_DATED_ST_STATUS_V1_R6_2_20260926.json")
    p.add_argument("--universe", default="data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R6_2_20260926.jsonl.gz")
    p.add_argument("--base-artifact", default="data/v4/artifact_store/v4_02/V4_02_DATED_ST_STATUS_V1_R6_2_20260926.jsonl.gz")
    p.add_argument("--output", default="data/v4/artifact_store/v4_02/V4_02_DATED_ST_STATUS_V1_R6_2_20260926_RECOVERED_R1.jsonl.gz")
    p.add_argument("--receipt", default="reports/v4_02/V4_02_DATED_ST_STATUS_V1_R6_2_20260926.json")
    p.add_argument("--recovery-receipt", default="reports/v4_02/V4_02_DATED_ST_STATUS_BOUNDED_RECOVERY_R1_20260926.json")
    p.add_argument("--ledger", default="reports/v4_baostock/request_ledger.json")
    args = p.parse_args()

    contract_path, base_receipt_path = ROOT / args.contract, ROOT / args.base_receipt
    universe_path, base_artifact_path = ROOT / args.universe, ROOT / args.base_artifact
    output_path, receipt_path = ROOT / args.output, ROOT / args.receipt
    recovery_receipt_path, ledger_path = ROOT / args.recovery_receipt, ROOT / args.ledger
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    base = json.loads(base_receipt_path.read_text(encoding="utf-8"))
    failed = sorted({str(item["trade_date"]) for item in base.get("query_failures", [])})
    expected_error = contract["scope"]["allowed_primary_error"]
    failure_errors = {str(item["trade_date"]): str(item.get("error", "")) for item in base.get("query_failures", [])}
    if len(failed) > int(contract["scope"]["max_failed_dates"]):
        raise SystemExit("BOUNDED_ISST_RECOVERY_DATE_LIMIT_EXCEEDED")
    if any(expected_error not in failure_errors[day] for day in failed):
        raise SystemExit("BOUNDED_ISST_RECOVERY_ERROR_NOT_ALLOWLISTED")
    if base.get("bounded_recovery"):
        raise SystemExit("BOUNDED_ISST_RECOVERY_ALREADY_APPLIED")
    if not failed:
        print(json.dumps({"status": "NO_RECOVERY_NEEDED", "dates": 0}, ensure_ascii=False))
        return 0
    if importlib.metadata.version("baostock") != "0.9.3":
        raise SystemExit("BOUNDED_ISST_RECOVERY_REQUIRES_ISOLATED_BAOSTOCK_0_9_3")

    members: dict[str, list[dict]] = {day: [] for day in failed}
    with gzip.open(universe_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            day = str(row["trade_date"])
            if day in members:
                members[day].append(row)

    recovered_by_key: dict[tuple[str, str], dict] = {}
    receipts = []
    expected_members = 0
    for rows in members.values():
        expected_members += len(rows)
    with BaoStockClient(RequestBudget(ledger_path), auth_mode="PUBLIC_ANONYMOUS", timeout=45) as client:
        for day in failed:
            started = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            try:
                provider_rows, meta = client.query_rows(
                    "query_daily_history_k_AStock_recovery", "query_daily_history_k_AStock",
                    date=day, max_rows=int(contract["scope"]["max_rows"]), max_pages=int(contract["scope"]["max_pages"]),
                )
                if meta.get("fields") != EXPECTED_FIELDS:
                    raise RuntimeError("UNEXPECTED_FULL_MARKET_FIELDS")
                normalized = []
                by_code = {}
                for row in provider_rows:
                    code, row_day = str(row.get("code", "")).strip().lower(), str(row.get("date", ""))
                    tradestatus, is_st = str(row.get("tradestatus", "")).strip(), str(row.get("isST", "")).strip()
                    if row_day != day or not code or code in by_code:
                        raise RuntimeError("INVALID_OR_DUPLICATE_PROVIDER_KEY")
                    if tradestatus in {"0", "1"} and is_st in {"0", "1"}:
                        normalized.append({"date": day, "code": code, "tradestatus": tradestatus, "isST": is_st})
                        by_code[code] = is_st
                revision = hashlib.sha256("".join(
                    "\t".join((row["date"], row["code"], row["tradestatus"], row["isST"])) + "\n"
                    for row in sorted(normalized, key=lambda value: value["code"])
                ).encode("ascii")).hexdigest()
                for member in members[day]:
                    code = str(member["source_security_key"]).lower()
                    value = by_code.get(code)
                    recovered_by_key[(day, code)] = {
                        "security_id": member["security_id"], "source_security_key": member["source_security_key"],
                        "trade_date": day, "is_st": value,
                        "source_provider": "BAOSTOCK_PUBLIC_ANONYMOUS_QUERY_DAILY_HISTORY_K_ASTOCK",
                        "binding_quality": "DIRECT_CODE_DATE" if value is not None else "UNKNOWN_NO_VALID_PROVIDER_ROW",
                        "source_revision": "sha256:" + revision if value is not None else None,
                    }
                receipts.append({"trade_date": day, "status": "PASS", "provider_row_count": len(provider_rows),
                                 "normalized_full_market_status_rows": len(normalized),
                                 "normalized_full_market_status_sha256": revision,
                                 "required_membership_rows": len(members[day]), "page_count": meta.get("page_count"),
                                 "started_at_utc": started,
                                 "finished_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat()})
            except Exception as exc:
                receipts.append({"trade_date": day, "status": "UNKNOWN", "required_membership_rows": len(members[day]),
                                 "error": type(exc).__name__ + ":" + str(exc)[:180], "started_at_utc": started,
                                 "finished_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat()})

    recovery_rows = (recovered_by_key[key] for key in sorted(recovered_by_key))
    recovery_digest, recovery_count = atomic_gzip(output_path.with_name(".isst_recovery_facts_R1.jsonl.gz"), recovery_rows)
    recovered_days = {item["trade_date"] for item in receipts if item["status"] == "PASS"}
    still_failed_days = {item["trade_date"] for item in receipts if item["status"] != "PASS"}

    # Publish a new merged candidate. The original merge artifact and receipt remain intact.
    fd, temp_name = tempfile.mkstemp(prefix=output_path.name + ".", suffix=".tmp", dir=output_path.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    counts: Counter[str] = Counter()
    digest = hashlib.sha256()
    recovered_rows = 0
    try:
        with gzip.open(base_artifact_path, "rt", encoding="utf-8") as base_stream, \
             gzip.open(temp_path, "wt", encoding="utf-8", newline="\n", compresslevel=6) as out:
            for line in base_stream:
                original = json.loads(line)
                key = (str(original["trade_date"]), str(original["source_security_key"]).lower())
                replacement = recovered_by_key.get(key) if key[0] in recovered_days else None
                if replacement and original.get("binding_quality") == "UNKNOWN_QUERY_FAILURE":
                    original = replacement
                    recovered_rows += 1
                out.write(json.dumps(original, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
                if original.get("is_st") in {"0", "1"}:
                    counts["IS_ST_" + original["is_st"]] += 1
                else:
                    counts[str(original.get("binding_quality"))] += 1
                digest.update((json.dumps(original, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
        with temp_path.open("rb+") as stream:
            os.fsync(stream.fileno())
        os.replace(temp_path, output_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    remaining_unknown = sum(value for key, value in counts.items() if key not in {"IS_ST_0", "IS_ST_1"})
    final_query_failures = [item for item in base.get("query_failures", []) if item.get("trade_date") in still_failed_days]
    recovery_receipt = {
        "contract_id": contract["contract_id"], "status": "RECOVERY_COMPLETE" if not still_failed_days else "RECOVERY_WITH_UNKNOWN",
        "contract_sha256": sha(contract_path), "base_receipt_sha256": sha(base_receipt_path),
        "base_artifact_sha256": sha(base_artifact_path), "recovery_fact_artifact": {
            "path": str(output_path.with_name(".isst_recovery_facts_R1.jsonl.gz").relative_to(ROOT)).replace("\\", "/"),
            "row_count": recovery_count, "normalized_sha256": recovery_digest,
            "sha256": sha(output_path.with_name(".isst_recovery_facts_R1.jsonl.gz"))},
        "max_retry_per_failed_date": 1, "retry_receipt_count": len(receipts), "retry_receipts": receipts,
        "recovered_dates": sorted(recovered_days), "still_failed_dates": sorted(still_failed_days),
        "expected_membership_rows": expected_members, "recovered_membership_rows": recovered_rows,
        "request_ledger_sha256": sha(ledger_path), "script_sha256": sha(Path(__file__).resolve()),
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    atomic_json(recovery_receipt_path, recovery_receipt)

    final = dict(base)
    final["status"] = "DATED_ST_STATUS_PASS" if remaining_unknown == 0 and not final_query_failures else "DATED_ST_STATUS_WITH_UNKNOWN"
    final["is_st_value_counts"] = {"0": counts["IS_ST_0"], "1": counts["IS_ST_1"], "UNKNOWN": remaining_unknown}
    final["binding_quality_counts"] = {key: value for key, value in counts.items() if key not in {"IS_ST_0", "IS_ST_1"}}
    final["query_failure_count"] = len(final_query_failures)
    final["query_failures"] = final_query_failures
    final["artifact"] = {"path": args.output, "row_count": base["membership_rows"], "sha256": sha(output_path)}
    final["normalized_output_sha256"] = digest.hexdigest()
    final["base_attempt_receipt_sha256"] = sha(base_receipt_path)
    final["bounded_recovery"] = {"receipt_path": args.recovery_receipt, "receipt_sha256": sha(recovery_receipt_path),
                                 "retry_query_count": len(receipts), "recovered_membership_rows": recovered_rows,
                                 "still_failed_dates": sorted(still_failed_days)}
    final["request_ledger_sha256"] = sha(ledger_path)
    final["execution_identity"] = {**final.get("execution_identity", {}), "recovery_script_sha256": sha(Path(__file__).resolve()),
                                   "finished_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
    atomic_json(receipt_path, final)
    print(json.dumps({"status": final["status"], "retry_dates": len(receipts), "recovered_rows": recovered_rows,
                      "remaining_unknown": remaining_unknown, "remaining_query_failures": len(final_query_failures)}, ensure_ascii=False))
    return 0 if final["status"] == "DATED_ST_STATUS_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
