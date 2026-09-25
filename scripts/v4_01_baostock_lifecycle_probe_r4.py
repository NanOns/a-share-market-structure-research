from __future__ import annotations

"""Capture bounded BaoStock listing/lifecycle facts and historical roster probes.

The output is explicitly reconstructed-at-observation evidence. It is not an
as-recorded snapshot and does not infer suspension, delisting, or issuer identity
from a missing bar or current catalog membership.
"""

import argparse
import hashlib
import importlib.metadata
import json
import re
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from market_calendar.trading_calendar import read_day_dates  # noqa: E402
from v4.contracts.source_overlap import sessions_from_index_chains  # noqa: E402
from workbench_analysis.baostock_supplemental import (  # noqa: E402
    BaoStockClient,
    RequestBudget,
    _atomic_json,
)

PACKAGE_SHA = "b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f"
EXTRACTED_ROOT = ROOT / "data/input_staging/extracted/20260924" / PACKAGE_SHA


def valid_iso_or_null(value: str | None) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def choose_probe_dates(sessions: list[int]) -> list[str]:
    if not sessions:
        raise ValueError("PACKAGE_SESSION_LIST_EMPTY")
    targets = (20240925, 20250925, 20260924)
    selected = []
    for target in targets:
        candidates = [value for value in sessions if value <= target]
        if not candidates:
            raise ValueError(f"NO_SESSION_AT_OR_BEFORE_{target}")
        selected.append(str(max(candidates)))
    return list(dict.fromkeys(f"{x[:4]}-{x[4:6]}-{x[6:]}" for x in selected))


