from __future__ import annotations

"""Run R8.3 atomic identity boundaries and signal-based relation linkage."""

import hashlib
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from scripts.v4_01_identity_event_discovery_r8_1 import (  # noqa: E402
    IDENTITY_R5, IDENTITY_R7, UNIVERSE_R6, UNIVERSE_R7, ROSTERS_R6,
    ALIAS_FACTS, R7_COMPLETENESS, R7_REPAIR, RAW_DAILY,
    digest, read_json, read_jsonl, read_jsonl_gzip, parquet_alias_candidates,
    scan_universe_assignments,
)
from scripts.v4_01_identity_event_discovery_r8_2 import POLICY  # noqa: E402
from workbench_analysis.official_code_change_event_index import (  # noqa: E402
    CONTRACT_ID as INDEX_CONTRACT_ID,
    REQUIRED_EXCHANGES,
    validate_index_coverage,
)
from workbench_analysis.security_identity_event_discovery import discover_identity_events  # noqa: E402

TASK_CARD = Path("docs/evidence/V4_R8_2_DM01_EXTERNAL_AUDIT_R3_20260928.md")
LINKAGE_CONTRACT = Path("config/security_identity_event_linkage_v1.json")
INDEX_CONTRACT = Path("config/official_security_code_change_event_index_v1.json")
INDEX_DIR = Path("data/v4/source_evidence/official_code_change_event_index")
INDEX_EVENTS = INDEX_DIR / "official_security_code_change_events_v1.jsonl"
INDEX_COVERAGE = INDEX_DIR / "coverage_receipt_v1.json"
INDEX_REPORT = Path("reports/v4_01/V4_01_OFFICIAL_CODE_CHANGE_EVENT_INDEX_R8_3.json")
DISCOVERY = Path("reports/v4_01/V4_01_IDENTITY_EVENT_DISCOVERY_R8_3.json")
LINKAGE = Path("reports/v4_01/V4_01_IDENTITY_RELATION_LINKAGE_R8_3.json")
QUEUE = Path("reports/v4_01/V4_01_R8_3_UNRESOLVED_LINKAGE_QUEUE.json")
START_DATE = "2023-07-04"
END_DATE = "2026-09-24"


def atomic_bytes(path: Path, data: bytes) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + f".{os.getpid()}.tmp")
    with temp.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, target)


