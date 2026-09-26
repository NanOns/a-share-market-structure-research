from __future__ import annotations

"""Resolve R6.2 required-scope lifecycle membership from accepted dated rosters."""

import argparse
import gzip
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402
from workbench_analysis.v4_01_required_scope import REQUIRED_BOARD_KEYS, required_board  # noqa: E402

CONTRACT = "DATED_ROSTER_MEMBERSHIP_BOUNDARY_V1"
WINDOW_START = "2023-07-04"
WINDOW_END = "2026-09-24"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_jsonl_gz(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temp = Path(temp_name)
    try:
        with gzip.open(temp, "wt", encoding="utf-8", newline="\n", compresslevel=6) as stream:
            for row in records:
                stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")
        with temp.open("rb+") as stream:
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def load_rosters(path: Path) -> tuple[list[str], dict[str, set[str]], dict[str, list[str]]]:
    days: list[str] = []
    by_day: dict[str, set[str]] = {}
    by_key: dict[str, list[str]] = defaultdict(list)
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            day, codes = row["trade_date"], row["source_codes"]
            if day in by_day or codes != sorted(set(codes)):
                raise SystemExit("R6_2_ROSTER_ORDER_OR_UNIQUENESS_INVALID")
            if row.get("row_count") != len(codes) or hashlib.sha256("\n".join(codes).encode("ascii")).hexdigest() != row.get("codes_sha256"):
                raise SystemExit("R6_2_ROSTER_ROW_DIGEST_INVALID")
            days.append(day)
            by_day[day] = set(codes)
            for code in codes:
                by_key[code].append(day)
    if len(days) != 786 or days[0] != WINDOW_START or days[-1] != WINDOW_END:
        raise SystemExit("R6_2_ROSTER_WINDOW_INVALID")
    return days, by_day, by_key


def split_runs(days: list[str], session_index: dict[str, int]) -> list[list[str]]:
    runs: list[list[str]] = []
    for day in days:
        if not runs or session_index[day] != session_index[runs[-1][-1]] + 1:
            runs.append([day])
        else:
            runs[-1].append(day)
    return runs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rosters", default="data/v4/artifact_store/v4_01/baostock_dated_rosters_R6_20260926.jsonl.gz")
    parser.add_argument("--roster-receipt", default="reports/v4_01/baostock_dated_roster_completeness_receipt_R6_20260926.json")
    parser.add_argument("--identity-map", default="data/v4/artifact_store/v4_01/security_entity_map_R5_20260925.json")
    parser.add_argument("--lifecycle-facts", default="reports/v4_01/baostock_lifecycle_facts_R4_20260925.json")
    parser.add_argument("--coverage-r6-1", default="reports/v4_01/V4_01_ALL_DAY_REQUIRED_ROSTER_COVERAGE_R6_1.json")
    parser.add_argument("--intervals", default="data/v4/artifact_store/v4_01/security_membership_intervals_R6_2_20260926.jsonl.gz")
    parser.add_argument("--receipt", default="reports/v4_01/V4_01_LIFECYCLE_BOUNDARY_RESOLUTION_R6_2.json")
    args = parser.parse_args()
    roster_path, map_path, facts_path = ROOT / args.rosters, ROOT / args.identity_map, ROOT / args.lifecycle_facts
    roster_receipt_path, old_coverage_path = ROOT / args.roster_receipt, ROOT / args.coverage_r6_1
    interval_path = ROOT / args.intervals
    roster_receipt = json.loads(roster_receipt_path.read_text("utf-8"))
    old_coverage = json.loads(old_coverage_path.read_text("utf-8"))
    if roster_receipt.get("status") != "PASS" or roster_receipt.get("summary", {}).get("session_count") != 786:
        raise SystemExit("R6_2_ACCEPTED_ROSTER_RECEIPT_REQUIRED")
    if old_coverage.get("status") != "BLOCKED" or old_coverage.get("session_count") != 786:
        raise SystemExit("R6_1_BLOCKED_COVERAGE_BINDING_INVALID")
    identity_doc = json.loads(map_path.read_text("utf-8"))
    facts_doc = json.loads(facts_path.read_text("utf-8"))
    if facts_doc.get("as_recorded_history") is not False:
        raise SystemExit("R6_2_RAW_PROVIDER_FACT_LINEAGE_INVALID")
    sessions, rosters, roster_days_by_key = load_rosters(roster_path)
    session_index = {day: index for index, day in enumerate(sessions)}
    facts = {str(row.get("source_security_key", "")).lower(): row for row in facts_doc.get("facts", [])}
    required = [row for row in identity_doc.get("records", []) if required_board(row)]
    identity_by_key = {str(row.get("source_security_key", "")).lower(): row
                       for row in identity_doc.get("records", [])}
    keys = [str(row.get("source_security_key") or "").lower() for row in required]
    if len(keys) != len(set(keys)) or any(not key for key in keys):
        raise SystemExit("R6_2_REQUIRED_IDENTITY_KEY_NOT_UNIQUE")
    required_by_key = {str(row["source_security_key"]).lower(): row for row in required}

    intervals: list[dict[str, Any]] = []
    unresolved_by_board = Counter()
    outdate_counts = Counter()
    present_count = absent_count = outside_count = pre_window_excluded_count = 0
    missing_fact_keys: list[str] = []
    unmapped_provider_type1_roster_keys = sorted(
        key for key in roster_days_by_key
        if facts.get(key, {}).get("security_type_provider") == "1" and key not in identity_by_key
    )
    roster_present_by_key = {key: set(days) for key, days in roster_days_by_key.items()}
    required_intervals_by_day: dict[str, set[str]] = {day: set() for day in sessions}

    for identity in required:
        key = str(identity["source_security_key"]).lower()
        board = required_board(identity)
        fact = facts.get(key)
        if not fact or fact.get("security_type_provider") != "1":
            missing_fact_keys.append(key)
            unresolved_by_board[board] += 1
            continue
        observed_days = [day for day in roster_days_by_key.get(key, []) if day in session_index]
        raw_ipo = fact.get("listed_from")
        raw_out = fact.get("listed_to_provider_reported")
        in_window_out = bool(raw_out and WINDOW_START <= raw_out <= WINDOW_END)
        if not observed_days and raw_out and raw_out < WINDOW_START:
            # The raw provider lifecycle fact places this identity wholly before the accepted roster window.
            pre_window_excluded_count += 1
            outside_count += 1
            continue
        if in_window_out:
            outdate_counts[board] += 1
            if raw_out in roster_present_by_key.get(key, set()):
                resolution = {"to_boundary_basis": "DATED_ROSTER_PRESENT_ON_PROVIDER_OUTDATE",
                              "boundary_quality": "RESOLVED_BY_SAME_DAY_ROSTER_PRESENCE", "unresolved": False}
                present_count += 1
            else:
                prior_days = [day for day in observed_days if day < raw_out]
                after_days = [day for day in observed_days if day > raw_out]
                if prior_days and not after_days:
                    resolution = {"to_boundary_basis": "LAST_DATED_ROSTER_MEMBERSHIP_BEFORE_PROVIDER_OUTDATE",
                                  "boundary_quality": "RESOLVED_BY_PRIOR_ROSTER_MEMBERSHIP_NO_REAPPEARANCE", "unresolved": False}
                    absent_count += 1
                else:
                    resolution = {"to_boundary_basis": "UNRESOLVED_OUTDATE_ROSTER_CONTRADICTION",
                                  "boundary_quality": "UNRESOLVED_OUTDATE_ROSTER_CONTRADICTION", "unresolved": True}
                    unresolved_by_board[board] += 1
        else:
            resolution = {"to_boundary_basis": "DATED_ROSTER_MEMBERSHIP_OBSERVATION_WINDOW",
                          "boundary_quality": "WINDOW_ONLY_PROVIDER_OUTDATE_NOT_IN_WINDOW", "unresolved": False}
            if raw_out:
                outside_count += 1

        runs = split_runs(observed_days, session_index)
        for run_index, run in enumerate(runs):
            is_last_run = run_index == len(runs) - 1
            start = run[0]
            end = run[-1]
            to_basis = "DATED_ROSTER_MEMBERSHIP_RUN_END"
            quality = "ROSTER_OBSERVED_WINDOW_SEGMENT"
            if in_window_out and is_last_run:
                to_basis = resolution["to_boundary_basis"]
                quality = resolution["boundary_quality"]
                if not resolution["unresolved"] and raw_out in run:
                    end = raw_out
                elif not resolution["unresolved"] and raw_out not in run:
                    end = run[-1]
            row = {
                "security_id": identity.get("security_id"),
                "source_security_key": key.upper(),
                "normalized_effective_from": start,
                "normalized_effective_to": end,
                "from_boundary_basis": "FIRST_DATED_ROSTER_MEMBERSHIP_IN_WINDOW",
                "to_boundary_basis": to_basis,
                "provider_ipo_date": raw_ipo,
                "provider_out_date": raw_out,
                "first_observed_roster_date": observed_days[0] if observed_days else None,
                "last_observed_roster_date": observed_days[-1] if observed_days else None,
                "boundary_quality": quality,
                "source_contract_id": CONTRACT,
                "provider_fact_contract_id": facts_doc.get("contract_id"),
                "provider_fact_source_revision_id": identity.get("source_revision_id"),
                "security_identity_source_contract_id": identity.get("source_contract_id"),
                "security_identity_source_revision_id": identity.get("source_revision_id"),
                "roster_run_index": run_index,
                "roster_run_count": len(runs),
            }
            intervals.append(row)
            for day in run:
                required_intervals_by_day[day].add(key)
        if not observed_days and not (raw_out and raw_out < WINDOW_START):
            unresolved_by_board[board] += 1

    daily = []
    by_board_missing = {board: 0 for board in REQUIRED_BOARD_KEYS}
    missing_total = 0
    for day in sessions:
        missing_by_board = {board: [] for board in REQUIRED_BOARD_KEYS}
        expected = required_intervals_by_day[day]
        for key in expected:
            identity = required_by_key[key]
            board = required_board(identity)
            if key not in rosters[day]:
                missing_by_board[board].append(key)
        for board in REQUIRED_BOARD_KEYS:
            missing_by_board[board].sort()
            by_board_missing[board] += len(missing_by_board[board])
        total = sum(map(len, missing_by_board.values()))
        missing_total += total
        daily.append({"trade_date": day, "expected_required_identity_count": len(expected),
                      "observed_required_identity_count": len(expected) - total,
                      "missing_required_identity_count": total,
                      "missing_by_board": {board: len(missing_by_board[board]) for board in REQUIRED_BOARD_KEYS}})

    intervals.sort(key=lambda row: (row["source_security_key"], row["normalized_effective_from"], row["roster_run_index"]))
    write_jsonl_gz(interval_path, intervals)
    resolver_path = Path(__file__)
    unresolved_count = sum(unresolved_by_board.values())
    receipt = {
        "stage": "V4-01-LIFECYCLE-BOUNDARY-RESOLUTION-R6_2",
        "contract_id": CONTRACT,
        "version": "1.0.0",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "PASS" if not unresolved_count and not missing_fact_keys and not missing_total else "BLOCKED",
        "stage_completion_authorized": False,
        "raw_provider_fact_preserved": True,
        "scope": {"window_start": WINDOW_START, "window_end": WINDOW_END,
                  "required_boards": list(REQUIRED_BOARD_KEYS), "dated_roster_session_count": len(sessions)},
        "resolution": {
            "required_security_count": len(required),
            "provider_outdate_in_window_count": sum(outdate_counts.values()),
            "outdate_present_same_day_count": present_count,
            "outdate_absent_same_day_count": absent_count,
            "provider_outdate_outside_window_count": outside_count,
            "provider_outdate_pre_window_excluded_count": pre_window_excluded_count,
            "resolved_by_same_day_presence": present_count,
            "resolved_by_prior_membership": absent_count,
            "unresolved_boundary_count": unresolved_count,
            "unresolved_boundary_by_board": {board: unresolved_by_board[board] for board in REQUIRED_BOARD_KEYS},
            "missing_provider_fact_count": len(missing_fact_keys),
            "missing_provider_fact_keys": missing_fact_keys,
            "roster_unmapped_provider_type1_identity_count": len(unmapped_provider_type1_roster_keys),
            "roster_unmapped_provider_type1_identity_keys": unmapped_provider_type1_roster_keys,
            "outdate_counts_by_board": {board: outdate_counts[board] for board in REQUIRED_BOARD_KEYS},
        },
        "normalized_intervals": {"path": args.intervals, "sha256": sha(interval_path),
                                 "row_count": len(intervals), "byte_count": interval_path.stat().st_size,
                                 "distinct_security_keys": len({row["source_security_key"] for row in intervals}),
                                 "source_contract_id": CONTRACT},
        "all_day_coverage": {"session_count": len(sessions), "days_with_missing_required_identity": sum(row["missing_required_identity_count"] > 0 for row in daily),
                             "total_missing_required_identity_rows": missing_total, "missing_by_board": by_board_missing,
                             "daily": daily},
        "inputs": {"roster_path": args.rosters, "roster_sha256": sha(roster_path),
                   "roster_receipt_path": args.roster_receipt, "roster_receipt_sha256": sha(roster_receipt_path),
                   "r6_1_coverage_path": args.coverage_r6_1, "r6_1_coverage_sha256": sha(old_coverage_path),
                   "identity_map_path": args.identity_map, "identity_map_sha256": sha(map_path),
                   "provider_lifecycle_facts_path": args.lifecycle_facts, "provider_lifecycle_facts_sha256": sha(facts_path),
                   "resolver_script_sha256": sha(resolver_path)},
        "lineage": "RECONSTRUCTED_CORRECTED_FROM_ACCEPTED_DATED_ROSTER; no provider raw fact mutation",
        "execution_identity": {"code_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()},
        "next_stage": "V4_01_R6_2_APPEND_LIFECYCLE_REVISIONS_AND_REBUILD_UNIVERSE" if not unresolved_count and not missing_total else "V4_01_REMEDIATE_R6_2_LIFECYCLE_BOUNDARIES",
    }
    _atomic_json(ROOT / args.receipt, receipt)
    print(json.dumps({"status": receipt["status"], "resolution": receipt["resolution"],
                      "coverage": {k: receipt["all_day_coverage"][k] for k in ("session_count", "days_with_missing_required_identity", "total_missing_required_identity_rows", "missing_by_board")},
                      "intervals": receipt["normalized_intervals"], "receipt": args.receipt}, ensure_ascii=False))
    return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