def canonical_rows(rows: list[dict[str, str]]) -> tuple[list[dict], dict]:
    facts = []
    malformed = {"invalid_code": 0, "invalid_ipo_date": 0, "invalid_out_date": 0, "duplicate_code": 0}
    seen = set()
    for row in rows:
        code = str(row.get("code", "")).strip().lower()
        if not re.fullmatch(r"(?:sh|sz|bj)\.\d{6}", code):
            malformed["invalid_code"] += 1
            continue
        if code in seen:
            malformed["duplicate_code"] += 1
            continue
        seen.add(code)
        raw_ipo = str(row.get("ipoDate", "")).strip()
        raw_out = str(row.get("outDate", "")).strip()
        ipo = valid_iso_or_null(raw_ipo)
        out = valid_iso_or_null(raw_out)
        malformed["invalid_ipo_date"] += int(bool(raw_ipo) and ipo is None)
        malformed["invalid_out_date"] += int(bool(raw_out) and out is None)
        if ipo and out and out < ipo:
            malformed["invalid_out_date"] += 1
            out = None
        facts.append({
            "source_security_key": code.upper(),
            "canonical_security_id": None,
            "identity_quality": "UNMAPPED_LISTING_KEY_ONLY",
            "listed_from": ipo,
            "listed_to_provider_reported": out,
            "security_type_provider": str(row.get("type", "")).strip() or None,
            "provider_status_observed": str(row.get("status", "")).strip() or None,
            "history_lineage": "RECONSTRUCTED_CORRECTED",
        })
    facts.sort(key=lambda item: item["source_security_key"])
    return facts, malformed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", default="reports/v4_baostock/request_ledger.json")
    parser.add_argument("--receipt", default="reports/v4_01/baostock_lifecycle_probe_R4_20260925.json")
    parser.add_argument("--facts", default="reports/v4_01/baostock_lifecycle_facts_R4_20260925.json")
    args = parser.parse_args()

    sessions = sessions_from_index_chains(EXTRACTED_ROOT, 1_000)
    probe_dates = choose_probe_dates(sessions)
    observed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    ledger_path = ROOT / args.ledger
    before = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    before_count = sum(int(item.get("count", 0)) for item in before.get("by_shanghai_date", {}).values())
    client = BaoStockClient(RequestBudget(ledger_path), auth_mode="PUBLIC_ANONYMOUS")
    started = time.monotonic()
    catalog_meta = {}
    facts = []
    rosters = []
    failures = {}
    try:
        with client:
            catalog, catalog_meta = client.query_rows(
                "query_stock_basic", "query_stock_basic", max_rows=10_000, max_pages=10
            )
            facts, malformed = canonical_rows(catalog)
            for day in probe_dates:
                rows, meta = client.probe_all_stock(day)
                codes = sorted({str(row.get("code", "")).strip().lower() for row in rows
                                if re.fullmatch(r"(?:sh|sz|bj)\.\d{6}", str(row.get("code", "")).strip().lower())})
                digest = hashlib.sha256("\n".join(codes).encode("ascii")).hexdigest()
                rosters.append({"effective_date": day, "row_count": len(rows), "unique_valid_code_count": len(codes),
                                "code_set_sha256": digest, "codes": codes, "provider_fields": meta["fields"],
                                "provider_error_code": meta["error_code"],
                                "history_lineage": "RECONSTRUCTED_CORRECTED"})
    except Exception as exc:
        malformed = {"invalid_code": 0, "invalid_ipo_date": 0, "invalid_out_date": 0, "duplicate_code": 0}
        failures["probe"] = type(exc).__name__ + ":" + str(exc)[:180]

    facts_by_code = {item["source_security_key"].lower(): item for item in facts}
    for roster in rosters:
        active_by_dates = set()
        unknown_by_dates = set()
        effective_date = roster["effective_date"]
        for code in roster["codes"]:
            item = facts_by_code.get(code)
            if item is None or item["listed_from"] is None:
                unknown_by_dates.add(code)
                continue
            if item["listed_from"] <= effective_date and (
                item["listed_to_provider_reported"] is None or item["listed_to_provider_reported"] >= effective_date
            ):
                active_by_dates.add(code)
        roster["basic_catalog_interval_candidate_count"] = len(active_by_dates)
        roster["roster_without_confirmed_basic_interval_count"] = len(set(roster["codes"]) - active_by_dates)
        roster["roster_missing_listing_fact_count"] = len(unknown_by_dates)

    after = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    after_count = sum(int(item.get("count", 0)) for item in after.get("by_shanghai_date", {}).values())
    facts_payload = {
        "contract_id": "V4_01_BAOSTOCK_LISTING_LIFECYCLE_FACT_CANDIDATES_V1",
        "version": "1.0.0",
        "observed_at_utc": observed_at,
        "provider": {"name": "BaoStock", "version": importlib.metadata.version("baostock"),
                     "auth_mode": client.auth_mode, **client.runtime_endpoint},
        "query": "query_stock_basic with code/date/type/status fields",
        "query_metadata": {"error_code": catalog_meta.get("error_code"), "fields": catalog_meta.get("fields"),
                           "page_count": catalog_meta.get("page_count"), "row_count": catalog_meta.get("row_count")},
        "source_revision_id": "sha256:" + hashlib.sha256(json.dumps(facts, ensure_ascii=False, sort_keys=True,
                                                         separators=(",", ":")).encode("utf-8")).hexdigest(),
        "history_lineage": "RECONSTRUCTED_CORRECTED",
        "as_recorded_history": False,
        "facts": facts,
        "malformed_counts": malformed,
    }
    _atomic_json(ROOT / args.facts, facts_payload)
    receipt = {
        "stage": "V4-01-BAOSTOCK-LIFECYCLE-RECONSTRUCTION-PROBE",
        "contract_id": "V4_01_BAOSTOCK_LIFECYCLE_RECONSTRUCTION_PROBE_V1",
        "observed_at_utc": observed_at,
        "status": "PROBE_PASS_ACCEPTANCE_PENDING" if not failures and len(rosters) == len(probe_dates) else "BLOCKED",
        "stage_completion_authorized": False,
        "candidate_facts": args.facts.replace("\\", "/"),
        "candidate_facts_sha256": hashlib.sha256((ROOT / args.facts).read_bytes()).hexdigest(),
        "candidate_fact_count": len(facts),
        "candidate_fact_revision_id": facts_payload["source_revision_id"],
        "identity_policy": "BaoStock listing codes are source keys only; canonical_security_id remains null pending accepted cross-source identity mapping.",
        "lifecycle_policy": "IPO/outDate are reconstructed listing-boundary candidates observed at retrieval time. Provider status is not used to backfill historical trade status; outDate boundary semantics remain acceptance-pending.",
        "historical_roster_probes": rosters,
        "malformed_counts": malformed,
        "request_count_delta": after_count - before_count,
        "request_budget": {"daily_soft_cap": 40_000, "daily_hard_cap": 45_000, "provider_limit": 50_000,
                           "count_after": after_count},
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "failures": failures,
        "execution_identity": {"input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                               "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        "blockers": ["canonical_identity_mapping_acceptance", "outDate_effective_boundary_independent_validation",
                     "full_actual_session_universe_materialization", "independent_lifecycle_evidence_review"],
        "next_stage": "BUILD_HISTORICAL_EVALUABLE_UNIVERSE_AFTER_LIFECYCLE_BOUNDARY_ACCEPTANCE",
    }
    _atomic_json(ROOT / args.receipt, receipt)
    print(json.dumps({"status": receipt["status"], "candidate_facts": len(facts), "probe_dates": probe_dates,
                      "rosters": [{key: value for key, value in row.items() if key != "codes"} for row in rosters],
                      "requests": receipt["request_count_delta"], "failures": failures}, ensure_ascii=False))
    return 0 if receipt["status"] == "PROBE_PASS_ACCEPTANCE_PENDING" else 2


if __name__ == "__main__":
    raise SystemExit(main())
