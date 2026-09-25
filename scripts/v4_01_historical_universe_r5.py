from __future__ import annotations

"""Rebuild V4-01 daily membership from exact dated rosters and stable IDs."""

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from v4_01_historical_evaluable_universe_r4 import (  # noqa: E402
    EXTRACTED_ROOT,
    PACKAGE_SHA,
    UNIVERSE_CONTRACT,
    LOCAL_ROOT,
    sha256_file,
    source_bar_dates,
)
from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rosters", default="data/v4/artifact_store/v4_01/baostock_dated_rosters_R5_20260925.jsonl.gz")
    parser.add_argument("--roster-receipt", default="reports/v4_01/baostock_dated_roster_receipt_R5_20260925.json")
    parser.add_argument("--identity-map", default="data/v4/artifact_store/v4_01/security_entity_map_R5_20260925.json")
    parser.add_argument("--identity-receipt", default="reports/v4_01/security_entity_map_receipt_R5_20260925.json")
    parser.add_argument("--output", default="data/v4/artifact_store/v4_01/v4_01_historical_universe_R5_20260925.jsonl.gz")
    parser.add_argument("--receipt", default="reports/v4_01/historical_evaluable_universe_receipt_R5_20260925.json")
    args = parser.parse_args()

    roster_path, roster_receipt_path = ROOT / args.rosters, ROOT / args.roster_receipt
    map_path, map_receipt_path = ROOT / args.identity_map, ROOT / args.identity_receipt
    roster_receipt = json.loads(roster_receipt_path.read_text("utf-8"))
    map_receipt = json.loads(map_receipt_path.read_text("utf-8"))
    candidate = json.loads((ROOT / "reports/v4_01/historical_evaluable_universe_receipt_R4_20260925.json").read_text("utf-8"))
    sessions = [item["trade_date"] for item in candidate["daily_reconstructed_universe"]["days"]]
    if roster_receipt.get("status") != "BUILT" or len(sessions) != 786:
        raise SystemExit("R5_DATED_ROSTER_NOT_COMPLETE")
    if roster_receipt.get("output", {}).get("sha256") != sha256_file(roster_path):
        raise SystemExit("R5_DATED_ROSTER_DIGEST_MISMATCH")

    rosters: dict[str, set[str]] = {}
    with gzip.open(roster_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            day, codes = item["trade_date"], item["source_codes"]
            if day in rosters or day not in sessions or codes != sorted(set(codes)):
                raise SystemExit("R5_DATED_ROSTER_ORDER_OR_UNIQUENESS_INVALID")
            if item["row_count"] != len(codes) or hashlib.sha256("\n".join(codes).encode("ascii")).hexdigest() != item["codes_sha256"]:
                raise SystemExit("R5_DATED_ROSTER_DAILY_DIGEST_INVALID")
            rosters[day] = set(codes)
    if list(rosters) != sessions:
        raise SystemExit("R5_DATED_ROSTER_SESSION_COVERAGE_INVALID")

    map_doc = json.loads(map_path.read_text("utf-8"))
    if map_receipt.get("output", {}).get("sha256") != sha256_file(map_path):
        raise SystemExit("R5_IDENTITY_MAP_DIGEST_MISMATCH")
    source_keys = {str(row["source_security_key"]).lower() for row in map_doc["records"]}
    source_keys |= {str(row.get("source_security_key", "")).lower() for row in map_doc.get("unresolved", []) if row.get("source_security_key")}
    session_ints = {int(date.fromisoformat(day).strftime("%Y%m%d")) for day in sessions}
    bar_dates, bar_errors = source_bar_dates(session_ints, source_keys)
    identity_by_key: dict[str, dict] = {}
    for row in map_doc["records"]:
        key = str(row["source_security_key"]).lower()
        if key in identity_by_key and identity_by_key[key] != row:
            raise SystemExit(f"R5_IDENTITY_MAP_DUPLICATE_ALIAS:{key}")
        identity_by_key[key] = row
    noncore_by_key = {str(row["source_security_key"]).lower(): row for row in map_doc.get("non_core_candidates", [])}
    unresolved_keys = {str(row["source_security_key"]).lower() for row in map_doc.get("unresolved", []) if row.get("source_security_key")}
    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_name(output_path.name + ".partial")
    daily = []
    totals = {"membership_rows": 0, "identity_resolved_rows": 0, "identity_unresolved_rows": 0,
              "source_bar_present_rows": 0, "source_bar_missing_rows": 0, "bse_candidate_rows": 0}
    root_digest = hashlib.sha256()
    with gzip.open(temp_path, "wt", encoding="utf-8", newline="\n", compresslevel=6) as stream:
        for index, day in enumerate(sessions, 1):
            trade_day = date.fromisoformat(day)
            day_int = int(trade_day.strftime("%Y%m%d"))
            active = []
            for code in sorted(rosters[day]):
                identity = identity_by_key.get(code)
                if identity and identity.get("security_type") == "A_STOCK":
                    active.append((code, identity, "BAOSTOCK_EXACT_DATED_ROSTER"))
                elif identity is None:
                    noncore = noncore_by_key.get(code, {})
                    if noncore.get("classification") != "BAOSTOCK_NON_A_STOCK_TYPE":
                        active.append((code, None, "ROSTER_MEMBER_IDENTITY_UNRESOLVED"))
            for row in map_doc["records"]:
                if row.get("exchange") != "BJ" or row.get("security_type") != "A_STOCK":
                    continue
                start = date.fromisoformat(row["symbol_effective_from"])
                end = date.fromisoformat(row["symbol_effective_to"]) if row.get("symbol_effective_to") else None
                code = str(row["source_security_key"]).lower()
                if start <= trade_day and (end is None or trade_day <= end) and code not in rosters[day]:
                    active.append((code, row, "BSE_OFFICIAL_INDEX_CAPTURE_CANDIDATE"))
            rows = []
            seen_ids: set[str] = set()
            for code, identity, basis in active:
                security_id = identity.get("security_id") if identity else None
                if security_id and security_id in seen_ids:
                    continue
                if security_id:
                    seen_ids.add(security_id)
                bar_present = code in bar_dates.get(day_int, set())
                if identity is None:
                    totals["identity_unresolved_rows"] += 1
                    row_quality = "UNRESOLVED_ROSTER_IDENTITY"
                    source_revision = None
                    security_type = "A_STOCK_CANDIDATE"
                else:
                    totals["identity_resolved_rows"] += 1
                    row_quality = identity.get("identity_quality", "IDENTITY_CANDIDATE")
                    source_revision = identity.get("source_revision_id")
                    security_type = identity.get("security_type")
                    if basis == "BSE_OFFICIAL_INDEX_CAPTURE_CANDIDATE":
                        totals["bse_candidate_rows"] += 1
                totals["source_bar_present_rows" if bar_present else "source_bar_missing_rows"] += 1
                row = {"trade_date": day, "security_id": security_id,
                       "source_security_key": code.upper(), "security_type": security_type,
                       "universe_contract_id": UNIVERSE_CONTRACT,
                       "membership_basis": basis, "lineage": "RECONSTRUCTED_CORRECTED",
                       "source_revision_id": source_revision,
                       "source_bar_present": bar_present,
                       "eligibility_status": "EVALUABLE_BAR_AVAILABLE" if bar_present and security_id else "MEMBER_BAR_OR_IDENTITY_UNRESOLVED",
                       "identity_quality": row_quality}
                rows.append(row)
                stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
            day_digest = hashlib.sha256("\n".join(f"{r['source_security_key']}\0{r['security_id'] or ''}\0{r['eligibility_status']}" for r in rows).encode("utf-8")).hexdigest()
            daily.append({"trade_date": day, "membership_row_count": len(rows),
                          "identity_unresolved_count": sum(r["security_id"] is None for r in rows),
                          "source_bar_present_count": sum(r["source_bar_present"] for r in rows),
                          "daily_digest": day_digest})
            totals["membership_rows"] += len(rows)
            root_digest.update(f"{day}\0{day_digest}\0{len(rows)}\n".encode("ascii"))
            if index % 100 == 0:
                print(json.dumps({"sessions": index, "total_sessions": len(sessions), "membership_rows": totals["membership_rows"]}), flush=True)
    with temp_path.open("rb+") as handle:
        import os
        os.fsync(handle.fileno())
    temp_path.replace(output_path)
    unresolved_members = totals["identity_unresolved_rows"]
    blockers = []
    if unresolved_members:
        blockers.append("EXACT_ROSTER_MEMBERS_WITHOUT_ACCEPTED_STABLE_IDENTITY")
    if map_receipt.get("status") != "PASS":
        blockers.append("IDENTITY_MAP_OR_BSE_LIFECYCLE_ACCEPTANCE_PENDING")
    if bar_errors:
        blockers.append("SOURCE_BAR_VALIDATION_ERRORS")
    doc = {"stage": "V4-01-HISTORICAL-UNIVERSE-R5", "contract_id": "V4_HISTORICAL_EVALUABLE_UNIVERSE_R5_V1",
           "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
           "status": "PASS" if not blockers else "BLOCKED", "stage_completion_authorized": False,
           "lineage": "RECONSTRUCTED_CORRECTED; exact dated BaoStock membership plus candidate BSE official lifecycle; never labeled AS_RECORDED",
           "inputs": {"roster_path": args.rosters, "roster_sha256": sha256_file(roster_path),
                      "identity_map_path": args.identity_map, "identity_map_sha256": sha256_file(map_path),
                      "source_selection_path": "reports/v4_01/canonical_source_selection_R4_20260925.json"},
           "summary": {"session_count": len(daily), **totals, "unresolved_core_membership_count": unresolved_members,
                       "unique_mapped_security_ids": len({r["security_id"] for r in identity_by_key.values()}),
                       "source_bar_validation_error_count": len(bar_errors), "daily_digest_root": root_digest.hexdigest()},
           "daily": daily, "source_bar_validation_errors": bar_errors[:100],
           "output": {"path": args.output, "sha256": sha256_file(output_path), "byte_count": output_path.stat().st_size,
                      "format": "GZIP_JSONL"},
           "blockers": blockers, "execution_identity": {"input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                                                             "script_sha256": sha256_file(Path(__file__))},
           "next_stage": "V4_01_FINAL_RECEIPT_R5"}
    _atomic_json(ROOT / args.receipt, doc)
    print(json.dumps({"status": doc["status"], "summary": doc["summary"], "receipt": args.receipt}, ensure_ascii=False))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
