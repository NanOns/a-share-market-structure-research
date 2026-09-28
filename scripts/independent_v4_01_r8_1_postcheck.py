from __future__ import annotations

"""Independent checks for the R8.1 identity event discovery receipt."""

import gzip
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402
from workbench_analysis.v4_01_alias_completeness import REQUIRED_BOARDS  # noqa: E402

EVENT_RECEIPT = Path("reports/v4_01/V4_01_IDENTITY_EVENT_DISCOVERY_R8_1.json")
ALIAS_RECEIPT = Path("reports/v4_01/V4_01_ALIAS_COMPLETENESS_R8_1.json")
OUTPUT = Path("reports/v4_01/V4_01_R8_1_INDEPENDENT_POSTCHECK_R1_20260928.json")
UNIVERSE = Path("data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R6_2_20260926.jsonl.gz")
ROSTERS = Path("data/v4/artifact_store/v4_01/baostock_dated_rosters_R6_20260926.jsonl.gz")
R7_IDENTITY = Path("data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json")
R7_UNIVERSE = Path("data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz")
PRIOR_R8 = Path("reports/v4_01/V4_01_HISTORICAL_CODE_CHANGE_ALIAS_COMPLETENESS_R8.json")
CROSS_STAGE = Path("reports/v4_02/V4_02_R8_CROSS_STAGE_POSTCHECK_20260928.json")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with (ROOT / path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path: Path) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main() -> int:
    event = read(EVENT_RECEIPT)
    alias = read(ALIAS_RECEIPT)
    prior_r8 = read(PRIOR_R8)
    cross = read(CROSS_STAGE)
    problems: list[str] = []
    checks: dict[str, str] = {}

    checks["event_receipt_pass"] = "PASS" if event.get("status") == "PASS" else "BLOCKED"
    if checks["event_receipt_pass"] != "PASS":
        problems.append("R8_1_EVENT_RECEIPT_NOT_PASS")
    checks["alias_receipt_binds_event"] = (
        "PASS" if alias.get("event_discovery_sha256") == sha(EVENT_RECEIPT) else "BLOCKED"
    )
    if checks["alias_receipt_binds_event"] != "PASS":
        problems.append("R8_1_ALIAS_RECEIPT_HASH_MISMATCH")
    checks["unresolved_required_scope_zero"] = (
        "PASS" if int(event.get("unresolved_required_scope_candidate_count", -1)) == 0 else "BLOCKED"
    )
    if checks["unresolved_required_scope_zero"] != "PASS":
        problems.append("R8_1_UNRESOLVED_REQUIRED_SCOPE_CANDIDATE")

    signals = event.get("signal_counts", {})
    required_signals = {
        "OFFICIAL_CODE_CHANGE_EVENT",
        "DATED_ALIAS_FACT",
        "ROSTER_EXIT_ENTRY_ADJACENCY",
        "LIFECYCLE_BOUNDARY_ADJACENCY",
        "PERSISTENT_RETROSPECTIVE_BAR_ALIAS",
        "SOURCE_SYMBOL_REASSIGNMENT_OR_CODE_REUSE_CANDIDATE",
    }
    checks["candidate_signal_union_present"] = (
        "PASS" if required_signals.issubset(signals) else "BLOCKED"
    )
    if checks["candidate_signal_union_present"] != "PASS":
        problems.append("R8_1_CANDIDATE_SIGNAL_UNION_INCOMPLETE")

    session_days: set[str] = set()
    source_keys: set[str] = set()
    board_rows: Counter[str] = Counter()
    universe_rows = 0
    with gzip.open(ROOT / UNIVERSE, "rt", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            universe_rows += 1
            session_days.add(str(row.get("trade_date") or ""))
            source_keys.add(str(row.get("source_security_key") or "").upper())
            board_rows[str(row.get("board_scope") or "")] += 1
    checks["accepted_universe_full_window"] = (
        "PASS"
        if len(session_days) == 786
        and universe_rows == int(event.get("scope", {}).get("required_universe_rows_scanned", -1))
        and dict(sorted(board_rows.items())) == event.get("scope", {}).get("required_universe_board_rows")
        else "BLOCKED"
    )
    if checks["accepted_universe_full_window"] != "PASS":
        problems.append("R8_1_ACCEPTED_UNIVERSE_SCAN_MISMATCH")

    roster_days: set[str] = set()
    roster_count = 0
    with gzip.open(ROOT / ROSTERS, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                row = json.loads(line)
                roster_count += 1
                roster_days.add(str(row.get("trade_date") or ""))
    checks["dated_roster_full_session_coverage"] = (
        "PASS" if len(roster_days) == 786 and roster_days == session_days else "BLOCKED"
    )
    if checks["dated_roster_full_session_coverage"] != "PASS":
        problems.append("R8_1_ROSTER_SESSION_COVERAGE_MISMATCH")

    required_scope_events = [
        row for row in event.get("events", []) if row.get("required_scope_affected")
    ]
    missing_source_events = [
        row["candidate_id"] for row in required_scope_events
        if not set(row.get("source_keys", [])) <= source_keys
    ]
    checks["candidate_keys_present_in_accepted_universe"] = (
        "PASS" if not missing_source_events else "BLOCKED"
    )
    if missing_source_events:
        problems.append("R8_1_CANDIDATE_KEY_NOT_IN_ACCEPTED_UNIVERSE")

    identity_evidence_errors = []
    for row in required_scope_events:
        status = row.get("resolution_status")
        evidence = row.get("resolution_evidence", [])
        if status == "CONFIRMED_SAME_ENTITY_CODE_CHANGE":
            ids = {str(fact.get("security_id") or "") for fact in evidence}
            hashes = {str(fact.get("evidence_hash") or fact.get("source_capture_sha256") or "").lower()
                      for fact in evidence}
            if len(ids) != 1 or "" in ids or not hashes or "" in hashes:
                identity_evidence_errors.append(row["candidate_id"])
        elif status == "CONFIRMED_DISTINCT_ENTITY" and row.get("resolution_reason") == "DIFFERENT_VERSIONED_LISTING_ANCHORS":
            anchors = [str(fact.get("list_date") or "") for fact in evidence]
            revisions = [str(fact.get("source_revision") or "") for fact in evidence]
            if len(anchors) != 2 or not all(anchors) or anchors[0] == anchors[1] or not all(revisions):
                identity_evidence_errors.append(row["candidate_id"])
        elif status not in {"CONFIRMED_DISTINCT_ENTITY", "CONFIRMED_SAME_ENTITY_CODE_CHANGE", "NOT_APPLICABLE"}:
            identity_evidence_errors.append(row["candidate_id"])
    checks["candidate_resolution_evidence_complete"] = (
        "PASS" if not identity_evidence_errors else "BLOCKED"
    )
    if identity_evidence_errors:
        problems.append("R8_1_CANDIDATE_RESOLUTION_EVIDENCE_INCOMPLETE")

    for record in event.get("evidence", {}).values():
        if isinstance(record, dict) and record.get("path") and record.get("sha256"):
            path = Path(str(record["path"]))
            if path.is_file() and sha(path) != str(record["sha256"]):
                problems.append("R8_1_INPUT_EVIDENCE_HASH_MISMATCH:" + path.as_posix())
    checks["input_evidence_hashes_match"] = (
        "PASS" if not any(item.startswith("R8_1_INPUT_EVIDENCE_HASH_MISMATCH") for item in problems) else "BLOCKED"
    )
    prior_evidence = prior_r8.get("evidence", {})
    current_hashes = event.get("canonical_repair", {}).get("r7_canonical_artifact_hashes", {})
    prior_hashes = event.get("canonical_repair", {}).get("prior_r8_canonical_artifact_hashes", {})
    actual_hashes = {
        "identity_map_sha256": sha(R7_IDENTITY),
        "required_universe_sha256": sha(R7_UNIVERSE),
    }
    checks["r7_hashes_unchanged_from_r8"] = (
        "PASS" if current_hashes == prior_hashes == actual_hashes
        and event.get("canonical_repair", {}).get("recanonicalization_required") is False
        else "BLOCKED"
    )
    if checks["r7_hashes_unchanged_from_r8"] != "PASS":
        problems.append("R8_1_R7_CANONICAL_HASH_CHANGED_OR_MISMATCH")
    checks["v4_02_r8_cross_stage_still_passes"] = (
        "PASS" if cross.get("status") == "PASS" and not cross.get("blockers") else "BLOCKED"
    )
    if checks["v4_02_r8_cross_stage_still_passes"] != "PASS":
        problems.append("V4_02_R8_CROSS_STAGE_POSTCHECK_NOT_PASS")

    status = "PASS" if not problems and all(value == "PASS" for value in checks.values()) else "BLOCKED"
    receipt = {
        "contract_id": "V4_01_R8_1_INDEPENDENT_POSTCHECK_R1",
        "version": "1.0.0",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "checks": checks,
        "counts": {
            "required_sessions": len(session_days),
            "required_universe_rows": universe_rows,
            "dated_roster_snapshots": roster_count,
            "required_scope_candidates": len(required_scope_events),
            "unresolved_required_scope_candidates": event.get("unresolved_required_scope_candidate_count"),
        },
        "required_boards": list(REQUIRED_BOARDS),
        "r7_canonical_hashes": actual_hashes,
        "problems": problems,
        "next_stage": "SEAL_GATE_A_JOINT_R2" if status == "PASS" else "REPAIR_R8_1_POSTCHECK_BLOCKERS",
    }
    _atomic_json(ROOT / OUTPUT, receipt)
    print(json.dumps({"status": status, "checks": checks, "receipt": OUTPUT.as_posix()}, ensure_ascii=False))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
