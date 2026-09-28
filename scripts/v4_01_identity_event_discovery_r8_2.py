from __future__ import annotations

"""Run the R8.2 identity relation policy against the accepted R8 evidence."""

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
sys.path.insert(0, str(ROOT))

from scripts.v4_01_identity_event_discovery_r8_1 import (  # noqa: E402
    IDENTITY_R5, IDENTITY_R7, UNIVERSE_R6, UNIVERSE_R7, ROSTERS_R6,
    ALIAS_FACTS, R7_COMPLETENESS, R7_REPAIR, RAW_DAILY,
    digest, read_json, read_jsonl, read_jsonl_gzip, parquet_alias_candidates,
    scan_universe_assignments,
)
from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402
from workbench_analysis.security_identity_event_discovery import discover_identity_events  # noqa: E402
from workbench_analysis.v4_01_alias_completeness import REQUIRED_BOARDS  # noqa: E402

POLICY = Path("config/identity_relation_evidence_policy_v1.json")
TASK_CARD = Path("docs/evidence/V4_R8_1_DM01_EXTERNAL_AUDIT_AND_R2_INCREMENTAL_WIRING_20260928.md")
OUTPUT = Path("reports/v4_01/V4_01_IDENTITY_EVENT_DISCOVERY_R8_2.json")
QUEUE = Path("reports/v4_01/V4_01_R8_2_UNRESOLVED_AUDIT_QUEUE.json")


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
        raise SystemExit("R8_2_OFFICIAL_EVIDENCE_HASH_MISMATCH")
    if any(str(row.get("evidence_hash") or "").lower() != official_digest.lower() for row in alias_facts):
        raise SystemExit("R8_2_ALIAS_FACT_EVIDENCE_HASH_MISMATCH")

    official_events = []
    by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in alias_facts:
        by_id[str(fact.get("security_id") or "")].append(fact)
    for security_id, facts in by_id.items():
        ordered = sorted(facts, key=lambda row: str(row.get("effective_from") or ""))
        if len(ordered) < 2:
            continue
        current = ordered[-1]
        official_events.append({
            "source_security_keys": [ordered[0]["source_security_key"], current["source_security_key"]],
            "effective_date": current["effective_from"],
            "entity_relation": "SAME_ENTITY",
            "evidence_class": "OFFICIAL_CODE_CHANGE_NOTICE",
            "canonical_security_id": security_id,
            "source_ref": current["evidence_ref"],
            "source_capture_path": current["evidence_capture_path"],
            "source_capture_sha256": current["evidence_hash"],
            "observed_at": current["observed_at"],
            "system_available_at": current["system_available_at"],
        })

    session_dates, required_source_keys, universe_rows, source_assignments, board_rows = scan_universe_assignments(
        UNIVERSE_R6, id_metadata
    )
    if len(session_dates) != 786:
        raise SystemExit("R8_2_ACCEPTED_SESSION_SET_INCOMPLETE")
    bars, bar_rows = parquet_alias_candidates()
    roster_snapshots = read_jsonl_gzip(ROSTERS_R6)
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
        "task_card": TASK_CARD.as_posix(),
        "resolution_policy": POLICY.as_posix(),
        "historical_backscan": True,
        "daily_incremental_mode_contracted": True,
        "weak_signal_confirmation_prohibited": True,
    }
    result["scope"] = {
        "required_boards": list(REQUIRED_BOARDS),
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
    result["evidence"] = {
        "task_card": {"path": TASK_CARD.as_posix(), "sha256": digest(ROOT / TASK_CARD)},
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
    result["next_stage"] = (
        "R8_2_EXTERNAL_AUDIT" if result["status"] == "PASS"
        else "BLOCKED_UNRESOLVED_REQUIRED_SCOPE_IDENTITY_EVENT"
    )
    queue = {
        "contract_id": "V4_01_R8_2_UNRESOLVED_AUDIT_QUEUE",
        "version": "1.0.0",
        "status": "OPEN" if result["unresolved_required_scope_candidate_count"] else "EMPTY",
        "policy": result["identity_relation_policy"],
        "candidate_count": result["unresolved_required_scope_candidate_count"],
        "events": [row for row in result["events"]
                   if row["required_scope_affected"] and row["resolution_status"] == "UNRESOLVED"],
        "next_stage": "INDEPENDENT_R8_2_POLICY_POSTCHECK_AND_OFFICIAL_EVIDENCE_TRIAGE",
    }
    _atomic_json(ROOT / OUTPUT, result)
    _atomic_json(ROOT / QUEUE, queue)
    print(json.dumps({"status": result["status"], "candidate_count": result["candidate_count"],
                      "candidate_status_counts": result["candidate_status_counts"],
                      "unresolved_required_scope_candidate_count": result["unresolved_required_scope_candidate_count"],
                      "receipts": [OUTPUT.as_posix(), QUEUE.as_posix()]}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
