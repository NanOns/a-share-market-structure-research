from __future__ import annotations

"""Build a bounded historical reconstructed universe from dated BaoStock rosters."""

import argparse
import bisect
import gzip
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v4.contracts.source_overlap import sessions_from_index_chains  # noqa: E402
from tdx.day_reader import DAY_STRUCT, validate_day_file  # noqa: E402
from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402
from workbench_analysis.security_entity_identity import bao_source_entity  # noqa: E402

PACKAGE_SHA = "b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f"
BUNDLE_ID = "6122afa9db83170f7b442d5ecc5c7c9287b9dd6b04c4d53729d55f71f7dd99d2"
EXTRACTED_ROOT = ROOT / "data/input_staging/extracted/20260924" / PACKAGE_SHA
FACTS_PATH = ROOT / "reports/v4_01/baostock_lifecycle_facts_R4_20260925.json"
LIFECYCLE_PROBE_PATH = ROOT / "reports/v4_01/baostock_lifecycle_probe_R4_20260925.json"
BOUNDARY_PROBE_PATH = ROOT / "reports/v4_01/baostock_lifecycle_boundary_probe_R4_20260925.json"
SELECTION_PATH = ROOT / "reports/v4_01/canonical_source_selection_R4_20260925.json"
LOCAL_ROOT = ROOT / "data/v4/local_tdx_snapshots/1644752b002fdeb4f3d3a2968b9c77729f27efcdae8923ad14d814abe5c78c70"
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


def source_key_for_path(path: Path, root: Path) -> tuple[str, str] | None:
    relative = path.relative_to(root).as_posix().lower()
    match = re.fullmatch(r"(sh|sz|bj)/lday/(sh|sz|bj)(\d{6})\.day", relative)
    if not match or match.group(1) != match.group(2):
        return None
    return f"{match.group(1)}.{match.group(3)}", match.group(1)


