"""Independent generic verifier for R4 candidate-to-accepted identity promotion."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_v4_08_r2_membership_evidence import atomic_json

AUTHORITY = "docs/evidence/V4_08_R3_INDEPENDENT_EXTERNAL_AUDIT_20260930.md"
AUTHORITY_SHA256 = "61890d7c6ac8fcf9a4790aea710bdc2f2e6e6882a3caf128c50a0837eafc8832"
IDENTITY_HEAD = "data/v4/V4_01_GO_FORWARD_IDENTITY_CANDIDATE_HEAD_R1.json"
IDENTITY_CANDIDATE = "data/v4/artifact_store/v4_01/security_entity_map_GO_FORWARD_20260930_R1.json"
GENERIC_REPLAY = "reports/v4_08/V4_08_R4_1_GENERIC_IDENTITY_PROMOTION.json"
CURRENT_ACCEPTED = "data/v4/artifact_store/v4_01/security_entity_map_GO_FORWARD_20260930_ACCEPTED_R1.json"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def bind(path):
    return {"path": path, "sha256": digest(path), "byte_count": (ROOT / path).stat().st_size}


def _pending_lifecycle_ids(candidate):
    return {str(event["security_id"]) for event in candidate.get("new_lifecycle_events", [])
            if event.get("acceptance") == "CANDIDATE_PENDING_EXTERNAL_PROMOTION" and event.get("security_id")}


def _expected_generic_artifact(candidate, authority_sha256):
    pending_ids = _pending_lifecycle_ids(candidate)
    candidate_records = candidate.get("records", [])
    pending_additions = [row for row in candidate_records
                         if str(row.get("security_id")) in pending_ids
                         and row.get("acceptance") == "CANDIDATE_PENDING_EXTERNAL_PROMOTION"]
    if not pending_ids or {str(row.get("security_id")) for row in pending_additions} != pending_ids:
        raise ValueError("CANDIDATE_LIFECYCLE_RECORD_SET_MISMATCH")
    expected = copy.deepcopy(candidate)
    expected["status"] = "ACCEPTED_GO_FORWARD_IDENTITY_TARGET_DAY_INCREMENT"
    expected["promotion_authority"] = {
        "audit_path": AUTHORITY,
        "audit_sha256": authority_sha256,
        "authorized_scope": "2026-09-30 TARGET-DAY INCREMENTAL IDENTITY CLOSURE",
    }
    for collection_name in ("records", "new_lifecycle_events"):
        for row in expected[collection_name]:
            if str(row.get("security_id")) in pending_ids:
                row["acceptance"] = "ACCEPTED"
    return expected, pending_ids


def verify():
    authority_sha = digest(AUTHORITY)
    head = read(IDENTITY_HEAD)
    candidate = read(IDENTITY_CANDIDATE)
    parent_path = candidate["parent_identity"]["path"]
    parent = read(parent_path)
    generic = read(GENERIC_REPLAY)
    accepted = read(CURRENT_ACCEPTED)
    expected, pending_ids = _expected_generic_artifact(candidate, authority_sha)

    parent_count = len(parent.get("records", []))
    candidate_records = candidate.get("records", [])
    generic_records = generic.get("records", [])
    parent_ids = {str(row.get("security_id")) for row in parent.get("records", [])}
    candidate_ids = {str(row.get("security_id")) for row in candidate_records}
    generic_ids = {str(row.get("security_id")) for row in generic_records}
    added_ids = candidate_ids - parent_ids

    diffs = []
    for before, after in zip(candidate_records, generic_records):
        if before != after:
            changed = {key for key in set(before) | set(after) if before.get(key) != after.get(key)}
            diffs.append({"security_id": after.get("security_id"), "changed_fields": sorted(changed)})

    event_diffs = []
    for before, after in zip(candidate.get("new_lifecycle_events", []), generic.get("new_lifecycle_events", [])):
        if before != after:
            event_diffs.append({"security_id": after.get("security_id"),
                                "changed_fields": sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))})

    checks = {
        "external_authority_digest_matches": authority_sha == AUTHORITY_SHA256,
        "candidate_head_digest_authorized": digest(IDENTITY_HEAD) == "9ef49acc749daeb954cce0433363d0f28e54720db58c92fc20da77080049bb2c",
        "candidate_artifact_digest_authorized": digest(IDENTITY_CANDIDATE) == "98c0d0c828c18d2dd012f5f2de27d420da49183c20116a790af91a33b7d12603",
        "candidate_head_binds_candidate_artifact": head.get("identity_revision", {}).get("sha256") == digest(IDENTITY_CANDIDATE),
        "candidate_parent_artifact_digest_matches": candidate.get("parent_identity", {}).get("sha256") == digest(parent_path),
        "candidate_records_append_parent_unchanged": candidate_records[:parent_count] == parent.get("records", []),
        "new_records_equal_authorized_lifecycle_event_set": added_ids == pending_ids,
        "all_new_records_promoted": all(row.get("acceptance") == "ACCEPTED" for row in generic_records[parent_count:]),
        "no_unauthorized_identity_added": generic_ids - parent_ids == pending_ids,
        "parent_rows_unchanged_after_promotion": generic_records[:parent_count] == parent.get("records", []),
        "only_acceptance_changed_on_promoted_records": all(item["changed_fields"] == ["acceptance"] for item in diffs),
        "only_acceptance_changed_on_pending_lifecycle_events": all(item["changed_fields"] == ["acceptance"] for item in event_diffs),
        "generic_replay_equals_independent_reconstruction": generic == expected,
        "generic_replay_matches_current_accepted_artifact": generic == accepted,
        "generic_replay_digest_matches_current_accepted_digest": digest(GENERIC_REPLAY) == digest(CURRENT_ACCEPTED),
    }
    result = {
        "contract_id": "V4_08_R4_1_GENERIC_IDENTITY_PROMOTION_EQUIVALENCE_V1",
        "status": "PASS_CURRENT_IDENTITY_PROMOTION_DATA_SALVAGED" if all(checks.values()) else "FAIL_EQUIVALENCE_REPLAY",
        "checks": checks,
        "candidate_head": bind(IDENTITY_HEAD),
        "candidate_artifact": bind(IDENTITY_CANDIDATE),
        "candidate_parent_artifact": bind(parent_path),
        "external_authority": bind(AUTHORITY),
        "generic_replay_artifact": bind(GENERIC_REPLAY),
        "current_accepted_artifact": bind(CURRENT_ACCEPTED),
        "generic_accepted_identity_sha256": digest(GENERIC_REPLAY),
        "current_accepted_identity_sha256": digest(CURRENT_ACCEPTED),
        "parent_record_count": parent_count,
        "candidate_addition_count": len(added_ids),
        "promoted_identity_count": len(pending_ids),
        "promoted_security_ids": sorted(pending_ids),
        "record_logical_diff": diffs,
        "lifecycle_event_logical_diff": event_diffs,
        "producer_expectation_set_imported": False,
    }
    output = ROOT / "reports/v4_08/V4_08_R4_1_GENERIC_IDENTITY_PROMOTION_EQUIVALENCE.json"
    atomic_json(output, result)
    print(json.dumps({"status": result["status"], "checks": checks,
                      "generic_accepted_identity_sha256": result["generic_accepted_identity_sha256"]}, ensure_ascii=False))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(verify())
