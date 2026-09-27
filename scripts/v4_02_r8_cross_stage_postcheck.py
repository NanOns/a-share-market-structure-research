from __future__ import annotations

"""Verify accepted V4-02 row keys against the R8 canonical identity/universe."""

import gzip
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from itertools import zip_longest
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402
from workbench_analysis.v4_joint_receipt import identity_set_is_compatible, key_set_diagnostics  # noqa: E402

R8_UNIVERSE = Path("data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz")
R8_IDENTITY = Path("data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json")
R8_ALIAS_FACTS = Path("data/v4/bootstrap/dated_security_alias_r7.jsonl")
R8_FINAL_RECEIPT = Path("reports/v4_01/v4_01_final_stage_receipt_R8_20260928.json")
R8_POSTCHECK = Path("reports/v4_01/V4_01_R8_IDENTITY_UNIVERSE_POSTCHECK_20260928.json")
ALIAS_COMPLETENESS = Path("reports/v4_01/V4_01_HISTORICAL_CODE_CHANGE_ALIAS_COMPLETENESS_R8.json")
V402_FINAL_RECEIPT = Path("reports/v4_02/V4_02_FINAL_RECEIPT_R6.json")
V402_ACCEPTED_HEAD = Path("data/v4/V4_02_ACCEPTED_HEAD.json")
V402_EXTERNAL_ACCEPTANCE = Path("reports/v4_02/V4_02_FINAL_EXTERNAL_ACCEPTANCE_R6.json")
V402_MANIFEST = Path("reports/v4_02/V4_02_FINAL_STAGING_MANIFEST_R6.json")
V402_TRADING_STATUS = Path("data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R7_20260927.jsonl.gz")
V402_ISST = Path("data/v4/artifact_store/v4_02/V4_02_DATED_ST_STATUS_R7_20260927.jsonl.gz")
V402_ADJUSTED = Path("data/v4/artifact_store/v4_02/V4_02_ADJUSTED_CANONICAL_DAILY_R7_20260927.parquet")
V402_WEEKLY = Path("data/v4/artifact_store/v4_02/V4_02_FORMAL_WEEKLY_RAW_QFQ_R7_20260927.parquet")
V402_MONTHLY = Path("data/v4/artifact_store/v4_02/V4_02_FORMAL_MONTHLY_RAW_QFQ_R7_20260927.parquet")
OUTPUT = Path("reports/v4_02/V4_02_R8_CROSS_STAGE_POSTCHECK_20260928.json")
CONTRACT = Path("config/v4_02_r8_cross_stage_postcheck_v1.json")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_day(value: object) -> str:
    return str(value).replace("-", "")


def jsonl_groups(path: Path) -> Iterator[tuple[str, list[dict]]]:
    current: str | None = None
    group: list[dict] = []
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            day = normalize_day(row.get("trade_date") or "")
            if not day:
                raise ValueError(f"V4_02_CROSS_STAGE_ROW_WITHOUT_DATE:{path}")
            if current is not None and day < current:
                raise ValueError(f"V4_02_CROSS_STAGE_ROWS_NOT_SORTED:{path}")
            if current is not None and day != current:
                yield current, group
                group = []
            current = day
            group.append(row)
    if current is not None:
        yield current, group


def parquet_groups(con, path: Path) -> Iterator[tuple[str, list[dict]]]:
    cursor = con.execute(
        "SELECT canonical_security_id AS security_id, source_security_key, board_scope, trade_date "
        "FROM read_parquet(?) ORDER BY trade_date, canonical_security_id",
        [str(path)],
    )
    current: str | None = None
    group: list[dict] = []
    while batch := cursor.fetchmany(100_000):
        for row in batch:
            day = normalize_day(row["trade_date"])
            if current is not None and day != current:
                yield current, group
                group = []
            current = day
            group.append(row)
    if current is not None:
        yield current, group


