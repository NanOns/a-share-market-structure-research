"""Pure planning for the final-schema V4 publication identity.

This module never connects to PostgreSQL, inserts DML, or changes a Head.
Database identity is the opaque ``publication_id``; ``revision_no`` is only the
lineage sequence and is never used as a foreign-key component.
"""
from datetime import date, datetime
import re
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from workbench_service.current_v4_context import canonical, digest
from .v4_publication_contract import (
    CONTRACT_ID as MODULE_CONTRACT_ID, MINIMUM_DAILY_PUBLICATION_CONTRACT_ID,
    OWNER_FAMILIES, required_module_keys, supported_owner_keys,
)
from .v4_source_manifest import (
    CONTRACT_ID as SOURCE_MANIFEST_CONTRACT_ID,
    build_source_manifest,
    CONTRACT_ID_R3 as SOURCE_MANIFEST_CONTRACT_ID_R3,
    build_source_manifest_r3,
)


CONTRACT_ID = "V4_PG_PUBLICATION_CANDIDATE_PLAN_R2"
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_MODULE = re.compile(r"^[a-z][a-z0-9_]{0,47}$")
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
_SOURCE_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
R3_SOURCE_EFFECTIVE_DATE = date(2026, 10, 16)


class CandidatePlanError(ValueError):
    pass


