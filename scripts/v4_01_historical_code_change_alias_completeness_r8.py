from __future__ import annotations

"""Discover and resolve Required-Scope historical code-change candidates for R8."""

import hashlib
import gzip
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402
from workbench_analysis.v4_01_alias_completeness import (  # noqa: E402
    REQUIRED_BOARDS,
    classify_candidate,
    pair_summary_candidates,
)

CONTRACT_PATH = Path("config/v4_01_historical_code_change_alias_completeness_v1.json")
TASK_CARD = Path("docs/evidence/V4_PRE03_JOINT_FINAL_SEAL_TASK_R1_20260927.md")
REV2_PATH = Path("docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md")
IDENTITY_BASELINE = Path("data/v4/artifact_store/v4_01/security_entity_map_R5_20260925.json")
IDENTITY_FINAL = Path("data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json")
UNIVERSE_BASELINE = Path("data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R6_2_20260926.jsonl.gz")
UNIVERSE_FINAL = Path("data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz")
ADJUSTED_BASELINE = Path("data/v4/artifact_store/v4_02/V4_02_ADJUSTED_CANONICAL_DAILY_R6_2_20260926.parquet")
ALIAS_FACTS = Path("data/v4/bootstrap/dated_security_alias_r7.jsonl")
R7_REPAIR_RECEIPT = Path("reports/v4_02/V4_01_CODE_CHANGE_ALIAS_AUDIT_R7.json")
OUTPUT = Path("reports/v4_01/V4_01_HISTORICAL_CODE_CHANGE_ALIAS_COMPLETENESS_R8.json")
MINIMUM_SHARED_SESSIONS = 20


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def evidence(path: Path) -> dict[str, object]:
    return {"path": path.as_posix(), "sha256": sha256(ROOT / path)}