def main() -> int:
    import duckdb
    import pyarrow.parquet as pq

    final_receipt = json.loads((ROOT / V402_FINAL_RECEIPT).read_text(encoding="utf-8"))
    accepted_head = json.loads((ROOT / V402_ACCEPTED_HEAD).read_text(encoding="utf-8"))
    external = json.loads((ROOT / V402_EXTERNAL_ACCEPTANCE).read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / V402_MANIFEST).read_text(encoding="utf-8"))
    r8_final = json.loads((ROOT / R8_FINAL_RECEIPT).read_text(encoding="utf-8"))
    r8_postcheck = json.loads((ROOT / R8_POSTCHECK).read_text(encoding="utf-8"))
    alias_gate = json.loads((ROOT / ALIAS_COMPLETENESS).read_text(encoding="utf-8"))
    contract = json.loads((ROOT / CONTRACT).read_text(encoding="utf-8"))
    alias_hash = sha256(ROOT / R8_ALIAS_FACTS)
    universe_hash = sha256(ROOT / R8_UNIVERSE)
    identity_hash = sha256(ROOT / R8_IDENTITY)
    r8_artifacts_match_receipt = (
        r8_final.get("canonical_identity_artifact", {}).get("sha256") == identity_hash
        and r8_final.get("canonical_alias_fact_artifact", {}).get("sha256") == alias_hash
        and r8_final.get("canonical_historical_universe_artifact", {}).get("sha256") == universe_hash
    )

    accepted_price_path = ROOT / final_receipt["evidence"]["production_build"]["path"]
    expected_components = manifest.get("components", {})
    manifest_alias_matches = expected_components.get("R6_ALIAS_FACTS", {}).get("sha256") == alias_hash
    manifest_daily_matches = expected_components.get("DAILY_R7", {}).get("sha256") == sha256(ROOT / V402_ADJUSTED)
    manifest_price_matches = expected_components.get("R6_PRICE", {}).get("sha256") == sha256(accepted_price_path)
    head_matches = (
        accepted_head.get("final_receipt_sha256") == sha256(ROOT / V402_FINAL_RECEIPT)
        and accepted_head.get("external_acceptance") == "EXTERNALLY_ACCEPTED"
        and accepted_head.get("status") == "PASS_WITH_BSE_SCOPE_DEGRADED"
        and accepted_head.get("external_acceptance_receipt_sha256") == sha256(ROOT / V402_EXTERNAL_ACCEPTANCE)
    )
    external_matches = (
        external.get("acceptance_result", {}).get("external_acceptance") == "EXTERNALLY_ACCEPTED"
        and external.get("acceptance_result", {}).get("stage_closed") is True
    )

    con = duckdb.connect(database=":memory:")
    baseline_key_mismatches: dict[str, int] = {}
    identity_ids: set[str] = set()
    required_universe_rows = 0
    session_count = 0
    sentinel = object()
    groups = [
        jsonl_groups(ROOT / R8_UNIVERSE),
        jsonl_groups(ROOT / V402_TRADING_STATUS),
        jsonl_groups(ROOT / V402_ISST),
        jsonl_groups(accepted_price_path),
    ]
    comparisons = {
        "trading_status": {"iterator": groups[1], "dupes": 0, "date_mismatch": 0, "key_mismatch": 0},
        "dated_isst": {"iterator": groups[2], "dupes": 0, "date_mismatch": 0, "key_mismatch": 0},
        "price_limit": {"iterator": groups[3], "dupes": 0, "date_mismatch": 0, "key_mismatch": 0},
    }
    expected_iter = groups[0]
    for expected_item in expected_iter:
        session_count += 1
        day, expected_rows = expected_item
        required_universe_rows += len(expected_rows)
        expected_keys: set[str] = set()
        for row in expected_rows:
            sid = str(row.get("security_id") or "")
            identity_ids.add(sid)
            expected_keys.add(sid)
        for name, info in comparisons.items():
            try:
                item = next(info["iterator"])
            except StopIteration:
                info["date_mismatch"] += 1
                continue
            artifact_day, rows = item
            if artifact_day != day:
                info["date_mismatch"] += 1
            keys: set[str] = set()
            seen: set[str] = set()
            for row in rows:
                sid = str(row.get("security_id") or row.get("canonical_security_id") or "")
                if sid in seen:
                    info["dupes"] += 1
                seen.add(sid)
                keys.add(sid)
            diagnostics = key_set_diagnostics(expected_keys, keys, int(info["dupes"]))
            info["key_mismatch"] += diagnostics["missing_key_count"] + diagnostics["extra_key_count"]
    for name, info in comparisons.items():
        if next(info["iterator"], sentinel) is not sentinel:
            info["date_mismatch"] += 1

    adjusted_mismatch = 0
    adjusted_duplicate = 0
    adjusted_rows = 0
    adjusted_identity_ids: set[str] = set()
    expected_groups = jsonl_groups(ROOT / R8_UNIVERSE)
    adjusted_groups = parquet_groups(con, ROOT / V402_ADJUSTED)
    for expected_item, adjusted_item in zip_longest(expected_groups, adjusted_groups, fillvalue=sentinel):
        if expected_item is sentinel or adjusted_item is sentinel:
            adjusted_mismatch += 1
            continue
        expected_day, expected_rows = expected_item
        adjusted_day, adjusted_rows_for_day = adjusted_item
        if expected_day != adjusted_day:
            adjusted_mismatch += 1
        expected_board = {str(row.get("security_id")): str(row.get("board_scope")) for row in expected_rows}
        seen_adjusted: set[str] = set()
        for row in adjusted_rows_for_day:
            adjusted_rows += 1
            sid = str(row.get("security_id") or "")
            adjusted_identity_ids.add(sid)
            if sid in seen_adjusted:
                adjusted_duplicate += 1
            seen_adjusted.add(sid)
            if sid not in expected_board or expected_board.get(sid) != str(row.get("board_scope") or ""):
                adjusted_mismatch += 1

    weekly_ids = {str(row[0]) for row in con.execute("SELECT DISTINCT canonical_security_id FROM read_parquet(?)", [str(ROOT / V402_WEEKLY)]).fetchall()}
    monthly_ids = {str(row[0]) for row in con.execute("SELECT DISTINCT canonical_security_id FROM read_parquet(?)", [str(ROOT / V402_MONTHLY)]).fetchall()}
    weekly_duplicate_keys = int(con.execute(
        "SELECT count(*) - count(DISTINCT (canonical_security_id, period_end_date)) FROM read_parquet(?)",
        [str(ROOT / V402_WEEKLY)],
    ).fetchone()[0])
    monthly_duplicate_keys = int(con.execute(
        "SELECT count(*) - count(DISTINCT (canonical_security_id, period_end_date)) FROM read_parquet(?)",
        [str(ROOT / V402_MONTHLY)],
    ).fetchone()[0])
    weekly_rows = pq.ParquetFile(ROOT / V402_WEEKLY).metadata.num_rows
    monthly_rows = pq.ParquetFile(ROOT / V402_MONTHLY).metadata.num_rows
    adjusted_parquet_rows = pq.ParquetFile(ROOT / V402_ADJUSTED).metadata.num_rows
    con.close()

    universe_identity_set = identity_ids
    weekly_extra_ids = 0 if identity_set_is_compatible(universe_identity_set, weekly_ids) else len(weekly_ids - universe_identity_set)
    monthly_extra_ids = 0 if identity_set_is_compatible(universe_identity_set, monthly_ids) else len(monthly_ids - universe_identity_set)
    adjusted_extra_ids = 0 if identity_set_is_compatible(universe_identity_set, adjusted_identity_ids) else len(adjusted_identity_ids - universe_identity_set)
    comparisons_summary = {
        name: {
            "duplicate_key_rows": info["dupes"],
            "date_group_mismatches": info["date_mismatch"],
            "key_set_mismatch_rows": info["key_mismatch"],
        }
        for name, info in comparisons.items()
    }
    criteria = {
        "cross_stage_contract_versioned": "PASS" if contract.get("contract_id") == "V4_02_R8_CROSS_STAGE_POSTCHECK_V1" else "BLOCKED",
        "accepted_v4_02_status_and_external_head_current": "PASS" if head_matches and external_matches else "BLOCKED",
        "accepted_manifest_binds_r8_alias_and_r7_daily": "PASS" if manifest_alias_matches and manifest_daily_matches else "BLOCKED",
        "accepted_manifest_binds_final_price_limit": "PASS" if manifest_price_matches else "BLOCKED",
        "r8_final_receipt_and_postcheck_pass": "PASS" if r8_final.get("status") == "PASS_WITH_BSE_SCOPE_DEGRADED" and r8_postcheck.get("status") == "PASS" else "BLOCKED",
        "r8_artifact_hashes_match_canonical_receipt": "PASS" if r8_artifacts_match_receipt else "BLOCKED",
        "generic_alias_completeness_pass": "PASS" if alias_gate.get("status") == "PASS" and alias_gate.get("unresolved_required_scope_candidate_count") == 0 else "BLOCKED",
        "trading_status_key_set_matches_r8_universe": "PASS" if comparisons_summary["trading_status"] == {"duplicate_key_rows": 0, "date_group_mismatches": 0, "key_set_mismatch_rows": 0} else "BLOCKED",
        "dated_isst_key_set_matches_r8_universe": "PASS" if comparisons_summary["dated_isst"] == {"duplicate_key_rows": 0, "date_group_mismatches": 0, "key_set_mismatch_rows": 0} else "BLOCKED",
        "price_limit_key_set_matches_r8_universe": "PASS" if comparisons_summary["price_limit"] == {"duplicate_key_rows": 0, "date_group_mismatches": 0, "key_set_mismatch_rows": 0} else "BLOCKED",
        "adjusted_daily_keys_and_board_match_r8_universe": "PASS" if adjusted_mismatch == 0 and adjusted_duplicate == 0 and adjusted_extra_ids == 0 else "BLOCKED",
        "weekly_identity_set_compatible": "PASS" if weekly_extra_ids == 0 and weekly_duplicate_keys == 0 else "BLOCKED",
        "monthly_identity_set_compatible": "PASS" if monthly_extra_ids == 0 and monthly_duplicate_keys == 0 else "BLOCKED",
    }
    blockers = [name for name, value in criteria.items() if value != "PASS"]
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    status = "PASS" if not blockers else "BLOCKED"
    receipt = {
        "contract_id": "V4_02_R8_CROSS_STAGE_POSTCHECK_V1",
        "version": "1.0.0",
        "stage": "V4-02-R8-CROSS-STAGE-IDENTITY-UNIVERSE-POSTCHECK",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "criteria": criteria,
        "blockers": blockers,
        "decision": "No V4-02 rebuild; this receipt compares existing accepted production artifacts with canonical V4-01 R8 keys.",
        "v4_02_accepted_state": {
            "status": accepted_head.get("status"),
            "external_acceptance": accepted_head.get("external_acceptance"),
            "external_receipt_sha256": sha256(ROOT / V402_EXTERNAL_ACCEPTANCE),
            "final_receipt_sha256": sha256(ROOT / V402_FINAL_RECEIPT),
            "accepted_head_sha256": sha256(ROOT / V402_ACCEPTED_HEAD),
            "manifest_sha256": sha256(ROOT / V402_MANIFEST),
        },
        "r8_binding": {
            "canonical_identity_sha256": identity_hash,
            "canonical_alias_fact_sha256": alias_hash,
            "canonical_historical_universe_sha256": universe_hash,
            "required_scope_membership_rows": required_universe_rows,
            "session_count": session_count,
        },
        "downstream_keys": {
            "trading_status": comparisons_summary["trading_status"],
            "dated_isst": comparisons_summary["dated_isst"],
            "price_limit": comparisons_summary["price_limit"],
            "adjusted_daily": {
                "rows": adjusted_parquet_rows,
                "identity_count": len(adjusted_identity_ids),
                "duplicate_identity_date_rows": adjusted_duplicate,
                "key_or_board_mismatch_rows": adjusted_mismatch,
                "extra_identity_count": adjusted_extra_ids,
            },
            "weekly": {"rows": weekly_rows, "identity_count": len(weekly_ids), "extra_identity_count": weekly_extra_ids,
                       "duplicate_identity_period_rows": weekly_duplicate_keys},
            "monthly": {"rows": monthly_rows, "identity_count": len(monthly_ids), "extra_identity_count": monthly_extra_ids,
                        "duplicate_identity_period_rows": monthly_duplicate_keys},
        },
        "manifest_binding": {
            "alias_fact_matches_r8": manifest_alias_matches,
            "adjusted_daily_r7_matches_manifest": manifest_daily_matches,
            "price_limit_matches_manifest": manifest_price_matches,
            "r8_universe_bound_by_cross_stage_full_key_comparison": True,
            "price_limit_artifact": final_receipt["evidence"]["production_build"]["path"],
        },
        "stage_contract": "DA-MSR-V4.2.2-CODEX-REV2; V4_02_R8_CROSS_STAGE_POSTCHECK_V1",
        "contract_evidence": {"path": CONTRACT.as_posix(), "sha256": sha256(ROOT / CONTRACT)},
        "execution_identity": {
            "input_commit": "1a70c8c733096936da4fa250a3f4def501ccfd1d",
            "execution_head": current_head,
        },
        "next_stage": "00_01_02_JOINT_FINAL_RECEIPT" if status == "PASS" else "BLOCKED_REVIEW_CROSS_STAGE_COUNTEREXAMPLE",
    }
    _atomic_json(ROOT / OUTPUT, receipt)
    print(json.dumps({"status": status, "criteria": criteria,
                      "downstream_keys": receipt["downstream_keys"], "receipt": OUTPUT.as_posix()}, ensure_ascii=False))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
