"""Pure planning for an append-only V4 accepted-publication transaction.

This module does not connect to PostgreSQL, write rows, or move a Head. It
validates producer-supplied identities and emits a candidate plan that can be
reviewed before any separately authorized database operation.
"""
from datetime import date
import re
from typing import Any, Mapping, Sequence

from workbench_service.current_v4_context import canonical, digest


CONTRACT_ID = "V4_PG_PUBLICATION_CANDIDATE_PLAN_R1"
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


def _requiredness(value: Any) -> str:
    result = value if isinstance(value, str) else value.get("requiredness") if isinstance(value, Mapping) else None
    if result not in {"REQUIRED", "OPTIONAL", "UNKNOWN"}:
        raise CandidatePlanError("MODULE_REQUIREDNESS_UNKNOWN")
    return result


def verify_source_identities(expected: Mapping[str, Any], observed: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    """Compare producer inputs with the exact source-revision manifest."""
    if not isinstance(expected, Mapping) or not isinstance(observed, Mapping) or not expected:
        raise CandidatePlanError("SOURCE_IDENTITY_MISSING")
    normalized_expected = {}
    normalized_observed = {}
    for source_key, target in (("expected", normalized_expected), ("observed", normalized_observed)):
        values = expected if source_key == "expected" else observed
        for key, binding in values.items():
            if not isinstance(key, str) or not _SOURCE_KEY.fullmatch(key) or not isinstance(binding, Mapping):
                raise CandidatePlanError("SOURCE_IDENTITY_INVALID")
            revision_id, source_digest = binding.get("source_revision_id"), binding.get("digest")
            if not isinstance(revision_id, str) or not revision_id.strip() or not isinstance(source_digest, str) or not _DIGEST.fullmatch(source_digest):
                raise CandidatePlanError("SOURCE_IDENTITY_INVALID")
            target[key] = {"source_revision_id": revision_id, "digest": source_digest}
    if normalized_expected != normalized_observed:
        raise CandidatePlanError("SOURCE_IDENTITY_MISMATCH")
    return dict(sorted(normalized_expected.items()))


def build_publication_candidate(
    *,
    publication_id: str,
    trade_date: str,
    revision: int,
    model_namespace_id: str,
    core_revision: int,
    source_manifest_sha256: str,
    computation_identity_sha256: str,
    expected_source_bindings: Mapping[str, Any],
    observed_source_bindings: Mapping[str, Any],
    module_requirements: Mapping[str, Any],
    module_results: Sequence[Mapping[str, Any]],
    prior_publication: tuple[str, int] | None = None,
    prior_session_state_head: str | None = None,
) -> dict[str, Any]:
    """Build a candidate-only plan without granting acceptance or PIT status."""
    if not isinstance(publication_id, str) or not publication_id.strip():
        raise CandidatePlanError("PUBLICATION_ID_REQUIRED")
    if not isinstance(model_namespace_id, str) or not model_namespace_id.strip():
        raise CandidatePlanError("MODEL_NAMESPACE_REQUIRED")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision <= 0:
        raise CandidatePlanError("PUBLICATION_REVISION_INVALID")
    if isinstance(core_revision, bool) or not isinstance(core_revision, int) or core_revision <= 0:
        raise CandidatePlanError("CORE_REVISION_INVALID")
    target_date = _valid_date(trade_date)
    if not _DIGEST.fullmatch(str(source_manifest_sha256)):
        raise CandidatePlanError("SOURCE_MANIFEST_DIGEST_INVALID")
    if not _DIGEST.fullmatch(str(computation_identity_sha256)):
        raise CandidatePlanError("COMPUTATION_IDENTITY_DIGEST_INVALID")
    source_bindings = verify_source_identities(expected_source_bindings, observed_source_bindings)
    if not isinstance(module_requirements, Mapping) or not module_requirements:
        raise CandidatePlanError("MODULE_REQUIREDNESS_UNKNOWN")

    requirements = {}
    for module, value in module_requirements.items():
        if not isinstance(module, str) or not _MODULE.fullmatch(module):
            raise CandidatePlanError("INVALID_MODULE_KEY")
        requirements[module] = _requiredness(value)
    unknown = sorted(module for module, status in requirements.items() if status == "UNKNOWN")

    normalized = {}
    for raw in module_results:
        if not isinstance(raw, Mapping):
            raise CandidatePlanError("MODULE_RESULT_INVALID")
        module = raw.get("module_key")
        if not isinstance(module, str) or not _MODULE.fullmatch(module):
            raise CandidatePlanError("INVALID_MODULE_KEY")
        if module in normalized:
            raise CandidatePlanError("DUPLICATE_MODULE_RESULT")
        if module not in requirements:
            raise CandidatePlanError("MODULE_NOT_IN_CONTRACT")
        owner_schema, owner_relation = raw.get("owner_schema"), raw.get("owner_relation")
        if not isinstance(owner_schema, str) or not _IDENTIFIER.fullmatch(owner_schema):
            raise CandidatePlanError("INVALID_OWNER_LOCATOR")
        if not isinstance(owner_relation, str) or not _IDENTIFIER.fullmatch(owner_relation):
            raise CandidatePlanError("INVALID_OWNER_LOCATOR")
        token, contract_id = raw.get("owner_version_token"), raw.get("owner_contract_id")
        if not isinstance(token, str) or not token.strip() or not isinstance(contract_id, str) or not contract_id.strip():
            raise CandidatePlanError("OWNER_IDENTITY_INCOMPLETE")
        owner_date = _valid_date(raw.get("owner_trade_date"))
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
            "module_key": module,
            "database_identity": dict(database_identity),
            "owner_schema": owner_schema,
            "owner_relation": owner_relation,
            "owner_version_token": token,
            "owner_trade_date": owner_date,
            "owner_contract_id": contract_id,
            "result_digest": result_digest,
            "row_count": count,
            "quality_status": quality,
            "as_recorded": recorded,
            "pit_eligible": pit,
        }

    missing_required = sorted(
        module for module, status in requirements.items()
        if status == "REQUIRED" and module not in normalized
    )
    plan_status = "CANDIDATE_READY" if not missing_required and not unknown else "CANDIDATE_INCOMPLETE"
    reasons = []
    if unknown:
        reasons.append("MODULE_REQUIREDNESS_UNKNOWN")
    if missing_required:
        reasons.append("REQUIRED_MODULE_RESULT_MISSING")

    body = {
        "contract_id": CONTRACT_ID,
        "candidate_only": True,
        "publish_status": "CANDIDATE",
        "accepted_at": None,
        "head_update": "NOT_AUTHORIZED_BY_PLAN",
        "publication_id": publication_id,
        "trade_date": target_date,
        "revision": revision,
        "model_namespace_id": model_namespace_id,
        "core_revision": core_revision,
        "source_manifest_sha256": source_manifest_sha256,
        "computation_identity_sha256": computation_identity_sha256,
        "source_bindings": source_bindings,
        "prior_publication": {
            "publication_id": prior_publication[0],
            "revision": int(prior_publication[1]),
        } if prior_publication else None,
        "prior_session_state_head": prior_session_state_head,
        "module_requirements": dict(sorted(requirements.items())),
        "module_results": [normalized[key] for key in sorted(normalized)],
        "missing_required_modules": missing_required,
        "unknown_requiredness_modules": unknown,
        "status": plan_status,
        "reasons": reasons,
    }
    body["module_results_digest"] = digest(canonical(body["module_results"]))
    body["candidate_digest"] = digest(canonical(body))
    return body