def source_bar_dates(session_set: set[int], source_keys: set[str]) -> tuple[dict[int, set[str]], list[dict]]:
    """Index validated source-file date coverage without inferring suspension."""
    by_date: dict[int, set[str]] = {}
    errors = []
    roots = ((EXTRACTED_ROOT, "PACKAGE"), (LOCAL_ROOT, "LOCAL"))
    for root, family in roots:
        for path in sorted(root.glob("*/lday/*.day"), key=lambda item: item.as_posix().casefold()):
            parsed = source_key_for_path(path, root)
            if parsed is None:
                continue
            code, market = parsed
            if code not in source_keys:
                continue
            validation = validate_day_file(path, market.upper())
            if not validation.get("valid"):
                errors.append({"source_family": family, "source_security_key": code.upper(),
                               "relative_path": path.relative_to(root).as_posix(),
                               "errors": validation.get("errors", [])})
                continue
            raw = path.read_bytes()
            for row in DAY_STRUCT.iter_unpack(raw):
                day = int(row[0])
                if day in session_set:
                    by_date.setdefault(day, set()).add(code)
    return by_date, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--formal-start", default="2024-09-25")
    parser.add_argument("--warmup-sessions", type=int, default=300)
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
    lifecycle_probe = json.loads(LIFECYCLE_PROBE_PATH.read_text(encoding="utf-8"))
    boundary_probe = json.loads(BOUNDARY_PROBE_PATH.read_text(encoding="utf-8"))

    sessions = sessions_from_index_chains(EXTRACTED_ROOT, max(args.warmup_sessions + 600, 800))
    session_dates = [date(int(str(value)[:4]), int(str(value)[4:6]), int(str(value)[6:])) for value in sessions]
    formal_index = next((index for index, item in enumerate(session_dates) if item >= formal_start), None)
    if formal_index is None:
        raise ValueError("FORMAL_START_AFTER_LAST_SOURCE_SESSION")
    first_index = max(0, formal_index - args.warmup_sessions)
    selected_sessions = session_dates[first_index:]
    if not selected_sessions or selected_sessions[-1] > date(2026, 9, 24):
        raise ValueError("UNIVERSE_SESSION_RANGE_OUTSIDE_SOURCE_CUTOFF")
    session_ints = {int(item.strftime("%Y%m%d")) for item in selected_sessions}
    boundary_unknown_by_day: dict[date, set[str]] = {}
    for code, fact in facts.items():
        out_date = as_date(fact.get("listed_to_provider_reported"))
        if out_date is None or out_date < selected_sessions[0] or out_date > selected_sessions[-1]:
            continue
        insertion = bisect.bisect_left(selected_sessions, out_date)
        adjacent = []
        if insertion < len(selected_sessions) and selected_sessions[insertion] == out_date:
            adjacent = [out_date]
        else:
            if insertion > 0:
                adjacent.append(selected_sessions[insertion - 1])
            if insertion < len(selected_sessions):
                adjacent.append(selected_sessions[insertion])
        for boundary_session in adjacent:
            boundary_unknown_by_day.setdefault(boundary_session, set()).add(code)
    bar_dates, bar_source_errors = source_bar_dates(session_ints, source_keys)

    # Independently replay the three archived dated rosters against the
    # lifecycle intervals; this does not turn reconstructed facts into PIT.
    roster_validations = []
    for roster in lifecycle_probe.get("historical_roster_probes", []):
        roster_day = date.fromisoformat(roster["effective_date"])
        actual = {code for code in roster.get("codes", [])
                  if facts.get(code, {}).get("security_type_provider") == "1"}
        expected = {code for code, fact in facts.items()
                    if (listed_from := as_date(fact.get("listed_from"))) is not None
                    and listed_from <= roster_day
                    and ((listed_to := as_date(fact.get("listed_to_provider_reported"))) is None or listed_to >= roster_day)}
        roster_validations.append({"effective_date": roster["effective_date"], "expected_type1_count": len(expected),
                                   "observed_type1_count": len(actual), "missing_count": len(expected - actual),
                                   "unexpected_count": len(actual - expected), "status": "PASS" if actual == expected else "BLOCKED"})

    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=output_path.name + ".", suffix=".tmp", dir=output_path.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    writer = gzip.open(temp_path, "wt", encoding="utf-8", newline="\n", compresslevel=6)
    days = []
    error = None
    total_rows = 0
    total_evaluable = 0
    rows_digest = hashlib.sha256()
    try:
        for index, session in enumerate(selected_sessions, start=1):
            day = session.isoformat()
            active = {
                code for code, fact in facts.items()
                if (listed_from := as_date(fact.get("listed_from"))) is not None
                and listed_from <= session
                and ((listed_to := as_date(fact.get("listed_to_provider_reported"))) is None or listed_to >= session)
            }
            boundary_codes = boundary_unknown_by_day.get(session, set())
            candidate_codes = active | boundary_codes
            bar_codes = bar_dates.get(int(session.strftime("%Y%m%d")), set())
            membership_rows = []
            digest_items = []
            day_evaluable = 0
            day_boundary_unknown = 0
            for code in sorted(candidate_codes):
                source_match = code in source_keys
                has_bar = code in bar_codes and source_match
                boundary_unknown = code in boundary_codes
                eligibility = ("LIFECYCLE_BOUNDARY_UNKNOWN" if boundary_unknown else
                               "EVALUABLE_BAR_AVAILABLE" if has_bar else "LISTED_BAR_MISSING_UNKNOWN")
                day_boundary_unknown += int(boundary_unknown)
                day_evaluable += int(has_bar and not boundary_unknown)
                identity = bao_source_entity(code.split(".", 1)[0], code, facts.get(code, {}).get("listed_from"))
                canonical_id = identity["security_id"] if source_match else None
                quality = "DATED_LISTING_FACT_AND_VALID_TDX_BAR" if has_bar else (
                    "DIRECT_CODE_MATCH_BAR_COVERAGE_UNKNOWN" if source_match else "SOURCE_IDENTITY_OR_HISTORY_UNRESOLVED")
                membership_rows.append({
                    "trade_date": day,
                    "canonical_security_id": canonical_id,
                    "source_security_key": code.upper(),
                    "universe_contract_id": UNIVERSE_CONTRACT,
                    "lifecycle_revision_id": lifecycle_revision,
                    "eligibility_status": eligibility,
                    "eligibility_reason": ("IPO_OUTDATE_BOUNDARY_NOT_UNIFORMLY_VALIDATED" if boundary_unknown else
                                           "BAOSTOCK_TYPE1_LISTING_INTERVAL_AND_VALID_SELECTED_SOURCE_BAR"),
                    "provider_trade_status": None,
                    "membership_basis": "RECONSTRUCTED_CORRECTED",
                    "quality": quality,
                    "identity_quality": identity["identity_quality"] if source_match else "UNMAPPED_LISTING_KEY_ONLY",
                })
                digest_items.append(f"{code}\0{eligibility}\n")
            day_digest = hashlib.sha256("".join(digest_items).encode("ascii")).hexdigest()
            rows_digest.update(f"{day}\0{day_digest}\0{len(candidate_codes)}\n".encode("ascii"))
            for membership_row in membership_rows:
                writer.write(json.dumps(membership_row, ensure_ascii=False, sort_keys=True,
                                        separators=(",", ":")) + "\n")
            total_rows += len(membership_rows)
            total_evaluable += day_evaluable
            days.append({"trade_date": day, "lifecycle_interval_candidate_count": len(active),
                         "membership_row_count": len(candidate_codes),
                         "source_bar_evaluable_count": day_evaluable,
                         "listed_bar_missing_unknown_count": len(candidate_codes) - day_evaluable - day_boundary_unknown,
                         "lifecycle_boundary_unknown_count": day_boundary_unknown,
                         "universe_digest": day_digest})
            if index % 100 == 0:
                print(json.dumps({"progress_sessions": index, "total_sessions": len(selected_sessions),
                                  "membership_rows": total_rows}, ensure_ascii=False), flush=True)
    except Exception as exc:
        error = type(exc).__name__ + ":" + str(exc)[:200]
    finally:
        writer.close()

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
        "status": "RECONSTRUCTED_UNIVERSE_BUILT_ACCEPTANCE_PENDING" if output_published and not bj_source_keys and all(x["status"] == "PASS" for x in roster_validations) else "BLOCKED",
        "stage_completion_authorized": False,
        "lineage": "RECONSTRUCTED_CORRECTED from BaoStock listing intervals and verified TDX bar presence; not AS_RECORDED",
        "outDate_boundary_policy": "Because stratified BaoStock roster checks disagree on whether the reported outDate itself is the last roster date, exact boundary sessions are retained as LIFECYCLE_BOUNDARY_UNKNOWN and excluded from evaluable_count. Non-session outDate values mark adjacent source sessions unknown.",
        "formal_window": {"requested_start": formal_start.isoformat(), "actual_first_session": session_dates[formal_index].isoformat(),
                          "last_session": selected_sessions[-1].isoformat(), "warmup_sessions": args.warmup_sessions,
                          "warmup_first_session": selected_sessions[0].isoformat(), "session_basis": "FROZEN_TDX_INDEX_BAR_DATE_PROXY"},
        "lifecycle_source": {"path": FACTS_PATH.relative_to(ROOT).as_posix(), "sha256": sha256_file(FACTS_PATH),
                             "revision_id": lifecycle_revision, "a_stock_type": "BaoStock provider type=1",
                             "roster_crosschecks": roster_validations,
                             "boundary_validation_sessions": len(roster_validations),
                             "boundary_mismatch_count": sum(x["missing_count"] + x["unexpected_count"] for x in roster_validations),
                             "ipo_outdate_boundary_probe_path": BOUNDARY_PROBE_PATH.relative_to(ROOT).as_posix(),
                             "ipo_outdate_boundary_probe_sha256": sha256_file(BOUNDARY_PROBE_PATH),
                             "ipo_outdate_boundary_mismatch_count": sum(x.get("status") != "PASS" for x in boundary_probe.get("cases", []))},
        "source_selection": {"path": SELECTION_PATH.relative_to(ROOT).as_posix(), "sha256": sha256_file(SELECTION_PATH),
                              "selection_digest": selection_doc["selection_digest"],
                              "mapped_source_key_count": len(source_keys), "unresolved_bj_source_key_count": len(bj_source_keys),
                              "retained_source_exception_count": len(selection_doc.get("source_exceptions", []))},
        "daily_reconstructed_universe": {"session_count": len(days), "membership_row_count": total_rows,
                                          "source_bar_evaluable_rows": total_evaluable,
                                          "lifecycle_boundary_unknown_rows": sum(x["lifecycle_boundary_unknown_count"] for x in days),
                                          "daily_digest_root": rows_digest.hexdigest(), "days": days,
                                          "daily_trade_status": "UNKNOWN_NOT_INFERRED",
                                          "bar_source_validation_errors": bar_source_errors[:100]},
        "output": {"path": args.output.replace("\\", "/") if output_published else None,
                   "format": "GZIP_JSONL; one reconstructed membership fact per line",
                   "sha256": sha256_file(output_path) if output_published else None,
                   "byte_count": output_path.stat().st_size if output_published else 0},
        "request_budget": {"additional_api_calls_for_full_daily_expansion": 0,
                           "daily_soft_cap": 40_000, "daily_hard_cap": 45_000, "provider_limit": 50_000},
        "execution_identity": {"input_commit": commit, "script_sha256": sha256_file(Path(__file__))},
        "failures": {"source_scan_or_write": error} if error else {},
        "blockers": (["NO_BSE_LIFECYCLE_CATALOG_OR_DATED_ROSTER"] if bj_source_keys else [])
                    + (["SOURCE_FILE_VALIDATION_ERRORS"] if bar_source_errors else [])
                    + (["THREE_DATED_ROSTER_CROSSCHECKS_FAILED"] if any(x["status"] != "PASS" for x in roster_validations) else [])
                    + (["OUTDATE_BOUNDARY_SEMANTICS_NOT_UNIFORM"] if any(x.get("status") != "PASS" for x in boundary_probe.get("cases", [])) else [])
                    + ["STABLE_SECURITY_ENTITY_MAP_NOT_ACCEPTED", "EXACT_DATED_HISTORICAL_ROSTERS_NOT_ACCEPTED",
                       "BSE_LIFECYCLE_AND_ALIAS_CLOSURE_PENDING", "SOURCE_EXCEPTION_CLASSIFICATION_OPEN"],
        "next_stage": "V4_01_R5_EXACT_DATED_ROSTERS_AND_BSE_IDENTITY_CLOSURE",
    }
    receipt_path = ROOT / args.receipt
    _atomic_json(receipt_path, receipt)
    print(json.dumps({"status": receipt["status"], "sessions": len(days), "expected_sessions": len(selected_sessions),
                      "membership_rows": total_rows, "evaluable_rows": total_evaluable, "bar_source_errors": len(bar_source_errors), "bse_source_keys": len(bj_source_keys),
                      "output_published": output_published,
                      "failure": error, "receipt": args.receipt}, ensure_ascii=False))
    return 0 if output_published and not bar_source_errors and not bj_source_keys and all(x["status"] == "PASS" for x in roster_validations) else 2


if __name__ == "__main__":
    raise SystemExit(main())