def atomic_json(path: Path, payload: Any) -> None:
    atomic_bytes(path, (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def exchange_for_key(key: str) -> str:
    normalized = key.upper()
    if normalized.startswith("SH."):
        code = normalized[3:]
        return "STAR" if code.startswith("688") else "SH_MAIN"
    if normalized.startswith("SZ."):
        code = normalized[3:]
        return "CHINEXT" if code.startswith(("300", "301", "302")) else "SZ_MAIN"
    return "UNKNOWN"


def official_event_rows(alias_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_identity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in alias_facts:
        if str(fact.get("contract_id") or "") == "DATED_SECURITY_ALIAS_V1":
            by_identity[str(fact.get("security_id") or "")].append(fact)
    rows: list[dict[str, Any]] = []
    for security_id, facts in sorted(by_identity.items()):
        ordered = sorted(facts, key=lambda row: str(row.get("effective_from") or ""))
        for prior, current in zip(ordered, ordered[1:]):
            old_key = str(prior.get("source_security_key") or "").upper()
            new_key = str(current.get("source_security_key") or "").upper()
            effective = str(current.get("effective_from") or "")
            source_ref = str(current.get("evidence_ref") or "")
            capture_path = str(current.get("evidence_capture_path") or "")
            capture_sha = str(current.get("evidence_hash") or "").lower()
            if not old_key or not new_key or not effective or not capture_path or not capture_sha:
                continue
            if effective[:10] < START_DATE or effective[:10] > END_DATE:
                continue
            source_parts = source_ref.rstrip("/").split("/")
            published_date = next((part for part in reversed(source_parts)
                                   if len(part) == 10 and part[4:5] == "-"), None)
            rows.append({
                "exchange": exchange_for_key(new_key),
                "old_source_security_key": old_key,
                "new_source_security_key": new_key,
                "effective_date": effective[:10],
                "entity_identifier": security_id,
                "canonical_security_id": security_id,
                "entity_relation": "SAME_ENTITY",
                "source_ref": source_ref,
                "source_capture_path": capture_path,
                "source_capture_sha256": capture_sha,
                "published_at": published_date,
                "observed_at": current.get("observed_at"),
                "system_available_at": current.get("system_available_at"),
                "evidence_class": "OFFICIAL_CODE_CHANGE_NOTICE",
                "index_method": "VERSIONED_ACCEPTED_DATED_ALIAS_FACT",
            })
    return sorted(rows, key=lambda row: (str(row["effective_date"]), str(row["old_source_security_key"])))


def write_event_index(events: list[dict[str, Any]], alias_facts_digest: str) -> tuple[dict[str, Any], dict[str, Any]]:
    atomic_bytes(INDEX_EVENTS, b"".join(
        (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for row in events
    ))
    coverage_records = []
    for exchange in sorted(REQUIRED_EXCHANGES):
        exchange_event_count = sum(row["exchange"] == exchange for row in events)
        coverage_records.append({
            "exchange": exchange,
            "window_start": START_DATE,
            "window_end": END_DATE,
            "coverage_complete": False,
            "query_or_index_method": (
                "LOCAL_ACCEPTED_DATED_ALIAS_FACTS_AND_CAPTURED_OFFICIAL_NOTICES; "
                "full-window exchange archive enumeration not captured"
            ),
            "source_revision": "sha256:" + alias_facts_digest,
            "event_count": exchange_event_count,
            "failed_query_count": 0,
            "unresolved_source_windows": [{"start": START_DATE, "end": END_DATE,
                                           "reason": "FULL_OFFICIAL_EVENT_ARCHIVE_COVERAGE_NOT_EVIDENCED"}],
        })
    atomic_json(INDEX_COVERAGE, {
        "contract_id": INDEX_CONTRACT_ID,
        "version": "1.0.0",
        "history_window": {"start": START_DATE, "end": END_DATE},
        "required_exchanges": sorted(REQUIRED_EXCHANGES),
        "query_or_index_method": "Local accepted aliases plus hash-bound captured official notice evidence",
        "source_revision": "sha256:" + alias_facts_digest,
        "query_count": 0,
        "failed_query_count": 0,
        "coverage_receipts": coverage_records,
        "events_path": INDEX_EVENTS.as_posix(),
        "events_sha256": digest(ROOT / INDEX_EVENTS),
        "coverage_limitations": ["No systematic full-window official exchange archive query/capture exists in current evidence."],
    })
    coverage = validate_index_coverage(coverage_records=coverage_records, events=events,
                                       window_start=START_DATE, window_end=END_DATE)
    coverage.update({
        "events_path": INDEX_EVENTS.as_posix(),
        "events_sha256": digest(ROOT / INDEX_EVENTS),
        "coverage_receipt_path": INDEX_COVERAGE.as_posix(),
        "coverage_receipt_sha256": digest(ROOT / INDEX_COVERAGE),
        "query_or_index_method": "Local accepted aliases plus hash-bound captured official notice evidence",
        "source_revision": "sha256:" + alias_facts_digest,
        "query_count": 0,
    })
    return coverage, {"coverage_receipts": coverage_records}


def main() -> int:
    started = time.perf_counter()
    baseline_identity = read_json(IDENTITY_R5)["records"]
    final_identity = read_json(IDENTITY_R7)["records"]
    identities = {str(row.get("source_security_key") or "").upper(): row for row in baseline_identity}
    id_metadata = {str(row.get("security_id") or ""): row for row in baseline_identity}
    final_by_key = {str(row.get("source_security_key") or "").upper(): row for row in final_identity}
    alias_facts = read_jsonl(ALIAS_FACTS)
    repair = read_json(R7_REPAIR)
    official_capture = Path(str(repair["evidence"]["source_capture_path"]))
    official_digest = digest(ROOT / official_capture)
    if official_digest.lower() != str(repair["evidence"]["source_capture_sha256"]).lower():
        raise SystemExit("R8_3_OFFICIAL_EVIDENCE_HASH_MISMATCH")
    if any(str(row.get("evidence_hash") or "").lower() != official_digest.lower() for row in alias_facts):
        raise SystemExit("R8_3_ALIAS_FACT_EVIDENCE_HASH_MISMATCH")

    index_events = official_event_rows(alias_facts)
    index_coverage, _ = write_event_index(index_events, digest(ROOT / ALIAS_FACTS))
    session_dates, required_source_keys, universe_rows, source_assignments, board_rows = scan_universe_assignments(
        UNIVERSE_R6, id_metadata
    )
    if len(session_dates) != 786:
        raise SystemExit("R8_3_ACCEPTED_SESSION_SET_INCOMPLETE")
    bars, bar_rows = parquet_alias_candidates()
    roster_snapshots = read_jsonl_gzip(ROSTERS_R6)
    result = discover_identity_events(
        mode="HISTORICAL_BACKSCAN",
        session_dates=session_dates,
        roster_snapshots=roster_snapshots,
        lifecycle_records=list(baseline_identity),
        identities=identities,
        required_scope_source_keys=required_source_keys,
        alias_facts=alias_facts,
        official_events=index_events,
        verified_evidence_digests={official_digest.lower()},
        retrospective_bar_candidates=bars,
        source_identity_assignments=source_assignments,
    )
    discovery_status = result["status"]
    result["observed_at_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    result["stage_contract"] = {
        "task_card": TASK_CARD.as_posix(),
        "linkage_contract": LINKAGE_CONTRACT.as_posix(),
        "index_contract": INDEX_CONTRACT.as_posix(),
        "resolution_policy": POLICY.as_posix(),
        "historical_backscan": True,
        "daily_incremental_mode_contracted": True,
        "atomic_boundary_events_required": True,
        "relation_candidate_requires_linkage_signal": True,
        "weak_signal_confirmation_prohibited": True,
        "canonical_identity_mutation": False,
    }
    result["scope"] = {
        "required_boards": ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"],
        "optional_bse": "DEGRADED_BSE; excluded from Required Scope gate",
        "formal_history_window": {"start": min(session_dates), "end": max(session_dates),
                                  "session_count": len(session_dates)},
        "required_universe_rows_scanned": universe_rows,
        "required_universe_board_rows": board_rows,
        "required_raw_bar_rows_scanned": bar_rows,
        "roster_snapshots_scanned": len(session_dates),
        "official_session_dates_derived_from_accepted_required_universe": True,
    }
    actual_hashes = {
        "identity_map_sha256": digest(ROOT / IDENTITY_R7),
        "required_universe_sha256": digest(ROOT / UNIVERSE_R7),
    }
    prior_evidence = read_json(R7_COMPLETENESS).get("evidence", {})
    prior_hashes = {
        "identity_map_sha256": str(prior_evidence.get("final_r7_identity_map", {}).get("sha256") or ""),
        "required_universe_sha256": str(prior_evidence.get("final_r7_required_universe", {}).get("sha256") or ""),
    }
    result["canonical_repair"] = {
        "r7_canonical_artifact_hashes": actual_hashes,
        "prior_r8_canonical_artifact_hashes": prior_hashes,
        "r7_canonical_artifacts_unchanged": actual_hashes == prior_hashes,
        "recanonicalization_required": False,
        "confirmed_same_entity_counterexamples": [
            row["candidate_id"] for row in result["events"]
            if row["resolution_status"] == "CONFIRMED_SAME_ENTITY_CODE_CHANGE"
            and any(final_by_key.get(key, {}).get("security_id") != row["resolved_security_id"]
                    for key in row["source_keys"])
        ],
    }
    result["official_index_coverage"] = index_coverage
    result["identity_discovery_status"] = discovery_status
    result["gate_a_status"] = (
        "PASS" if discovery_status == "PASS" and index_coverage["event_index_completeness_pass"]
        and result["unresolved_required_scope_candidate_count"] == 0
        and result["unlinked_boundary_anomaly_count"] == 0
        else "BLOCKED"
    )
    if result["gate_a_status"] != "PASS":
        result["status"] = "BLOCKED"
    result["evidence"] = {
        "task_card": {"path": TASK_CARD.as_posix(), "sha256": digest(ROOT / TASK_CARD)},
        "linkage_contract": {"path": LINKAGE_CONTRACT.as_posix(), "sha256": digest(ROOT / LINKAGE_CONTRACT)},
        "index_contract": {"path": INDEX_CONTRACT.as_posix(), "sha256": digest(ROOT / INDEX_CONTRACT)},
        "relation_policy": {"path": POLICY.as_posix(), "sha256": digest(ROOT / POLICY)},
        "baseline_identity_map": {"path": IDENTITY_R5.as_posix(), "sha256": digest(ROOT / IDENTITY_R5)},
        "baseline_required_universe": {"path": UNIVERSE_R6.as_posix(), "sha256": digest(ROOT / UNIVERSE_R6)},
        "roster_snapshots": {"path": ROSTERS_R6.as_posix(), "sha256": digest(ROOT / ROSTERS_R6)},
        "baseline_adjusted_daily": {"path": RAW_DAILY.as_posix(), "sha256": digest(ROOT / RAW_DAILY),
                                    "rows": bar_rows, "candidate_pair_count": len(bars)},
        "dated_alias_facts": {"path": ALIAS_FACTS.as_posix(), "sha256": digest(ROOT / ALIAS_FACTS)},
        "official_code_change_notice": {"path": official_capture.as_posix(), "sha256": official_digest,
                                        "source_ref": repair["evidence"]["source_ref"],
                                        "effective_date": "2025-02-17"},
        "official_event_index": {"path": INDEX_EVENTS.as_posix(), "sha256": digest(ROOT / INDEX_EVENTS)},
        "official_event_index_coverage": {"path": INDEX_COVERAGE.as_posix(),
                                           "sha256": digest(ROOT / INDEX_COVERAGE)},
        "r7_identity_map": {"path": IDENTITY_R7.as_posix(), "sha256": actual_hashes["identity_map_sha256"]},
        "r7_required_universe": {"path": UNIVERSE_R7.as_posix(), "sha256": actual_hashes["required_universe_sha256"]},
    }
    result["execution_identity"] = {
        "execution_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "script_sha256": digest(Path(__file__).resolve().relative_to(ROOT)),
        "python_version": sys.version.split()[0],
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "tdx_root_write_count": 0,
        "identity_merge_count": 0,
    }
    result["next_stage"] = "R8_3_EXTERNAL_AUDIT" if result["gate_a_status"] == "PASS" else "BLOCKED_OFFICIAL_EVENT_INDEX_COVERAGE"
    relation_report = {
        "contract_id": "V4_01_IDENTITY_RELATION_LINKAGE_R8_3",
        "version": "1.0.0",
        "linkage_contract": result["linkage_contract"],
        "status": result["gate_a_status"],
        "candidate_count": result["candidate_count"],
        "candidate_status_counts": result["candidate_status_counts"],
        "unresolved_required_scope_candidate_count": result["unresolved_required_scope_candidate_count"],
        "boundary_event_count": result["boundary_event_count"],
        "boundary_event_counts": result["boundary_event_counts"],
        "unlinked_boundary_event_count": result["unlinked_boundary_event_count"],
        "unlinked_boundary_anomaly_count": result["unlinked_boundary_anomaly_count"],
        "ambiguous_name_boundary_group_count": result["ambiguous_name_boundary_group_count"],
        "events": result["events"],
        "boundary_events": result["boundary_events"],
        "official_index_coverage": index_coverage,
    }
    queue = {
        "contract_id": "V4_01_R8_3_UNRESOLVED_LINKAGE_QUEUE",
        "version": "1.0.0",
        "status": "OPEN" if result["unresolved_required_scope_candidate_count"] else "EMPTY",
        "candidate_count": result["unresolved_required_scope_candidate_count"],
        "events": [row for row in result["events"]
                   if row["required_scope_affected"] and row["resolution_status"] == "UNRESOLVED"],
        "note": "Atomic unlinked ordinary security boundaries are not relation candidates or queue entries.",
    }
    atomic_json(INDEX_REPORT, index_coverage)
    atomic_json(DISCOVERY, result)
    atomic_json(LINKAGE, relation_report)
    atomic_json(QUEUE, queue)
    print(json.dumps({
        "status": result["status"],
        "gate_a_status": result["gate_a_status"],
        "identity_discovery_status": discovery_status,
        "candidate_count": result["candidate_count"],
        "candidate_status_counts": result["candidate_status_counts"],
        "unresolved_required_scope_candidate_count": result["unresolved_required_scope_candidate_count"],
        "boundary_event_count": result["boundary_event_count"],
        "index_coverage_status": index_coverage["coverage_status"],
        "receipts": [INDEX_REPORT.as_posix(), DISCOVERY.as_posix(), LINKAGE.as_posix(), QUEUE.as_posix()],
    }, ensure_ascii=False))
    return 0 if result["gate_a_status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
