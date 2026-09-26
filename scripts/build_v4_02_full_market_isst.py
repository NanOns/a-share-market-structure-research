from __future__ import annotations

"""Build dated isST facts from bounded full-market BaoStock daily queries."""

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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def code_digest(rows: list[dict[str, str]]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: (item["code"], item["date"])):
        digest.update("\t".join((row["date"], row["code"], row["tradestatus"], row["isST"])).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", default="data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R6_2_20260926.jsonl.gz")
    parser.add_argument("--calendar-receipt", default="reports/v4_02/V4_02_FORMAL_MARKET_CALENDAR_ACCEPTANCE_V2.json")
    parser.add_argument("--contract", default="config/v4_02_full_market_isst_contract_v1.json")
    parser.add_argument("--output", default="data/v4/artifact_store/v4_02/V4_02_DATED_ST_STATUS_V1_R6_2_20260926.jsonl.gz")
    parser.add_argument("--receipt", default="reports/v4_02/V4_02_DATED_ST_STATUS_V1_R6_2_20260926.json")
    parser.add_argument("--ledger", default="reports/v4_baostock/request_ledger.json")
    args = parser.parse_args()

    universe_path, calendar_path = ROOT / args.universe, ROOT / args.calendar_receipt
    contract_path, output_path, receipt_path = ROOT / args.contract, ROOT / args.output, ROOT / args.receipt
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    calendar = json.loads(calendar_path.read_text(encoding="utf-8"))
    if calendar.get("status") != "FORMAL_MARKET_CALENDAR_PASS":
        raise SystemExit("FORMAL_CALENDAR_NOT_ACCEPTED")
    sessions = int(calendar["markets"][0]["session_count"])
    if sessions != int(calendar["markets"][1]["session_count"]):
        raise SystemExit("MARKET_SESSION_COUNTS_DIFFER")

    # The R6.2 required-scope universe is date ordered. Stream one market day
    # at a time so provider rows can be bound without materializing 4m rows.
    source = gzip.open(universe_path, "rt", encoding="utf-8")
    pending = json.loads(next(source))
    membership_rows = 0
    actual_membership_rows = 0
    facts_counts: Counter[str] = Counter()
    query_receipts: list[dict] = []
    failures: list[dict] = []
    output_digest = hashlib.sha256()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=output_path.name + ".", suffix=".tmp", dir=output_path.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    start_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    prior_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(45)
    try:
        with gzip.open(temp_path, "wt", encoding="utf-8", newline="\n", compresslevel=6) as target:
            with BaoStockClient(RequestBudget(ROOT / args.ledger), auth_mode="PUBLIC_ANONYMOUS", timeout=45) as client:
                if importlib.metadata.version("baostock") != "0.9.3":
                    raise SystemExit("FULL_MARKET_ISST_REQUIRES_ISOLATED_BAOSTOCK_0_9_3")
                current_session = None
                day_members: list[dict] = []
                queried = 0

                def flush_day(day: str, members: list[dict]) -> None:
                    nonlocal membership_rows, actual_membership_rows
                    nonlocal queried
                    if queried >= sessions:
                        raise RuntimeError("UNIVERSE_HAS_MORE_DATES_THAN_ACCEPTED_CALENDAR")
                    started = time.monotonic()
                    query_error = None
                    normalized: list[dict[str, str]] = []
                    try:
                        rows, meta = client.query_rows(
                            "query_daily_history_k_AStock", "query_daily_history_k_AStock",
                            date=day, max_rows=20000, max_pages=1,
                        )
                        expected_fields = contract["provider"]["expected_fields"]
                        if meta.get("fields") != expected_fields:
                            raise RuntimeError("UNEXPECTED_FULL_MARKET_FIELDS")
                        seen: set[str] = set()
                        for row in rows:
                            code = str(row.get("code", "")).strip().lower()
                            row_date = str(row.get("date", ""))
                            status = str(row.get("tradestatus", "")).strip()
                            is_st = str(row.get("isST", "")).strip()
                            if row_date != day or not code or code in seen:
                                raise RuntimeError("INVALID_OR_DUPLICATE_PROVIDER_KEY")
                            seen.add(code)
                            if status not in {"0", "1"} or is_st not in {"0", "1"}:
                                continue
                            normalized.append({"date": day, "code": code, "tradestatus": status, "isST": is_st})
                        day_hash = code_digest(normalized)
                        provider_by_code = {row["code"]: row for row in normalized}
                        binding_revision = "sha256:" + day_hash
                        for member in members:
                            key = str(member["source_security_key"]).lower()
                            provider_row = provider_by_code.get(key)
                            if member.get("source_bar_present") is True:
                                actual_membership_rows += 1
                            value = {
                                "security_id": member["security_id"],
                                "source_security_key": member["source_security_key"],
                                "trade_date": day,
                                "is_st": provider_row["isST"] if provider_row else None,
                                "source_provider": "BAOSTOCK_PUBLIC_ANONYMOUS_QUERY_DAILY_HISTORY_K_ASTOCK",
                                "binding_quality": "DIRECT_CODE_DATE" if provider_row else "UNKNOWN_NO_VALID_PROVIDER_ROW",
                                "source_revision": binding_revision if provider_row else None,
                            }
                            encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                            target.write(encoded + "\n")
                            output_digest.update((encoded + "\n").encode("utf-8"))
                            facts_counts[value["binding_quality"]] += 1
                            facts_counts["IS_ST_" + str(value["is_st"])] += 1
                        query_receipts.append({
                            "trade_date": day, "required_membership_rows": len(members),
                            "provider_row_count": len(rows), "normalized_status_row_count": len(normalized),
                            "normalized_full_market_status_sha256": day_hash,
                            "provider_error_code": meta.get("error_code"), "page_count": meta.get("page_count"),
                            "elapsed_seconds": round(time.monotonic() - started, 3), "status": "PASS",
                        })
                    except Exception as exc:
                        query_error = type(exc).__name__ + ":" + str(exc)[:180]
                        failures.append({"trade_date": day, "error": query_error})
                        # Missing or invalid provider data is explicitly UNKNOWN.
                        for member in members:
                            if member.get("source_bar_present") is True:
                                actual_membership_rows += 1
                            value = {
                                "security_id": member["security_id"],
                                "source_security_key": member["source_security_key"],
                                "trade_date": day, "is_st": None,
                                "source_provider": "BAOSTOCK_PUBLIC_ANONYMOUS_QUERY_DAILY_HISTORY_K_ASTOCK",
                                "binding_quality": "UNKNOWN_QUERY_FAILURE", "source_revision": None,
                            }
                            encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                            target.write(encoded + "\n")
                            output_digest.update((encoded + "\n").encode("utf-8"))
                            facts_counts["UNKNOWN_QUERY_FAILURE"] += 1
                        query_receipts.append({"trade_date": day, "required_membership_rows": len(members),
                                               "status": "UNKNOWN", "error": query_error})
                    membership_rows += len(members)
                    queried += 1
                    if queried % 50 == 0 or queried == sessions:
                        print(json.dumps({"sessions_queried": queried, "sessions_expected": sessions,
                                          "membership_rows": membership_rows,
                                          "unknown": facts_counts["UNKNOWN_NO_VALID_PROVIDER_ROW"] + facts_counts["UNKNOWN_QUERY_FAILURE"],
                                          "failures": len(failures)}, ensure_ascii=False), flush=True)

                for line in source:
                    row = json.loads(line)
                    day = row["trade_date"]
                    if current_session is None:
                        current_session = day
                    if day != current_session:
                        flush_day(current_session, day_members)
                        current_session, day_members = day, []
                    day_members.append(row)
                if current_session is not None:
                    flush_day(current_session, day_members)
                if queried != sessions:
                    raise RuntimeError(f"CALENDAR_UNIVERSE_SESSION_COUNT_MISMATCH:{queried}:{sessions}")
            with temp_path.open("rb+") as stream:
                stream.flush()
                os.fsync(stream.fileno())
        os.replace(temp_path, output_path)
    finally:
        source.close()
        socket.setdefaulttimeout(prior_timeout)
        if temp_path.exists():
            temp_path.unlink()

    output_sha = sha256(output_path)
    end_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    unknown = facts_counts["UNKNOWN_NO_VALID_PROVIDER_ROW"] + facts_counts["UNKNOWN_QUERY_FAILURE"]
    status = "DATED_ST_STATUS_PASS" if not failures and unknown == 0 and membership_rows == 4036121 else "DATED_ST_STATUS_WITH_UNKNOWN"
    receipt = {
        "contract_id": "V4_02_DATED_ST_STATUS_V1",
        "version": "1.0.0",
        "stage": "V4-02 / FINAL CLOSURE PACK",
        "status": status,
        "stage_contract": "V4_02_FULL_MARKET_DATED_ISST_V1",
        "source_cutoff": "2026-09-24",
        "session_count": sessions,
        "membership_rows": membership_rows,
        "actual_bar_membership_rows": actual_membership_rows,
        "is_st_value_counts": {"0": facts_counts["IS_ST_0"], "1": facts_counts["IS_ST_1"], "UNKNOWN": unknown},
        "binding_quality_counts": {key: value for key, value in facts_counts.items() if key.startswith("DIRECT_") or key.startswith("UNKNOWN_")},
        "query_failure_count": len(failures),
        "query_failures": failures,
        "query_receipt_count": len(query_receipts),
        "query_receipts": query_receipts,
        "artifact": {"path": args.output, "row_count": membership_rows, "sha256": output_sha},
        "normalized_output_sha256": output_digest.hexdigest(),
        "input_hashes": {"universe_sha256": sha256(universe_path), "calendar_receipt_sha256": sha256(calendar_path),
                         "contract_sha256": sha256(contract_path)},
        "execution_identity": {"script_sha256": sha256(Path(__file__).resolve()), "started_at_utc": start_utc, "finished_at_utc": end_utc},
        "next_stage": "PRICE_LIMIT_RULE_V1_AND_WHOLE_STAGE_FINAL_PUBLICATION",
        "limitations": ["BaoStock is a supplemental status source, not a price authority.",
                        "Missing or invalid provider rows remain UNKNOWN and are not inferred from a local bar."],
    }
    atomic_json(receipt_path, receipt)
    print(json.dumps({"status": status, "membership_rows": membership_rows, "unknown": unknown,
                      "query_failures": len(failures), "artifact_sha256": output_sha}, ensure_ascii=False))
    return 0 if status == "DATED_ST_STATUS_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