def scan_required_universe(path: Path) -> dict[str, object]:
    rows = 0
    sessions: set[str] = set()
    boards: Counter[str] = Counter()
    identity_unknown_rows = 0
    keys_by_identity: dict[str, set[str]] = defaultdict(set)
    ids_by_source_key: dict[str, set[str]] = defaultdict(set)
    with gzip.open(ROOT / path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            rows += 1
            sessions.add(str(row.get("trade_date") or ""))
            board = str(row.get("board_scope") or "")
            boards[board] += 1
            sid = str(row.get("security_id") or "")
            source_key = str(row.get("source_security_key") or "").upper()
            if not sid or sid == "UNKNOWN" or str(row.get("identity_status") or "").upper() == "UNKNOWN":
                identity_unknown_rows += 1
            if sid and source_key:
                keys_by_identity[sid].add(source_key)
                ids_by_source_key[source_key].add(sid)
    return {
        "rows_scanned": rows,
        "session_count": len(sessions),
        "first_session": min(sessions) if sessions else None,
        "last_session": max(sessions) if sessions else None,
        "board_rows": dict(sorted(boards.items())),
        "identity_unknown_rows": identity_unknown_rows,
        "stable_ids_with_multiple_source_keys": sum(len(keys) > 1 for keys in keys_by_identity.values()),
        "source_keys_assigned_to_multiple_stable_ids": sum(len(ids) > 1 for ids in ids_by_source_key.values()),
    }


def main() -> int:
    import duckdb

    contract = json.loads((ROOT / CONTRACT_PATH).read_text(encoding="utf-8"))
    baseline = json.loads((ROOT / IDENTITY_BASELINE).read_text(encoding="utf-8"))
    final = json.loads((ROOT / IDENTITY_FINAL).read_text(encoding="utf-8"))
    repair = json.loads((ROOT / R7_REPAIR_RECEIPT).read_text(encoding="utf-8"))
    alias_facts = [
        json.loads(line)
        for line in (ROOT / ALIAS_FACTS).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    baseline_by_key = {str(row.get("source_security_key", "")).upper(): row for row in baseline["records"]}
    final_by_key = {str(row.get("source_security_key", "")).upper(): row for row in final["records"]}
    verified_digests: set[str] = set()
    official_evidence_path = Path(repair["evidence"]["source_capture_path"])
    official_evidence_digest = sha256(ROOT / official_evidence_path)
    if official_evidence_digest != str(repair["evidence"]["source_capture_sha256"]).lower():
        raise SystemExit("ALIAS_COMPLETENESS_OFFICIAL_EVIDENCE_DIGEST_MISMATCH")
    for fact in alias_facts:
        if str(fact.get("evidence_hash") or "").lower() != official_evidence_digest:
            raise SystemExit("ALIAS_COMPLETENESS_FACT_EVIDENCE_BINDING_MISMATCH")
        verified_digests.add(official_evidence_digest)
    baseline_universe_receipt = json.loads(
        (ROOT / "reports/v4_01/historical_evaluable_universe_receipt_R6_2_20260926.json").read_text(encoding="utf-8")
    )

    adjusted_path = ROOT / ADJUSTED_BASELINE
    con = duckdb.connect(database=":memory:")
    query = """
        WITH source_rows AS (
          SELECT canonical_security_id, source_security_key, board_scope,
                 trade_date, raw_open, raw_high, raw_low, raw_close, volume, amount
          FROM read_parquet(?)
          WHERE board_scope IN ('SH_MAIN', 'SZ_MAIN', 'CHINEXT', 'STAR')
            AND source_security_key IS NOT NULL
        )
        SELECT a.source_security_key AS code_a,
               a.canonical_security_id AS id_a,
               b.source_security_key AS code_b,
               b.canonical_security_id AS id_b,
               count(DISTINCT a.trade_date) AS identical_raw_bar_dates,
               min(a.trade_date) AS first_date,
               max(a.trade_date) AS last_date
        FROM source_rows a
        JOIN source_rows b
          ON a.trade_date = b.trade_date
         AND a.raw_open = b.raw_open
         AND a.raw_high = b.raw_high
         AND a.raw_low = b.raw_low
         AND a.raw_close = b.raw_close
         AND a.volume = b.volume
         AND a.amount = b.amount
         AND a.source_security_key < b.source_security_key
         AND a.canonical_security_id <> b.canonical_security_id
        GROUP BY code_a, id_a, code_b, id_b
        HAVING count(DISTINCT a.trade_date) >= ?
        ORDER BY code_a, code_b
    """
    baseline_universe_rows = int(baseline_universe_receipt.get("required_scope", {}).get("membership_rows", 0))
    pair_rows = con.execute(query, [str(adjusted_path), MINIMUM_SHARED_SESSIONS]).fetchall()
    adjusted_rows_scanned = int(
        con.execute("SELECT count(*) FROM read_parquet(?)", [str(adjusted_path)]).fetchone()[0]
    )
    pair_summaries = [
        {
            "code_a": row[0], "id_a": row[1], "code_b": row[2], "id_b": row[3],
            "identical_raw_bar_dates": row[4], "first_date": str(row[5]), "last_date": str(row[6]),
        }
        for row in pair_rows
    ]
    con.close()
    candidates_by_pair = {
        tuple(row["source_keys"]): row
        for row in pair_summary_candidates(pair_summaries, minimum_shared_sessions=MINIMUM_SHARED_SESSIONS)
    }
    alias_fact_groups: dict[str, list[dict]] = defaultdict(list)
    for fact in alias_facts:
        alias_fact_groups[str(fact.get("security_id") or "")].append(fact)
    for fact_group in alias_fact_groups.values():
        keys = sorted({str(row.get("source_security_key") or "").upper() for row in fact_group if row.get("source_security_key")})
        for left, right in combinations(keys, 2):
            left_id = str(baseline_by_key.get(left, {}).get("security_id") or "")
            right_id = str(baseline_by_key.get(right, {}).get("security_id") or "")
            pair = (left, right)
            candidates_by_pair.setdefault(
                pair,
                {
                    "source_keys": list(pair),
                    "security_ids": [left_id, right_id],
                    "shared_identical_raw_bar_sessions": 0,
                    "first_shared_date": None,
                    "last_shared_date": None,
                    "candidate_reason": "VERSIONED_DATED_ALIAS_FACT_LINKS_SOURCE_KEYS",
                },
            )
    candidates = [candidates_by_pair[key] for key in sorted(candidates_by_pair)]
    universe_scan = scan_required_universe(UNIVERSE_BASELINE)

    official_ref = str(repair["evidence"]["source_ref"])
    raw_bar_digest = sha256(adjusted_path)
    alias_digest = sha256(ROOT / ALIAS_FACTS)
    universe_digest = sha256(ROOT / UNIVERSE_BASELINE)
    baseline_identity_digest = sha256(ROOT / IDENTITY_BASELINE)
    resolved_candidates = []
    for candidate in candidates:
        resolved_candidates.append(
            classify_candidate(
                candidate,
                baseline_identity_by_key=baseline_by_key,
                final_identity_by_key=final_by_key,
                alias_facts=alias_facts,
                verified_evidence_digests=verified_digests,
                evidence_refs=[official_ref, ADJUSTED_BASELINE.as_posix()],
                evidence_digests=[raw_bar_digest, universe_digest, baseline_identity_digest, alias_digest],
            )
        )

    status_counts = {
        status: sum(row["resolution_status"] == status for row in resolved_candidates)
        for status in (
            "CONFIRMED_SAME_ENTITY_CODE_CHANGE",
            "CONFIRMED_DISTINCT_ENTITY",
            "UNRESOLVED",
            "NOT_APPLICABLE",
        )
    }
    unresolved_by_board = {board: 0 for board in REQUIRED_BOARDS}
    candidates_by_board = {board: 0 for board in REQUIRED_BOARDS}
    for row in resolved_candidates:
        if row.get("old_board") in candidates_by_board:
            candidates_by_board[str(row["old_board"])] += 1
        if row.get("new_board") in candidates_by_board and row.get("new_board") != row.get("old_board"):
            candidates_by_board[str(row["new_board"])] += 1
        if row["resolution_status"] == "UNRESOLVED":
            for board in {row.get("old_board"), row.get("new_board")}:
                if board in unresolved_by_board:
                    unresolved_by_board[str(board)] += 1

    session_count = int(baseline_universe_receipt.get("summary", {}).get("session_count", 0))
    unresolved_count = status_counts["UNRESOLVED"]
    all_candidates_resolved = unresolved_count == 0 and universe_scan["session_count"] == 786 and all(
        row["resolution_status"] in RESOLUTION_STATUSES_ACCEPTED for row in resolved_candidates
    )
    scan_status = "PASS" if all_candidates_resolved and session_count == 786 else "BLOCKED"
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    script_path = Path(__file__).resolve().relative_to(ROOT)
    report = {
        "contract_id": contract["contract_id"],
        "version": contract["version"],
        "stage": "V4-01-R8-GENERIC-HISTORICAL-CODE-CHANGE-ALIAS-COMPLETENESS",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": scan_status,
        "stage_contract": "DA-MSR-V4.2.2-CODEX-REV2; HISTORICAL_CODE_CHANGE_ALIAS_COMPLETENESS_V1; V4_PRE03_JOINT_FINAL_SEAL_TASK_R1",
        "scope": {
            "required_boards": list(REQUIRED_BOARDS),
            "optional_bse": "DEGRADED_BSE; excluded from Required Scope gate",
            "formal_history_window": {"start": "2023-07-04", "end": "2026-09-24", "session_count": session_count},
            "candidate_scan_covers_all_required_boards_and_all_rows_in_the_accepted_formal_history_window": universe_scan["rows_scanned"] == baseline_universe_rows and universe_scan["session_count"] == session_count == 786,
            "pre_window_bar_limitation": "No pre-2023 raw-bar series is claimed by the 786-session V4-01/V4-02 formal artifacts.",
        },
        "candidate_generation": {
            "method": "Scan every accepted universe membership row for source-key/identity assignments; scan every Required-Scope raw-bar row for persistent exact OHLCV-and-amount continuity across different source keys and baseline stable IDs; include versioned dated alias facts. Weak one-session price coincidence is excluded.",
            "minimum_shared_sessions": MINIMUM_SHARED_SESSIONS,
            "identity_literals_in_discovery_logic": [],
            "adjusted_daily_rows_scanned": adjusted_rows_scanned,
            "required_universe_membership_rows_scanned": universe_scan["rows_scanned"],
            "required_universe_sessions_scanned": universe_scan["session_count"],
            "stable_ids_with_multiple_source_keys_in_baseline_universe": universe_scan["stable_ids_with_multiple_source_keys"],
            "source_keys_assigned_to_multiple_stable_ids_in_baseline_universe": universe_scan["source_keys_assigned_to_multiple_stable_ids"],
            "identity_unknown_membership_rows": universe_scan["identity_unknown_rows"],
            "board_rows_scanned": universe_scan["board_rows"],
            "discovered_pair_count": len(candidates),
            "distinct_identity_pair_only": True,
            "old_id_new_id_split_candidates_are_included": True,
        },
        "candidate_status_counts": status_counts,
        "required_scope": {
            board: {
                "status": "PASS" if unresolved_by_board[board] == 0 else "BLOCKED",
                "code_change_candidate_count": candidates_by_board[board],
                "unresolved_code_change_candidate_count": unresolved_by_board[board],
            }
            for board in REQUIRED_BOARDS
        },
        "unresolved_required_scope_candidate_count": unresolved_count,
        "candidates": resolved_candidates,
        "evidence": {
            "contract": evidence(CONTRACT_PATH),
            "task_card": evidence(TASK_CARD),
            "technical_contract": evidence(REV2_PATH),
            "baseline_identity_map": {**evidence(IDENTITY_BASELINE), "records": len(baseline.get("records", []))},
            "baseline_required_universe": {**evidence(UNIVERSE_BASELINE), "rows_from_accepted_receipt": baseline_universe_rows},
            "baseline_adjusted_daily": {**evidence(ADJUSTED_BASELINE), "rows": adjusted_rows_scanned},
            "final_r7_identity_map": {**evidence(IDENTITY_FINAL), "records": len(final.get("records", []))},
            "final_r7_required_universe": evidence(UNIVERSE_FINAL),
            "dated_alias_facts": evidence(ALIAS_FACTS),
            "r7_alias_repair_receipt": evidence(R7_REPAIR_RECEIPT),
            "official_code_change_evidence": {
                "path": official_evidence_path.as_posix(),
                "sha256": official_evidence_digest,
                "source_ref": official_ref,
                "source_revision": repair["evidence"]["source_revision"],
            },
        },
        "execution_identity": {
            "input_commit": "1a70c8c733096936da4fa250a3f4def501ccfd1d",
            "execution_head": current_head,
            "script_sha256": sha256(ROOT / script_path),
            "duckdb_version": duckdb.__version__,
        },
        "fail_closed": {
            "unresolved_candidate_effect": "identity=UNKNOWN for impacted formal capability",
            "unresolved_required_scope_limit": 0,
            "formal_identity_merge_applied_by_discovery": False,
        },
        "next_stage": "V4_01_R8_IDENTITY_UNIVERSE_POSTCHECK" if scan_status == "PASS" else "BLOCKED_UNRESOLVED_OR_INCOMPLETE_ALIAS_CANDIDATE_SET",
    }
    _atomic_json(ROOT / OUTPUT, report)
    print(json.dumps({"status": scan_status, "candidate_status_counts": status_counts,
                      "candidate_count": len(candidates), "unresolved": unresolved_count,
                      "output": OUTPUT.as_posix()}, ensure_ascii=False))
    return 0 if scan_status == "PASS" else 2


RESOLUTION_STATUSES_ACCEPTED = {
    "CONFIRMED_SAME_ENTITY_CODE_CHANGE",
    "CONFIRMED_DISTINCT_ENTITY",
    "NOT_APPLICABLE",
}


if __name__ == "__main__":
    raise SystemExit(main())
