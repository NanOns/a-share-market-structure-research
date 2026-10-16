"""Pure planning for the final-schema V4 publication identity.

This module never connects to PostgreSQL, inserts DML, or changes a Head.
Database identity is the opaque ``publication_id``; ``revision_no`` is only the
lineage sequence and is never used as a foreign-key component.
"""
from datetime import date
import re
from typing import Any, Mapping, Sequence

from workbench_service.current_v4_context import canonical, digest
from .v4_publication_contract import CONTRACT_ID as MODULE_CONTRACT_ID, required_module_keys


CONTRACT_ID = "V4_PG_PUBLICATION_CANDIDATE_PLAN_R2"
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_MODULE = re.compile(r"^[a-z][a-z0-9_]{0,47}$")
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
_SOURCE_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")


class CandidatePlanError(ValueError):
    pass


def _valid_date(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as exc:
            raise CandidatePlanError("INVALID_TRADE_DATE") from exc
    raise CandidatePlanError("INVALID_TRADE_DATE")


def verify_source_identities(expected: Mapping[str, Any], observed: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    """Compare producer inputs with the exact source-revision manifest."""
    if not isinstance(expected, Mapping) or not isinstance(observed, Mapping) or not expected:
        raise CandidatePlanError("SOURCE_IDENTITY_MISSING")
    normalized_expected, normalized_observed = {}, {}
    for values, target in ((expected, normalized_expected), (observed, normalized_observed)):
        for key, binding in values.items():
            if not isinstance(key, str) or not _SOURCE_KEY.fullmatch(key) or not isinstance(binding, Mapping):
                raise CandidatePlanError("SOURCE_IDENTITY_INVALID")
            revision_id, source_digest = binding.get("source_revision_id"), binding.get("digest")
            if (not isinstance(revision_id, str) or not revision_id.strip()
                    or not isinstance(source_digest, str) or not _DIGEST.fullmatch(source_digest)):
                raise CandidatePlanError("SOURCE_IDENTITY_INVALID")
            target[key] = {"source_revision_id": revision_id, "digest": source_digest}
    if normalized_expected != normalized_observed:
        raise CandidatePlanError("SOURCE_IDENTITY_MISMATCH")
    return dict(sorted(normalized_expected.items()))


def _validate_prior_session(*, prior_publication_id, prior_state_head, prior_state_digest, gap_reason):
    if prior_publication_id is not None:
        if (not isinstance(prior_publication_id, str) or not prior_publication_id.strip()
                or not isinstance(prior_state_head, str) or not prior_state_head.strip()
                or not isinstance(prior_state_digest, str) or not _DIGEST.fullmatch(prior_state_digest)
                or gap_reason is not None):
            raise CandidatePlanError("PRIOR_SESSION_IDENTITY_INVALID")
    elif prior_state_head is not None or prior_state_digest is not None or not isinstance(gap_reason, str) or not gap_reason.strip():
        raise CandidatePlanError("PRIOR_SESSION_IDENTITY_INVALID")


def build_publication_candidate(
    *,
    publication_id: str,
    trade_date: str,
    revision_no: int,
    publication_lineage_id: str,
    model_namespace_id: str,
    core_revision: int,
    source_manifest_sha256: str,
    computation_identity_sha256: str,
    expected_source_bindings: Mapping[str, Any],
    observed_source_bindings: Mapping[str, Any],
    module_results: Sequence[Mapping[str, Any]],
    state_head_id: str,
    state_logical_digest: str,
    same_day_revision_parent_id: str | None = None,
    prior_session_publication_id: str | None = None,
    prior_session_state_head: str | None = None,
    prior_session_state_logical_digest: str | None = None,
    prior_session_gap_reason: str | None = None,
) -> dict[str, Any]:
    """Build a candidate-only plan using immutable publication_id identity."""
    if not isinstance(publication_id, str) or not publication_id.strip():
        raise CandidatePlanError("PUBLICATION_ID_REQUIRED")
    if not isinstance(model_namespace_id, str) or not model_namespace_id.strip():
        raise CandidatePlanError("MODEL_NAMESPACE_REQUIRED")
    if not isinstance(publication_lineage_id, str) or not publication_lineage_id.strip():
        raise CandidatePlanError("PUBLICATION_LINEAGE_REQUIRED")
    if isinstance(revision_no, bool) or not isinstance(revision_no, int) or revision_no <= 0:
        raise CandidatePlanError("PUBLICATION_REVISION_NO_INVALID")
    if isinstance(core_revision, bool) or not isinstance(core_revision, int) or core_revision <= 0:
        raise CandidatePlanError("CORE_REVISION_INVALID")
    target_date = _valid_date(trade_date)
    if not _DIGEST.fullmatch(str(source_manifest_sha256)):
        raise CandidatePlanError("SOURCE_MANIFEST_DIGEST_INVALID")
    if not _DIGEST.fullmatch(str(computation_identity_sha256)):
        raise CandidatePlanError("COMPUTATION_IDENTITY_DIGEST_INVALID")
    if not isinstance(state_head_id, str) or not state_head_id.strip() or not _DIGEST.fullmatch(str(state_logical_digest)):
        raise CandidatePlanError("PUBLICATION_STATE_IDENTITY_INVALID")
    _validate_prior_session(
        prior_publication_id=prior_session_publication_id,
        prior_state_head=prior_session_state_head,
        prior_state_digest=prior_session_state_logical_digest,
        gap_reason=prior_session_gap_reason,
    )
    if same_day_revision_parent_id is None and revision_no != 1:
        raise CandidatePlanError("SAME_DAY_REVISION_PARENT_MISSING")
    if same_day_revision_parent_id is not None and (revision_no <= 1 or not same_day_revision_parent_id.strip()):
        raise CandidatePlanError("SAME_DAY_REVISION_PARENT_INVALID")
    source_bindings = verify_source_identities(expected_source_bindings, observed_source_bindings)

    normalized = {}
    for raw in module_results:
        if not isinstance(raw, Mapping):
            raise CandidatePlanError("MODULE_RESULT_INVALID")
        module = raw.get("module_key")
        if not isinstance(module, str) or not _MODULE.fullmatch(module):
            raise CandidatePlanError("INVALID_MODULE_KEY")
        if module in normalized:
            raise CandidatePlanError("DUPLICATE_MODULE_RESULT")
        if module not in required_module_keys():
            raise CandidatePlanError("MODULE_NOT_IN_EFFECTIVE_CONTRACT")
        if raw.get("module_contract_id") != MODULE_CONTRACT_ID:
            raise CandidatePlanError("MODULE_CONTRACT_ID_MISMATCH")
        schema, relation = raw.get("owner_schema"), raw.get("owner_relation")
        if not isinstance(schema, str) or not _IDENTIFIER.fullmatch(schema) or not isinstance(relation, str) or not _IDENTIFIER.fullmatch(relation):
            raise CandidatePlanError("INVALID_OWNER_LOCATOR")
        token, contract = raw.get("owner_version_token"), raw.get("owner_contract_id")
        if not isinstance(token, str) or not token.strip() or not isinstance(contract, str) or not contract.strip():
            raise CandidatePlanError("OWNER_IDENTITY_INCOMPLETE")
        owner_date = _valid_date(raw.get("owner_trade_date"))
        if owner_date != target_date:
            raise CandidatePlanError("OWNER_T0_MISMATCH")
        result_digest = raw.get("result_digest")
        if not isinstance(result_digest, str) or not _DIGEST.fullmatch(result_digest):
            raise CandidatePlanError("MODULE_RESULT_DIGEST_INVALID")
        count = raw.get("row_count")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise CandidatePlanError("MODULE_RESULT_ROW_COUNT_INVALID")
        quality = raw.get("quality_status")
        if not isinstance(quality, str) or not quality.strip():
            raise CandidatePlanError("MODULE_QUALITY_STATUS_MISSING")
        recorded, pit = raw.get("as_recorded"), raw.get("pit_eligible")
        if not isinstance(recorded, bool) or not isinstance(pit, bool):
            raise CandidatePlanError("OWNER_QUALIFICATION_MISSING")
        database_identity = raw.get("database_identity")
        if not isinstance(database_identity, Mapping) or not {"database", "database_oid", "host", "port"}.issubset(database_identity):
            raise CandidatePlanError("OWNER_DATABASE_IDENTITY_MISSING")
        normalized[module] = {
            "module_key": module, "module_contract_id": MODULE_CONTRACT_ID,
            "database_identity": dict(database_identity), "owner_schema": schema,
            "owner_relation": relation, "owner_version_token": token,
            "owner_trade_date": owner_date, "owner_contract_id": contract,
            "result_digest": result_digest, "row_count": count,
            "quality_status": quality, "as_recorded": recorded, "pit_eligible": pit,
        }

    required = set(required_module_keys())
    missing_required = sorted(required - set(normalized))
    extras = sorted(set(normalized) - required)
    if extras:
        raise CandidatePlanError("MODULE_NOT_IN_EFFECTIVE_CONTRACT")
    status = "CANDIDATE_READY" if not missing_required else "CANDIDATE_INCOMPLETE"
    body = {
        "contract_id": CONTRACT_ID,
        "module_contract_id": MODULE_CONTRACT_ID,
        "candidate_only": True,
        "publish_status": "CANDIDATE",
        "accepted_at": None,
        "head_update": "NOT_AUTHORIZED_BY_PLAN",
        "publication_id": publication_id,
        "trade_date": target_date,
        "revision_no": revision_no,
        "publication_lineage_id": publication_lineage_id,
        "same_day_revision_parent_id": same_day_revision_parent_id,
        "model_namespace_id": model_namespace_id,
        "core_revision": core_revision,
        "source_manifest_sha256": source_manifest_sha256,
        "computation_identity_sha256": computation_identity_sha256,
        "state_head_id": state_head_id,
        "state_logical_digest": state_logical_digest,
        "prior_session_publication_id": prior_session_publication_id,
        "prior_session_state_head": prior_session_state_head,
        "prior_session_state_logical_digest": prior_session_state_logical_digest,
        "prior_session_gap_reason": prior_session_gap_reason,
        "source_bindings": source_bindings,
        "module_results": [normalized[key] for key in sorted(normalized)],
        "missing_required_modules": missing_required,
        "status": status,
        "reasons": ["REQUIRED_MODULE_RESULT_MISSING"] if missing_required else [],
    }
    body["module_results_digest"] = digest(canonical(body["module_results"]))
    body["candidate_digest"] = digest(canonical(body))
    return body


def plan_publication_head_change(candidate: Mapping[str, Any], current_head: Mapping[str, Any] | None) -> dict[str, Any]:
    """Describe exact publication-id CAS; never execute or grant a write."""
    if not isinstance(candidate, Mapping) or candidate.get("status") != "CANDIDATE_READY":
        raise CandidatePlanError("CANDIDATE_NOT_READY")
    target = {"trade_date": candidate["trade_date"], "model_namespace_id": candidate["model_namespace_id"]}
    if current_head is None:
        if int(candidate["revision_no"]) != 1 or candidate.get("same_day_revision_parent_id") is not None:
            raise CandidatePlanError("INITIAL_PUBLICATION_IDENTITY_INVALID")
        return {
            "action": "INSERT_IF_ABSENT", "target": target,
            "expected_prior_head": None,
            "prior_session_publication_id": candidate.get("prior_session_publication_id"),
            "prior_session_state_head": candidate.get("prior_session_state_head"),
            "prior_session_state_logical_digest": candidate.get("prior_session_state_logical_digest"),
            "initial_boundary_review_required": candidate.get("prior_session_publication_id") is None,
            "write_executed": False,
        }
    if current_head.get("trade_date") != candidate["trade_date"] or current_head.get("model_namespace_id") != candidate["model_namespace_id"]:
        raise CandidatePlanError("HEAD_SELECTOR_MISMATCH")
    current_id, current_revision = current_head.get("publication_id"), int(current_head.get("revision_no", 0))
    if not isinstance(current_id, str) or current_revision <= 0:
        raise CandidatePlanError("CURRENT_HEAD_IDENTITY_INVALID")
    current_state_head, current_state_digest = current_head.get("state_head_id"), current_head.get("state_logical_digest")
    if (not isinstance(current_state_head, str) or not current_state_head.strip()
            or not isinstance(current_state_digest, str) or not _DIGEST.fullmatch(current_state_digest)):
        raise CandidatePlanError("CURRENT_HEAD_STATE_IDENTITY_INVALID")
    if current_head.get("publication_lineage_id") != candidate.get("publication_lineage_id"):
        raise CandidatePlanError("PUBLICATION_LINEAGE_MISMATCH")
    if current_id == candidate["publication_id"]:
        if (current_revision != int(candidate["revision_no"])
                or current_head.get("source_manifest_sha256") != candidate["source_manifest_sha256"]
                or current_head.get("computation_identity_sha256") != candidate["computation_identity_sha256"]):
            raise CandidatePlanError("PUBLICATION_IDENTITY_CONFLICT")
        if (current_head.get("module_results_digest") != candidate.get("module_results_digest")
                or current_head.get("state_head_id") != candidate.get("state_head_id")
                or current_head.get("state_logical_digest") != candidate.get("state_logical_digest")):
            raise CandidatePlanError("IDEMPOTENT_IDENTITY_UNVERIFIED")
        return {"action": "IDEMPOTENT_REPLAY", "target": target, "expected_prior_head": dict(current_head), "write_executed": False}
    if int(candidate["revision_no"]) != current_revision + 1:
        raise CandidatePlanError("PUBLICATION_REVISION_NOT_NEXT")
    if candidate.get("same_day_revision_parent_id") != current_id:
        raise CandidatePlanError("HEAD_CAS_PRECONDITION_MISMATCH")
    return {
        "action": "CAS_UPDATE", "target": target,
        "expected_prior_head": {
            "publication_id": current_id,
            "revision_no": current_revision,
            "state_head_id": current_state_head,
            "state_logical_digest": current_state_digest,
        },
        "write_executed": False,
    }
