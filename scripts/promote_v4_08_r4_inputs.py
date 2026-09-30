"""Generic R4 identity/calendar promotion, with a non-mutating replay mode."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_v4_08_r2_membership_evidence import atomic_json

AUDIT = "docs/evidence/V4_08_R3_INDEPENDENT_EXTERNAL_AUDIT_20260930.md"
AUDIT_SHA256 = "61890d7c6ac8fcf9a4790aea710bdc2f2e6e6882a3caf128c50a0837eafc8832"
AUTH = {
    "identity_candidate_head": "9ef49acc749daeb954cce0433363d0f28e54720db58c92fc20da77080049bb2c",
    "identity_candidate_artifact": "98c0d0c828c18d2dd012f5f2de27d420da49183c20116a790af91a33b7d12603",
    "calendar_candidate_head": "800a32d26b8a6089f67eda77e84c2364d4d0fd8a9879ed1b5c620be71202631b",
    "calendar_candidate_artifact": "abb832c49e447996b33d7ebf4f233ccfbd4d7f4abc0722caa164d8e25a9ecfc3",
}
IDENTITY_HEAD = "data/v4/V4_01_GO_FORWARD_IDENTITY_CANDIDATE_HEAD_R1.json"
IDENTITY_CANDIDATE = "data/v4/artifact_store/v4_01/security_entity_map_GO_FORWARD_20260930_R1.json"
IDENTITY_ACCEPTED = "data/v4/artifact_store/v4_01/security_entity_map_GO_FORWARD_20260930_ACCEPTED_R1.json"
CALENDAR_HEAD = "data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_CANDIDATE_HEAD_R1.json"
CALENDAR_CANDIDATE = "data/v4/artifact_store/v4_02/market_calendar_GO_FORWARD_20260930_R1.json"


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def binding(path):
    return {"path": path, "sha256": sha(path)}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def require(path, expected):
    actual = sha(path)
    if actual != expected:
        raise ValueError(f"EXTERNAL_AUTHORIZATION_DIGEST_MISMATCH:{path}:{actual}")


def _promotion_identity_set(candidate):
    pending_events = [event for event in candidate.get("new_lifecycle_events", [])
                      if event.get("acceptance") == "CANDIDATE_PENDING_EXTERNAL_PROMOTION"]
    event_ids = {str(event.get("security_id")) for event in pending_events if event.get("security_id")}
    pending_records = [record for record in candidate.get("records", [])
                       if str(record.get("security_id")) in event_ids
                       and record.get("acceptance") == "CANDIDATE_PENDING_EXTERNAL_PROMOTION"]
    record_ids = {str(record.get("security_id")) for record in pending_records}
    if not event_ids or event_ids != record_ids or len(event_ids) != len(pending_events):
        raise ValueError("IDENTITY_EVENT_RECORD_PROMOTION_SET_MISMATCH")
    return event_ids, pending_events, pending_records


def build_generic_identity_promotion(candidate, authority_sha256=AUDIT_SHA256):
    event_ids, pending_events, pending_records = _promotion_identity_set(candidate)
    accepted = copy.deepcopy(candidate)
    accepted["status"] = "ACCEPTED_GO_FORWARD_IDENTITY_TARGET_DAY_INCREMENT"
    accepted["promotion_authority"] = {
        "audit_path": AUDIT,
        "audit_sha256": authority_sha256,
        "authorized_scope": "2026-09-30 TARGET-DAY INCREMENTAL IDENTITY CLOSURE",
    }
    for collection_name in ("records", "new_lifecycle_events"):
        for item in accepted[collection_name]:
            if str(item.get("security_id")) in event_ids:
                item["acceptance"] = "ACCEPTED"
    return accepted, event_ids, pending_events, pending_records


def generic_replay(output_path):
    require(AUDIT, AUDIT_SHA256)
    require(IDENTITY_HEAD, AUTH["identity_candidate_head"])
    require(IDENTITY_CANDIDATE, AUTH["identity_candidate_artifact"])
    candidate_head = read(IDENTITY_HEAD)
    candidate = read(IDENTITY_CANDIDATE)
    if candidate_head.get("status") != "CANDIDATE_READY_PENDING_EXTERNAL_PROMOTION":
        raise ValueError("IDENTITY_CANDIDATE_NOT_PENDING_EXTERNAL_PROMOTION")
    if candidate_head.get("identity_revision", {}).get("sha256") != sha(IDENTITY_CANDIDATE):
        raise ValueError("IDENTITY_CANDIDATE_HEAD_BINDING_INVALID")
    accepted, event_ids, events, records = build_generic_identity_promotion(candidate)
    atomic_json(ROOT / output_path, accepted)
    print(json.dumps({"status": "GENERIC_REPLAY_WRITTEN", "identity_candidate_artifact_sha256": sha(IDENTITY_CANDIDATE),
                      "generic_identity_artifact_sha256": sha(output_path), "candidate_lifecycle_event_count": len(events),
                      "promoted_record_count": len(records), "promoted_identity_count": len(event_ids), "output_path": output_path}))


def promote():
    # The current R4.1 policy is evaluated before any accepted input head is written.
    gate = read("reports/v4_08/V4_08_R4_1_NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN.json")
    if gate.get("status") != "PASS" or gate.get("hard_gated_equity_symbol_hits") != 0 or gate.get("unclassified_paths"):
        raise ValueError("NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC_HARD_GATE_FAILED")
    require(AUDIT, AUDIT_SHA256)
    for path, expected in ((IDENTITY_HEAD, AUTH["identity_candidate_head"]),
                           (IDENTITY_CANDIDATE, AUTH["identity_candidate_artifact"]),
                           (CALENDAR_HEAD, AUTH["calendar_candidate_head"]),
                           (CALENDAR_CANDIDATE, AUTH["calendar_candidate_artifact"])):
        require(path, expected)
    candidate_head = read(IDENTITY_HEAD)
    candidate = read(IDENTITY_CANDIDATE)
    if candidate_head.get("status") != "CANDIDATE_READY_PENDING_EXTERNAL_PROMOTION":
        raise ValueError("IDENTITY_CANDIDATE_NOT_PENDING_EXTERNAL_PROMOTION")
    if candidate_head.get("identity_revision", {}).get("sha256") != sha(IDENTITY_CANDIDATE):
        raise ValueError("IDENTITY_CANDIDATE_HEAD_BINDING_INVALID")
    parent = read(candidate["parent_identity"]["path"])
    if candidate.get("records", [])[:len(parent.get("records", []))] != parent.get("records", []):
        raise ValueError("IDENTITY_PARENT_PREFIX_CHANGED")
    accepted, event_ids, events, additions = build_generic_identity_promotion(candidate, sha(AUDIT))
    accepted_path = IDENTITY_ACCEPTED
    atomic_json(ROOT / accepted_path, accepted)
    accepted_hash = sha(accepted_path)
    identity_head_path = "data/v4/V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1.json"
    atomic_json(ROOT / identity_head_path, {
        "head_id": "V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1", "status": "ACCEPTED",
        "identity_revision": binding(accepted_path), "authorized_candidate_head": binding(IDENTITY_HEAD),
        "authorized_candidate_digest": AUTH["identity_candidate_head"],
        "parent_accepted_head": candidate["parent_accepted_head"],
        "promotion_authority": {"audit_path": AUDIT, "audit_sha256": sha(AUDIT),
                                "scope": "2026-09-30 TARGET-DAY INCREMENTAL IDENTITY CLOSURE"},
        "whole_market_lifecycle_completeness_claim": False,
    })
    calendar = read(CALENDAR_CANDIDATE)
    candidate_calendar_head = read(CALENDAR_HEAD)
    if candidate_calendar_head.get("extension", {}).get("sha256") != AUTH["calendar_candidate_artifact"]:
        raise ValueError("CALENDAR_CANDIDATE_HEAD_BINDING_INVALID")
    if calendar.get("status") != "CANDIDATE_READY_PENDING_EXTERNAL_PROMOTION":
        raise ValueError("CALENDAR_CANDIDATE_BINDING_INVALID")
    calendar_head_path = "data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_ACCEPTED_HEAD_R1.json"
    atomic_json(ROOT / calendar_head_path, {
        "head_id": "V4_02_GO_FORWARD_CALENDAR_EXTENSION_ACCEPTED_HEAD_R1", "status": "ACCEPTED",
        "market_calendar_id": "V4_02_GO_FORWARD_CALENDAR_20260930_R1", "coverage_end": "2026-09-30",
        "accepted_extension": binding(CALENDAR_CANDIDATE), "authorized_candidate_head": binding(CALENDAR_HEAD),
        "authorized_candidate_digest": AUTH["calendar_candidate_head"],
        "parent_accepted_calendar": calendar["parent_accepted_calendar"],
        "promotion_authority": {"audit_path": AUDIT, "audit_sha256": sha(AUDIT),
                                "scope": "SSE/SZSE MARKET SESSIONS THROUGH 2026-09-30"},
    })
    parent_count = len(parent["records"])
    before = candidate["records"]
    after = accepted["records"]
    changes = []
    for old, new in zip(before, after):
        if old != new:
            diff = {key: {"before": old.get(key), "after": new.get(key)}
                    for key in sorted(set(old) | set(new)) if old.get(key) != new.get(key)}
            changes.append({"security_id": new["security_id"], "changes": diff})
    if any(set(item["changes"]) != {"acceptance"} for item in changes):
        raise ValueError("IDENTITY_PROMOTION_MUTATED_NON_ACCEPTANCE_FACTS")
    atomic_json(ROOT / "reports/v4_01/V4_01_GO_FORWARD_IDENTITY_EXTERNAL_PROMOTION_R1.json", {
        "status": "PASS_EXACT_EXTERNAL_PROMOTION", "candidate_head": binding(IDENTITY_HEAD),
        "candidate_artifact_sha256": AUTH["identity_candidate_artifact"],
        "accepted_head": binding(identity_head_path), "accepted_artifact": binding(accepted_path),
        "parent_records_exactly_preserved": accepted["records"][:parent_count] == candidate["records"][:parent_count],
        "active_acceptance_count": len(additions), "logical_diff": changes,
        "audit_authority": binding(AUDIT), "p0_gate": binding("reports/v4_08/V4_08_R4_1_NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN.json"),
    })
    sessions = [row for row in calendar["sessions"] if row["market"] in {"SSE", "SZSE"}]
    atomic_json(ROOT / "reports/v4_02/V4_02_GO_FORWARD_CALENDAR_EXTENSION_EXTERNAL_PROMOTION_R1.json", {
        "status": "PASS_EXACT_EXTERNAL_PROMOTION", "candidate_head": binding(CALENDAR_HEAD),
        "candidate_extension_sha256": AUTH["calendar_candidate_artifact"],
        "accepted_head": binding(calendar_head_path), "accepted_extension": binding(CALENDAR_CANDIDATE),
        "accepted_session_count": len(sessions), "coverage_end": "2026-09-30",
        "closed_dates": ["2026-09-25", "2026-09-26", "2026-09-27"],
        "parent_digest_unchanged": sha(calendar["parent_accepted_calendar"]["path"]) == calendar["parent_accepted_calendar"]["sha256"],
        "stock_bars_used_to_invent_sessions": False, "audit_authority": binding(AUDIT),
        "p0_gate": binding("reports/v4_08/V4_08_R4_1_NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN.json"),
    })
    print(json.dumps({"status": "PASS_EXACT_EXTERNAL_PROMOTION", "identity_artifact_sha256": accepted_hash,
                      "identity_head": identity_head_path, "calendar_head": calendar_head_path,
                      "candidate_lifecycle_event_count": len(events), "active_identity_additions": len(additions),
                      "calendar_sessions": len(sessions)}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generic-replay-output", help="Write the generic identity replay to a repository-relative evidence path; do not update accepted heads")
    args = parser.parse_args()
    if args.generic_replay_output:
        generic_replay(args.generic_replay_output)
    else:
        promote()


if __name__ == "__main__":
    main()