def plan_publication_head_change(candidate: Mapping[str, Any], current_head: Mapping[str, Any] | None) -> dict[str, Any]:
    """Describe an exact CAS/initial insert; never execute or grant a write."""
    if not isinstance(candidate, Mapping) or candidate.get("status") != "CANDIDATE_READY":
        raise CandidatePlanError("CANDIDATE_NOT_READY")
    target = {
        "trade_date": candidate["trade_date"],
        "model_namespace_id": candidate["model_namespace_id"],
    }
    if current_head is None:
        if int(candidate["revision"]) != 1:
            raise CandidatePlanError("INITIAL_PUBLICATION_REVISION_INVALID")
        return {
            "action": "INSERT_IF_ABSENT",
            "target": target,
            "expected_prior_head": None,
            "prior_session_state_head": candidate.get("prior_session_state_head"),
            "initial_boundary_review_required": candidate.get("prior_session_state_head") is None,
            "write_executed": False,
        }
    if current_head.get("trade_date") != candidate["trade_date"] or current_head.get("model_namespace_id") != candidate["model_namespace_id"]:
        raise CandidatePlanError("HEAD_SELECTOR_MISMATCH")
    current_identity = (current_head.get("publication_id"), int(current_head.get("revision", 0)))
    candidate_identity = (candidate.get("publication_id"), int(candidate.get("revision", 0)))
    if current_identity == candidate_identity:
        if current_head.get("source_manifest_sha256") != candidate.get("source_manifest_sha256") or current_head.get("computation_identity_sha256") != candidate.get("computation_identity_sha256"):
            raise CandidatePlanError("PUBLICATION_IDENTITY_CONFLICT")
        if current_head.get("module_results_digest") != candidate.get("module_results_digest"):
            raise CandidatePlanError("IDEMPOTENT_IDENTITY_UNVERIFIED")
        return {
            "action": "IDEMPOTENT_REPLAY",
            "target": target,
            "expected_prior_head": current_head,
            "write_executed": False,
        }
    if int(candidate["revision"]) != current_identity[1] + 1:
        raise CandidatePlanError("PUBLICATION_REVISION_NOT_NEXT")
    prior = candidate.get("prior_publication")
    if prior != {"publication_id": current_identity[0], "revision": current_identity[1]}:
        raise CandidatePlanError("HEAD_CAS_PRECONDITION_MISMATCH")
    return {
        "action": "CAS_UPDATE",
        "target": target,
        "expected_prior_head": {"publication_id": current_identity[0], "revision": current_identity[1]},
        "write_executed": False,
    }
