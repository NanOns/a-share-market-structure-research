"""R6 contract for binding an existing daily producer result to a publication.

The module validates and stores rows supplied by the existing V4 producer; it
does not calculate prices, moving averages, profiles, or signals. R6 deliberately
keeps publishability blocked unless the versioned completeness rules pass,
independent source/PIT proof is rebuilt from PG, and the typed readback verifies.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from dataclasses import dataclass, field
import hashlib
import json
import math
import re
from typing import Any, Mapping, Sequence


CONTRACT_ID = "V4_DAILY_CORE_RESULT_BINDING_R6"
CONTRACT_VERSION = "1.0.0"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MAX_ROWS = 20_000
R3_SOURCE_EFFECTIVE_DATE = date(2026, 10, 16)
_PRICE_FIELDS = ("open", "high", "low", "close", "volume", "amount", "turnover_rate")
_PROFILE_FIELDS = ("ma5", "ma20", "ma60")
DAILY_COMPLETENESS_CONTRACT = {
    "contract_id": "V4_DAILY_COMPLETENESS_R1",
    "version": "1.0.0",
    "minimum_rows": 1,
    "maximum_missing_close_rows": 0,
    "require_trading_ohlc": True,
    "require_unique_security_ids": True,
    "require_source_revision_binding": True,
    "require_independent_source_pit_proof": True,
}


class CoreResultError(ValueError):
    pass


_PG_READBACK_PROOF = object()


@dataclass(frozen=True)
class VerifiedDailyCoreResult:
    """Typed evidence emitted only after the full PostgreSQL readback check.

    This object deliberately is not a Mapping: a caller cannot make a dict that
    happens to contain ``status=PG_READBACK_VERIFIED`` and pass the Head planner.
    The private proof identity is also checked by the planner-facing validator.
    """

    contract_id: str
    publication_id: str
    publication_revision: int
    trade_date: str
    source_manifest_sha256: str
    result_identity: str
    result_sha256: str
    producer_receipt_sha256: str
    readback_receipt_sha256: str
    completeness_contract_id: str
    completeness_contract_version: str
    row_count: int
    missing_price_rows: int
    completeness_status: str
    observed_completeness_status: str
    universe_completeness_status: str
    universe_contract_id: str
    universe_sha256: str | None
    universe_reconciliation_count: int
    universe_readback_receipt_sha256: str | None
    quality_status: str
    status: str
    publishable: bool
    _proof: object = field(repr=False, compare=False)


def is_verified_daily_core_result(value: Any) -> bool:
    """Return whether value is a sealed result produced by this module's PG reader."""
    if not isinstance(value, VerifiedDailyCoreResult) or value._proof is not _PG_READBACK_PROOF:
        return False
    try:
        return _sha(_verified_result_receipt_material(value)) == value.readback_receipt_sha256
    except (TypeError, ValueError, AttributeError):
        return False


def _verified_result_receipt_material(value: VerifiedDailyCoreResult) -> dict[str, Any]:
    """All verified fields, especially every field consumed by Head planning."""
    return {
        "contract_id": value.contract_id,
        "publication_id": value.publication_id,
        "publication_revision": value.publication_revision,
        "trade_date": value.trade_date,
        "source_manifest_sha256": value.source_manifest_sha256,
        "result_identity": value.result_identity,
        "result_sha256": value.result_sha256,
        "producer_receipt_sha256": value.producer_receipt_sha256,
        "completeness_contract_id": value.completeness_contract_id,
        "completeness_contract_version": value.completeness_contract_version,
        "row_count": value.row_count,
        "missing_price_rows": value.missing_price_rows,
        "completeness_status": value.completeness_status,
        "observed_completeness_status": value.observed_completeness_status,
        "universe_completeness_status": value.universe_completeness_status,
        "universe_contract_id": value.universe_contract_id,
        "universe_sha256": value.universe_sha256,
        "universe_reconciliation_count": value.universe_reconciliation_count,
        "universe_readback_receipt_sha256": value.universe_readback_receipt_sha256,
        "quality_status": value.quality_status,
        "status": value.status,
        "publishable": value.publishable,
    }


