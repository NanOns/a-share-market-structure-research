from __future__ import annotations

"""Run the accepted-history backscan for generic security identity events."""

import gzip
import hashlib
import json
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402
from workbench_analysis.security_identity_event_discovery import discover_identity_events  # noqa: E402
from workbench_analysis.v4_01_alias_completeness import REQUIRED_BOARDS  # noqa: E402

CONTRACT = Path("config/security_identity_event_discovery_v1.json")
TASK_CARD = Path("docs/evidence/V4_R8_1_DM01_IMPLEMENTATION_PACK_R1_20260928.md")
REAUDIT = Path("docs/evidence/V4_PRE03_JOINT_R1_EXTERNAL_REAUDIT_20260928.md")
IDENTITY_R5 = Path("data/v4/artifact_store/v4_01/security_entity_map_R5_20260925.json")
IDENTITY_R7 = Path("data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json")
UNIVERSE_R6 = Path("data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R6_2_20260926.jsonl.gz")
UNIVERSE_R7 = Path("data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz")
ROSTERS_R6 = Path("data/v4/artifact_store/v4_01/baostock_dated_rosters_R6_20260926.jsonl.gz")
ALIAS_FACTS = Path("data/v4/bootstrap/dated_security_alias_r7.jsonl")
R7_COMPLETENESS = Path("reports/v4_01/V4_01_HISTORICAL_CODE_CHANGE_ALIAS_COMPLETENESS_R8.json")
R7_REPAIR = Path("reports/v4_02/V4_01_CODE_CHANGE_ALIAS_AUDIT_R7.json")
RAW_DAILY = Path("data/v4/artifact_store/v4_02/V4_02_ADJUSTED_CANONICAL_DAILY_R6_2_20260926.parquet")
OUTPUT = Path("reports/v4_01/V4_01_IDENTITY_EVENT_DISCOVERY_R8_1.json")
ALIAS_OUTPUT = Path("reports/v4_01/V4_01_ALIAS_COMPLETENESS_R8_1.json")
MINIMUM_SHARED_SESSIONS = 20


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (ROOT / path).read_text(encoding="utf-8").splitlines() if line.strip()]