def _valid_date(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            parsed = date.fromisoformat(value)
            if parsed.isoformat() != value:
                raise ValueError("noncanonical")
            return parsed.isoformat()
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
    source_manifest_sha256: str | None = None,
    source_manifest_rows: Sequence[Mapping[str, Any]] | None = None,
    source_manifest_contract_id: str,
    computation_identity_sha256: str,
    expected_source_bindings: Mapping[str, Any],
    observed_source_bindings: Mapping[str, Any],
    database_identity: Mapping[str, Any],
    module_results: Sequence[Mapping[str, Any]],
    state_head_id: str,
    state_logical_digest: str,
    same_day_revision_parent_id: str | None = None,
    prior_session_publication_id: str | None = None,
    prior_session_state_head: str | None = None,
    prior_session_state_logical_digest: str | None = None,
    prior_session_gap_reason: str | None = None,
    verified_core_result: Any = None,
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
    core_result = None
    if verified_core_result is not None:
        from .v4_daily_core_result_r6 import is_verified_daily_core_result
        if (not is_verified_daily_core_result(verified_core_result)
                or verified_core_result.status != "PG_READBACK_VERIFIED"
                or verified_core_result.publishable is not True
                or verified_core_result.completeness_status != "PASS"
                or verified_core_result.completeness_contract_id != "V4_DAILY_COMPLETENESS_R1"
                or verified_core_result.completeness_contract_version != "1.0.0"
                or date.fromisoformat(target_date) >= R3_SOURCE_EFFECTIVE_DATE
                   and (verified_core_result.universe_completeness_status != "PASS"
                        or verified_core_result.universe_contract_id != "V4_MARKET_UNIVERSE_COMPLETENESS_R1"
                        or not _DIGEST.fullmatch(str(verified_core_result.universe_sha256 or "")))
                or verified_core_result.publication_id != publication_id
                or verified_core_result.publication_revision != revision_no
                or verified_core_result.trade_date != target_date
                or verified_core_result.source_manifest_sha256 != source_manifest_sha256):
            raise CandidatePlanError("CORE_RESULT_PG_READBACK_REQUIRED")
        core_result = verified_core_result
    if source_manifest_contract_id not in {SOURCE_MANIFEST_CONTRACT_ID, SOURCE_MANIFEST_CONTRACT_ID_R3}:
        raise CandidatePlanError("SOURCE_MANIFEST_CONTRACT_UNSUPPORTED")
    if date.fromisoformat(target_date) >= R3_SOURCE_EFFECTIVE_DATE and source_manifest_contract_id != SOURCE_MANIFEST_CONTRACT_ID_R3:
        raise CandidatePlanError("NEW_PUBLICATION_REQUIRES_R3_SOURCE_MANIFEST")
    if not source_manifest_rows:
        raise CandidatePlanError("CANDIDATE_SOURCE_MANIFEST_UNVERIFIED")
    try:
        produced_manifest = (build_source_manifest_r3(source_manifest_rows)
                             if source_manifest_contract_id == SOURCE_MANIFEST_CONTRACT_ID_R3
                             else build_source_manifest(source_manifest_rows))
        normalized_source_rows = produced_manifest["source_rows"]
        calculated_source_manifest = produced_manifest["source_manifest_sha256"]
    except Exception as exc:
        raise CandidatePlanError("CANDIDATE_SOURCE_MANIFEST_UNVERIFIED") from exc
    if source_manifest_sha256 is not None and not _DIGEST.fullmatch(str(source_manifest_sha256)):
        raise CandidatePlanError("SOURCE_MANIFEST_DIGEST_INVALID")
    if source_manifest_sha256 is not None and calculated_source_manifest != str(source_manifest_sha256).lower():
        raise CandidatePlanError("SOURCE_MANIFEST_DIGEST_MISMATCH")
    source_manifest_sha256 = calculated_source_manifest
    # The canonical publication relation binds these rows to the identical source
    # revision IDs and package digests. Never let either caller map be the only
    # source of truth for a candidate manifest.
    source_row_bindings = {
        row["source_key"]: {
            "source_revision_id": row["source_revision_id"],
            "digest": row["digest"],
        }
        for row in normalized_source_rows
    }
    if not _DIGEST.fullmatch(str(computation_identity_sha256)):
        raise CandidatePlanError("COMPUTATION_IDENTITY_DIGEST_INVALID")
    if not isinstance(state_head_id, str) or not state_head_id.strip() or not _DIGEST.fullmatch(str(state_logical_digest)):
        raise CandidatePlanError("PUBLICATION_STATE_IDENTITY_INVALID")
    if (not isinstance(database_identity, Mapping)
            or not {"database", "database_oid", "host", "port"}.issubset(database_identity)
            or not isinstance(database_identity.get("database"), str) or not database_identity["database"].strip()
            or isinstance(database_identity.get("database_oid"), bool) or not isinstance(database_identity["database_oid"], int)
            or not isinstance(database_identity.get("host"), str) or not database_identity["host"].strip()
            or isinstance(database_identity.get("port"), bool) or not isinstance(database_identity["port"], int)):
        raise CandidatePlanError("PUBLICATION_DATABASE_IDENTITY_INVALID")
    candidate_database_identity = dict(database_identity)
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
    if source_bindings != dict(sorted(source_row_bindings.items())):
        raise CandidatePlanError("SOURCE_MANIFEST_BINDING_MISMATCH")
    for row in normalized_source_rows:
        if row["source_package_target_trade_date"] != target_date:
            raise CandidatePlanError("SOURCE_PACKAGE_T0_MISMATCH")
        package_observed_at = row["source_package_page_observed_at"]
        if package_observed_at is None:
            raise CandidatePlanError("SOURCE_PACKAGE_OBSERVATION_CLOCK_MISSING")
        try:
            package_observed_date = datetime.fromisoformat(
                package_observed_at.replace("Z", "+00:00")
            ).astimezone(ZoneInfo("Asia/Shanghai")).date()
        except (TypeError, ValueError) as exc:
            raise CandidatePlanError("SOURCE_PACKAGE_OBSERVATION_CLOCK_INVALID") from exc
        if package_observed_date < date.fromisoformat(target_date):
            raise CandidatePlanError("FUTURE_TRADE_DATE_WITHOUT_SAME_DAY_SOURCE_OBSERVATION")
        if row["digest"] != row["revision_digest"]:
            raise CandidatePlanError("SOURCE_MANIFEST_REVISION_DIGEST_MISMATCH")
        if row["tombstone"]:
            raise CandidatePlanError("SOURCE_MANIFEST_TOMBSTONED")
        if row["effective_from"] is not None and row["effective_from"] > target_date:
            raise CandidatePlanError("SOURCE_MANIFEST_OUTSIDE_T0_WINDOW")
        if row["effective_to"] is not None and row["effective_to"] < target_date:
            raise CandidatePlanError("SOURCE_MANIFEST_OUTSIDE_T0_WINDOW")
        if any(row[clock] is None for clock in ("observed_at", "ingested_at", "system_available_at")):
            raise CandidatePlanError("SOURCE_MANIFEST_CLOCK_MISSING")
        observed_at, ingested_at, system_available_at = (
            row["observed_at"], row["ingested_at"], row["system_available_at"]
        )
        if system_available_at < max(observed_at, ingested_at):
            raise CandidatePlanError("SOURCE_MANIFEST_CLOCK_ORDER_INVALID")

    normalized = {}
    for raw in module_results:
        if not isinstance(raw, Mapping):
            raise CandidatePlanError("MODULE_RESULT_INVALID")
        module = raw.get("module_key")
        if not isinstance(module, str) or not _MODULE.fullmatch(module):
            raise CandidatePlanError("INVALID_MODULE_KEY")
        if module in normalized:
            raise CandidatePlanError("DUPLICATE_MODULE_RESULT")
        if module not in supported_owner_keys():
            raise CandidatePlanError("MODULE_NOT_IN_EFFECTIVE_CONTRACT")
        if raw.get("module_contract_id") != MODULE_CONTRACT_ID:
            raise CandidatePlanError("MODULE_CONTRACT_ID_MISMATCH")
        schema, relation = raw.get("owner_schema"), raw.get("owner_relation")
        if not isinstance(schema, str) or not _IDENTIFIER.fullmatch(schema) or not isinstance(relation, str) or not _IDENTIFIER.fullmatch(relation):
            raise CandidatePlanError("INVALID_OWNER_LOCATOR")
        token, contract = raw.get("owner_version_token"), raw.get("owner_contract_id")
        if not isinstance(token, str) or not token.strip() or not isinstance(contract, str) or not contract.strip():
            raise CandidatePlanError("OWNER_IDENTITY_INCOMPLETE")
        owner_family = OWNER_FAMILIES[module]
        if contract != owner_family["owner_contract_id"] or relation != owner_family["relation"]:
            raise CandidatePlanError("OWNER_FAMILY_CONTRACT_MISMATCH")
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
        owner_database_identity = raw.get("database_identity")
        if not isinstance(owner_database_identity, Mapping) or not {"database", "database_oid", "host", "port"}.issubset(owner_database_identity):
            raise CandidatePlanError("OWNER_DATABASE_IDENTITY_MISSING")
        if dict(owner_database_identity) != candidate_database_identity:
            raise CandidatePlanError("OWNER_DATABASE_IDENTITY_MISMATCH")
        normalized[module] = {
            "module_key": module, "module_contract_id": MODULE_CONTRACT_ID,
            "database_identity": candidate_database_identity, "owner_schema": schema,
            "owner_relation": relation, "owner_version_token": token,
            "owner_trade_date": owner_date, "owner_contract_id": contract,
            "result_digest": result_digest, "row_count": count,
            "quality_status": quality, "as_recorded": recorded, "pit_eligible": pit,
        }

    required = set(required_module_keys())
    missing_required = sorted(required - set(normalized))
    extras = sorted(set(normalized) - set(supported_owner_keys()))
    if extras:
        raise CandidatePlanError("MODULE_NOT_IN_EFFECTIVE_CONTRACT")
    status = "METADATA_CANDIDATE_INCOMPLETE" if missing_required else "METADATA_CANDIDATE_READY"
    readiness_reasons = ["REQUIRED_MODULE_RESULT_MISSING"] if missing_required else []
    publishable = core_result is not None
    body = {
        "contract_id": CONTRACT_ID,
        "module_contract_id": MODULE_CONTRACT_ID,
        "candidate_only": True,
        "publish_status": "PUBLISHABLE_BUSINESS_SNAPSHOT" if publishable else "BLOCKED_BUSINESS_PUBLISHABILITY",
        "metadata_readiness_status": "SOURCE_AND_IDENTITY_VALIDATED" if not missing_required else "INCOMPLETE",
        # Metadata-only candidates stay blocked. A verified typed readback can
        # bind the actual Core result after PG source/PIT and completeness checks.
        "business_publishability_status": "PUBLISHABLE_BUSINESS_SNAPSHOT" if publishable else "BLOCKED_CORE_RESULT_NOT_BOUND",
        "business_publishability_reasons": [] if publishable else ["NO_VERIFIED_CURRENT_DAILY_CORE_RESULT_BINDING"],
        "core_result_binding": ({
            "contract_id": core_result.contract_id,
            "result_identity": core_result.result_identity,
            "result_sha256": core_result.result_sha256,
            "readback_receipt_sha256": core_result.readback_receipt_sha256,
            "row_count": core_result.row_count,
            "completeness_status": core_result.completeness_status,
            "completeness_contract_id": core_result.completeness_contract_id,
            "completeness_contract_version": core_result.completeness_contract_version,
            "source_manifest_sha256": core_result.source_manifest_sha256,
            "status": core_result.status,
        } if publishable else None),
        "accepted_at": None,
        "head_update": "PLAN_ONLY_NOT_EXECUTED",
        "minimum_publish_contract_id": MINIMUM_DAILY_PUBLICATION_CONTRACT_ID,
        "minimum_publish_checks": {
            "publication_identity": "PASS",
            "single_target_database_identity": "PASS",
            "state_head_identity": "PASS",
            "computation_identity_digest": "PASS",
            "source_manifest_rows_and_digest": "PASS",
            "source_revision_digest_t0_tombstone_and_clock_rules": "PASS",
            "accepted_source_package_binding": "PASS",
            "core_business_result_binding": "PASS_PG_TYPED_READBACK" if publishable else "BLOCKED_NO_VERIFIED_CURRENT_DAILY_PRODUCER",
            "optional_owner_families": "NOT_REQUIRED_BY_CONTRACT",
            "pg_candidate_readback_and_head_write": "READY_FOR_EXPLICIT_HEAD_PLAN" if publishable else "BLOCKED_UNTIL_BUSINESS_PUBLISHABLE",
        },
        "global_requiredness_status": ("PASS_PUBLISHABLE_BUSINESS_SNAPSHOT" if publishable else "PASS_METADATA_IDENTITY_ONLY") if not missing_required else "FAIL_REQUIRED_OWNER_MISSING",
        "publication_id": publication_id,
        "trade_date": target_date,
        "revision_no": revision_no,
        "publication_lineage_id": publication_lineage_id,
        "same_day_revision_parent_id": same_day_revision_parent_id,
        "model_namespace_id": model_namespace_id,
        "database_identity": candidate_database_identity,
        "core_revision": core_revision,
        "source_manifest_sha256": source_manifest_sha256,
        "source_manifest_contract_id": source_manifest_contract_id,
        "source_manifest_rows": normalized_source_rows,
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
        "reasons": readiness_reasons,
    }
    body["module_results_digest"] = digest(canonical(body["module_results"]))
    body["candidate_digest"] = digest(canonical(body))
    return body


def plan_publication_head_change(
    candidate: Mapping[str, Any], current_head: Mapping[str, Any] | None, *,
    verified_core_result: Any = None,
) -> dict[str, Any]:
    """Describe exact publication-id CAS; never execute or grant a write."""
    if not isinstance(candidate, Mapping):
        raise CandidatePlanError("CANDIDATE_NOT_READY")
    supplied_digest = candidate.get("candidate_digest")
    integrity_body = dict(candidate)
    integrity_body.pop("candidate_digest", None)
    if not _DIGEST.fullmatch(str(supplied_digest or "")) or digest(canonical(integrity_body)) != supplied_digest:
        raise CandidatePlanError("CANDIDATE_DIGEST_MISMATCH")
    if (not isinstance(candidate, Mapping) or candidate.get("status") != "METADATA_CANDIDATE_READY"
            or candidate.get("metadata_readiness_status") != "SOURCE_AND_IDENTITY_VALIDATED"
            or candidate.get("business_publishability_status") != "PUBLISHABLE_BUSINESS_SNAPSHOT"
            or candidate.get("global_requiredness_status") != "PASS_PUBLISHABLE_BUSINESS_SNAPSHOT"
            or candidate.get("minimum_publish_contract_id") != MINIMUM_DAILY_PUBLICATION_CONTRACT_ID
            or not candidate.get("source_manifest_sha256")):
        raise CandidatePlanError("CANDIDATE_NOT_READY")
    from .v4_daily_core_result_r6 import is_verified_daily_core_result
    core_result = verified_core_result
    if (not is_verified_daily_core_result(core_result)
            or core_result.status != "PG_READBACK_VERIFIED"
            or core_result.publishable is not True
            or core_result.completeness_status != "PASS"
            or core_result.completeness_contract_id != "V4_DAILY_COMPLETENESS_R1"
            or core_result.completeness_contract_version != "1.0.0"
            or date.fromisoformat(str(candidate.get("trade_date"))) >= R3_SOURCE_EFFECTIVE_DATE
               and (core_result.universe_completeness_status != "PASS"
                    or core_result.universe_contract_id != "V4_MARKET_UNIVERSE_COMPLETENESS_R1"
                    or not _DIGEST.fullmatch(str(core_result.universe_sha256 or "")))
            or core_result.contract_id != "V4_DAILY_CORE_RESULT_BINDING_R6"
            or core_result.publication_id != candidate.get("publication_id")
            or core_result.publication_revision != candidate.get("revision_no")
            or core_result.trade_date != candidate.get("trade_date")
            or core_result.source_manifest_sha256 != candidate.get("source_manifest_sha256")
            or not isinstance(candidate.get("core_result_binding"), Mapping)
            or candidate["core_result_binding"].get("result_identity") != core_result.result_identity
            or candidate["core_result_binding"].get("result_sha256") != core_result.result_sha256
            or candidate["core_result_binding"].get("readback_receipt_sha256") != core_result.readback_receipt_sha256
            or candidate["core_result_binding"].get("completeness_status") != core_result.completeness_status
            or candidate["core_result_binding"].get("completeness_contract_id") != core_result.completeness_contract_id
            or candidate["core_result_binding"].get("completeness_contract_version") != core_result.completeness_contract_version
            or not _DIGEST.fullmatch(str(core_result.result_sha256))
            or not _DIGEST.fullmatch(str(core_result.readback_receipt_sha256))
            or isinstance(core_result.row_count, bool)
            or not isinstance(core_result.row_count, int) or core_result.row_count <= 0):
        raise CandidatePlanError("CORE_RESULT_PG_READBACK_REQUIRED")
    target = {"trade_date": candidate["trade_date"], "model_namespace_id": candidate["model_namespace_id"]}
    def sealed_plan(body):
        body["core_result_readback_receipt_sha256"] = core_result.readback_receipt_sha256
        body["plan_receipt_sha256"] = digest(canonical(body))
        return body
    if current_head is None:
        if int(candidate["revision_no"]) != 1 or candidate.get("same_day_revision_parent_id") is not None:
            raise CandidatePlanError("INITIAL_PUBLICATION_IDENTITY_INVALID")
        return sealed_plan({
            "action": "INSERT_IF_ABSENT", "target": target,
            "expected_prior_head": None,
            "prior_session_publication_id": candidate.get("prior_session_publication_id"),
            "prior_session_state_head": candidate.get("prior_session_state_head"),
            "prior_session_state_logical_digest": candidate.get("prior_session_state_logical_digest"),
            "initial_boundary_review_required": candidate.get("prior_session_publication_id") is None,
            "write_executed": False,
        })
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
        return sealed_plan({"action": "IDEMPOTENT_REPLAY", "target": target, "expected_prior_head": dict(current_head), "write_executed": False})
    if int(candidate["revision_no"]) != current_revision + 1:
        raise CandidatePlanError("PUBLICATION_REVISION_NOT_NEXT")
    if candidate.get("same_day_revision_parent_id") != current_id:
        raise CandidatePlanError("HEAD_CAS_PRECONDITION_MISMATCH")
    return sealed_plan({
        "action": "CAS_UPDATE", "target": target,
        "expected_prior_head": {
            "publication_id": current_id,
            "revision_no": current_revision,
            "state_head_id": current_state_head,
            "state_logical_digest": current_state_digest,
        },
        "write_executed": False,
    })
