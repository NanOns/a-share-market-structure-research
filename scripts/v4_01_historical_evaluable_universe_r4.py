from __future__ import annotations

"""Build a bounded historical reconstructed universe from dated BaoStock rosters."""

import argparse
import gzip
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v4.contracts.source_overlap import sessions_from_index_chains  # noqa: E402
from workbench_analysis.baostock_supplemental import BaoStockClient, RequestBudget, _atomic_json  # noqa: E402

PACKAGE_SHA = "b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f"
BUNDLE_ID = "6122afa9db83170f7b442d5ecc5c7c9287b9dd6b04c4d53729d55f71f7dd99d2"
EXTRACTED_ROOT = ROOT / "data/input_staging/extracted/20260924" / PACKAGE_SHA
FACTS_PATH = ROOT / "reports/v4_01/baostock_lifecycle_facts_R4_20260925.json"
SELECTION_PATH = ROOT / "reports/v4_01/canonical_source_selection_R4_20260925.json"
UNIVERSE_CONTRACT = "V4_RESEARCH_UNIVERSE_V1"

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def as_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--formal-start", default="2024-09-25")
    parser.add_argument("--warmup-sessions", type=int, default=300)
    parser.add_argument("--ledger", default="reports/v4_baostock/request_ledger.json")
    parser.add_argument("--output", default="data/v4/historical_universe/v4_01_reconstructed_a_stock_universe_R4_20260925.jsonl.gz")
    parser.add_argument("--receipt", default="reports/v4_01/historical_evaluable_universe_receipt_R4_20260925.json")
    args = parser.parse_args()

    formal_start = date.fromisoformat(args.formal_start)
    facts_doc = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    facts = {item["source_security_key"].lower(): item for item in facts_doc["facts"]
             if item.get("security_type_provider") == "1"}
    lifecycle_revision = facts_doc["source_revision_id"]
    selection_doc = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    source_keys = {str(item["source_security_key"]).lower() for item in selection_doc["segments"]}
    bj_source_keys = {key for key in source_keys if key.startswith("bj.")}

    sessions = sessions_from_index_chains(EXTRACTED_ROOT, max(args.warmup_sessions + 600, 800))
    session_dates = [date(int(str(value)[:4]), int(str(value)[4:6]), int(str(value)[6:])) for value in sessions]
    formal_index = next((index for index, item in enumerate(session_dates) if item >= formal_start), None)
    if formal_index is None:
        raise ValueError("FORMAL_START_AFTER_LAST_SOURCE_SESSION")
    first_index = max(0, formal_index - args.warmup_sessions)
    selected_sessions = session_dates[first_index:]
    if not selected_sessions or selected_sessions[-1] > date(2026, 9, 24):
        raise ValueError("UNIVERSE_SESSION_RANGE_OUTSIDE_SOURCE_CUTOFF")

    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=output_path.name + ".", suffix=".tmp", dir=output_path.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    writer = gzip.open(temp_path, "wt", encoding="utf-8", newline="\n", compresslevel=6)
    ledger_path = ROOT / args.ledger
    before = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    before_count = sum(int(item.get("count", 0)) for item in before.get("by_shanghai_date", {}).values())
    client = BaoStockClient(RequestBudget(ledger_path), auth_mode="PUBLIC_ANONYMOUS")
    started = time.monotonic()
    days = []
    mismatches = []
    error = None
    total_rows = 0
    total_tradable = 0
    total_suspended = 0
    rows_digest = hashlib.sha256()
    try:
        with client:
            for index, session in enumerate(selected_sessions, start=1):
                day = session.isoformat()
                rows, metadata = client.probe_all_stock(day)
                if metadata.get("error_code") != "0":
                    raise RuntimeError(f"ALL_STOCK_QUERY_ERROR:{day}:{metadata.get('error_code')}")
                active_codes = {}
                for row in rows:
                    code = str(row.get("code", "")).strip().lower()
                    fact = facts.get(code)
                    if fact is None:
                        continue
                    active_codes[code] = str(row.get("tradeStatus", "")).strip()

                expected = {
                    code for code, fact in facts.items()
                    if (listed_from := as_date(fact.get("listed_from"))) is not None
                    and listed_from <= session
                    and ((listed_to := as_date(fact.get("listed_to_provider_reported"))) is None or listed_to >= session)
                }
                observed = set(active_codes)
                missing = sorted(expected - observed)
                unexpected = sorted(observed - expected)
                if missing or unexpected:
                    mismatches.append({"trade_date": day, "expected_active_a_stock_count": len(expected),
                                       "observed_active_a_stock_count": len(observed),
                                       "missing_count": len(missing), "unexpected_count": len(unexpected),
                                       "missing_sample": missing[:10], "unexpected_sample": unexpected[:10]})

                membership_rows = []
                digest_items = []
                day_tradable = day_suspended = 0
                for code in sorted(observed):
                    trade_status = active_codes[code]
                    source_match = code in source_keys
                    if trade_status == "1":
                        eligibility = "RECONSTRUCTED_TRADABLE_MEMBER" if source_match else "SOURCE_HISTORY_UNAVAILABLE"
                        day_tradable += int(source_match)
                    elif trade_status == "0":
                        eligibility = "RECONSTRUCTED_SUSPENDED_MEMBER" if source_match else "SOURCE_HISTORY_UNAVAILABLE"
                        day_suspended += int(source_match)
                    else:
                        eligibility = "TRADE_STATUS_UNKNOWN"
                    canonical_id = code.upper() if source_match else None
                    quality = "DIRECT_PROVIDER_CODE_AND_TDX_SOURCE_KEY_MATCH" if source_match else "IDENTITY_OR_HISTORY_UNRESOLVED"
                    membership_rows.append({
                        "trade_date": session,
                        "canonical_security_id": canonical_id,
                        "source_security_key": code.upper(),
                        "universe_contract_id": UNIVERSE_CONTRACT,
                        "lifecycle_revision_id": lifecycle_revision,
                        "eligibility_status": eligibility,
                        "eligibility_reason": "DATED_BAOSTOCK_ROSTER_AND_TYPE1_LIFECYCLE_INTERVAL",
                        "provider_trade_status": trade_status if trade_status in {"0", "1"} else None,
                        "membership_basis": "RECONSTRUCTED_CORRECTED",
                        "quality": quality,
                    })
                    digest_items.append(f"{code}\0{eligibility}\0{trade_status}\n")
                day_digest = hashlib.sha256("".join(digest_items).encode("ascii")).hexdigest()
                rows_digest.update(f"{session.isoformat()}\0{day_digest}\0{len(observed)}\n".encode("ascii"))
                for membership_row in membership_rows:
                    membership_row["trade_date"] = membership_row["trade_date"].isoformat()
                    writer.write(json.dumps(membership_row, ensure_ascii=False, sort_keys=True,
                                            separators=(",", ":")) + "\n")
                total_rows += len(membership_rows)
                total_tradable += day_tradable
                total_suspended += day_suspended
                days.append({"trade_date": day, "provider_roster_rows": len(rows),
                             "a_stock_roster_count": len(observed), "tradable_source_matched_count": day_tradable,
                             "suspended_source_matched_count": day_suspended, "universe_digest": day_digest,
                             "evaluable_count": day_tradable, "unknown_or_unresolved_count": len(observed) - day_tradable - day_suspended,
                             "provider_error_code": metadata.get("error_code")})
                if index % 50 == 0:
                    print(json.dumps({"progress_sessions": index, "total_sessions": len(selected_sessions),
                                      "membership_rows": total_rows, "request_budget_used_today": before_count + index}, ensure_ascii=False), flush=True)
    except Exception as exc:
        error = type(exc).__name__ + ":" + str(exc)[:200]
    finally:
        writer.close()

    after = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    after_count = sum(int(item.get("count", 0)) for item in after.get("by_shanghai_date", {}).values())
    output_published = error is None and len(days) == len(selected_sessions)
    if output_published:
        with temp_path.open("rb+") as stream:
            os.fsync(stream.fileno())
        os.replace(temp_path, output_path)
    else:
        temp_path.unlink(missing_ok=True)

    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    receipt = {
        "stage": "V4-01-HISTORICAL-EVALUABLE-UNIVERSE-R4",
        "contract_id": "V4_HISTORICAL_EVALUABLE_UNIVERSE_RECONSTRUCTION_V1",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "RECONSTRUCTED_UNIVERSE_BUILT_ACCEPTANCE_PENDING" if output_published and not mismatches and not bj_source_keys else "BLOCKED",
        "stage_completion_authorized": False,
        "lineage": "RECONSTRUCTED_CORRECTED; retrieved now from dated provider rosters; not AS_RECORDED",
        "formal_window": {"requested_start": formal_start.isoformat(), "actual_first_session": session_dates[formal_index].isoformat(),
                          "last_session": selected_sessions[-1].isoformat(), "warmup_sessions": args.warmup_sessions,
                          "warmup_first_session": selected_sessions[0].isoformat(), "session_basis": "FROZEN_TDX_INDEX_BAR_DATE_PROXY"},
        "lifecycle_source": {"path": FACTS_PATH.relative_to(ROOT).as_posix(), "sha256": sha256_file(FACTS_PATH),
                             "revision_id": lifecycle_revision, "a_stock_type": "BaoStock provider type=1",
                             "boundary_validation_sessions": 3, "boundary_mismatch_count": sum(x["missing_count"] + x["unexpected_count"] for x in mismatches)},
        "source_selection": {"path": SELECTION_PATH.relative_to(ROOT).as_posix(), "sha256": sha256_file(SELECTION_PATH),
                              "selection_digest": selection_doc["selection_digest"],
                              "mapped_source_key_count": len(source_keys), "unresolved_bj_source_key_count": len(bj_source_keys)},
        "daily_reconstructed_universe": {"session_count": len(days), "membership_row_count": total_rows,
                                          "tradable_source_matched_rows": total_tradable,
                                          "suspended_source_matched_rows": total_suspended,
                                          "daily_digest_root": rows_digest.hexdigest(), "days": days,
                                          "lifecycle_roster_mismatches": mismatches[:100]},
        "output": {"path": args.output.replace("\\", "/") if output_published else None,
                   "format": "GZIP_JSONL; one reconstructed membership fact per line",
                   "sha256": sha256_file(output_path) if output_published else None,
                   "byte_count": output_path.stat().st_size if output_published else 0},
        "request_budget": {"requests_before": before_count, "requests_after": after_count,
                           "request_count_delta": after_count - before_count,
                           "daily_soft_cap": 40_000, "daily_hard_cap": 45_000, "provider_limit": 50_000},
        "execution_identity": {"input_commit": commit, "script_sha256": sha256_file(Path(__file__))},
        "failures": {"query_or_write": error} if error else {},
        "blockers": (["NO_BSE_LIFECYCLE_CATALOG_OR_DATED_ROSTER"] if bj_source_keys else [])
                    + (["DATED_ROSTER_DIFFERS_FROM_CURRENT_BASIC_INTERVAL_CANDIDATES"] if mismatches else [])
                    + ["ONLINE_MODEL_INDEPENDENT_ACCEPTANCE", "FORMAL_CALENDAR_ACCEPTANCE", "ADJUSTED_HISTORY_AND_PRICE_LIMIT_ACCEPTANCE"],
        "next_stage": "V4_01_FORMAL_IDENTITY_LIFECYCLE_AND_ADJUSTMENT_ACCEPTANCE",
    }
    receipt_path = ROOT / args.receipt
    _atomic_json(receipt_path, receipt)
    print(json.dumps({"status": receipt["status"], "sessions": len(days), "expected_sessions": len(selected_sessions),
                      "membership_rows": total_rows, "mismatches": len(mismatches), "bse_source_keys": len(bj_source_keys),
                      "output_published": output_published, "requests": after_count - before_count,
                      "failure": error, "receipt": args.receipt}, ensure_ascii=False))
    return 0 if output_published and not mismatches and not bj_source_keys else 2


if __name__ == "__main__":
    raise SystemExit(main())
