from __future__ import annotations

"""Bounded empirical validation of BaoStock IPO/outDate interval boundaries."""

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v4.contracts.source_overlap import sessions_from_index_chains  # noqa: E402
from workbench_analysis.baostock_supplemental import BaoStockClient, RequestBudget, _atomic_json  # noqa: E402

PACKAGE_SHA = "b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f"
FACTS_PATH = ROOT / "reports/v4_01/baostock_lifecycle_facts_R4_20260925.json"
EXTRACTED_ROOT = ROOT / "data/input_staging/extracted/20260924" / PACKAGE_SHA


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", default="reports/v4_baostock/request_ledger.json")
    parser.add_argument("--receipt", default="reports/v4_01/baostock_lifecycle_boundary_probe_R4_20260925.json")
    parser.add_argument("--max-requests", type=int, default=18)
    args = parser.parse_args()

    facts_doc = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    stock_facts = [item for item in facts_doc["facts"] if item.get("security_type_provider") == "1"]
    type1_codes = {item["source_security_key"].lower() for item in stock_facts}
    sessions = sessions_from_index_chains(EXTRACTED_ROOT, 900)
    session_dates = [date(int(str(value)[:4]), int(str(value)[4:6]), int(str(value)[6:])) for value in sessions]
    session_index = {day: index for index, day in enumerate(session_dates)}
    cases = []
    for year in (2024, 2025, 2026):
        delisted = [item for item in stock_facts if item.get("source_security_key", "").startswith(("SH.", "SZ."))
                    and str(item.get("listed_to_provider_reported") or "").startswith(f"{year}-")
                    and date.fromisoformat(item["listed_to_provider_reported"]) in session_index]
        ipo = [item for item in stock_facts if item.get("source_security_key", "").startswith(("SH.", "SZ."))
               and item.get("listed_from", "").startswith(f"{year}-")
               and date.fromisoformat(item["listed_from"]) in session_index]
        if delisted:
            item = sorted(delisted, key=lambda x: (x["listed_to_provider_reported"], x["source_security_key"]))[len(delisted) // 2]
            boundary = date.fromisoformat(item["listed_to_provider_reported"])
            idx = session_index[boundary]
            if idx > 0 and idx + 1 < len(session_dates):
                cases.append({"kind": "DELIST", "code": item["source_security_key"].lower(),
                              "boundary_date": boundary.isoformat(),
                              "probe_dates": [session_dates[idx - 1].isoformat(), boundary.isoformat(), session_dates[idx + 1].isoformat()],
                              "expected_presence": [True, True, False]})
        if ipo:
            item = sorted(ipo, key=lambda x: (x["listed_from"], x["source_security_key"]))[len(ipo) // 2]
            boundary = date.fromisoformat(item["listed_from"])
            idx = session_index[boundary]
            if idx > 0 and idx + 1 < len(session_dates):
                cases.append({"kind": "IPO", "code": item["source_security_key"].lower(),
                              "boundary_date": boundary.isoformat(),
                              "probe_dates": [session_dates[idx - 1].isoformat(), boundary.isoformat(), session_dates[idx + 1].isoformat()],
                              "expected_presence": [False, True, True]})
    unique_dates = sorted({day for case in cases for day in case["probe_dates"]})
    if len(unique_dates) > args.max_requests:
        raise ValueError("BOUNDARY_PROBE_EXCEEDS_REQUEST_LIMIT")

    ledger_path = ROOT / args.ledger
    before = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    before_count = sum(int(item.get("count", 0)) for item in before.get("by_shanghai_date", {}).values())
    client = BaoStockClient(RequestBudget(ledger_path), auth_mode="PUBLIC_ANONYMOUS")
    started = time.monotonic()
    rosters = {}
    failures = {}
    try:
        with client:
            for day in unique_dates:
                rows, metadata = client.probe_all_stock(day)
                if metadata.get("error_code") != "0":
                    raise RuntimeError(f"QUERY_ALL_STOCK_FAILED:{day}:{metadata.get('error_code')}")
                roster_codes = {str(row.get("code", "")).strip().lower() for row in rows}
                observed_type1_codes = roster_codes & type1_codes
                rosters[day] = {"provider_row_count": len(rows), "type1_candidate_row_count": len(observed_type1_codes),
                                "type1_code_set_sha256": hashlib.sha256("\n".join(sorted(observed_type1_codes)).encode("ascii")).hexdigest(),
                                "candidate_membership": {case["code"]: case["code"] in type1_codes
                                                          and case["code"] in roster_codes for case in cases if day in case["probe_dates"]}}
    except Exception as exc:
        failures["session_or_query"] = type(exc).__name__ + ":" + str(exc)[:200]

    for case in cases:
        actual = [rosters.get(day, {}).get("candidate_membership", {}).get(case["code"])
                  for day in case["probe_dates"]]
        case["observed_presence"] = actual
        case["status"] = "PASS" if actual == case["expected_presence"] else "BLOCKED"

    after = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    after_count = sum(int(item.get("count", 0)) for item in after.get("by_shanghai_date", {}).values())
    receipt = {
        "stage": "V4-01-BAOSTOCK-LIFECYCLE-BOUNDARY-PROBE-R4",
        "contract_id": "V4_01_BAOSTOCK_LIFECYCLE_BOUNDARY_PROBE_V1",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "BOUNDARY_PROBE_PASS_ACCEPTANCE_PENDING" if cases and not failures and all(x["status"] == "PASS" for x in cases) else "BLOCKED",
        "boundary_semantics": {"ipoDate": "membership starts on the reported IPO date when it is an exchange session",
                               "outDate": "membership includes the reported outDate session; absent starting the next session"},
        "facts_revision_id": facts_doc["source_revision_id"],
        "cases": cases,
        "rosters": rosters,
        "request_count_delta": after_count - before_count,
        "configured_request_limit": args.max_requests,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "failures": failures,
        "execution_identity": {"input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                               "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        "limitation": "Boundary probes are stratified samples. They do not constitute AS_RECORDED lineage, daily trade-status history, issuer-level identity, or a substitute for independent acceptance.",
        "stage_completion_authorized": False,
    }
    _atomic_json(ROOT / args.receipt, receipt)
    print(json.dumps({"status": receipt["status"], "case_count": len(cases), "query_date_count": len(unique_dates),
                      "request_count_delta": receipt["request_count_delta"],
                      "case_statuses": {x["status"] for x in cases}, "failures": failures}, ensure_ascii=False))
    return 0 if receipt["status"] == "BOUNDARY_PROBE_PASS_ACCEPTANCE_PENDING" else 2


if __name__ == "__main__":
    raise SystemExit(main())