def _read_consumed_source_proofs(pg: Any, *, publication_id: str, publication_revision: int,
                                 target: str, source_manifest_sha256: str,
                                 core_source_revision_ids: set[str],
                                 allow_candidate: bool = False,
                                 candidate_cutoff: datetime | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Rebuild the publication manifest and exact TDX artifact bindings from PG.

    This intentionally INNER JOINs the independent package fact relation. A
    trigger-created core row or consumed-source row alone is not proof of the
    underlying source artifact.
    """
    query = """SELECT p.trade_date,p.source_manifest_contract_id,p.source_manifest_sha256,
                      cs.source_key,cs.source_revision_id,cs.digest,
                      sr.logical_fact_id,sr.revision_no,sr.digest,sr.effective_from,sr.effective_to,
                      sr.provider_available_at,sr.observed_at,sr.ingested_at,sr.system_available_at,
                      sr.tombstone,sr.source_package_id,sr.source_package_source_key,sr.source_fact_digest,
                      sp.package_id,sp.contract_version,sp.package_sha256,sp.page_observed_at,
                      sp.target_trade_date,sp.parser_version,sp.accepted_scope,sp.manifest,
                      f.package_id,f.source_key,f.logical_fact_id,f.fact_digest,f.source_fact_sha256,
                      f.record_locator,f.record_count,f.acceptance_receipt_id,p.status,p.accepted_at
                 FROM v4.publications p
                 JOIN v4.publication_consumed_sources cs ON cs.publication_id=p.publication_id
                 JOIN v4.source_revisions sr ON sr.source_revision_id=cs.source_revision_id
                 JOIN v4.source_packages sp ON sp.package_id=sr.source_package_id
                 JOIN v4.source_package_facts f
                   ON f.package_id=sr.source_package_id
                  AND f.source_key=sr.source_package_source_key
                  AND f.logical_fact_id=sr.logical_fact_id
                  AND f.fact_digest=sr.source_fact_digest
                WHERE p.publication_id=%s AND p.revision_no=%s
                ORDER BY convert_to(cs.source_key,'UTF8')"""
    try:
        raw_rows = pg.execute(query, (publication_id, publication_revision)).fetchall()
    except Exception as exc:
        raise CoreResultError("CORE_RESULT_INDEPENDENT_SOURCE_PROOF_UNAVAILABLE") from exc
    if not raw_rows:
        raise CoreResultError("CORE_RESULT_INDEPENDENT_SOURCE_PROOF_MISSING")
    columns = (
        "publication_trade_date", "source_manifest_contract_id", "publication_manifest_sha256",
        "source_key", "source_revision_id", "consumed_digest", "logical_fact_id", "revision_no",
        "revision_digest", "effective_from", "effective_to", "provider_available_at", "observed_at",
        "ingested_at", "system_available_at", "tombstone", "revision_package_id",
        "revision_package_source_key", "revision_source_fact_digest", "source_package_id",
        "source_package_contract_version", "source_package_sha256", "source_package_page_observed_at",
        "source_package_target_trade_date", "source_package_parser_version", "source_package_accepted_scope",
        "source_package_manifest", "fact_package_id", "fact_source_key", "fact_logical_fact_id",
        "fact_digest", "source_fact_sha256", "record_locator", "fact_record_count", "acceptance_receipt_id",
        "publication_status", "publication_accepted_at",
    )
    try:
        from .v4_source_manifest import (
            CONTRACT_ID as SOURCE_MANIFEST_CONTRACT_ID,
            CONTRACT_ID_R3 as SOURCE_MANIFEST_CONTRACT_ID_R3,
            build_source_manifest, build_source_manifest_r3,
        )
        proof_rows = [dict(zip(columns, row)) for row in raw_rows]
        seen_source_keys = set()
        manifest_rows = []
        tdx_bindings = []
        observed_trade_date = None
        for proof in proof_rows:
            if proof["publication_trade_date"].isoformat() != target:
                raise CoreResultError("CORE_RESULT_CONSUMED_SOURCE_T0_MISMATCH")
            if (proof["source_manifest_contract_id"] not in {SOURCE_MANIFEST_CONTRACT_ID, SOURCE_MANIFEST_CONTRACT_ID_R3}
                    or str(proof["publication_manifest_sha256"]).strip() != source_manifest_sha256):
                raise CoreResultError("CORE_RESULT_CONSUMED_SOURCE_MANIFEST_IDENTITY_MISMATCH")
            observed_trade_date = proof["publication_trade_date"].isoformat()
            accepted_at = proof["publication_accepted_at"]
            if proof["publication_status"] == "ACCEPTED":
                if not isinstance(accepted_at, datetime) or accepted_at.tzinfo is None:
                    raise CoreResultError("CORE_RESULT_PUBLICATION_ACCEPTANCE_CUTOFF_INVALID")
            elif (allow_candidate and proof["publication_status"] == "CANDIDATE"
                  and accepted_at is None and isinstance(candidate_cutoff, datetime)
                  and candidate_cutoff.tzinfo is not None):
                # Use a server timestamp before candidate insertion. Any later
                # ACCEPTED timestamp is necessarily no earlier than this cutoff.
                accepted_at = candidate_cutoff
            else:
                raise CoreResultError("CORE_RESULT_PUBLICATION_ACCEPTANCE_CUTOFF_INVALID")
            accepted_at = accepted_at.astimezone(timezone.utc)
            key = proof["source_key"]
            if key in seen_source_keys:
                raise CoreResultError("CORE_RESULT_CONSUMED_SOURCE_KEY_DUPLICATE")
            seen_source_keys.add(key)
            if not isinstance(proof["source_revision_id"], str) or not proof["source_revision_id"].strip():
                raise CoreResultError("CORE_RESULT_CONSUMED_SOURCE_REVISION_INVALID")
            if (proof["source_package_id"] != proof["revision_package_id"]
                    or proof["source_package_id"] != proof["fact_package_id"]
                    or proof["source_key"] != proof["revision_package_source_key"]
                    or proof["source_key"] != proof["fact_source_key"]
                    or proof["logical_fact_id"] != proof["fact_logical_fact_id"]
                    or str(proof["consumed_digest"]).strip() != str(proof["revision_digest"]).strip()
                    or str(proof["revision_digest"]).strip() != str(proof["fact_digest"]).strip()
                    or str(proof["revision_source_fact_digest"]).strip() != str(proof["fact_digest"]).strip()
                    or proof["source_package_accepted_scope"] != "ACCEPTED_SOURCE_PACKAGE"
                    or proof["source_package_target_trade_date"].isoformat() != target
                    or not isinstance(proof["acceptance_receipt_id"], str)
                    or not proof["acceptance_receipt_id"].strip()
                    or proof["tombstone"] is True
                    or proof["effective_from"] is not None and proof["effective_from"].isoformat() > target
                    or proof["effective_to"] is not None and proof["effective_to"].isoformat() < target):
                raise CoreResultError("CORE_RESULT_CONSUMED_SOURCE_ARTIFACT_MISMATCH")
            if proof["source_package_manifest"] is None:
                raise CoreResultError("CORE_RESULT_SOURCE_PACKAGE_MANIFEST_MISSING")
            package_manifest = proof["source_package_manifest"]
            is_manifest_r3 = proof["source_manifest_contract_id"] == SOURCE_MANIFEST_CONTRACT_ID_R3
            if (proof["publication_trade_date"] >= R3_SOURCE_EFFECTIVE_DATE
                    and not is_manifest_r3):
                raise CoreResultError("CORE_RESULT_NEW_PUBLICATION_REQUIRES_R3_MANIFEST")
            has_acceptance_proof_fields = any(
                name in package_manifest for name in ("acceptance_receipt_id", "AS_RECORDED", "PIT_ELIGIBLE")
            )
            if (is_manifest_r3 or has_acceptance_proof_fields) and (
                    package_manifest.get("acceptance_receipt_id") != proof["acceptance_receipt_id"]
                    or package_manifest.get("AS_RECORDED") is not True
                    or package_manifest.get("PIT_ELIGIBLE") is not True):
                raise CoreResultError("CORE_RESULT_SOURCE_ACCEPTANCE_PROOF_INVALID")
            if is_manifest_r3:
                from .v4_daily_source_ingest_r6 import verify_source_package_manifest_authority
                try:
                    verify_source_package_manifest_authority(package_manifest)
                except ValueError as exc:
                    raise CoreResultError("CORE_RESULT_SOURCE_ACCEPTANCE_SIGNATURE_INVALID") from exc
            cutoff_clocks = {
                "source_package_page_observed_at": proof["source_package_page_observed_at"],
                "observed_at": proof["observed_at"],
                "ingested_at": proof["ingested_at"],
                "system_available_at": proof["system_available_at"],
            }
            if proof["provider_available_at"] is not None:
                cutoff_clocks["provider_available_at"] = proof["provider_available_at"]
            for clock_name, clock_value in cutoff_clocks.items():
                if (not isinstance(clock_value, datetime) or clock_value.tzinfo is None
                        or clock_value.astimezone(timezone.utc) > accepted_at):
                    raise CoreResultError("CORE_RESULT_SOURCE_AFTER_PUBLICATION_ACCEPTANCE:" + clock_name)
            package_bindings = package_manifest.get("source_fact_bindings")
            expected_fact = {
                "source_key": key, "logical_fact_id": proof["logical_fact_id"],
                "fact_digest": str(proof["fact_digest"]).strip(),
                "source_fact_sha256": str(proof["source_fact_sha256"]).strip(),
                "record_locator": proof["record_locator"],
            }
            if is_manifest_r3:
                expected_fact["acceptance_receipt_id"] = proof["acceptance_receipt_id"]
            is_core_tdx_fact = key == "tdx" and proof["source_revision_id"] in core_source_revision_ids
            if is_core_tdx_fact:
                if (isinstance(proof["fact_record_count"], bool)
                        or not isinstance(proof["fact_record_count"], int)
                        or proof["fact_record_count"] <= 0):
                    raise CoreResultError("CORE_RESULT_SOURCE_PACKAGE_RECORD_COUNT_MISSING")
                expected_fact["record_count"] = proof["fact_record_count"]
            if (not isinstance(package_bindings, list) or not any(
                    isinstance(item, Mapping) and all(item.get(name) == value for name, value in expected_fact.items())
                    for item in package_bindings)):
                raise CoreResultError("CORE_RESULT_SOURCE_PACKAGE_MANIFEST_FACT_MISMATCH")
            manifest_rows.append({
                "source_key": key, "source_revision_id": proof["source_revision_id"],
                "digest": str(proof["consumed_digest"]).strip(),
                "logical_fact_id": proof["logical_fact_id"], "revision_no": int(proof["revision_no"]),
                "revision_digest": str(proof["revision_digest"]).strip(),
                "effective_from": proof["effective_from"], "effective_to": proof["effective_to"],
                "provider_available_at": proof["provider_available_at"], "observed_at": proof["observed_at"],
                "ingested_at": proof["ingested_at"], "system_available_at": proof["system_available_at"],
                "tombstone": proof["tombstone"], "source_package_id": proof["source_package_id"],
                "source_package_contract_version": proof["source_package_contract_version"],
                "source_package_sha256": str(proof["source_package_sha256"]).strip(),
                "source_package_page_observed_at": proof["source_package_page_observed_at"],
                "source_package_target_trade_date": proof["source_package_target_trade_date"],
                "source_package_parser_version": proof["source_package_parser_version"],
                "source_package_accepted_scope": proof["source_package_accepted_scope"],
            })
            if is_manifest_r3:
                acceptance_proof = package_manifest.get("acceptance_proof") or {}
                manifest_rows[-1].update({
                    "source_package_acceptance_receipt_id": proof["acceptance_receipt_id"],
                    "source_package_as_recorded": package_manifest.get("AS_RECORDED"),
                    "source_package_pit_eligible": package_manifest.get("PIT_ELIGIBLE"),
                    "source_package_acceptance_proof_sha256": acceptance_proof.get("receipt_sha256"),
                    "source_fact_digest": str(proof["fact_digest"]).strip(),
                    "source_fact_sha256": str(proof["source_fact_sha256"]).strip(),
                    "source_fact_record_locator": proof["record_locator"],
                    "source_fact_record_count": proof["fact_record_count"],
                    "source_fact_acceptance_receipt_id": proof["acceptance_receipt_id"],
                })
            if key == "tdx" and proof["source_revision_id"] in core_source_revision_ids:
                tdx_bindings.append({
                    "source_key": "tdx", "source_revision_id": proof["source_revision_id"],
                    "source_package_id": proof["source_package_id"],
                    "package_sha256": str(proof["source_package_sha256"]).strip(),
                    "logical_fact_id": proof["logical_fact_id"],
                    "fact_digest": str(proof["fact_digest"]).strip(),
                    "source_fact_sha256": str(proof["source_fact_sha256"]).strip(),
                    "acceptance_receipt_id": proof["acceptance_receipt_id"],
                    "record_count": proof["fact_record_count"],
                    "target_trade_date": target, "record_locator": proof["record_locator"],
                })
        if observed_trade_date != target:
            raise CoreResultError("CORE_RESULT_CONSUMED_SOURCE_T0_MISMATCH")
        rebuilt = (build_source_manifest_r3(manifest_rows)
                   if proof_rows[0]["source_manifest_contract_id"] == SOURCE_MANIFEST_CONTRACT_ID_R3
                   else build_source_manifest(manifest_rows))
        if rebuilt["source_manifest_sha256"] != source_manifest_sha256:
            raise CoreResultError("CORE_RESULT_CONSUMED_SOURCE_MANIFEST_DIGEST_MISMATCH")
        if not tdx_bindings or {item["source_revision_id"] for item in tdx_bindings} != core_source_revision_ids:
            raise CoreResultError("CORE_RESULT_ROW_SOURCE_NOT_IN_PUBLICATION_CONSUMED_SET")
        tdx_bindings.sort(key=lambda item: item["source_revision_id"].encode("utf-8"))
        return rebuilt["source_rows"], tdx_bindings
    except CoreResultError:
        raise
    except Exception as exc:
        raise CoreResultError("CORE_RESULT_INDEPENDENT_SOURCE_PROOF_INVALID") from exc


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _date(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if not isinstance(value, str):
        raise CoreResultError("CORE_RESULT_T0_INVALID")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise CoreResultError("CORE_RESULT_T0_INVALID") from exc
    if parsed.isoformat() != value:
        raise CoreResultError("CORE_RESULT_T0_NONCANONICAL")
    return value


def _number(value: Any, field: str, *, nullable: bool = True) -> float | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool):
        raise CoreResultError("CORE_RESULT_VALUE_INVALID:" + field)
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise CoreResultError("CORE_RESULT_VALUE_INVALID:" + field) from exc
    if not math.isfinite(number) or number < 0:
        raise CoreResultError("CORE_RESULT_VALUE_INVALID:" + field)
    return number


_ARTIFACT_BINDING_FIELDS = (
    "source_key", "source_revision_id", "source_package_id", "package_sha256",
    "logical_fact_id", "fact_digest", "source_fact_sha256", "acceptance_receipt_id",
    "target_trade_date", "record_locator", "record_count",
)


def _normalize_artifact_bindings(value: Any, target: str) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise CoreResultError("CORE_RESULT_SOURCE_ARTIFACT_BINDINGS_REQUIRED")
    normalized = []
    seen_revision_ids = set()
    for raw in value:
        if not isinstance(raw, Mapping) or set(raw) != set(_ARTIFACT_BINDING_FIELDS):
            raise CoreResultError("CORE_RESULT_SOURCE_ARTIFACT_BINDING_INVALID")
        item = dict(raw)
        for name in ("source_key", "source_revision_id", "source_package_id", "logical_fact_id", "acceptance_receipt_id"):
            if not isinstance(item[name], str) or not item[name].strip():
                raise CoreResultError("CORE_RESULT_SOURCE_ARTIFACT_BINDING_INVALID")
        if item["source_key"] != "tdx" or item["target_trade_date"] != target:
            raise CoreResultError("CORE_RESULT_SOURCE_ARTIFACT_BINDING_T0_OR_KEY_MISMATCH")
        if item["source_revision_id"] in seen_revision_ids:
            raise CoreResultError("CORE_RESULT_SOURCE_ARTIFACT_REVISION_DUPLICATE")
        seen_revision_ids.add(item["source_revision_id"])
        for name in ("package_sha256", "fact_digest", "source_fact_sha256"):
            if not isinstance(item[name], str) or not _SHA256.fullmatch(item[name]):
                raise CoreResultError("CORE_RESULT_SOURCE_ARTIFACT_DIGEST_INVALID")
        if not isinstance(item["record_locator"], Mapping) or not item["record_locator"]:
            raise CoreResultError("CORE_RESULT_SOURCE_ARTIFACT_LOCATOR_REQUIRED")
        if (isinstance(item["record_count"], bool) or not isinstance(item["record_count"], int)
                or item["record_count"] <= 0):
            raise CoreResultError("CORE_RESULT_SOURCE_ARTIFACT_RECORD_COUNT_INVALID")
        normalized.append(item)
    normalized.sort(key=lambda item: item["source_revision_id"].encode("utf-8"))
    return normalized


def _evaluate_completeness(rows: Sequence[Mapping[str, Any]], missing_price_rows: int,
                           source_bindings: Sequence[Mapping[str, Any]]) -> tuple[str, list[str]]:
    """Evaluate the frozen R1 rule against actual normalized producer rows."""
    reasons = []
    if not rows or len(rows) < DAILY_COMPLETENESS_CONTRACT["minimum_rows"]:
        reasons.append("CORE_ROWSET_EMPTY")
    if missing_price_rows > DAILY_COMPLETENESS_CONTRACT["maximum_missing_close_rows"]:
        reasons.append("CORE_CLOSE_MISSING")
    expected_row_count = sum(
        item.get("record_count", 0) for item in source_bindings
        if isinstance(item.get("record_count"), int) and not isinstance(item.get("record_count"), bool)
    )
    if (not source_bindings or any(isinstance(item.get("record_count"), bool)
                                   or not isinstance(item.get("record_count"), int)
                                   or item["record_count"] <= 0 for item in source_bindings)
            or len(rows) != expected_row_count):
        reasons.append("CORE_SOURCE_PACKAGE_RECORD_COUNT_MISMATCH")
    bound_ids = {item["source_revision_id"] for item in source_bindings}
    if not rows or any(row.get("source_revision_id") not in bound_ids for row in rows):
        reasons.append("CORE_SOURCE_REVISION_UNBOUND")
    if len({row.get("security_id") for row in rows}) != len(rows):
        reasons.append("CORE_SECURITY_ID_DUPLICATE")
    if any(row.get("trade_status") == "TRADING" and any(
            row.get(key) is None for key in ("open", "high", "low", "close")) for row in rows):
        reasons.append("CORE_TRADING_OHLC_INCOMPLETE")
    return ("PASS" if not reasons else "FAIL", reasons)


def build_daily_core_result_plan(
    *,
    publication_id: str,
    publication_revision: int,
    trade_date: str,
    source_manifest_sha256: str,
    producer_contract_id: str,
    producer_sha256: str,
    producer_receipt: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    completeness_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a deterministic plan from actual producer rows, never computed here."""
    target = _date(trade_date)
    if (not isinstance(publication_id, str) or not publication_id.strip()
            or isinstance(publication_revision, bool) or not isinstance(publication_revision, int)
            or publication_revision <= 0):
        raise CoreResultError("CORE_RESULT_PUBLICATION_IDENTITY_INVALID")
    if not _SHA256.fullmatch(str(source_manifest_sha256)) or not _SHA256.fullmatch(str(producer_sha256)):
        raise CoreResultError("CORE_RESULT_DIGEST_INVALID")
    if not isinstance(producer_contract_id, str) or not producer_contract_id.strip():
        raise CoreResultError("CORE_RESULT_PRODUCER_CONTRACT_REQUIRED")
    if not isinstance(producer_receipt, Mapping):
        raise CoreResultError("CORE_RESULT_PRODUCER_RECEIPT_REQUIRED")
    receipt = dict(producer_receipt)
    receipt_digest = receipt.pop("receipt_sha256", None)
    artifact_bindings = _normalize_artifact_bindings(receipt.get("source_artifact_bindings"), target)
    if artifact_bindings != receipt.get("source_artifact_bindings"):
        raise CoreResultError("CORE_RESULT_SOURCE_ARTIFACT_BINDING_ORDER_INVALID")
    receipt["source_artifact_bindings"] = artifact_bindings
    if set(receipt) != {
        "trade_date", "producer_contract_id", "producer_sha256", "publication_id",
        "publication_revision", "source_manifest_sha256", "source_artifact_bindings",
    }:
        raise CoreResultError("CORE_RESULT_PRODUCER_RECEIPT_FIELDS_INVALID")
    if (receipt_digest != _sha(receipt)
            or receipt.get("trade_date") != target
            or receipt.get("producer_contract_id") != producer_contract_id
            or receipt.get("producer_sha256") != producer_sha256
            or receipt.get("publication_id") != publication_id
            or receipt.get("publication_revision") != publication_revision
            or receipt.get("source_manifest_sha256") != source_manifest_sha256):
        raise CoreResultError("CORE_RESULT_PRODUCER_RECEIPT_BINDING_MISMATCH")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows or len(rows) > _MAX_ROWS:
        raise CoreResultError("CORE_RESULT_ROWS_EMPTY_OR_LIMIT_EXCEEDED")

    normalized = []
    seen = set()
    missing_price = 0
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise CoreResultError("CORE_RESULT_ROW_INVALID")
        security = str(raw.get("security_id") or "").strip().upper()
        if not security or security in seen or _date(raw.get("trade_date")) != target:
            raise CoreResultError("CORE_RESULT_ROW_IDENTITY_INVALID")
        seen.add(security)
        security_type = raw.get("security_type")
        if not isinstance(security_type, str) or security_type not in {"STOCK", "INDEX", "FUND", "UNKNOWN"}:
            raise CoreResultError("CORE_RESULT_SECURITY_TYPE_INVALID")
        trade_status = raw.get("trade_status")
        if trade_status not in {"TRADING", "SUSPENDED", "DELISTED", "UNKNOWN"}:
            raise CoreResultError("CORE_RESULT_TRADE_STATUS_INVALID")
        values = {field: _number(raw.get(field), field) for field in (*_PRICE_FIELDS, *_PROFILE_FIELDS)}
        if trade_status == "TRADING" and any(values[field] is None for field in ("open", "high", "low", "close")):
            raise CoreResultError("CORE_RESULT_TRADING_PRICE_MISSING")
        if (values["high"] is not None and any(values[field] is not None for field in ("open", "low", "close"))
                and values["high"] < max(values[field] for field in ("open", "low", "close") if values[field] is not None)):
            raise CoreResultError("CORE_RESULT_OHLC_RANGE_INVALID")
        if (values["low"] is not None and any(values[field] is not None for field in ("open", "high", "close"))
                and values["low"] > min(values[field] for field in ("open", "high", "close") if values[field] is not None)):
            raise CoreResultError("CORE_RESULT_OHLC_RANGE_INVALID")
        if values["close"] is None:
            missing_price += 1
        if raw.get("price_basis") != "TDX_GBBQ_UNCHANGED":
            raise CoreResultError("CORE_RESULT_PRICE_BASIS_UNSUPPORTED")
        turnover_status = raw.get("turnover_status")
        if turnover_status not in {"AVAILABLE", "TURNOVER_UNAVAILABLE"}:
            raise CoreResultError("CORE_RESULT_TURNOVER_STATUS_REQUIRED")
        if (turnover_status == "AVAILABLE") != (values["turnover_rate"] is not None):
            raise CoreResultError("CORE_RESULT_TURNOVER_STATUS_VALUE_MISMATCH")
        history_status = raw.get("history_status")
        if history_status not in {"SUFFICIENT", "INSUFFICIENT_NEW_LISTING_HISTORY", "HISTORY_UNKNOWN"}:
            raise CoreResultError("CORE_RESULT_HISTORY_STATUS_REQUIRED")
        source_revision_id = raw.get("source_revision_id")
        if not isinstance(source_revision_id, str) or not source_revision_id.strip():
            raise CoreResultError("CORE_RESULT_SOURCE_REVISION_MISSING")
        row = {
            "trade_date": target, "security_id": security, "security_type": security_type,
            "trade_status": trade_status, **values, "price_basis": "TDX_GBBQ_UNCHANGED",
            "turnover_status": turnover_status, "history_status": history_status,
            "source_revision_id": source_revision_id,
            "profile_payload": dict(raw.get("profile_payload") or {}),
            "quality_status": str(raw.get("quality_status") or "UNKNOWN"),
        }
        row["row_sha256"] = _sha(row)
        normalized.append(row)
    normalized.sort(key=lambda row: row["security_id"].encode("utf-8"))
    if not {row["source_revision_id"] for row in normalized}.issubset(
            {binding["source_revision_id"] for binding in artifact_bindings}):
        raise CoreResultError("CORE_RESULT_ROW_SOURCE_NOT_IN_PRODUCER_RECEIPT")

    if completeness_contract is None:
        completeness_contract_id = "UNRESOLVED"
        completeness_contract_version = "UNRESOLVED"
        completeness_status = "CONTRACT_UNRESOLVED"
        completeness_reasons = ["COMPLETENESS_CONTRACT_REQUIRED"]
        publishability = "BLOCKED_COMPLETENESS_CONTRACT_UNRESOLVED"
    else:
        if (not isinstance(completeness_contract, Mapping)
                or dict(completeness_contract) != DAILY_COMPLETENESS_CONTRACT):
            raise CoreResultError("CORE_RESULT_COMPLETENESS_CONTRACT_UNSUPPORTED")
        completeness_contract_id = DAILY_COMPLETENESS_CONTRACT["contract_id"]
        completeness_contract_version = DAILY_COMPLETENESS_CONTRACT["version"]
        completeness_status, completeness_reasons = _evaluate_completeness(normalized, missing_price, artifact_bindings)
        publishability = ("CORE_RESULT_COMPLETENESS_PASS" if completeness_status == "PASS"
                          else "BLOCKED_CORE_RESULT_INCOMPLETE")
    material = {
        "contract_id": CONTRACT_ID, "contract_version": CONTRACT_VERSION,
        "publication_id": publication_id, "publication_revision": publication_revision,
        "trade_date": target, "source_manifest_sha256": source_manifest_sha256,
        "producer_contract_id": producer_contract_id, "producer_sha256": producer_sha256,
        "producer_receipt_sha256": receipt_digest, "rows": normalized,
    }
    result_sha = _sha(material)
    result_identity = "v4-core-r6-" + _sha({
        "publication_id": publication_id, "publication_revision": publication_revision,
        "trade_date": target, "source_manifest_sha256": source_manifest_sha256,
        "producer_contract_id": producer_contract_id, "producer_sha256": producer_sha256,
        "result_sha256": result_sha,
    })
    return {
        "contract_id": CONTRACT_ID, "contract_version": CONTRACT_VERSION,
        "publication_id": publication_id, "publication_revision": publication_revision,
        "trade_date": target, "result_identity": result_identity,
        "result_contract_id": CONTRACT_ID, "producer_contract_id": producer_contract_id,
        "producer_sha256": producer_sha256, "source_manifest_sha256": source_manifest_sha256,
        "producer_receipt_sha256": receipt_digest,
        "producer_source_artifact_bindings": artifact_bindings,
        "result_sha256": result_sha, "row_count": len(normalized),
        "missing_price_rows": missing_price, "completeness_contract_id": completeness_contract_id,
        "completeness_contract_version": completeness_contract_version,
        "completeness_status": completeness_status, "completeness_reasons": completeness_reasons,
        "publishability_status": publishability,
        "quality_status": "CORE_RESULT_ROWS_VERIFIED_CANDIDATE",
        "rows": normalized, "write_mode": "PLAN_ONLY_NO_DATABASE_IO",
    }


def persist_daily_core_result(pg: Any, plan: Mapping[str, Any]) -> dict[str, Any]:
    """Append one producer-built core candidate inside the caller's transaction.

    This controlled writer never connects, commits, accepts a Head, or makes a
    completeness decision. It requires the explicit V4 writer DSN, an already
    open writable transaction, a matching CANDIDATE publication and verified
    source-package/PIT bindings. The caller owns transaction rollback/commit.
    """
    from workbench_db.v4_native import configured_dsn
    try:
        writer_dsn = configured_dsn()
    except RuntimeError as exc:
        raise CoreResultError("CORE_RESULT_WRITER_DSN_REQUIRED_NO_READER_FALLBACK") from exc
    from psycopg.conninfo import conninfo_to_dict
    configured_writer = conninfo_to_dict(writer_dsn).get("user")
    if not configured_writer:
        raise CoreResultError("CORE_RESULT_WRITER_ROLE_REQUIRED")
    if not isinstance(plan, Mapping) or plan.get("contract_id") != CONTRACT_ID:
        raise CoreResultError("CORE_RESULT_PLAN_CONTRACT_REQUIRED")
    target = _date(plan.get("trade_date"))
    try:
        read_only = pg.execute("SHOW transaction_read_only").fetchone()[0]
    except Exception as exc:
        raise CoreResultError("CORE_RESULT_WRITE_TRANSACTION_UNVERIFIABLE") from exc
    if str(read_only).lower() in {"on", "true", "1"}:
        raise CoreResultError("CORE_RESULT_WRITE_TRANSACTION_MUST_BE_WRITABLE")
    receipt_body = {
        "trade_date": target,
        "producer_contract_id": plan.get("producer_contract_id"),
        "producer_sha256": plan.get("producer_sha256"),
        "publication_id": plan.get("publication_id"),
        "publication_revision": plan.get("publication_revision"),
        "source_manifest_sha256": plan.get("source_manifest_sha256"),
        "source_artifact_bindings": plan.get("producer_source_artifact_bindings"),
    }
    receipt = dict(receipt_body, receipt_sha256=_sha(receipt_body))
    rebuilt = build_daily_core_result_plan(
        publication_id=plan.get("publication_id"),
        publication_revision=plan.get("publication_revision"),
        trade_date=target,
        source_manifest_sha256=plan.get("source_manifest_sha256"),
        producer_contract_id=plan.get("producer_contract_id"),
        producer_sha256=plan.get("producer_sha256"),
        producer_receipt=receipt,
        rows=plan.get("rows"),
        completeness_contract=(DAILY_COMPLETENESS_CONTRACT
                              if plan.get("completeness_contract_id") == DAILY_COMPLETENESS_CONTRACT["contract_id"]
                              and plan.get("completeness_contract_version") == DAILY_COMPLETENESS_CONTRACT["version"]
                              else None),
    )
    for field_name in (
        "result_identity", "result_sha256", "producer_receipt_sha256", "row_count",
        "missing_price_rows", "completeness_contract_id", "completeness_contract_version",
        "completeness_status", "publishability_status", "quality_status",
    ):
        if rebuilt.get(field_name) != plan.get(field_name):
            raise CoreResultError("CORE_RESULT_PLAN_DIGEST_OR_COUNT_MISMATCH")
    try:
        role = pg.execute(
            """SELECT current_user, r.rolsuper, r.rolcreaterole, r.rolcreatedb, r.rolreplication,
                      r.rolbypassrls,
                      has_schema_privilege(current_user,'v4','CREATE'),
                      has_table_privilege(current_user,'v4.daily_core_result_snapshots','INSERT'),
                      has_table_privilege(current_user,'v4.daily_core_result_rows','INSERT'),
                      (has_table_privilege(current_user,'v4.daily_core_result_snapshots','UPDATE')
                       OR has_table_privilege(current_user,'v4.daily_core_result_snapshots','DELETE')
                       OR has_table_privilege(current_user,'v4.daily_core_result_snapshots','TRUNCATE')),
                      (has_table_privilege(current_user,'v4.daily_core_result_rows','UPDATE')
                       OR has_table_privilege(current_user,'v4.daily_core_result_rows','DELETE')
                       OR has_table_privilege(current_user,'v4.daily_core_result_rows','TRUNCATE'))"""
        ).fetchone()
    except Exception as exc:
        raise CoreResultError("CORE_RESULT_WRITER_ROLE_UNVERIFIABLE") from exc
    if (role is None or role[0] != configured_writer
            or any(bool(value) for value in role[1:7])
            or not all(bool(value) for value in role[7:9])
            or any(bool(value) for value in role[9:])):
        raise CoreResultError("CORE_RESULT_WRITER_ROLE_INVALID")
    pub = pg.execute(
        """SELECT trade_date, revision_no, source_manifest_sha256, status
             FROM v4.publications WHERE publication_id=%s""",
        (plan["publication_id"],),
    ).fetchone()
    if (pub is None or pub[0].isoformat() != target
            or int(pub[1]) != plan["publication_revision"]
            or str(pub[2]).strip() != plan["source_manifest_sha256"]
            or pub[3] != "CANDIDATE"):
        raise CoreResultError("CORE_RESULT_PUBLICATION_MUST_BE_MATCHING_CANDIDATE")
    cutoff = pg.execute("SELECT statement_timestamp()").fetchone()[0]
    _, artifact_bindings = _read_consumed_source_proofs(
        pg, publication_id=plan["publication_id"],
        publication_revision=plan["publication_revision"], target=target,
        source_manifest_sha256=plan["source_manifest_sha256"],
        core_source_revision_ids={str(row["source_revision_id"]) for row in plan["rows"]},
        allow_candidate=True, candidate_cutoff=cutoff,
    )
    if artifact_bindings != plan["producer_source_artifact_bindings"]:
        raise CoreResultError("CORE_RESULT_SOURCE_AUTHORITY_PLAN_MISMATCH")
    if _evaluate_completeness(plan["rows"], plan["missing_price_rows"], artifact_bindings)[0] != plan["completeness_status"]:
        raise CoreResultError("CORE_RESULT_SOURCE_PACKAGE_ROW_COUNT_MISMATCH")
    if pg.execute(
        """SELECT 1 FROM v4.daily_core_result_snapshots
            WHERE publication_id=%s AND publication_revision=%s""",
        (plan["publication_id"], plan["publication_revision"]),
    ).fetchone() is not None:
        raise CoreResultError("CORE_RESULT_APPEND_ONLY_SNAPSHOT_ALREADY_EXISTS")
    snapshot = (
        plan["publication_id"], plan["publication_revision"], target,
        plan["result_identity"], CONTRACT_ID, plan["producer_contract_id"],
        plan["producer_sha256"], plan["producer_receipt_sha256"],
        plan["source_manifest_sha256"], plan["result_sha256"], plan["row_count"],
        plan["missing_price_rows"], plan["completeness_contract_id"],
        plan["completeness_contract_version"], plan["completeness_status"],
        plan["quality_status"],
    )
    pg.execute(
        """INSERT INTO v4.daily_core_result_snapshots
           (publication_id,publication_revision,trade_date,result_identity,result_contract_id,
            producer_contract_id,producer_sha256,producer_receipt_sha256,source_manifest_sha256,
            result_sha256,row_count,missing_price_rows,completeness_contract_id,
            completeness_contract_version,completeness_status,quality_status,captured_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,clock_timestamp())""",
        snapshot,
    )
    from psycopg.types.json import Jsonb
    for row in plan["rows"]:
        pg.execute(
            """INSERT INTO v4.daily_core_result_rows
               (publication_id,publication_revision,trade_date,security_id,security_type,trade_status,
                open,high,low,close,volume,amount,turnover_rate,turnover_status,ma5,ma20,ma60,
                history_status,price_basis,source_revision_id,profile_payload,quality_status,row_sha256)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (plan["publication_id"], plan["publication_revision"], target, row["security_id"],
             row["security_type"], row["trade_status"], row["open"], row["high"], row["low"],
             row["close"], row["volume"], row["amount"], row["turnover_rate"],
             row["turnover_status"], row["ma5"], row["ma20"], row["ma60"],
             row["history_status"], row["price_basis"], row["source_revision_id"],
             Jsonb(row["profile_payload"]), row["quality_status"], row["row_sha256"]),
        )
    return {"status": "CANDIDATE_CORE_RESULT_APPENDED", "persisted": True,
            "publication_id": plan["publication_id"],
            "publication_revision": plan["publication_revision"],
            "trade_date": target, "row_count": plan["row_count"],
            "transaction_owner": "CALLER_NO_AUTOCOMMIT"}


def read_daily_core_result(pg: Any, *, publication_id: str, publication_revision: int,
                           trade_date: str, source_manifest_sha256: str) -> VerifiedDailyCoreResult:
    """Read back a result inside the caller's explicit read-only RR snapshot.

    The caller must begin a READ ONLY, REPEATABLE READ transaction before this
    call. The function verifies that transaction on the same PG connection;
    it never upgrades transaction isolation or accepts a cursor/mock that
    cannot attest it.
    """
    target = _date(trade_date)
    if (not isinstance(publication_id, str) or not publication_id.strip()
            or isinstance(publication_revision, bool) or not isinstance(publication_revision, int)
            or publication_revision <= 0 or not _SHA256.fullmatch(str(source_manifest_sha256))):
        raise CoreResultError("CORE_RESULT_PUBLICATION_IDENTITY_INVALID")
    try:
        isolation = pg.execute("SHOW transaction_isolation").fetchone()[0]
        read_only = pg.execute("SHOW transaction_read_only").fetchone()[0]
    except Exception as exc:
        raise CoreResultError("CORE_RESULT_READ_TRANSACTION_UNVERIFIABLE") from exc
    if str(isolation).lower().replace("_", " ") != "repeatable read" or str(read_only).lower() not in {"on", "true", "1"}:
        raise CoreResultError("CORE_RESULT_READ_TRANSACTION_MUST_BE_REPEATABLE_READ_ONLY")
    snapshot = pg.execute(
        """SELECT trade_date,result_identity,result_contract_id,producer_contract_id,
                  producer_sha256,producer_receipt_sha256,source_manifest_sha256,result_sha256,row_count,
                  missing_price_rows,completeness_contract_id,completeness_contract_version,
                  completeness_status,quality_status
             FROM v4.daily_core_result_snapshots
            WHERE publication_id=%s AND publication_revision=%s""",
        (publication_id, publication_revision),
    ).fetchone()
    if snapshot is None:
        raise CoreResultError("CORE_RESULT_PG_ROW_MISSING")
    if (snapshot[0].isoformat() != target or str(snapshot[6]).strip() != source_manifest_sha256
            or snapshot[2] != CONTRACT_ID):
        raise CoreResultError("CORE_RESULT_PG_PUBLICATION_IDENTITY_MISMATCH")
    rows = pg.execute(
        """SELECT trade_date,security_id,security_type,trade_status,open,high,low,close,
                  volume,amount,turnover_rate,turnover_status,ma5,ma20,ma60,history_status,price_basis,source_revision_id,
                  profile_payload,quality_status,row_sha256
             FROM v4.daily_core_result_rows
            WHERE publication_id=%s AND publication_revision=%s
            ORDER BY security_id COLLATE "C""",
        (publication_id, publication_revision),
    ).fetchall()
    columns = ("trade_date", "security_id", "security_type", "trade_status", *_PRICE_FIELDS,
               "turnover_status", *_PROFILE_FIELDS, "history_status", "price_basis", "source_revision_id",
               "profile_payload", "quality_status", "row_sha256")
    material_rows = []
    missing_price = 0
    for values in rows:
        item = dict(zip(columns, values))
        if item["trade_date"].isoformat() != target or item["price_basis"] != "TDX_GBBQ_UNCHANGED":
            raise CoreResultError("CORE_RESULT_PG_ROW_IDENTITY_MISMATCH")
        row_sha = item.pop("row_sha256")
        # Date and scalar conversions are canonicalized to match the producer plan.
        item["trade_date"] = item["trade_date"].isoformat()
        if _sha(item) != str(row_sha).strip():
            raise CoreResultError("CORE_RESULT_PG_ROW_DIGEST_MISMATCH")
        if item["close"] is None:
            missing_price += 1
        material_rows.append({**item, "row_sha256": str(row_sha).strip()})
    if len(rows) == 0 or len(rows) > _MAX_ROWS:
        raise CoreResultError("CORE_RESULT_PG_ROWSET_EMPTY_OR_LIMIT_EXCEEDED")
    ordered_ids = [row["security_id"] for row in material_rows]
    if len(set(ordered_ids)) != len(ordered_ids) or ordered_ids != sorted(ordered_ids, key=lambda item: item.encode("utf-8")):
        raise CoreResultError("CORE_RESULT_PG_ROWSET_ORDER_OR_DUPLICATE_INVALID")
    if len(rows) != int(snapshot[8]) or missing_price != int(snapshot[9]):
        raise CoreResultError("CORE_RESULT_PG_ROWSET_COUNT_MISMATCH")
    source_revision_ids = {str(row["source_revision_id"]) for row in material_rows}
    _, artifact_bindings = _read_consumed_source_proofs(
        pg, publication_id=publication_id, publication_revision=publication_revision,
        target=target, source_manifest_sha256=source_manifest_sha256,
        core_source_revision_ids=source_revision_ids,
    )
    producer_receipt_body = {
        "trade_date": target, "producer_contract_id": str(snapshot[3]),
        "producer_sha256": str(snapshot[4]).strip(), "publication_id": publication_id,
        "publication_revision": publication_revision,
        "source_manifest_sha256": source_manifest_sha256,
        "source_artifact_bindings": artifact_bindings,
    }
    producer_receipt_sha = _sha(producer_receipt_body)
    if producer_receipt_sha != str(snapshot[5]).strip():
        raise CoreResultError("CORE_RESULT_PRODUCER_RECEIPT_SOURCE_BINDING_MISMATCH")
    material = {
        "contract_id": CONTRACT_ID, "contract_version": CONTRACT_VERSION,
        "publication_id": publication_id, "publication_revision": publication_revision,
        "trade_date": target, "source_manifest_sha256": source_manifest_sha256,
        "producer_contract_id": snapshot[3], "producer_sha256": str(snapshot[4]).strip(),
        "producer_receipt_sha256": str(snapshot[5]).strip(), "rows": material_rows,
    }
    result_sha = _sha(material)
    if result_sha != str(snapshot[7]).strip():
        raise CoreResultError("CORE_RESULT_PG_AGGREGATE_DIGEST_MISMATCH")
    expected_identity = "v4-core-r6-" + _sha({
        "publication_id": publication_id, "publication_revision": publication_revision,
        "trade_date": target, "source_manifest_sha256": source_manifest_sha256,
        "producer_contract_id": snapshot[3], "producer_sha256": str(snapshot[4]).strip(),
        "result_sha256": result_sha,
    })
    if expected_identity != snapshot[1]:
        raise CoreResultError("CORE_RESULT_PG_RESULT_IDENTITY_MISMATCH")
    observed_completeness_status = str(snapshot[12])
    universe_proof = None
    universe_status = "LEGACY_NOT_REQUIRED"
    universe_contract_id = "LEGACY_DIAGNOSTIC"
    universe_sha256 = None
    universe_reconciliation_count = 0
    universe_readback_receipt_sha256 = None
    if date.fromisoformat(target) >= R3_SOURCE_EFFECTIVE_DATE:
        try:
            from .v4_universe_pg_r1 import read_universe_snapshot, is_verified_universe_readback
            universe_proof = read_universe_snapshot(
                pg, publication_id=publication_id, publication_revision=publication_revision,
                trade_date=target, source_manifest_sha256=source_manifest_sha256,
                core_rows=material_rows,
            )
            if (not is_verified_universe_readback(universe_proof)
                    or universe_proof.publication_id != publication_id
                    or universe_proof.publication_revision != publication_revision
                    or universe_proof.trade_date != target
                    or universe_proof.source_manifest_sha256 != source_manifest_sha256):
                raise CoreResultError("UNIVERSE_TYPED_READBACK_IDENTITY_MISMATCH")
            universe_status = "PASS"
            universe_contract_id = "V4_MARKET_UNIVERSE_COMPLETENESS_R1"
            universe_sha256 = universe_proof.universe_sha256
            universe_reconciliation_count = universe_proof.expected_count
            universe_readback_receipt_sha256 = universe_proof.readback_receipt_sha256
        except Exception as exc:
            reason = str(exc)
            universe_status = ("BLOCKED_UNIVERSE_READBACK_NOT_PERSISTED"
                               if any(tag in reason for tag in (
                                   "UNIVERSE_PG_SNAPSHOT_MISSING", "UNIVERSE_PG_SCHEMA_NOT_INSTALLED",
                                   "UNIVERSE_PG_READBACK_UNAVAILABLE"))
                               else "BLOCKED_UNIVERSE_AUTHORITY_OR_READ_PRIVILEGE"
                               if any(tag in reason for tag in (
                                   "AUTHORITY_UNAVAILABLE", "READER", "PRIVILEGE", "NO_WRITER_FALLBACK"))
                               else "FAIL_UNIVERSE_READBACK_INVALID")
            universe_contract_id = "V4_MARKET_UNIVERSE_COMPLETENESS_R1"
    if (snapshot[10] != DAILY_COMPLETENESS_CONTRACT["contract_id"]
            or snapshot[11] != DAILY_COMPLETENESS_CONTRACT["version"]):
        completeness_status = "CONTRACT_UNRESOLVED"
        publishable = False
    else:
        completeness_status, _ = _evaluate_completeness(
            material_rows, missing_price, artifact_bindings,
        )
        if observed_completeness_status != completeness_status:
            raise CoreResultError("CORE_RESULT_PG_COMPLETENESS_DECLARATION_MISMATCH")
        publishable = completeness_status == "PASS" and universe_status in {"PASS", "LEGACY_NOT_REQUIRED"}
    receipt_body = {
        "contract_id": CONTRACT_ID, "publication_id": publication_id,
        "publication_revision": publication_revision, "trade_date": target,
        "source_manifest_sha256": source_manifest_sha256,
        "result_identity": str(snapshot[1]), "result_sha256": result_sha,
        "producer_receipt_sha256": producer_receipt_sha,
        "completeness_contract_id": str(snapshot[10]),
        "completeness_contract_version": str(snapshot[11]),
        "row_count": len(rows), "missing_price_rows": missing_price,
        "completeness_status": completeness_status,
        "universe_completeness_status": universe_status,
        "universe_contract_id": universe_contract_id,
        "universe_sha256": universe_sha256,
        "universe_reconciliation_count": universe_reconciliation_count,
        "universe_readback_receipt_sha256": universe_readback_receipt_sha256,
        "observed_completeness_status": observed_completeness_status,
        "quality_status": str(snapshot[13]), "status": "PG_READBACK_VERIFIED",
        "publishable": publishable,
    }
    return VerifiedDailyCoreResult(
        contract_id=CONTRACT_ID, publication_id=publication_id,
        publication_revision=publication_revision, trade_date=target,
        source_manifest_sha256=source_manifest_sha256,
        result_identity=str(snapshot[1]), result_sha256=result_sha,
        producer_receipt_sha256=producer_receipt_sha,
        readback_receipt_sha256=_sha(receipt_body),
        completeness_contract_id=str(snapshot[10]),
        completeness_contract_version=str(snapshot[11]),
        row_count=len(rows), missing_price_rows=missing_price,
        completeness_status=completeness_status,
        observed_completeness_status=observed_completeness_status,
        universe_completeness_status=universe_status,
        universe_contract_id=universe_contract_id,
        universe_sha256=universe_sha256,
        universe_reconciliation_count=universe_reconciliation_count,
        universe_readback_receipt_sha256=universe_readback_receipt_sha256,
        quality_status=str(snapshot[13]), status="PG_READBACK_VERIFIED", publishable=publishable,
        _proof=_PG_READBACK_PROOF,
    )
