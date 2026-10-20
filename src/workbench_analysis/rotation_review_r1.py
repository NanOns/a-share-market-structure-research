"""Human independent-review gate for a dated rotation candidate.

The review record is scoped to one immutable candidate token. It never changes
the accepted Head, rotation owner, or published rotation events.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re

from .r43_owner_replay import checked
from .operational_daily_storage_v1 import atomic_json, exclusive_lock

CONTRACT = "V4_ROTATION_INDEPENDENT_REVIEW_R1"
REVIEW_ROOT = "data/v4/reviews/rotation"


def _review_path(root, token):
    if not re.fullmatch(r"[0-9a-f]{64}", str(token)):
        raise ValueError("ROTATION_REVIEW_TOKEN_INVALID")
    return Path(root) / REVIEW_ROOT / (token + ".json")


def snapshot(root, bff):
    """Re-read the bound domain and calculate whether a human review may pass."""
    root = Path(root).resolve()
    api = bff.api
    token = api.token
    day = api.candidate["accepted_trade_date"]
    owner_ref = api.candidate.get("owners", {}).get(day, {}).get("rotation")
    if not owner_ref:
        return {"contract_id": CONTRACT, "status": "BLOCKED_OWNER_MISSING",
                "trade_date": day, "context_token": token, "reason": "ROTATION_OWNER_NOT_BOUND"}
    owner_path = checked(root, owner_ref)
    owner_bytes = owner_path.read_bytes()
    if len(owner_bytes) != owner_ref.get("bytes") or hashlib.sha256(owner_bytes).hexdigest() != owner_ref.get("sha256"):
        raise ValueError("ROTATION_OWNER_BINDING_MISMATCH")

    query = {"context_token": token, "trade_date": day}
    code, home = bff.get("/api/v4/home", query)
    if code != 200 or home.get("context_token") != token:
        raise ValueError("ROTATION_REVIEW_HOME_READBACK_FAILED")
    sectors = []
    for offset in (0, 200):
        code, page = bff.get("/api/v4/sectors", query | {"limit": "200", "offset": str(offset)})
        if code != 200 or page.get("context_token") != token:
            raise ValueError("ROTATION_REVIEW_SECTOR_READBACK_FAILED")
        sectors.extend(page.get("items") or [])

    summary = home.get("rotation_owner_summary") or {}
    identifiers = [row.get("entity_id") for row in sectors]
    unique_ids = len(identifiers) == len(set(identifiers)) and all(identifiers)
    total = summary.get("total")
    states = summary.get("current_states") or {}
    unknown = states.get("UNKNOWN", 0)
    expected = total == 400 and len(sectors) == total and unique_ids
    status = "READY_FOR_INDEPENDENT_REVIEW" if expected and unknown == 0 else "BLOCKED_QUALITY"
    context = home.get("context") or {}
    return {
        "contract_id": CONTRACT,
        "status": status,
        "trade_date": day,
        "context_token": token,
        "owner": {"path": owner_ref["path"], "bytes": len(owner_bytes),
                  "sha256": hashlib.sha256(owner_bytes).hexdigest()},
        "readback": {"home_status": code, "sector_rows": len(sectors),
                     "sector_ids_unique": bool(unique_ids), "expected_sector_rows": total},
        "current_states": states,
        "prior_states": summary.get("prior_states") or {},
        "unknown_reasons": summary.get("unknown_reasons") or {},
        "unknown_count": unknown,
        "accepted_transition_count": home.get("rotation_total", 0),
        "limitations": {
            "AS_RECORDED": context.get("AS_RECORDED"),
            "PIT_ELIGIBLE": context.get("PIT_ELIGIBLE"),
            "knowledge_lineage": context.get("knowledge_lineage"),
            "membership_observed_at": context.get("membership_observed_at"),
            "data_updated_at": context.get("data_updated_at"),
            "formal_head_change": False,
            "published_rotation_events_change": False,
        },
        "existing_review": _load_review(root, token),
    }


def _load_review(root, token):
    path = _review_path(root, token)
    if not path.exists():
        return None
    raw = path.read_bytes()
    record = json.loads(raw)
    if record.get("contract_id") != CONTRACT or record.get("context_token") != token:
        raise ValueError("ROTATION_REVIEW_RECORD_INVALID")
    return record


def read_review(root, bff):
    result = snapshot(root, bff)
    review = result.pop("existing_review", None)
    if review:
        result["status"] = review.get("review_status")
        result["review"] = review
    return result


def record_review(root, bff, body):
    if not isinstance(body, dict) or set(body) != {
        "context_token", "reviewer", "acknowledge_evidence", "acknowledge_scope", "decision"
    }:
        raise ValueError("ROTATION_REVIEW_FIELDS_INVALID")
    if body.get("context_token") != bff.api.token:
        raise ValueError("CONTEXT_TOKEN_MISMATCH")
    reviewer = str(body.get("reviewer", "")).strip()
    if not 1 <= len(reviewer) <= 80:
        raise ValueError("ROTATION_REVIEWER_REQUIRED")
    if body.get("acknowledge_evidence") is not True or body.get("acknowledge_scope") is not True:
        raise ValueError("ROTATION_REVIEW_ACKNOWLEDGEMENT_REQUIRED")
    current = snapshot(root, bff)
    decision = body.get("decision")
    readback = current.get("readback") or {}
    complete_readback = (readback.get("sector_rows") == 400 and
                         readback.get("expected_sector_rows") == 400 and
                         readback.get("sector_ids_unique") is True)
    if decision == "ACCEPT_COMPLETE_CANDIDATE" and current["status"] != "READY_FOR_INDEPENDENT_REVIEW":
        raise ValueError("ROTATION_REVIEW_QUALITY_GATE_BLOCKED")
    if decision == "ACCEPT_WITH_LIMITATIONS" and not complete_readback:
        raise ValueError("ROTATION_REVIEW_COVERAGE_GATE_BLOCKED")
    if decision not in ("ACCEPT_COMPLETE_CANDIDATE", "ACCEPT_WITH_LIMITATIONS"):
        raise ValueError("ROTATION_REVIEW_DECISION_INVALID")
    path = _review_path(root, bff.api.token)
    lock_path = path.with_suffix(".lock")
    with exclusive_lock(root, lock_path):
        prior = _load_review(root, bff.api.token)
        if prior:
            return prior
        record = {
            "contract_id": CONTRACT,
            "review_status": ("INDEPENDENT_ACCEPTANCE_PASSED_FOR_CANDIDATE"
                              if decision == "ACCEPT_COMPLETE_CANDIDATE"
                              else "CANDIDATE_REVIEW_ACCEPTED_WITH_LIMITATIONS"),
            "decision": decision,
            "trade_date": current["trade_date"],
            "context_token": current["context_token"],
            "reviewer_attestation": reviewer,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "evidence_digest": hashlib.sha256(json.dumps(current, sort_keys=True, ensure_ascii=False,
                                                           separators=(",", ":")).encode()).hexdigest(),
            "owner": current["owner"],
            "readback": current["readback"],
            "current_states": current["current_states"],
            "prior_states": current["prior_states"],
            "unknown_reasons": current["unknown_reasons"],
            "unknown_count": current["unknown_count"],
            "limitations": current["limitations"],
            "scope": "DATED_CANDIDATE_REVIEW_ONLY",
            "formal_head_change": False,
            "published_rotation_events_change": False,
            "independent_external_acceptance": False,
        }
        atomic_json(root, path, record)
        return record
