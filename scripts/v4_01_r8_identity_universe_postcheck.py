from __future__ import annotations

"""Independent R8 postcheck of canonical identity and all-day universe rows."""

import gzip
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import zip_longest
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402
from workbench_analysis.v4_01_alias_completeness import (  # noqa: E402
    REQUIRED_BOARDS,
    required_scope_alias_gate_passes,
    validate_alias_interval_integrity,
    validate_confirmed_alias_coverage,
)
from workbench_analysis.dated_security_alias import DatedSecurityAliasResolver  # noqa: E402

BASELINE_UNIVERSE = Path("data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R6_2_20260926.jsonl.gz")
FINAL_UNIVERSE = Path("data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz")
FINAL_IDENTITY = Path("data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json")
ALIAS_FACTS = Path("data/v4/bootstrap/dated_security_alias_r7.jsonl")
ALIAS_RECEIPT = Path("reports/v4_01/V4_01_HISTORICAL_CODE_CHANGE_ALIAS_COMPLETENESS_R8.json")
BASELINE_UNIVERSE_RECEIPT = Path("reports/v4_01/historical_evaluable_universe_receipt_R6_2_20260926.json")
BASELINE_GATES = Path("reports/v4_01/required_scope_gates_receipt_R6_20260926.json")
REPAIR_RECEIPT = Path("reports/v4_02/V4_01_CODE_CHANGE_ALIAS_AUDIT_R7.json")
ADJUSTED_DAILY = Path("data/v4/artifact_store/v4_02/V4_02_ADJUSTED_CANONICAL_DAILY_R6_2_20260926.parquet")
OUTPUT = Path("reports/v4_01/V4_01_R8_IDENTITY_UNIVERSE_POSTCHECK_20260928.json")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_jsonl_gz(path: Path) -> Iterator[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def group_by_trade_date(rows: Iterator[dict]) -> Iterator[tuple[str, list[dict]]]:
    current_date: str | None = None
    group: list[dict] = []
    for row in rows:
        trade_date = str(row.get("trade_date") or "")
        if not trade_date:
            raise ValueError("R8_UNIVERSE_ROW_WITHOUT_TRADE_DATE")
        if current_date is not None and trade_date < current_date:
            raise ValueError("R8_UNIVERSE_ROWS_NOT_SORTED_BY_TRADE_DATE")
        if current_date is not None and trade_date != current_date:
            yield current_date, group
            group = []
        current_date = trade_date
        group.append(row)
    if current_date is not None:
        yield current_date, group


def normalized_board(board: str, exchange: str) -> str:
    if board == "MAIN" and exchange == "SH":
        return "SH_MAIN"
    if board == "MAIN" and exchange == "SZ":
        return "SZ_MAIN"
    return board


def main() -> int:
    import duckdb

    baseline_map = json.loads((ROOT / "data/v4/artifact_store/v4_01/security_entity_map_R5_20260925.json").read_text(encoding="utf-8"))
    final_map = json.loads((ROOT / FINAL_IDENTITY).read_text(encoding="utf-8"))
    alias_facts = [json.loads(line) for line in (ROOT / ALIAS_FACTS).read_text(encoding="utf-8").splitlines() if line.strip()]
    alias_gate = json.loads((ROOT / ALIAS_RECEIPT).read_text(encoding="utf-8"))
    universe_receipt = json.loads((ROOT / BASELINE_UNIVERSE_RECEIPT).read_text(encoding="utf-8"))
    gates_receipt = json.loads((ROOT / BASELINE_GATES).read_text(encoding="utf-8"))
    repair_receipt = json.loads((ROOT / REPAIR_RECEIPT).read_text(encoding="utf-8"))
    resolver = DatedSecurityAliasResolver(alias_facts)
    alias_ids = {str(row.get("security_id") or "") for row in alias_facts}
    alias_key_to_id = {str(row.get("source_security_key") or "").upper(): str(row.get("security_id") or "") for row in alias_facts}
    baseline_by_key = {str(row.get("source_security_key") or "").upper(): row for row in baseline_map["records"]}
    final_by_key = {str(row.get("source_security_key") or "").upper(): row for row in final_map["records"]}
    alias_integrity = validate_alias_interval_integrity(alias_facts)

    days_with_missing = 0
    total_missing = 0
    missing_by_board = Counter({board: 0 for board in REQUIRED_BOARDS})
    membership_mismatch = 0
    missing_key_count = 0
    extra_key_count = 0
    duplicate_identity_date_rows = 0
    source_symbol_interval_errors = 0
    board_interval_errors = 0
    unresolved_identity_rows = 0
    final_rows = 0
    baseline_rows = 0
    expected_rows_after_alias_dedup = 0
    alias_rows_by_date: dict[str, set[str]] = defaultdict(set)
    board_rows = Counter()
    dates: list[str] = []

    baseline_groups = group_by_trade_date(load_jsonl_gz(ROOT / BASELINE_UNIVERSE))
    final_groups = group_by_trade_date(load_jsonl_gz(ROOT / FINAL_UNIVERSE))
    sentinel = object()
    for baseline_group, final_group in zip_longest(baseline_groups, final_groups, fillvalue=sentinel):
        if baseline_group is sentinel or final_group is sentinel:
            membership_mismatch += 1
            continue
        baseline_date, baseline_day_rows = baseline_group
        final_date, final_day_rows = final_group
        dates.append(final_date)
        if baseline_date != final_date:
            membership_mismatch += 1

        expected_day: set[tuple[str, str, str]] = set()
        for row in baseline_day_rows:
            baseline_rows += 1
            source_key = str(row.get("source_security_key") or "").upper()
            source_id = str(row.get("security_id") or "")
            alias_id = alias_key_to_id.get(source_key)
            if alias_id:
                expected_id = alias_id
                expected_alias = resolver.resolve_alias(alias_id, baseline_date)
                expected_board = resolver.resolve_board(alias_id, baseline_date)
                if expected_alias is None or expected_board is None:
                    source_symbol_interval_errors += 1
                    continue
                expected_day.add((expected_id, baseline_date, expected_board))
            else:
                expected_day.add((source_id, baseline_date, str(row.get("board_scope") or "")))
        expected_rows_after_alias_dedup += len(expected_day)

        actual_day: set[tuple[str, str, str]] = set()
        actual_seen: set[tuple[str, str]] = set()
        for row in final_day_rows:
            final_rows += 1
            sid = str(row.get("security_id") or "")
            source_key = str(row.get("source_security_key") or "").upper()
            board = str(row.get("board_scope") or "")
            key = (sid, final_date)
            if key in actual_seen:
                duplicate_identity_date_rows += 1
            actual_seen.add(key)
            if not sid or sid == "UNKNOWN" or str(row.get("identity_status") or "").upper() == "UNKNOWN":
                unresolved_identity_rows += 1
            actual_day.add((sid, final_date, board))
            board_rows[board] += 1

            if sid in alias_ids:
                resolved_alias = resolver.resolve_alias(sid, final_date)
                resolved_board = resolver.resolve_board(sid, final_date)
                alias_rows_by_date[final_date].add(source_key)
                if resolved_alias is None or resolved_alias.upper() != source_key:
                    source_symbol_interval_errors += 1
                if resolved_board is None or resolved_board != board:
                    board_interval_errors += 1
            else:
                record = final_by_key.get(source_key)
                if record is None or str(record.get("security_id") or "") != sid:
                    source_symbol_interval_errors += 1
                    continue
                expected_board = normalized_board(str(record.get("board") or ""), str(record.get("exchange") or ""))
                start = str(record.get("symbol_effective_from") or record.get("list_date") or "0001-01-01")
                end = record.get("symbol_effective_to")
                if final_date < start or (end is not None and final_date > str(end)):
                    source_symbol_interval_errors += 1
                if expected_board != board:
                    board_interval_errors += 1

        missing = expected_day - actual_day
        extra = actual_day - expected_day
        if missing or extra:
            membership_mismatch += len(missing) + len(extra)
        if missing:
            days_with_missing += 1
            total_missing += len(missing)
            for _, _, board in missing:
                if board in missing_by_board:
                    missing_by_board[board] += 1

    alias_gap_count = validate_confirmed_alias_coverage(alias_facts, dates)
    duplicate_alias_active_ids = alias_integrity["alias_interval_conflicts"]
    alias_interval_conflicts = alias_integrity["entity_alias_interval_conflicts"]
    unresolved_candidates = int(alias_gate.get("unresolved_required_scope_candidate_count", -1))

    con = duckdb.connect(database=":memory:")
    bar_path = ROOT / ADJUSTED_DAILY
    structural_invalid = int(
        con.execute(
            """
            SELECT count(*) FROM read_parquet(?)
            WHERE raw_open IS NULL OR raw_high IS NULL OR raw_low IS NULL OR raw_close IS NULL
               OR volume IS NULL OR amount IS NULL
               OR raw_high < greatest(raw_open, raw_close)
               OR raw_low > least(raw_open, raw_close)
               OR raw_high < raw_low OR volume < 0 OR amount < 0
            """,
            [str(bar_path)],
        ).fetchone()[0]
    )
    con.close()

    baseline_board_stats = universe_receipt.get("required_scope", {}).get("boards", {})
    identity_unresolved_source = sum(
        int(baseline_board_stats.get(name, {}).get("identity_unresolved", 0)) for name in REQUIRED_BOARDS
    )
    source_exception_unresolved = int(
        gates_receipt.get("source_exception_gate", {}).get("unexplained_required_a_stock_exception_count", -1)
    )
    row_count_matches = final_rows == int(repair_receipt.get("scan", {}).get("output_membership_rows", -1))
    input_row_binding_matches = baseline_rows == int(repair_receipt.get("scan", {}).get("input_membership_rows", -1))
    duplicate_removal_matches = baseline_rows - final_rows == int(repair_receipt.get("scan", {}).get("duplicate_membership_rows_removed", -1))
    criteria = {
        "generic_alias_completeness_gate": "PASS" if required_scope_alias_gate_passes(alias_gate) else "BLOCKED",
        "required_scope_identity_unresolved": "PASS" if unresolved_identity_rows == 0 and identity_unresolved_source == 0 else "BLOCKED",
        "duplicate_stable_security_id_trade_date": "PASS" if duplicate_identity_date_rows == 0 else "BLOCKED",
        "source_alias_interval_conflicts": "PASS" if duplicate_alias_active_ids == 0 else "BLOCKED",
        "same_entity_alias_interval_conflicts": "PASS" if alias_interval_conflicts == 0 else "BLOCKED",
        "confirmed_code_change_alias_gaps": "PASS" if alias_gap_count == 0 else "BLOCKED",
        "dated_board_facts_follow_alias_intervals": "PASS" if board_interval_errors == 0 else "BLOCKED",
        "source_symbol_resolves_only_in_effective_interval": "PASS" if source_symbol_interval_errors == 0 else "BLOCKED",
        "normalized_membership_matches_recanonicalized_r6_2": "PASS" if membership_mismatch == 0 else "BLOCKED",
        "all_day_required_identity_coverage": "PASS" if len(dates) == 786 and days_with_missing == 0 and total_missing == 0 and all(value == 0 for value in missing_by_board.values()) else "BLOCKED",
        "historical_universe_row_accounting": "PASS" if row_count_matches and input_row_binding_matches and duplicate_removal_matches else "BLOCKED",
        "source_bar_structural_validity": "PASS" if structural_invalid == 0 else "BLOCKED",
        "required_scope_source_exception_closure": "PASS" if source_exception_unresolved == 0 else "BLOCKED",
    }
    blockers = [key for key, value in criteria.items() if value != "PASS"]
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    report = {
        "contract_id": "V4_01_R8_IDENTITY_UNIVERSE_POSTCHECK_V1",
        "version": "1.0.0",
        "stage": "V4-01-R8-IDENTITY-UNIVERSE-POSTCHECK",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "PASS" if not blockers else "BLOCKED",
        "criteria": criteria,
        "blockers": blockers,
        "scope": {
            "required_boards": list(REQUIRED_BOARDS),
            "optional_bse": "DEGRADED_BSE; excluded from Required Scope gate",
            "session_count": len(dates),
            "required_scope_membership_rows": final_rows,
            "board_membership_rows": dict(sorted(board_rows.items())),
            "identity_unresolved": unresolved_identity_rows,
            "all_day_coverage": {
                "days_with_missing_required_identity": days_with_missing,
                "total_missing_required_identity_rows": total_missing,
                "missing_by_board": dict(missing_by_board),
            },
            "duplicate_stable_id_trade_date_rows": duplicate_identity_date_rows,
            "source_alias_interval_conflicts": duplicate_alias_active_ids,
            "same_entity_alias_interval_conflicts": alias_interval_conflicts,
            "confirmed_code_change_alias_gaps": alias_gap_count,
            "wrong_dated_board_rows": board_interval_errors,
            "wrong_source_symbol_or_interval_rows": source_symbol_interval_errors,
            "normalized_membership_mismatch_rows": membership_mismatch,
            "baseline_rows": baseline_rows,
            "expected_rows_after_alias_dedup": expected_rows_after_alias_dedup,
            "duplicate_rows_removed": baseline_rows - final_rows,
            "source_bar_structural_invalid_rows": structural_invalid,
            "source_exception_unresolved": source_exception_unresolved,
        },
        "inputs": {
            str(FINAL_IDENTITY): {"sha256": sha256(ROOT / FINAL_IDENTITY), "bytes": (ROOT / FINAL_IDENTITY).stat().st_size},
            str(ALIAS_FACTS): {"sha256": sha256(ROOT / ALIAS_FACTS), "bytes": (ROOT / ALIAS_FACTS).stat().st_size},
            str(FINAL_UNIVERSE): {"sha256": sha256(ROOT / FINAL_UNIVERSE), "bytes": (ROOT / FINAL_UNIVERSE).stat().st_size},
            str(BASELINE_UNIVERSE): {"sha256": sha256(ROOT / BASELINE_UNIVERSE), "bytes": (ROOT / BASELINE_UNIVERSE).stat().st_size},
            str(ADJUSTED_DAILY): {"sha256": sha256(bar_path), "bytes": bar_path.stat().st_size},
            str(ALIAS_RECEIPT): {"sha256": sha256(ROOT / ALIAS_RECEIPT)},
            str(REPAIR_RECEIPT): {"sha256": sha256(ROOT / REPAIR_RECEIPT)},
        },
        "execution_identity": {
            "input_commit": "1a70c8c733096936da4fa250a3f4def501ccfd1d",
            "execution_head": current_head,
            "baseline_scope_receipt_sha256": sha256(ROOT / BASELINE_UNIVERSE_RECEIPT),
            "baseline_required_scope_gate_sha256": sha256(ROOT / BASELINE_GATES),
            "duckdb_version": duckdb.__version__,
        },
        "next_stage": "V4_01_R8_FINAL_RECEIPT" if not blockers else "BLOCKED_REMEDIATE_R8_POSTCHECK",
    }
    _atomic_json(ROOT / OUTPUT, report)
    print(json.dumps({"status": report["status"], "criteria": criteria,
                      "scope": report["scope"], "receipt": OUTPUT.as_posix()}, ensure_ascii=False))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
