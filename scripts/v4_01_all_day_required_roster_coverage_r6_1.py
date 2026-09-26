from __future__ import annotations

"""Seal all-day required lifecycle identity coverage against the accepted R6 rosters."""

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402
from workbench_analysis.v4_01_required_scope import (  # noqa: E402
    REQUIRED_BOARD_KEYS, all_day_required_roster_coverage, required_board,
)


ROSTER = ROOT / "data/v4/artifact_store/v4_01/baostock_dated_rosters_R6_20260926.jsonl.gz"
ROSTER_RECEIPT = ROOT / "reports/v4_01/baostock_dated_roster_completeness_receipt_R6_20260926.json"
MAP = ROOT / "data/v4/artifact_store/v4_01/security_entity_map_R5_20260925.json"
SCOPE_RECEIPT = ROOT / "reports/v4_01/required_scope_gates_receipt_R6_20260926.json"
LIFECYCLE = ROOT / "reports/v4_01/baostock_lifecycle_facts_R4_20260925.json"
DEFAULT_OUTPUT = "reports/v4_01/V4_01_ALL_DAY_REQUIRED_ROSTER_COVERAGE_R6_1.json"
PRE_INTERVAL = ROOT / "reports/v4_01/V4_01_ALL_DAY_REQUIRED_ROSTER_COVERAGE_R6_1_PRE_INTERVAL.json"
REQUERY_RECEIPT = ROOT / "reports/v4_01/V4_01_MISSING_DAY_REQUERY_R6_1.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def code_digest(codes: list[str]) -> str:
    return hashlib.sha256("\n".join(codes).encode("ascii")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    roster_receipt = read_json(ROSTER_RECEIPT)
    scope_receipt = read_json(SCOPE_RECEIPT)
    lifecycle = read_json(LIFECYCLE)
    pre_interval = read_json(PRE_INTERVAL)
    requery = read_json(REQUERY_RECEIPT)
    roster_sha = sha256(ROSTER)
    map_sha = sha256(MAP)
    lifecycle_sha = sha256(LIFECYCLE)
    if roster_receipt.get("status") != "PASS" or roster_receipt.get("summary", {}).get("session_count") != 786:
        raise SystemExit("R6_ROSTER_RECEIPT_NOT_ACCEPTED_OR_WRONG_SESSION_COUNT")
    if map_sha != scope_receipt.get("inputs", {}).get("identity_map_sha256"):
        raise SystemExit("R6_IDENTITY_MAP_DIGEST_MISMATCH")
    if lifecycle_sha != scope_receipt.get("inputs", {}).get("lifecycle_facts_sha256"):
        raise SystemExit("R6_LIFECYCLE_FACTS_DIGEST_MISMATCH")
    if read_json(MAP).get("inputs", {}).get("lifecycle_facts_sha256") != lifecycle_sha:
        raise SystemExit("IDENTITY_MAP_LIFECYCLE_BINDING_MISMATCH")
    pre_interval_sha = sha256(PRE_INTERVAL)
    requery_by_day = {row["trade_date"]: row for row in requery.get("requeried_dates", [])}
    targeted_days = [row for row in pre_interval.get("daily", []) if row["missing_required_identity_count"]]
    if (pre_interval.get("status") != "BLOCKED"
            or requery.get("status") != "PASS"
            or requery.get("requeried_date_count") != len(targeted_days)
            or requery.get("input_all_day_coverage_sha256") != pre_interval_sha):
        raise SystemExit("R6_1_BOUNDARY_REQUERY_EVIDENCE_INCOMPLETE")
    for old in targeted_days:
        check = requery_by_day.get(old["trade_date"])
        if (not check or not check.get("fresh_runs_stable")
                or check.get("fresh_query_1", {}).get("codes_sha256") != check.get("accepted_roster_codes_sha256")
                or check.get("fresh_query_2", {}).get("codes_sha256") != check.get("accepted_roster_codes_sha256")
                or check.get("target_codes_present_in_both_fresh_rosters")
                or check.get("fresh_query_1", {}).get("provider_error_code") != "0"
                or check.get("fresh_query_2", {}).get("provider_error_code") != "0"
                or check.get("daily_market_provider_error_code") != "0"):
            raise SystemExit(f"R6_1_TARGETED_REQUERY_NOT_STABLE:{old['trade_date']}")

    days = [row["trade_date"] for row in roster_receipt["daily_completeness"]]
    rosters: dict[str, set[str]] = {}
    with gzip.open(ROSTER, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            day, codes = row.get("trade_date"), row.get("source_codes")
            if day in rosters or not isinstance(codes, list) or codes != sorted(set(codes)):
                raise SystemExit("R6_ROSTER_RECORD_INVALID")
            if row.get("row_count") != len(codes) or code_digest(codes) != row.get("codes_sha256"):
                raise SystemExit(f"R6_ROSTER_RECORD_DIGEST_INVALID:{day}")
            rosters[day] = set(codes)
    if list(rosters) != days:
        raise SystemExit("R6_ROSTER_DATES_OR_ORDER_MISMATCH")
    receipt_daily = {row["trade_date"]: row for row in roster_receipt["daily_completeness"]}
    if any(receipt_daily[day].get("row_count") != len(rosters[day])
           or receipt_daily[day].get("codes_sha256") != code_digest(sorted(rosters[day])) for day in days):
        raise SystemExit("R6_ROSTER_RECEIPT_DAILY_DIGEST_MISMATCH")

    identity_doc = read_json(MAP)
    identities = [row for row in identity_doc.get("records", []) if required_board(row)]
    if len({row.get("source_security_key", "").lower() for row in identities}) != len(identities):
        raise SystemExit("DUPLICATE_REQUIRED_IDENTITY_KEYS")
    for board in REQUIRED_BOARD_KEYS:
        expected = scope_receipt["required_scope"][board]["identity"].get("security_keys")
        actual = sum(required_board(row) == board for row in identities)
        if actual != expected:
            raise SystemExit(f"REQUIRED_IDENTITY_BOARD_COUNT_MISMATCH:{board}:{actual}:{expected}")
    # Bind accepted lifecycle facts directly as well as through the R6 gate and identity map.
    lifecycle_by_key = {str(row.get("source_security_key", "")).lower(): row for row in lifecycle.get("facts", [])}
    for row in identities:
        key = str(row.get("source_security_key", "")).lower()
        fact = lifecycle_by_key.get(key)
        if (not fact or str(fact.get("security_type_provider")) != "1"
                or fact.get("listed_from") != row.get("list_date")
                or not row.get("security_id") or not row.get("source_revision_id")):
            raise SystemExit(f"ACCEPTED_LIFECYCLE_IDENTITY_BINDING_INVALID:{key}")

    coverage = all_day_required_roster_coverage(identities, days, rosters)
    requery_checks = [requery_by_day[row["trade_date"]] for row in targeted_days]
    roster_confirmed_absent = all(
        check.get("fresh_runs_stable")
        and check.get("fresh_query_1", {}).get("codes_sha256") == check.get("accepted_roster_codes_sha256")
        and check.get("fresh_query_2", {}).get("codes_sha256") == check.get("accepted_roster_codes_sha256")
        and not check.get("target_codes_present_in_both_fresh_rosters")
        for check in requery_checks
    )
    code_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    script_sha = sha256(Path(__file__))
    daily_material = "".join(
        f"{row['trade_date']}\0{row['row_count']}\0{row['codes_sha256']}\0"
        f"{coverage['daily'][index]['expected_required_identity_count']}\0"
        f"{coverage['daily'][index]['observed_required_identity_count']}\0"
        f"{coverage['daily'][index]['missing_required_identity_count']}\0"
        f"{coverage['daily'][index]['missing_board_sha256']}\n"
        for index, row in enumerate(roster_receipt["daily_completeness"])
    )
    coverage["roster_coverage_daily_digest_root"] = hashlib.sha256(daily_material.encode("ascii")).hexdigest()
    receipt = {
        "stage": "V4-01-R6.1", "contract_id": "V4_01_ALL_DAY_REQUIRED_ROSTER_COVERAGE_R6_1",
        "version": "1.0.0", "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "PASS" if coverage["session_count"] == 786 and coverage["total_missing_required_identity_rows"] == 0 else "BLOCKED",
        **coverage,
        "inputs": {
            "roster_path": str(ROSTER.relative_to(ROOT)), "roster_sha256": roster_sha,
            "roster_receipt_path": str(ROSTER_RECEIPT.relative_to(ROOT)),
            "roster_receipt_sha256": sha256(ROSTER_RECEIPT),
            "identity_map_path": str(MAP.relative_to(ROOT)), "identity_map_sha256": map_sha,
            "lifecycle_facts_path": str(LIFECYCLE.relative_to(ROOT)), "lifecycle_facts_sha256": lifecycle_sha,
            "scope_gate_receipt_path": str(SCOPE_RECEIPT.relative_to(ROOT)),
            "scope_gate_receipt_sha256": sha256(SCOPE_RECEIPT),
            "pre_interval_coverage_receipt_path": str(PRE_INTERVAL.relative_to(ROOT)),
            "pre_interval_coverage_receipt_sha256": pre_interval_sha,
            "targeted_requery_receipt_path": str(REQUERY_RECEIPT.relative_to(ROOT)),
            "targeted_requery_receipt_sha256": sha256(REQUERY_RECEIPT),
            "lifecycle_source_revision_id": lifecycle.get("source_revision_id"),
            "identity_source_revision_ids_sha256": hashlib.sha256("\n".join(sorted(
                {str(row.get("source_revision_id")) for row in identities}
            )).encode("utf-8")).hexdigest(),
        },
        "acceptance_rule": "For every R6 trading session, every accepted SH_MAIN/SZ_MAIN/CHINEXT/STAR identity active_on(day) under the existing inclusive R6 lifecycle interval must occur in that exact dated R6 roster; BSE remains excluded optional scope.",
        "out_date_boundary_resolution": "UNRESOLVED: 39 active-interval identities are absent on their reported end dates, while 90 other end-date identities occur in the R6 rosters; no generalized end-date reinterpretation is accepted.",
        "targeted_requery": {"status": requery.get("status"), "dates_requeried": requery.get("requeried_date_count"),
                             "dates_with_stable_roster_matching_R6": sum(
                                 check.get("fresh_runs_stable")
                                 and check.get("fresh_query_1", {}).get("codes_sha256") == check.get("accepted_roster_codes_sha256")
                                 and check.get("fresh_query_2", {}).get("codes_sha256") == check.get("accepted_roster_codes_sha256")
                                 for check in requery_checks),
                             "all_targeted_rosters_reconfirmed_without_truncation": roster_confirmed_absent},
        "execution_identity": {"execution_commit": code_head, "script_path": str(Path(__file__).relative_to(ROOT)),
                               "script_sha256": script_sha},
        "next_stage": "V4_01_FINAL_RECEIPT_R6_1" if coverage["total_missing_required_identity_rows"] == 0 else (
            "RECONCILE_OUTDATE_BOUNDARY_SEMANTICS" if roster_confirmed_absent else
            "REPAIR_PROVIDER_CONFIRMED_MISSING_DATES"),
    }
    _atomic_json(ROOT / args.output, receipt)
    print(json.dumps({key: receipt[key] for key in (
        "status", "session_count", "days_with_missing_required_identity", "max_missing_per_day",
        "total_missing_required_identity_rows", "missing_by_board", "roster_coverage_daily_digest_root",
    )}, ensure_ascii=False))
    return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