def read_jsonl_gzip(path: Path):
    with gzip.open(ROOT / path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def parquet_alias_candidates() -> tuple[list[dict[str, Any]], int]:
    import duckdb

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
         AND a.raw_open = b.raw_open AND a.raw_high = b.raw_high
         AND a.raw_low = b.raw_low AND a.raw_close = b.raw_close
         AND a.volume = b.volume AND a.amount = b.amount
         AND a.source_security_key < b.source_security_key
         AND a.canonical_security_id <> b.canonical_security_id
        GROUP BY code_a, id_a, code_b, id_b
        HAVING count(DISTINCT a.trade_date) >= ?
        ORDER BY code_a, code_b
    """
    path = str(ROOT / RAW_DAILY)
    rows = con.execute(query, [path, MINIMUM_SHARED_SESSIONS]).fetchall()
    scanned = int(con.execute("SELECT count(*) FROM read_parquet(?)", [path]).fetchone()[0])
    con.close()
    return (
        [
            {
                "source_keys": [str(row[0]).upper(), str(row[2]).upper()],
                "security_ids": [str(row[1]), str(row[3])],
                "shared_identical_raw_bar_sessions": int(row[4]),
                "first_shared_date": str(row[5]),
                "last_shared_date": str(row[6]),
            }
            for row in rows
        ],
        scanned,
    )


def scan_universe_assignments(
    path: Path, id_metadata: dict[str, dict[str, Any]]
) -> tuple[set[str], set[str], int, dict[str, list[dict[str, Any]]], dict[str, int]]:
    dates: set[str] = set()
    row_count = 0
    by_source: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    source_keys: set[str] = set()
    board_rows: dict[str, int] = defaultdict(int)
    with gzip.open(ROOT / path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            row_count += 1
            day = str(row.get("trade_date") or "")
            key = str(row.get("source_security_key") or "").upper()
            security_id = str(row.get("security_id") or "")
            board = str(row.get("board_scope") or "")
            dates.add(day)
            board_rows[board] += 1
            if key and security_id:
                source_keys.add(key)
                entry = by_source[key].setdefault(
                    security_id,
                    {"first": day, "last": day, "security_id": security_id},
                )
                entry["first"] = min(str(entry["first"]), day)
                entry["last"] = max(str(entry["last"]), day)
    assignments: dict[str, list[dict[str, Any]]] = {}
    for key, versions in by_source.items():
        if len(versions) < 2:
            continue
        assignments[key] = []
        for security_id, span in sorted(versions.items(), key=lambda item: item[1]["first"]):
            metadata = dict(id_metadata.get(security_id, {}))
            metadata.update(
                security_id=security_id,
                effective_from=span["first"],
                effective_to=span["last"],
            )
            assignments[key].append(metadata)
    return dates, source_keys, row_count, assignments, dict(sorted(board_rows.items()))


def main() -> int:
    started = time.perf_counter()
    contract = read_json(CONTRACT)
    baseline_identity = read_json(IDENTITY_R5)["records"]
    final_identity = read_json(IDENTITY_R7)["records"]
    identities = {str(row.get("source_security_key") or "").upper(): row for row in baseline_identity}
    id_metadata = {str(row.get("security_id") or ""): row for row in baseline_identity}
    final_by_key = {str(row.get("source_security_key") or "").upper(): row for row in final_identity}
    alias_facts = read_jsonl(ALIAS_FACTS)
    old_completeness = read_json(R7_COMPLETENESS)
    repair = read_json(R7_REPAIR)
    official_capture = Path(str(repair["evidence"]["source_capture_path"]))
    official_digest = digest(ROOT / official_capture)
    if official_digest.lower() != str(repair["evidence"]["source_capture_sha256"]).lower():
        raise SystemExit("R8_1_OFFICIAL_EVIDENCE_HASH_MISMATCH")
    if any(str(row.get("evidence_hash") or "").lower() != official_digest.lower() for row in alias_facts):
        raise SystemExit("R8_1_ALIAS_FACT_EVIDENCE_HASH_MISMATCH")

    official_events = []
    by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in alias_facts:
        by_id[str(fact.get("security_id") or "")].append(fact)
    for security_id, facts in by_id.items():
        ordered = sorted(facts, key=lambda row: str(row.get("effective_from") or ""))
        if len(ordered) < 2:
            continue
        official_events.append(
            {
                "old_source_security_key": ordered[0]["source_security_key"],
                "new_source_security_key": ordered[-1]["source_security_key"],
                "effective_date": ordered[-1]["effective_from"],
                "entity_relation": "SAME_ENTITY",
                "security_id": security_id,
                "source_ref": ordered[-1]["evidence_ref"],
                "source_capture_path": ordered[-1]["evidence_capture_path"],
                "source_capture_sha256": ordered[-1]["evidence_hash"],
                "observed_at": ordered[-1]["observed_at"],
                "system_available_at": ordered[-1]["system_available_at"],
            }
        )

    session_dates, required_source_keys, universe_rows, source_assignments, board_rows = scan_universe_assignments(
        UNIVERSE_R6, id_metadata
    )
    if len(session_dates) != 786:
        raise SystemExit("R8_1_ACCEPTED_SESSION_SET_INCOMPLETE")
    bars, bar_rows = parquet_alias_candidates()
    started_roster = time.perf_counter()

    # R6 roster snapshots are ordered by the accepted official session set. The
    # discovery component retains only two snapshots at a time.
    roster_snapshots = read_jsonl_gzip(ROSTERS_R6)
    facts_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in alias_facts:
        facts_by_key[str(fact.get("source_security_key") or "").upper()].append(fact)
    verified_digests = {official_digest.lower()}
    lifecycle = list(baseline_identity)

    result = discover_identity_events(
        mode="HISTORICAL_BACKSCAN",
        session_dates=session_dates,
        roster_snapshots=roster_snapshots,
        lifecycle_records=lifecycle,
        identities=identities,
        required_scope_source_keys=required_source_keys,
        alias_facts=alias_facts,
        official_events=official_events,
        verified_evidence_digests=verified_digests,
        retrospective_bar_candidates=bars,
        source_identity_assignments=source_assignments,
    )
    result["observed_at_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    result["stage_contract"] = {
        "technical_baseline": "DA-MSR-V4.2.2-CODEX-REV2",
        "implementation_pack": str(TASK_CARD),
        "external_reaudit": str(REAUDIT),
        "event_discovery_contract": str(CONTRACT),
    }
    result["scope"] = {
        "required_boards": list(REQUIRED_BOARDS),
        "optional_bse": "DEGRADED_BSE; excluded from Required Scope gate",
        "formal_history_window": {
            "start": min(session_dates),
            "end": max(session_dates),
            "session_count": len(session_dates),
        },
        "required_universe_rows_scanned": universe_rows,
        "required_universe_board_rows": board_rows,
        "required_raw_bar_rows_scanned": bar_rows,
        "roster_snapshots_scanned": len(session_dates),
        "official_session_dates_derived_from_accepted_required_universe": True,
    }
    r7_hashes = {
        "identity_map_sha256": digest(ROOT / IDENTITY_R7),
        "required_universe_sha256": digest(ROOT / UNIVERSE_R7),
    }
    prior_evidence = old_completeness.get("evidence", {})
    prior_hashes = {
        "identity_map_sha256": str(prior_evidence.get("final_r7_identity_map", {}).get("sha256") or ""),
        "required_universe_sha256": str(prior_evidence.get("final_r7_required_universe", {}).get("sha256") or ""),
    }
    result["canonical_repair"] = {
        "new_historical_same_entity_counterexamples_requiring_repair": [
            event["candidate_id"] for event in result["events"]
            if event["resolution_status"] == "CONFIRMED_SAME_ENTITY_CODE_CHANGE"
            and any(final_by_key.get(key, {}).get("security_id") != event["resolved_security_id"]
                    for key in event["source_keys"])
        ],
        "r7_canonical_artifact_hashes": r7_hashes,
        "prior_r8_canonical_artifact_hashes": prior_hashes,
        "r7_canonical_artifacts_unchanged": r7_hashes == prior_hashes,
        "recanonicalization_required": False,
    }
    result["evidence"] = {
        "contract": {"path": CONTRACT.as_posix(), "sha256": digest(ROOT / CONTRACT)},
        "implementation_pack": {"path": TASK_CARD.as_posix(), "sha256": digest(ROOT / TASK_CARD)},
        "external_reaudit": {"path": REAUDIT.as_posix(), "sha256": digest(ROOT / REAUDIT)},
        "baseline_identity_map": {"path": IDENTITY_R5.as_posix(), "sha256": digest(ROOT / IDENTITY_R5)},
        "baseline_required_universe": {"path": UNIVERSE_R6.as_posix(), "sha256": digest(ROOT / UNIVERSE_R6)},
        "roster_snapshots": {"path": ROSTERS_R6.as_posix(), "sha256": digest(ROOT / ROSTERS_R6)},
        "baseline_adjusted_daily": {"path": RAW_DAILY.as_posix(), "sha256": digest(ROOT / RAW_DAILY),
                                    "rows": bar_rows, "candidate_pair_count": len(bars)},
        "dated_alias_facts": {"path": ALIAS_FACTS.as_posix(), "sha256": digest(ROOT / ALIAS_FACTS)},
        "official_code_change_notice": {"path": official_capture.as_posix(), "sha256": official_digest,
                                        "source_ref": repair["evidence"]["source_ref"],
                                        "effective_date": "2025-02-17",
                                        "observed_at": repair["evidence"].get("observed_at"),
                                        "system_available_at": repair["evidence"].get("system_available_at")},
        "r7_identity_map": {"path": IDENTITY_R7.as_posix(), "sha256": r7_hashes["identity_map_sha256"]},
        "r7_required_universe": {"path": UNIVERSE_R7.as_posix(), "sha256": r7_hashes["required_universe_sha256"]},
    }
    result["execution_identity"] = {
        "execution_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "script_sha256": digest(Path(__file__).resolve().relative_to(ROOT)),
        "python_version": sys.version.split()[0],
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "candidate_discovery_elapsed_seconds": round(time.perf_counter() - started_roster, 3),
        "tdx_root_write_count": 0,
        "identity_merge_count": 0,
    }
    result["next_stage"] = (
        "R8_1_IDENTITY_UNIVERSE_POSTCHECK" if result["status"] == "PASS"
        else "BLOCKED_UNRESOLVED_REQUIRED_SCOPE_IDENTITY_EVENT"
    )
    alias_report = {
        "contract_id": "V4_01_ALIAS_COMPLETENESS_R8_1",
        "version": "1.0.0",
        "status": result["status"],
        "event_discovery_receipt": OUTPUT.as_posix(),
        "event_discovery_sha256": None,
        "candidate_count": result["candidate_count"],
        "candidate_status_counts": result["candidate_status_counts"],
        "unresolved_required_scope_candidate_count": result["unresolved_required_scope_candidate_count"],
        "candidate_signal_coverage": result["signal_counts"],
        "required_scope": list(REQUIRED_BOARDS),
        "fail_closed": result["fail_closed"],
        "next_stage": result["next_stage"],
    }
    _atomic_json(ROOT / OUTPUT, result)
    alias_report["event_discovery_sha256"] = digest(ROOT / OUTPUT)
    _atomic_json(ROOT / ALIAS_OUTPUT, alias_report)
    print(json.dumps(
        {
            "status": result["status"],
            "candidate_count": result["candidate_count"],
            "candidate_status_counts": result["candidate_status_counts"],
            "signal_counts": result["signal_counts"],
            "unresolved_required_scope_candidate_count": result["unresolved_required_scope_candidate_count"],
            "r7_canonical_artifacts_unchanged": result["canonical_repair"]["r7_canonical_artifacts_unchanged"],
            "receipts": [OUTPUT.as_posix(), ALIAS_OUTPUT.as_posix()],
        },
        ensure_ascii=False,
    ))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
