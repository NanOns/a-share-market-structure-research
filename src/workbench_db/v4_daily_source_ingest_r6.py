"""Fail-closed source-package planning for the live V4 daily freeze (R6).

The current operational producer freezes its exact inputs to immutable files.
This adapter verifies those bytes and plans a PG package/revision transaction;
it does not connect to PG or promote an unaccepted freeze.  In particular,
the current executor's AS_RECORDED=False / PIT_ELIGIBLE=False freeze remains
diagnostic until a matching, independently accepted readiness receipt exists.
"""
from __future__ import annotations

from datetime import date, datetime, time, timezone
import base64
import hashlib
import json
import math
from zoneinfo import ZoneInfo
from pathlib import Path
import re
from typing import Any, Mapping



CONTRACT_ID = "V4_DAILY_SOURCE_INGEST_ADAPTER_R6"
CONTRACT_VERSION = "1.2.0"
ACCEPTANCE_CONTRACT_ID = "V4_DAILY_SOURCE_ACCEPTANCE_RECEIPT_R3"
PIT_CLOCK_CONTRACT_ID = "V4_DAILY_PIT_DECISION_CLOCK_R1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_NAMES = ("tdx", "native_baostock", "runtime_manifest")
_TDX_BOARD_SCOPES = ("SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR")


class SourceIngestError(ValueError):
    pass


class SourceIngestConflict(SourceIngestError):
    """An immutable package, revision, or consumed key conflicts with this plan."""


class _IndependentAcceptanceProof:
    """Internal capability returned only by a configured authority verifier."""

    __slots__ = ("plan_sha256", "authority_receipt_id", "authority_id", "receipt_sha256")

    def __init__(self, plan_sha256: str, authority_receipt_id: str,
                 authority_id: str = "", receipt_sha256: str = ""):
        self.plan_sha256 = plan_sha256
        self.authority_receipt_id = authority_receipt_id
        self.authority_id = authority_id
        self.receipt_sha256 = receipt_sha256


def _acceptance_authority_registry(pg: Any | None = None) -> Mapping[str, Any]:
    from workbench_analysis.contract_registry_pg_v1 import load_unique_current_approved_contract
    from .v4_publication_reader import PgPublicationReader, readonly_connection

    def read(cursor: Any) -> Mapping[str, Any]:
        identity = PgPublicationReader._read_database_identity(cursor)
        registered = load_unique_current_approved_contract(
            cursor, "V4_DAILY_SOURCE_ACCEPTANCE_AUTHORITY_REGISTRY_R1", "1.0.0",
            expected_database_identity=identity,
        )
        if not isinstance(registered.parsed_json, Mapping):
            raise SourceIngestError("INDEPENDENT_ACCEPTANCE_AUTHORITY_CONTRACT_INVALID")
        return registered.parsed_json

    if pg is not None:
        return read(pg)
    with readonly_connection() as cursor:
        return read(cursor)


def _verify_independent_acceptance_authority(
    plan: Mapping[str, Any], *, pg: Any | None = None,
) -> _IndependentAcceptanceProof:
    """Verify an Ed25519 receipt against the currently approved PG contract.

    The issuer registry is a versioned runtime contract, not a repository file.
    Its bytes and approval event are resolved in one repeatable-read, read-only
    transaction. Missing approval or an ambiguous namespace fails closed.
    """
    receipt = plan.get("acceptance_receipt")
    if not isinstance(receipt, Mapping):
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_RECEIPT_REQUIRED")
    try:
        registry = _acceptance_authority_registry(pg)
    except Exception as exc:
        code = getattr(exc, "code", None) or str(exc)
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_AUTHORITY_UNAVAILABLE:" + str(code)) from exc
    if (not isinstance(registry, Mapping)
            or registry.get("contract_id") != "V4_DAILY_SOURCE_ACCEPTANCE_AUTHORITY_REGISTRY_R1"
            or registry.get("status") != "ACTIVE"):
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_AUTHORITY_UNAVAILABLE")
    issuers = registry.get("issuers")
    issuer_id = receipt.get("issuer_id")
    issuer = issuers.get(issuer_id) if isinstance(issuers, Mapping) and isinstance(issuer_id, str) else None
    if not isinstance(issuer, Mapping) or issuer.get("status") != "ACTIVE":
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_AUTHORITY_UNAVAILABLE")
    capabilities = issuer.get("capabilities")
    if (not isinstance(capabilities, list)
            or not {"ACCEPT_SOURCE_PACKAGE", "AS_RECORDED", "PIT_ELIGIBLE"}.issubset(set(capabilities))):
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_AUTHORITY_SCOPE_INVALID")
    signature_text = receipt.get("signature_ed25519")
    if not isinstance(signature_text, str) or not signature_text:
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_SIGNATURE_MISSING")
    signed = {key: value for key, value in receipt.items() if key not in {"signature_ed25519", "receipt_sha256"}}
    receipt_sha = hashlib.sha256(_canonical(signed)).hexdigest()
    if receipt.get("receipt_sha256") != receipt_sha:
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_RECEIPT_DIGEST_MISMATCH")
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(issuer["public_key_b64"], validate=True))
        public_key.verify(base64.b64decode(signature_text, validate=True), _canonical(signed))
    except ImportError as exc:
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_CRYPTO_PROVIDER_UNAVAILABLE") from exc
    except (KeyError, TypeError, ValueError, InvalidSignature) as exc:
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_SIGNATURE_INVALID") from exc
    manifest = plan.get("package_manifest")
    bindings = manifest.get("source_fact_bindings") if isinstance(manifest, Mapping) else None
    if not isinstance(bindings, list) or not bindings:
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_SOURCE_FACT_BINDINGS_MISSING")
    unsigned_bindings = [
        {key: value for key, value in item.items() if key != "acceptance_receipt_id"}
        for item in bindings if isinstance(item, Mapping)
    ]
    if len(unsigned_bindings) != len(bindings):
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_SOURCE_FACT_BINDINGS_INVALID")
    bindings_sha = hashlib.sha256(_canonical(unsigned_bindings)).hexdigest()
    if bindings_sha != manifest.get("source_fact_bindings_sha256"):
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_SOURCE_FACT_BINDINGS_DIGEST_MISMATCH")
    descriptor = {key: manifest.get(key) for key in (
        "contract_id", "contract_version", "trade_date", "source_freeze_sha256",
        "source_readiness_sha256", "source_fact_bindings_sha256", "price_basis",
    )}
    if hashlib.sha256(_canonical(descriptor)).hexdigest() != manifest.get("package_sha256"):
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_PACKAGE_DIGEST_MISMATCH")
    required = {
        "contract_id": ACCEPTANCE_CONTRACT_ID,
        "acceptance_id": manifest.get("acceptance_receipt_id") if isinstance(manifest, Mapping) else None,
        "trade_date": plan.get("trade_date"),
        "source_freeze_sha256": manifest.get("source_freeze_sha256") if isinstance(manifest, Mapping) else None,
        "source_readiness_sha256": manifest.get("source_readiness_sha256") if isinstance(manifest, Mapping) else None,
        "source_fact_bindings_sha256": manifest.get("source_fact_bindings_sha256") if isinstance(manifest, Mapping) else None,
        "package_sha256": manifest.get("package_sha256") if isinstance(manifest, Mapping) else None,
        "source_ready": True,
        "readiness_observed_at": manifest.get("source_readiness_observed_at"),
        "as_recorded": True,
        "pit_eligible": True,
        "pit_clock_contract_id": PIT_CLOCK_CONTRACT_ID,
    }
    for key, expected in required.items():
        if receipt.get(key) != expected:
            raise SourceIngestError("INDEPENDENT_ACCEPTANCE_RECEIPT_BINDING_MISMATCH:" + key)
    if (not isinstance(manifest, Mapping) or manifest.get("accepted_scope") != "ACCEPTED_SOURCE_PACKAGE"
            or manifest.get("AS_RECORDED") is not True or manifest.get("PIT_ELIGIBLE") is not True):
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_SCOPE_NOT_GRANTED")
    accepted_at = _utc_timestamp(receipt.get("accepted_at"), "INDEPENDENT_ACCEPTANCE_TIME_INVALID")
    signed_at = _utc_timestamp(receipt.get("signed_at"), "INDEPENDENT_ACCEPTANCE_SIGNATURE_TIME_INVALID")
    pit_cutoff_at = _utc_timestamp(receipt.get("pit_cutoff_at"), "INDEPENDENT_ACCEPTANCE_CUTOFF_INVALID")
    observed_at = manifest.get("source_observed_at") if isinstance(manifest, Mapping) else None
    ready_at = _utc_timestamp(manifest.get("source_readiness_observed_at"), "SOURCE_READINESS_TIME_INVALID")
    if (accepted_at < max(_utc_timestamp(observed_at, "SOURCE_OBSERVATION_TIME_INVALID"), ready_at)
            or signed_at < max(_utc_timestamp(observed_at, "SOURCE_OBSERVATION_TIME_INVALID"), ready_at)
            or accepted_at > signed_at or signed_at > pit_cutoff_at
            or observed_at is None or _utc_timestamp(observed_at, "SOURCE_OBSERVATION_TIME_INVALID") > pit_cutoff_at):
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_TIME_ORDER_INVALID")
    target = date.fromisoformat(str(plan.get("trade_date")))
    cutoff = datetime.fromisoformat(pit_cutoff_at.replace("Z", "+00:00")).astimezone(ZoneInfo("Asia/Shanghai"))
    calendar_sha = receipt.get("trading_calendar_sha256")
    if not isinstance(calendar_sha, str) or not _SHA256.fullmatch(calendar_sha):
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_TRADING_CALENDAR_PROOF_MISSING")
    session = receipt.get("decision_session")
    if (session == "T0_AFTER_CLOSE" and cutoff.date() == target
            and cutoff.time() >= time(15, 0)):
        pass
    elif (session == "T1_PREOPEN"
          and receipt.get("next_trade_date") == cutoff.date().isoformat()
          and cutoff.date() > target and cutoff.time() < time(9, 30)):
        pass
    else:
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_CUTOFF_SESSION_INVALID")
    _receipt_id = receipt.get("acceptance_id")
    if not isinstance(_receipt_id, str) or not _receipt_id.strip():
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_RECEIPT_ID_INVALID")
    return _IndependentAcceptanceProof(
        hashlib.sha256(_canonical(dict(plan))).hexdigest(), _receipt_id,
        str(issuer_id), receipt_sha,
    )


def verify_source_package_manifest_authority(
    manifest: Mapping[str, Any], *, pg: Any | None = None,
) -> dict[str, str]:
    """Re-verify the persisted Ed25519 evidence from the immutable PG manifest."""
    proof = manifest.get("acceptance_proof") if isinstance(manifest, Mapping) else None
    receipt = proof.get("receipt") if isinstance(proof, Mapping) else None
    if not isinstance(receipt, Mapping):
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_PERSISTED_PROOF_MISSING")
    plan = {
        "contract_id": CONTRACT_ID, "contract_version": manifest.get("contract_version"),
        "trade_date": manifest.get("trade_date"), "package_id": manifest.get("package_id"),
        "package_sha256": manifest.get("package_sha256"), "package_manifest": dict(manifest),
        "source_facts": manifest.get("source_fact_bindings"),
        "acceptance_receipt": dict(receipt),
    }
    verified = _verify_independent_acceptance_authority(plan, pg=pg)
    if (proof.get("receipt_sha256") != verified.receipt_sha256
            or proof.get("issuer_id") != verified.authority_id
            or proof.get("contract_id") != ACCEPTANCE_CONTRACT_ID):
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_PERSISTED_PROOF_MISMATCH")
    return {"issuer_id": verified.authority_id, "receipt_sha256": verified.receipt_sha256}



RAW_OWNER_AUTHORITY_CONTRACT_ID = "V4_STAGE00_RAW_OWNER_RECEIPT_AUTHORITY_REGISTRY_R1"
RAW_OWNER_RECEIPT_CONTRACT_ID = "V4_STAGE00_RAW_OWNER_RECEIPT_R1"


def _derive_raw_owner_results(pg: Any, source: Mapping[str, Any],
                              package: Mapping[str, Any], tdx_fact: Mapping[str, Any],
                              database_identity: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Derive B/C/D receipt inputs from this PG snapshot and verified package."""
    def relation_exists(name: str) -> bool:
        row = pg.execute("SELECT to_regclass(%s)", (name,)).fetchone()
        return bool(row and row[0])

    lifecycle_ready = all(relation_exists(name) for name in (
        "v4.security_lifecycle_facts", "v4.security_lifecycle_history",
    ))
    publication_ready = all(relation_exists(name) for name in (
        "v4.publications", "v4.publication_heads", "v4.model_namespaces",
    ))
    if not lifecycle_ready:
        raise SourceIngestError("RAW_OWNER_UPSTREAM_BLOCKED:V4-00B")
    if not publication_ready:
        raise SourceIngestError("RAW_OWNER_UPSTREAM_BLOCKED:V4-00C")
    if not source.get("accepted") or package.get("accepted_scope") != "ACCEPTED_SOURCE_PACKAGE":
        raise SourceIngestError("RAW_OWNER_UPSTREAM_BLOCKED:V4-00D")
    base = {
        "trade_date": package.get("target_trade_date"),
        "source_package_id": package.get("package_id"),
        "source_package_sha256": package.get("package_sha256"),
        "source_revision_id": tdx_fact.get("source_revision_id"),
        "database_identity": dict(database_identity),
        "evidence_source": "PG_STAGE00_DIAGNOSTIC",
    }
    results = {}
    for owner, scope in (
        ("V4-00B", "LIFECYCLE_SCHEMA"), ("V4-00C", "PUBLICATION_IDENTITY"),
        ("V4-00D", "A_STOCK_TDX_SOURCE"),
    ):
        result = {
            **base, "owner": owner,
            "status": "FULL_PASS" if owner == "V4-00D" else "DEGRADED_PASS",
            "accepted_scopes": [scope],
        }
        result["evidence_sha256"] = hashlib.sha256(_canonical(result)).hexdigest()
        results[owner] = result
    return results


def _raw_owner_authority_registry(pg: Any | None = None) -> Mapping[str, Any]:
    from workbench_analysis.contract_registry_pg_v1 import load_unique_current_approved_contract
    from .v4_publication_reader import PgPublicationReader, readonly_connection
    def read(cursor: Any) -> Mapping[str, Any]:
        identity = PgPublicationReader._read_database_identity(cursor)
        registered = load_unique_current_approved_contract(
            cursor, RAW_OWNER_AUTHORITY_CONTRACT_ID, "1.0.0",
            expected_database_identity=identity,
        )
        return registered.parsed_json
    if pg is not None:
        value = read(pg)
    else:
        with readonly_connection() as cursor:
            value = read(cursor)
    if not isinstance(value, Mapping) or value.get("contract_id") != RAW_OWNER_AUTHORITY_CONTRACT_ID or value.get("status") != "ACTIVE":
        raise SourceIngestError("RAW_OWNER_AUTHORITY_REGISTRY_INVALID")
    return value


def produce_raw_owner_receipt(
    source: Mapping[str, Any], owner_results: Mapping[str, Any] | None = None, *,
    signed_at: str, signer: Any, pg: Any | None = None,
) -> dict[str, Any]:
    """Build a RAW Owner receipt from accepted PG-shaped source evidence.

    ``signer`` is an injected independent signing capability; the gate never
    signs its own result. The returned receipt is verified against the current
    PG-approved issuer registry before it can be persisted or consumed.
    """
    package = source.get("package") if isinstance(source, Mapping) else None
    facts = source.get("facts", []) if isinstance(source, Mapping) else []
    if not source.get("accepted") or not isinstance(package, Mapping):
        raise SourceIngestError("RAW_OWNER_SOURCE_NOT_ACCEPTED")
    manifest = package.get("manifest")
    if (package.get("accepted_scope") != "ACCEPTED_SOURCE_PACKAGE"
            or not isinstance(manifest, Mapping)
            or manifest.get("package_id") != package.get("package_id")
            or manifest.get("package_sha256") != package.get("package_sha256")
            or manifest.get("trade_date") != package.get("target_trade_date")):
        raise SourceIngestError("RAW_OWNER_PACKAGE_IDENTITY_INVALID")
    verify_source_package_manifest_authority(manifest, pg=pg)
    tdx_fact = next((row for row in facts if row.get("source_key") == "tdx" and row.get("source_revision_id")), None)
    if not isinstance(tdx_fact, Mapping):
        raise SourceIngestError("RAW_OWNER_TDX_REVISION_REQUIRED")
    coverage = manifest.get("accepted_board_coverage")
    if (not isinstance(coverage, Mapping)
            or not isinstance(coverage.get("roster_sha256"), str)
            or not _SHA256.fullmatch(coverage["roster_sha256"])
            or coverage.get("target_trade_date") != package.get("target_trade_date")):
        raise SourceIngestError("RAW_OWNER_VERIFIED_ROSTER_REQUIRED")
    universe_fact = next((row for row in facts if row.get("source_key") == "security_universe"), None)
    universe_locator = universe_fact.get("record_locator") if isinstance(universe_fact, Mapping) else None
    if (not isinstance(universe_locator, Mapping)
            or universe_locator.get("universe_sha256") != coverage.get("universe_sha256")
            or universe_locator.get("universe_id") != coverage.get("universe_id")
            or universe_locator.get("record_count") != coverage.get("roster_count")):
        raise SourceIngestError("RAW_OWNER_ROSTER_SOURCE_BINDING_MISMATCH")
    acceptance_proof = manifest.get("acceptance_proof")
    acceptance = acceptance_proof.get("receipt", {}) if isinstance(acceptance_proof, Mapping) else {}
    if (manifest.get("AS_RECORDED") is not True or manifest.get("PIT_ELIGIBLE") is not True
            or acceptance.get("as_recorded") is not True or acceptance.get("pit_eligible") is not True):
        raise SourceIngestError("RAW_OWNER_KNOWLEDGE_CLOCK_NOT_ACCEPTED")
    if manifest.get("price_basis") != "TDX_GBBQ_UNCHANGED":
        raise SourceIngestError("RAW_OWNER_RAW_PRICE_BASIS_UNPROVEN")
    identity_status = "RESOLVED" if (
        universe_locator.get("universe_id") and universe_locator.get("universe_sha256")
        and universe_locator.get("record_count") == coverage.get("roster_count")
    ) else "UNRESOLVED"
    trading_status = (
        "TRADING_WITH_SUSPENSIONS" if coverage.get("suspended_row_count", 0) > 0 else "TRADING"
    )
    knowledge_status = (
        "AS_RECORDED" if acceptance.get("as_recorded") is True
        and acceptance.get("pit_eligible") is True else "POST_HOC_OR_UNKNOWN"
    )
    if identity_status != "RESOLVED" or knowledge_status != "AS_RECORDED":
        raise SourceIngestError("RAW_OWNER_SOURCE_FACT_STATUS_NOT_ACCEPTED")
    normalized_signed_at = _utc_timestamp(signed_at, "RAW_OWNER_SIGNED_TIME_INVALID")
    signed_clock = datetime.fromisoformat(normalized_signed_at.replace("Z", "+00:00"))
    latest_source_clock = max(
        datetime.fromisoformat(_utc_timestamp(tdx_fact.get(key), "RAW_OWNER_SOURCE_TIME_INVALID").replace("Z", "+00:00"))
        for key in ("observed_at", "ingested_at", "system_available_at")
    )
    if signed_clock < latest_source_clock:
        raise SourceIngestError("RAW_OWNER_SIGNED_BEFORE_SOURCE_AVAILABLE")
    from .v4_publication_reader import PgPublicationReader
    if pg is None:
        raise SourceIngestError("RAW_OWNER_SAME_PG_SNAPSHOT_REQUIRED")
    database_identity = PgPublicationReader._read_database_identity(pg)
    from v4.contracts.phase0_gate import _package_acceptance_errors
    source_errors = _package_acceptance_errors(package, list(facts),
                                                acceptance_verified=True)
    if source_errors:
        raise SourceIngestError("RAW_OWNER_SOURCE_PACKAGE_INVALID:" + ",".join(source_errors))
    normalized_owners = _derive_raw_owner_results(
        pg, source, package, tdx_fact, database_identity,
    )
    if owner_results is not None:
        for owner, expected in normalized_owners.items():
            supplied = owner_results.get(owner) if isinstance(owner_results, Mapping) else None
            if not isinstance(supplied, Mapping) or any(
                supplied.get(key) != expected.get(key) for key in (
                    "owner", "status", "accepted_scopes", "trade_date", "source_package_id",
                    "source_package_sha256", "source_revision_id", "database_identity",
                    "evidence_source", "evidence_sha256",
                )
            ):
                raise SourceIngestError("RAW_OWNER_INPUT_INVALID:" + owner)
    issuer_id = signer.get("issuer_id") if isinstance(signer, Mapping) else getattr(signer, "issuer_id", None)
    sign_bytes = signer.get("sign") if isinstance(signer, Mapping) else getattr(signer, "sign", None)
    if not isinstance(issuer_id, str) or not callable(sign_bytes):
        raise SourceIngestError("RAW_OWNER_SIGNING_CAPABILITY_INVALID")
    body = {
        "contract_id": RAW_OWNER_RECEIPT_CONTRACT_ID,
        "receipt_id": f"v4-00e-raw-{package['target_trade_date']}-{package['package_id']}-{tdx_fact['source_revision_id']}",
        "owner": "V4-00E",
        "status": ("DEGRADED_ACCEPTED" if any(
            item.get("status") == "DEGRADED_PASS" for item in normalized_owners.values()
        ) else "ACCEPTED"),
        "scope": "RAW_BOOTSTRAP",
        "trade_date": package["target_trade_date"],
        "source_package_id": package["package_id"],
        "source_package_sha256": package["package_sha256"],
        "source_revision_id": tdx_fact["source_revision_id"],
        "source_revision_sha256": tdx_fact["digest"],
        "raw_basis": manifest["price_basis"], "source_identity_status": identity_status,
        "source_trading_status": trading_status,
        "source_knowledge_status": knowledge_status,
        "source_universe_id": coverage["universe_id"],
        "source_universe_sha256": coverage["universe_sha256"],
        "source_roster_sha256": coverage["roster_sha256"],
        "source_roster_count": coverage["roster_count"],
        "source_scope_roster_count": coverage["scope_roster_count"],
        "source_trading_row_count": coverage["trading_row_count"],
        "source_suspended_row_count": coverage["suspended_row_count"],
        "source_tdx_record_count": tdx_fact.get("record_count"),
        "source_tdx_ohlcva_sha256": coverage["tdx_ohlcva_sha256"],
        "owner_results": normalized_owners, "issuer_id": str(issuer_id),
        "signed_at": normalized_signed_at,
    }
    signature = sign_bytes(_canonical(body))
    receipt = {**body, "signature_ed25519": str(signature)}
    receipt["receipt_sha256"] = hashlib.sha256(_canonical(receipt)).hexdigest()
    verify_raw_owner_receipt(receipt, pg=pg)
    return receipt


def verify_raw_owner_receipt(receipt: Mapping[str, Any], *, pg: Any | None = None) -> str:
    if not isinstance(receipt, Mapping) or receipt.get("contract_id") != RAW_OWNER_RECEIPT_CONTRACT_ID:
        raise SourceIngestError("RAW_OWNER_RECEIPT_CONTRACT_INVALID")
    signature = receipt.get("signature_ed25519")
    issuer_id = receipt.get("issuer_id")
    registry = _raw_owner_authority_registry(pg)
    issuers = registry.get("issuers")
    issuer = issuers.get(issuer_id) if isinstance(issuers, Mapping) else None
    if (not isinstance(issuer, Mapping) or issuer.get("status") != "ACTIVE"
            or "SIGN_RAW_OWNER_RECEIPT" not in issuer.get("capabilities", [])):
        raise SourceIngestError("RAW_OWNER_ISSUER_NOT_APPROVED")
    digest = receipt.get("receipt_sha256")
    unsigned = {k: v for k, v in receipt.items() if k not in {"signature_ed25519", "receipt_sha256"}}
    if hashlib.sha256(_canonical({**unsigned, "signature_ed25519": signature})).hexdigest() != digest:
        raise SourceIngestError("RAW_OWNER_RECEIPT_DIGEST_MISMATCH")
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(issuer["public_key_b64"], validate=True))
        public_key.verify(base64.b64decode(str(signature), validate=True), _canonical(unsigned))
    except ImportError as exc:
        raise SourceIngestError("RAW_OWNER_CRYPTO_PROVIDER_UNAVAILABLE") from exc
    except (KeyError, TypeError, ValueError, InvalidSignature) as exc:
        raise SourceIngestError("RAW_OWNER_SIGNATURE_INVALID") from exc
    return str(issuer_id)


def persist_raw_owner_receipt(pg: Any, receipt: Mapping[str, Any]) -> None:
    """Insert an immutable, independently signed Owner receipt in caller transaction."""
    verify_raw_owner_receipt(receipt, pg=pg)
    pg.execute(
        """INSERT INTO v4.stage00_raw_owner_receipts
           (receipt_id, trade_date, source_package_id, source_revision_id,
            receipt_sha256, receipt, issuer_id)
           VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s)
           ON CONFLICT (receipt_id) DO NOTHING""",
        (receipt["receipt_id"], receipt["trade_date"], receipt["source_package_id"],
         receipt["source_revision_id"], receipt["receipt_sha256"],
         json.dumps(dict(receipt), ensure_ascii=False, sort_keys=True), receipt["issuer_id"]),
    )
    row = pg.execute(
        "SELECT receipt_sha256 FROM v4.stage00_raw_owner_receipts WHERE receipt_id=%s FOR KEY SHARE",
        (receipt["receipt_id"],),
    ).fetchone()
    if row is None or str(row[0]).strip() != receipt["receipt_sha256"]:
        raise SourceIngestError("RAW_OWNER_RECEIPT_IMMUTABLE_CONFLICT")


def produce_and_persist_raw_owner_receipt(
    pg: Any, source: Mapping[str, Any], owner_results: Mapping[str, Any] | None = None, *,
    signed_at: str, signer: Any,
) -> dict[str, Any]:
    """Produce and persist an independently signed E receipt in caller transaction."""
    receipt = produce_raw_owner_receipt(
        source, owner_results, signed_at=signed_at, signer=signer, pg=pg,
    )
    persist_raw_owner_receipt(pg, receipt)
    return receipt


def read_raw_owner_receipt(pg: Any, *, trade_date: str, source_package_id: str,
                           source_revision_id: str) -> tuple[Mapping[str, Any] | None, bool]:
    row = pg.execute(
        """SELECT receipt, receipt_sha256 FROM v4.stage00_raw_owner_receipts
             WHERE trade_date=%s AND source_package_id=%s AND source_revision_id=%s
             ORDER BY receipt_id LIMIT 2""",
        (trade_date, source_package_id, source_revision_id),
    ).fetchall()
    if not row:
        return None, False
    if len(row) != 1 or not isinstance(row[0][0], Mapping):
        raise SourceIngestError("RAW_OWNER_RECEIPT_AMBIGUOUS")
    receipt = row[0][0]
    if str(row[0][1]).strip() != receipt.get("receipt_sha256"):
        raise SourceIngestError("RAW_OWNER_RECEIPT_STORAGE_DIGEST_MISMATCH")
    verify_raw_owner_receipt(receipt, pg=pg)
    return receipt, True


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _tdx_board_scope(source_security_key: Any) -> str | None:
    """Map a native TDX code to the four Stage00 core board scopes."""
    value = str(source_security_key or "").strip().upper()
    match = re.fullmatch(r"(SH|SZ|BJ)\.(\d{6})", value)
    if not match:
        return None
    exchange, code = match.groups()
    if exchange == "BJ":
        return "BSE" if code.startswith(("4", "8", "92")) else None
    if exchange == "SH":
        if code.startswith(("688", "689")):
            return "STAR"
        if code.startswith(("600", "601", "603", "605")):
            return "SH_MAIN"
        return None
    if code.startswith(("300", "301")):
        return "CHINEXT"
    if code.startswith(("000", "001", "002", "003")):
        return "SZ_MAIN"
    return None


def _same_t0_a_share_roster(universe_doc: Mapping[str, Any], target_bars: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Reconcile the complete signed same-T0 roster with native TDX rows."""
    entries = universe_doc.get("securities")
    if not isinstance(entries, list) or not entries:
        raise SourceIngestError("SECURITY_UNIVERSE_SECURITIES_REQUIRED")
    expected: dict[str, tuple[str, str]] = {}
    out_of_scope_a_shares: dict[str, str] = {}
    suspended = {board: 0 for board in _TDX_BOARD_SCOPES}
    seen_security_ids: set[str] = set()
    for row in entries:
        if not isinstance(row, Mapping):
            raise SourceIngestError("SECURITY_UNIVERSE_ROW_INVALID")
        key = str(row.get("source_security_key") or row.get("security_id") or "").strip().upper()
        board = _tdx_board_scope(key)
        security_id = str(row.get("security_id") or "").strip().upper()
        if not key or not re.fullmatch(r"(SH|SZ|BJ)\.\d{6}", key):
            raise SourceIngestError("SECURITY_UNIVERSE_NON_A_SHARE_OR_BOARD_UNKNOWN:" + (key or "<empty>"))
        if not security_id or security_id in seen_security_ids:
            raise SourceIngestError("SECURITY_UNIVERSE_SECURITY_ID_INVALID_OR_DUPLICATE")
        seen_security_ids.add(security_id)
        asset_class, share_class = row.get("asset_class"), row.get("share_class")
        exchange, lifecycle = row.get("exchange"), row.get("status")
        if (asset_class not in {"COMMON_STOCK", "PREFERRED_STOCK", "ETF", "INDEX", "BOND", "OTHER"}
                or share_class not in {"A", "B", "NOT_APPLICABLE"}
                or exchange not in {"SSE", "SZSE", "BSE", "OTHER"}
                or lifecycle not in {"ACTIVE", "SUSPENDED", "NEWLY_LISTED", "DELISTED", "CODE_MIGRATION"}
                or not isinstance(row.get("source_id"), str) or not row["source_id"].strip()):
            raise SourceIngestError("SECURITY_UNIVERSE_CLASSIFICATION_OR_LIFECYCLE_INVALID:" + key)
        exchange_for_key = {"SH": "SSE", "SZ": "SZSE", "BJ": "BSE"}[key.split(".", 1)[0]]
        if exchange != exchange_for_key:
            raise SourceIngestError("SECURITY_UNIVERSE_EXCHANGE_IDENTITY_MISMATCH:" + key)
        if asset_class != "COMMON_STOCK" or share_class != "A":
            if board in _TDX_BOARD_SCOPES:
                raise SourceIngestError("SECURITY_UNIVERSE_SECURITY_CLASS_CODE_CONFLICT:" + key)
            continue
        if lifecycle == "DELISTED":
            continue
        if board == "BSE":
            if key in out_of_scope_a_shares:
                raise SourceIngestError("SECURITY_UNIVERSE_DUPLICATE_SOURCE_SECURITY_KEY:" + key)
            out_of_scope_a_shares[key] = str(lifecycle)
            continue
        if board not in _TDX_BOARD_SCOPES:
            raise SourceIngestError("SECURITY_UNIVERSE_A_SHARE_BOARD_UNKNOWN:" + key)
        if row.get("board_scope") is not None and row.get("board_scope") != board:
            raise SourceIngestError("SECURITY_UNIVERSE_BOARD_SCOPE_MISMATCH:" + key)
        if key in expected:
            raise SourceIngestError("SECURITY_UNIVERSE_DUPLICATE_SOURCE_SECURITY_KEY:" + key)
        expected[key] = (board, str(lifecycle))
        if lifecycle == "SUSPENDED":
            suspended[board] += 1
    normalized_universe = []
    for row in entries:
        key = str(row.get("source_security_key") or row.get("security_id") or "").strip().upper()
        normalized_universe.append({
            "security_id": str(row.get("security_id") or key).strip().upper(),
            "asset_class": row["asset_class"], "share_class": row["share_class"],
            "exchange": row["exchange"], "status": row["status"], "source_id": row["source_id"],
        })
    universe_digest = hashlib.sha256(_canonical({
        "contract_id": "V4_MARKET_UNIVERSE_COMPLETENESS_R1", "contract_version": "1.0.0",
        "trade_date": universe_doc.get("trade_date"), "universe_id": universe_doc.get("universe_id"),
        "exchange_scope": ["BSE", "SSE", "SZSE"],
        "securities": sorted(normalized_universe, key=lambda item: item["security_id"]),
    })).hexdigest()
    if universe_doc.get("universe_sha256") != universe_digest:
        raise SourceIngestError("SECURITY_UNIVERSE_DIGEST_MISMATCH")
    bar_keys: set[str] = set()
    board_counts = {board: 0 for board in _TDX_BOARD_SCOPES}
    for row in target_bars:
        key = str(row.get("source_security_key") or "").strip().upper()
        if key in out_of_scope_a_shares:
            if str(row.get("trading_status", row.get("trade_status", "TRADING"))).upper() not in {
                "TRADING", "TRADED", "SUSPENDED",
            }:
                raise SourceIngestError("TDX_TARGET_TRADING_STATUS_INVALID:" + key)
            continue
        if key not in expected:
            raise SourceIngestError("TDX_TARGET_SECURITY_OUTSIDE_A_SHARE_ROSTER:" + (key or "<empty>"))
        if key in bar_keys:
            raise SourceIngestError("TDX_TARGET_SECURITY_DUPLICATE:" + key)
        bar_keys.add(key)
        board, lifecycle = expected[key]
        declared_status = str(row.get("trading_status", row.get("trade_status", "TRADING"))).upper()
        if declared_status not in {"TRADING", "TRADED", "SUSPENDED"}:
            raise SourceIngestError("TDX_TARGET_TRADING_STATUS_INVALID:" + key)
        if lifecycle == "SUSPENDED":
            if declared_status not in {"SUSPENDED", "TRADING", "TRADED"}:
                raise SourceIngestError("TDX_SUSPENDED_SECURITY_STATUS_MISMATCH:" + key)
        else:
            if declared_status == "SUSPENDED":
                raise SourceIngestError("TDX_ACTIVE_SECURITY_REPORTED_SUSPENDED:" + key)
            board_counts[board] += 1
    for key, (board, lifecycle) in expected.items():
        if lifecycle != "SUSPENDED" and key not in bar_keys:
            raise SourceIngestError("TDX_ACTIVE_A_SHARE_MISSING_AT_T0:" + board + ":" + key)
        if lifecycle == "SUSPENDED" and key in bar_keys:
            # Some native snapshots retain a status row for a suspended code;
            # that is valid identity evidence, but it is not a traded bar.
            continue
    empty = [board for board, count in board_counts.items() if count == 0]
    if empty:
        raise SourceIngestError("TDX_A_SHARE_BOARD_HAS_NO_TRADING_ROWS:" + ",".join(empty))
    return {"board_counts": board_counts, "suspended_counts": suspended,
            "roster_count": len(entries), "scope_roster_count": len(expected),
            "trading_row_count": sum(board_counts.values()),
            "suspended_row_count": sum(suspended.values()),
            "trading_keys": sorted(key for key, (_, status) in expected.items() if status != "SUSPENDED"),
            "roster_sha256": hashlib.sha256(_canonical(sorted(
                [{"source_security_key": key, "board_scope": board, "lifecycle_status": status}
                 for key, (board, status) in expected.items()], key=lambda item: item["source_security_key"]
            ))).hexdigest()}


def _verified_tdx_raw_bars(target_bars: list[Mapping[str, Any]], target_date: str) -> tuple[list[dict[str, Any]], str]:
    """Validate and digest the native unadjusted TDX OHLCVA rows."""
    normalized = []
    for row in target_bars:
        if row.get("trade_date") != target_date:
            raise SourceIngestError("TDX_RAW_BAR_T0_MISMATCH")
        values = {}
        for key in ("open", "high", "low", "close", "amount", "volume"):
            value = row.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise SourceIngestError("TDX_RAW_OHLCVA_VALUE_INVALID:" + key)
            values[key] = value
        if (values["low"] <= 0 or values["open"] <= 0 or values["close"] <= 0
                or values["high"] < max(values["open"], values["close"])
                or values["low"] > min(values["open"], values["close"])
                or values["amount"] < 0 or values["volume"] < 0):
            raise SourceIngestError("TDX_RAW_OHLCVA_RANGE_INVALID")
        if (not isinstance(row.get("source_entry"), str) or not row["source_entry"]
                or not isinstance(row.get("entry_sha256"), str)
                or not _SHA256.fullmatch(row["entry_sha256"])):
            raise SourceIngestError("TDX_RAW_ENTRY_PROVENANCE_MISSING")
        normalized.append({
            "source_security_key": str(row.get("source_security_key") or "").strip().upper(),
            "trade_date": target_date, **values,
            "source_entry": row["source_entry"], "entry_sha256": row["entry_sha256"],
        })
    normalized.sort(key=lambda item: item["source_security_key"])
    return normalized, hashlib.sha256(_canonical(normalized)).hexdigest()


def _load_bound_file(root: Path, ref: Mapping[str, Any], *, code: str) -> tuple[Path, str, int]:
    relative, expected = ref.get("path"), ref.get("sha256")
    if not isinstance(relative, str) or not relative or not isinstance(expected, str) or not _SHA256.fullmatch(expected):
        raise SourceIngestError(code + "_BINDING_INVALID")
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise SourceIngestError(code + "_PATH_OUTSIDE_PROJECT") from exc
    if not path.is_file():
        raise SourceIngestError(code + "_FILE_MISSING")
    actual = _file_sha256(path)
    if actual != expected:
        raise SourceIngestError(code + "_DIGEST_MISMATCH")
    return path, actual, path.stat().st_size


def _tdx_package_metadata(freeze: Mapping[str, Any], trade_date: str) -> list[dict[str, Any]]:
    """Build separately identified, date-bound TDX package source facts.

    ZIP bytes remain in the configured read-only source snapshot. The PG fact
    stores their verified immutable identity, source revision and first
    availability clock, while the normalized target-session rows are stored
    as their own byte-bound source fact below.
    """
    effective = freeze.get("effective_package")
    if not isinstance(effective, Mapping):
        return []
    download = effective.get("download")
    if not isinstance(download, Mapping):
        return []
    package_sha = download.get("sha256")
    byte_count = download.get("bytes")
    if not isinstance(package_sha, str) or not _SHA256.fullmatch(package_sha):
        raise SourceIngestError("TDX_PACKAGE_SOURCE_DIGEST_INVALID")
    if isinstance(byte_count, bool) or not isinstance(byte_count, int) or byte_count <= 0:
        raise SourceIngestError("TDX_PACKAGE_SOURCE_BYTE_COUNT_INVALID")
    provider_date = effective.get("provider_package_date", effective.get("update_date"))
    try:
        provider_date = date.fromisoformat(str(provider_date)).isoformat()
    except ValueError as exc:
        raise SourceIngestError("TDX_PACKAGE_PROVIDER_DATE_INVALID") from exc
    if provider_date < trade_date:
        raise SourceIngestError("TDX_PACKAGE_PROVIDER_DATE_PRECEDES_T0")
    transport = effective.get("source_transport_v2")
    available_at = (transport.get("received_at") if isinstance(transport, Mapping)
                    else effective.get("downloaded_at"))
    available_at = _utc_timestamp(available_at, "TDX_PACKAGE_FIRST_AVAILABLE_AT_INVALID")
    validation = effective.get("zip_validation")
    if not isinstance(validation, Mapping) or validation.get("status") != "PASS" or validation.get("crc_integrity") != "PASS":
        raise SourceIngestError("TDX_PACKAGE_ZIP_VALIDATION_REQUIRED")
    entry = {
        "source_id": "TDX_OFFICIAL_DAILY_CURRENT_PACKAGE_R1",
        "source_key": "tdx_package_current",
        "provider": "TDX_OFFICIAL_DAILY_PACKAGE",
        "T0": trade_date,
        "provider_package_date": provider_date,
        "source_revision_number": effective.get("source_revision_number"),
        "package_sha256": package_sha,
        "package_bytes": byte_count,
        "first_available_at": available_at,
        "parser_contract": "TDX_DAY_TARGET_SESSION_V2",
        "zip_validation": dict(validation),
        "AS_RECORDED": False,
        "PIT_ELIGIBLE": False,
        "source_role": "OFFICIAL_CURRENT_PACKAGE",
    }
    revision = entry["source_revision_number"]
    if isinstance(revision, bool) or not isinstance(revision, int) or revision <= 0:
        raise SourceIngestError("TDX_PACKAGE_REVISION_NUMBER_INVALID")
    result = [entry]
    fallback = effective.get("local_fallback_receipt")
    if isinstance(fallback, Mapping):
        fallback_sha = fallback.get("sha256")
        if not isinstance(fallback_sha, str) or not _SHA256.fullmatch(fallback_sha):
            raise SourceIngestError("TDX_LOCAL_COMPOSITE_SOURCE_DIGEST_INVALID")
        result.append({
            "source_id": "TDX_LOCAL_DATED_FALLBACK_COMPOSITE_R1",
            "source_key": "tdx_local_composite",
            "provider": "TDX_READ_ONLY_LOCAL_NATIVE_PLUS_OFFICIAL_PACKAGE",
            "T0": trade_date,
            "source_revision_number": 1,
            "package_sha256": fallback_sha,
            "package_bytes": None,
            "first_available_at": available_at,
            "parser_contract": "TDX_LOCAL_DATED_FALLBACK_V1",
            "zip_validation": None,
            "AS_RECORDED": False,
            "PIT_ELIGIBLE": False,
            "source_role": "DERIVED_LOCAL_COMPOSITE_CANDIDATE",
            "official_package_sha256": package_sha,
        })
    return result


def _utc_timestamp(value: Any, code: str) -> str:
    if not isinstance(value, str):
        raise SourceIngestError(code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceIngestError(code) from exc
    if parsed.tzinfo is None:
        raise SourceIngestError(code)
    return parsed.astimezone(timezone.utc).isoformat()


def build_source_ingest_plan(
    project_root: str | Path,
    *,
    trade_date: str,
    source_freeze: Mapping[str, Any],
    source_readiness: Mapping[str, Any] | None = None,
    acceptance_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify a real executor freeze and return a deterministic, non-writing PG plan.

    A caller-provided self-hashed receipt is never an authority. Since no
    independent acceptance authority is wired to this adapter, all plans stay
    diagnostic until one is integrated and independently verified.
    """
    try:
        target = date.fromisoformat(trade_date)
    except (TypeError, ValueError) as exc:
        raise SourceIngestError("TARGET_TRADE_DATE_INVALID") from exc
    if target.isoformat() != trade_date:
        raise SourceIngestError("TARGET_TRADE_DATE_NONCANONICAL")
    if not isinstance(source_freeze, Mapping):
        raise SourceIngestError("SOURCE_FREEZE_BINDING_REQUIRED")
    root = Path(project_root).resolve()
    freeze_path, freeze_sha, freeze_bytes = _load_bound_file(root, source_freeze, code="SOURCE_FREEZE")
    try:
        freeze = json.loads(freeze_path.read_bytes())
    except (OSError, ValueError) as exc:
        raise SourceIngestError("SOURCE_FREEZE_JSON_INVALID") from exc
    if (not isinstance(freeze, Mapping)
            or freeze.get("contract_id") != "DYNAMIC_DAILY_SOURCE_FREEZE_V1"
            or freeze.get("target_session") != target.isoformat()):
        raise SourceIngestError("SOURCE_FREEZE_CONTRACT_OR_T0_MISMATCH")
    if freeze.get("canonical_qfq_authority") != "TDX_GBBQ_UNCHANGED":
        raise SourceIngestError("SOURCE_FREEZE_PRICE_BASIS_UNSUPPORTED")
    readiness_doc = None
    readiness_sha = None
    if source_readiness is not None:
        readiness_path, readiness_sha, _ = _load_bound_file(root, source_readiness, code="SOURCE_READINESS")
        try:
            readiness_doc = json.loads(readiness_path.read_bytes())
        except (OSError, ValueError) as exc:
            raise SourceIngestError("SOURCE_READINESS_JSON_INVALID") from exc
        if (not isinstance(readiness_doc, Mapping)
                or readiness_doc.get("contract_id") != "V4_DAILY_SOURCE_READINESS_V2"
                or readiness_doc.get("trade_date") != target.isoformat()
                or readiness_doc.get("source_freeze", {}).get("sha256") != freeze_sha):
            raise SourceIngestError("SOURCE_READINESS_FREEZE_BINDING_MISMATCH")

    sources = {}
    tdx_document: Mapping[str, Any] | None = None
    tdx_raw_sha256: str | None = None
    for name in _SOURCE_NAMES:
        ref = freeze.get(name) if name != "runtime_manifest" else freeze.get("runtime_manifest")
        if not isinstance(ref, Mapping):
            raise SourceIngestError("SOURCE_FAMILY_MISSING:" + name)
        path, sha, byte_count = _load_bound_file(root, ref, code="SOURCE_FAMILY_" + name.upper())
        if name == "tdx":
            try:
                document = json.loads(path.read_bytes())
            except (OSError, ValueError) as exc:
                raise SourceIngestError("TDX_BAR_ARTIFACT_INVALID") from exc
            if (not isinstance(document, Mapping) or document.get("target_session") != target.isoformat()
                    or not isinstance(document.get("target_bars"), list) or not document["target_bars"]):
                raise SourceIngestError("TDX_BAR_ARTIFACT_T0_OR_ROWS_INVALID")
            tdx_document = document
            _, tdx_raw_sha256 = _verified_tdx_raw_bars(document["target_bars"], target.isoformat())
            security_keys = [str(row.get("source_security_key") or "") for row in document["target_bars"]]
            if (any(not key for key in security_keys) or len(security_keys) != len(set(security_keys))
                    or any(str(row.get("trade_date") or "") != target.isoformat()
                           for row in document["target_bars"])):
                raise SourceIngestError("TDX_BAR_ARTIFACT_IDENTITY_INVALID")
            record_count = len(document["target_bars"])
            locator = {"path": ref["path"], "record_count": record_count,
                       "first_security_key": str(document["target_bars"][0].get("source_security_key", "")),
                       "last_security_key": str(document["target_bars"][-1].get("source_security_key", ""))}
        elif name == "native_baostock":
            try:
                document = json.loads(path.read_bytes())
            except (OSError, ValueError) as exc:
                raise SourceIngestError("BAOSTOCK_NATIVE_RESPONSE_INVALID") from exc
            if (not isinstance(document, Mapping) or document.get("target_date") != target.isoformat()
                    or not isinstance(document.get("daily_rows"), list)
                    or not isinstance(document.get("adjustment_factor_rows"), list)):
                raise SourceIngestError("BAOSTOCK_NATIVE_RESPONSE_T0_OR_ROWS_INVALID")
            record_count = None
            locator = {"path": ref["path"], "response_sha256": sha,
                       "daily_row_count": len(document["daily_rows"]),
                       "factor_row_count": len(document["adjustment_factor_rows"]),
                       "role": "RAW_DAILY_CROSSCHECK_AND_FACTOR_AUDIT"}
        else:
            record_count = None
            locator = {"path": ref["path"], "manifest_sha256": sha, "role": "RUNTIME_ACCEPTANCE"}
        fact = {
            "source_key": name,
            "logical_fact_id": f"daily-source:{target.isoformat()}:{name}",
            "record_locator": locator,
            "source_fact_sha256": sha,
            "record_count": record_count,
            "byte_count": byte_count,
        }
        fact["fact_digest"] = hashlib.sha256(_canonical(fact)).hexdigest()
        sources[name] = fact

    # The same-T0 security master is a separate source family from the Core
    # bar rowset. Older freezes may omit it and remain diagnostic, but they
    # cannot receive source acceptance.
    universe_ref = freeze.get("security_universe")
    universe_source_keys: set[str] | None = None
    universe_doc: Mapping[str, Any] | None = None
    if universe_ref is not None:
        universe_path, universe_sha, universe_bytes = _load_bound_file(root, universe_ref, code="SECURITY_UNIVERSE")
        try:
            universe_doc = json.loads(universe_path.read_bytes())
        except (OSError, ValueError) as exc:
            raise SourceIngestError("SECURITY_UNIVERSE_JSON_INVALID") from exc
        if (not isinstance(universe_doc, Mapping)
                or universe_doc.get("contract_id") != "V4_MARKET_UNIVERSE_COMPLETENESS_R1"
                or universe_doc.get("trade_date") != target.isoformat()
                or not isinstance(universe_doc.get("universe_id"), str)
                or not isinstance(universe_doc.get("securities"), list)
                or not universe_doc.get("securities")):
            raise SourceIngestError("SECURITY_UNIVERSE_CONTRACT_T0_OR_ROWS_INVALID")
        if universe_doc.get("exchange_scope") != ["SSE", "SZSE", "BSE"]:
            raise SourceIngestError("SECURITY_UNIVERSE_EXCHANGE_SCOPE_NOT_EXPLICIT")
        if not isinstance(universe_doc.get("universe_sha256"), str) or not _SHA256.fullmatch(universe_doc["universe_sha256"]):
            raise SourceIngestError("SECURITY_UNIVERSE_DIGEST_REQUIRED")
        universe_doc = universe_doc
        universe_ids = [str(row.get("security_id") or "").strip().upper()
                        for row in universe_doc["securities"] if isinstance(row, Mapping)]
        universe_source_keys = {
            str(row.get("source_security_key") or row.get("security_id") or "").strip().upper()
            for row in universe_doc["securities"] if isinstance(row, Mapping)
        }
        if len(universe_ids) != len(universe_doc["securities"]) or any(not sid for sid in universe_ids) or len(universe_ids) != len(set(universe_ids)):
            raise SourceIngestError("SECURITY_UNIVERSE_SECURITY_ID_INVALID")
        universe_fact = {
            "source_key": "security_universe",
            "logical_fact_id": f"daily-source:{target.isoformat()}:security_universe",
            "record_locator": {"path": universe_ref["path"], "record_count": len(universe_ids),
                               "universe_id": universe_doc["universe_id"],
                               "exchange_scope": universe_doc.get("exchange_scope"),
                               "universe_sha256": universe_doc.get("universe_sha256")},
            "source_fact_sha256": universe_sha, "record_count": len(universe_ids),
            "byte_count": universe_bytes,
        }
        universe_fact["fact_digest"] = hashlib.sha256(_canonical(universe_fact)).hexdigest()
        sources["security_universe"] = universe_fact

    # Stage00 D consumes coverage from this same immutable TDX artifact. The
    # derived fact is included in the bindings digest and independent receipt.
    if tdx_document is not None:
        if universe_doc is None:
            raise SourceIngestError("SECURITY_UNIVERSE_SAME_T0_ROSTER_REQUIRED")
        roster = _same_t0_a_share_roster(universe_doc, tdx_document["target_bars"])
        coverage_counts = {board: 0 for board in _TDX_BOARD_SCOPES}
        for row in tdx_document["target_bars"]:
            board = _tdx_board_scope(row.get("source_security_key"))
            declared = row.get("board_scope")
            if board is None or (declared is not None and declared != board):
                raise SourceIngestError("TDX_BOARD_IDENTITY_INVALID")
            if universe_source_keys is None or str(row.get("source_security_key") or "").strip().upper() not in universe_source_keys:
                raise SourceIngestError("TDX_UNIVERSE_SOURCE_BINDING_MISMATCH")
            if str(row.get("source_security_key") or "").strip().upper() in roster["trading_keys"]:
                coverage_counts[board] += 1
        if coverage_counts != roster["board_counts"]:
            raise SourceIngestError("TDX_ROSTER_COVERAGE_COUNT_MISMATCH")
        coverage_body = {"boards": list(_TDX_BOARD_SCOPES), "counts": coverage_counts,
                         "target_trade_date": target.isoformat(),
                         "universe_id": universe_doc["universe_id"],
                         "universe_sha256": universe_doc["universe_sha256"],
                         "roster_count": roster["roster_count"],
                         "scope_roster_count": roster["scope_roster_count"],
                         "trading_row_count": roster["trading_row_count"],
                         "suspended_row_count": roster["suspended_row_count"],
                         "suspended_counts": roster["suspended_counts"],
                         "roster_sha256": roster["roster_sha256"],
                         "tdx_ohlcva_sha256": tdx_raw_sha256}
        coverage_digest = hashlib.sha256(_canonical(coverage_body)).hexdigest()
        accepted_board_coverage = {**coverage_body, "digest": coverage_digest}
        sources["tdx_board_coverage"] = {
            "source_key": "tdx_board_coverage",
            "logical_fact_id": f"daily-source:{target.isoformat()}:tdx_board_coverage",
            "record_locator": coverage_body, "source_fact_sha256": coverage_digest,
            "record_count": sum(coverage_counts.values()),
            "byte_count": len(_canonical(coverage_body)), "fact_digest": coverage_digest,
        }
    else:
        accepted_board_coverage = None

    package_sources = _tdx_package_metadata(freeze, target.isoformat())
    for package in package_sources:
        metadata_raw = _canonical(package)
        fact = {
            "source_key": package["source_key"],
            "logical_fact_id": f"daily-source:{target.isoformat()}:{package['source_key']}:{package['package_sha256']}",
            "record_locator": {"embedded_metadata": package, "role": package["source_role"]},
            "source_fact_sha256": hashlib.sha256(metadata_raw).hexdigest(),
            "record_count": 1,
            "byte_count": len(metadata_raw),
        }
        fact["fact_digest"] = hashlib.sha256(_canonical(fact)).hexdigest()
        sources[package["source_key"]] = fact

    bindings = [sources[key] for key in sorted(sources)]
    bindings_sha = hashlib.sha256(_canonical(bindings)).hexdigest()
    proposed_acceptance_id = acceptance_receipt.get("acceptance_id") if isinstance(acceptance_receipt, Mapping) else None
    # Package identity commits the exact frozen source facts. The independent
    # receipt signs this descriptor hash; its signature is recorded outside
    # the descriptor to avoid a self-referential digest.
    descriptor = {
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "trade_date": target.isoformat(),
        "source_freeze_sha256": freeze_sha,
        "source_readiness_sha256": readiness_sha,
        "source_fact_bindings_sha256": bindings_sha,
        "price_basis": "TDX_GBBQ_UNCHANGED",
    }
    package_sha = hashlib.sha256(_canonical(descriptor)).hexdigest()
    package_id = f"v4-daily-r6-{target.strftime('%Y%m%d')}-{package_sha[:24]}"
    package_manifest = {
        **descriptor,
        "source_freeze_path": source_freeze["path"],
        "source_freeze_bytes": freeze_bytes,
        "source_freeze_contract_id": freeze["contract_id"],
        "source_observed_at": _utc_timestamp(freeze.get("observed_at"), "SOURCE_OBSERVATION_TIME_INVALID"),
        "source_readiness_observed_at": (_utc_timestamp(readiness_doc.get("observed_at"), "SOURCE_READINESS_TIME_INVALID")
                                         if isinstance(readiness_doc, Mapping) and readiness_doc.get("observed_at") is not None else None),
        "source_fact_bindings": bindings,
        "accepted_board_coverage": accepted_board_coverage,
        "tdx_source_packages": package_sources,
        "tdx_source_packages_sha256": hashlib.sha256(_canonical(package_sources)).hexdigest(),
        "adjustment_factor_role": freeze.get("factor_role"),
        "package_id": package_id,
        "package_sha256": package_sha,
        "acceptance_receipt_id": None,
        "acceptance_proof": None,
        "accepted_scope": "DIAGNOSTIC_ONLY",
        "AS_RECORDED": False,
        "PIT_ELIGIBLE": False,
    }
    accepted = False
    if isinstance(readiness_doc, Mapping) and readiness_doc.get("source_ready") is not True:
        receipt_status = "SOURCE_READINESS_NOT_READY"
    elif (isinstance(readiness_doc, Mapping)
          and (readiness_doc.get("AS_RECORDED") is not True or readiness_doc.get("PIT_ELIGIBLE") is not True
               or freeze.get("AS_RECORDED") is not True or freeze.get("PIT_ELIGIBLE") is not True)):
        receipt_status = "SOURCE_PIT_AUTHORITY_UNAVAILABLE"
    elif acceptance_receipt is not None and readiness_doc is None:
        receipt_status = "SOURCE_READINESS_REQUIRED_FOR_ACCEPTANCE"
    elif acceptance_receipt is not None and not any(row.get("source_key") == "security_universe" for row in bindings):
        receipt_status = "UNIVERSE_INDEPENDENT_SOURCE_FACT_REQUIRED_FOR_ACCEPTANCE"
    elif acceptance_receipt is not None:
        candidate_manifest = {
            **package_manifest, "acceptance_receipt_id": proposed_acceptance_id,
            "accepted_scope": "ACCEPTED_SOURCE_PACKAGE", "AS_RECORDED": True,
            "PIT_ELIGIBLE": True,
        }
        candidate = {
            "contract_id": CONTRACT_ID, "contract_version": CONTRACT_VERSION,
            "trade_date": target.isoformat(), "package_id": package_id,
            "package_sha256": package_sha, "package_manifest": candidate_manifest,
            "source_facts": bindings, "acceptance_receipt": dict(acceptance_receipt),
        }
        try:
            proof = _verify_independent_acceptance_authority(candidate)
        except SourceIngestError as exc:
            receipt_status = str(exc)
        else:
            accepted = True
            acceptance_id = proof.authority_receipt_id
            package_manifest.update({
                "acceptance_receipt_id": acceptance_id,
                "accepted_scope": "ACCEPTED_SOURCE_PACKAGE",
                "AS_RECORDED": True,
                "PIT_ELIGIBLE": True,
                "acceptance_proof": {
                    "contract_id": ACCEPTANCE_CONTRACT_ID,
                    "issuer_id": proof.authority_id,
                    "receipt_sha256": proof.receipt_sha256,
                    "accepted_at": acceptance_receipt["accepted_at"],
                    "pit_cutoff_at": acceptance_receipt["pit_cutoff_at"],
                    "receipt": dict(acceptance_receipt),
                },
            })
            for fact in bindings:
                fact["acceptance_receipt_id"] = acceptance_id
            package_manifest["source_fact_bindings"] = bindings
            receipt_status = "INDEPENDENT_ACCEPTANCE_RECEIPT_VERIFIED"
    else:
        receipt_status = "INDEPENDENT_ACCEPTANCE_AUTHORITY_REQUIRED"
    return {
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "trade_date": target.isoformat(),
        "package_id": package_id,
        "package_sha256": package_sha,
        "package_manifest": package_manifest,
        "source_facts": [sources[key] for key in sorted(sources)],
        "acceptance_receipt": dict(acceptance_receipt) if accepted and acceptance_receipt is not None else None,
        "status": "ACCEPTED" if accepted else "DIAGNOSTIC_ONLY",
        "capture_status": "CAPTURED",
        "acceptance_status": receipt_status,
        "readiness_status": "ACCEPTANCE_RECEIPT_VERIFIED" if accepted else receipt_status,
        "write_mode": "PLAN_ONLY_NO_DATABASE_IO",
        "source_readiness_embedded": readiness_doc is not None,
    }


def _persist_accepted_source_ingest_plan_transaction(
    pg: Any,
    plan: Mapping[str, Any],
    *,
    publication_id: str,
    publication_revision: int,
    ingested_at: str,
    system_available_at: str,
) -> dict[str, Any]:
    """Persist package provenance inside the caller's authorized transaction.

    This function intentionally has no DSN lookup, no commit, and no Head
    mutation. Callers must begin a transaction explicitly and must not call it
    with a production connection absent separate write authorization.
    """
    if not isinstance(plan, Mapping) or plan.get("contract_id") != CONTRACT_ID:
        raise SourceIngestError("SOURCE_INGEST_PLAN_CONTRACT_INVALID")
    if plan.get("status") != "ACCEPTED":
        return {"status": plan.get("status", "DATA_UNAVAILABLE"), "persisted": False}
    proof = _verify_independent_acceptance_authority(plan, pg=pg)
    plan_digest = hashlib.sha256(_canonical(dict(plan))).hexdigest()
    if (not isinstance(proof, _IndependentAcceptanceProof)
            or proof.plan_sha256 != plan_digest
            or not isinstance(proof.authority_receipt_id, str)
            or not proof.authority_receipt_id.strip()):
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_PROOF_INVALID")
    if not isinstance(publication_id, str) or not publication_id.strip():
        raise SourceIngestError("PUBLICATION_ID_REQUIRED")
    if isinstance(publication_revision, bool) or not isinstance(publication_revision, int) or publication_revision <= 0:
        raise SourceIngestError("PUBLICATION_REVISION_INVALID")
    ingested = _utc_timestamp(ingested_at, "INGESTED_TIME_INVALID")
    system_available = _utc_timestamp(system_available_at, "SYSTEM_AVAILABLE_TIME_INVALID")
    if system_available < max(ingested, plan["package_manifest"]["source_observed_at"]):
        raise SourceIngestError("SOURCE_SYSTEM_CLOCK_ORDER_INVALID")
    savepoint = "v4_source_ingest_r6"
    pg.execute("SAVEPOINT " + savepoint)
    try:
        # Stable package and logical-fact lock ordering makes same-package
        # retries idempotent and revision allocation race-safe.
        pg.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (plan["package_id"],))
        publication = pg.execute(
            "SELECT revision_no FROM v4.publications WHERE publication_id=%s FOR KEY SHARE",
            (publication_id,),
        ).fetchone()
        if publication is None or int(publication[0]) != publication_revision:
            raise SourceIngestConflict("PUBLICATION_IDENTITY_CONFLICT")
        manifest = plan["package_manifest"]
        if manifest.get("accepted_scope") != "ACCEPTED_SOURCE_PACKAGE":
            raise SourceIngestConflict("SOURCE_PACKAGE_AUTHORITY_NOT_ACCEPTED")
        cursor = pg.execute(
            """SELECT package_id, package_sha256, manifest, accepted_scope
                 FROM v4.source_packages WHERE package_id=%s FOR KEY SHARE""",
            (plan["package_id"],),
        )
        existing = cursor.fetchone()
        if existing:
            actual_id, actual_sha, actual_manifest, actual_scope = existing
            if (actual_id != plan["package_id"] or str(actual_sha).strip() != plan["package_sha256"]
                    or actual_manifest != manifest or actual_scope != "ACCEPTED_SOURCE_PACKAGE"):
                raise SourceIngestConflict("SOURCE_PACKAGE_REPLAY_CONFLICT")
        page_observed_at = manifest["source_observed_at"]
        if not existing:
            pg.execute(
                """INSERT INTO v4.source_packages
                   (package_id, contract_version, package_sha256, source_page_url,
                    page_observed_at, declared_update_date, target_trade_date,
                    parser_version, manifest, accepted_scope)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)""",
                (plan["package_id"], CONTRACT_VERSION, plan["package_sha256"],
                 "urn:v4:daily-source-freeze:sha256:" + manifest["source_freeze_sha256"],
                 page_observed_at, plan["trade_date"], plan["trade_date"],
                 CONTRACT_ID, json.dumps(manifest, ensure_ascii=False, sort_keys=True), "ACCEPTED_SOURCE_PACKAGE"),
            )
            for fact in plan["source_facts"]:
                pg.execute(
                    """INSERT INTO v4.source_package_facts
                       (package_id, source_key, logical_fact_id, fact_digest,
                        source_fact_sha256, record_locator, record_count, byte_count,
                        acceptance_receipt_id)
                       VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)""",
                    (plan["package_id"], fact["source_key"], fact["logical_fact_id"],
                     fact["fact_digest"], fact["source_fact_sha256"],
                     json.dumps(fact["record_locator"], ensure_ascii=False, sort_keys=True),
                     fact["record_count"], fact["byte_count"], manifest["acceptance_receipt_id"]),
                )
        for logical_fact_id in sorted(f["logical_fact_id"] for f in plan["source_facts"]):
            pg.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (logical_fact_id,))
        persisted_facts = 0
        for fact in plan["source_facts"]:
            logical_fact_id = fact["logical_fact_id"]
            source_revision_id = "v4sr-" + hashlib.sha256(_canonical({
                "package_id": plan["package_id"], "source_key": fact["source_key"],
                "fact_digest": fact["fact_digest"],
            })).hexdigest()[:40]
            payload = {
                "contract_id": CONTRACT_ID, "contract_version": CONTRACT_VERSION,
                "source_key": fact["source_key"], "source_fact_sha256": fact["source_fact_sha256"],
                "producer_receipt_id": plan["package_manifest"]["acceptance_receipt_id"],
                "package_id": plan["package_id"], "record_locator": fact["record_locator"],
                "record_count": fact["record_count"],
            }
            current = pg.execute(
                "SELECT logical_fact_id,revision_no,digest,payload,source_package_id,source_package_source_key,source_fact_digest "
                "FROM v4.source_revisions WHERE source_revision_id=%s FOR KEY SHARE",
                (source_revision_id,),
            ).fetchone()
            if current:
                observed_payload = current[3]
                if (current[0] != fact["logical_fact_id"] or str(current[2]).strip() != fact["fact_digest"]
                        or current[4] != plan["package_id"] or current[5] != fact["source_key"]
                        or str(current[6]).strip() != fact["fact_digest"] or observed_payload != payload):
                    raise SourceIngestConflict("SOURCE_REVISION_REPLAY_CONFLICT")
            else:
                prior = pg.execute(
                    """SELECT revision_no,source_revision_id FROM v4.source_revisions
                        WHERE logical_fact_id=%s ORDER BY revision_no DESC LIMIT 1 FOR KEY SHARE""",
                    (logical_fact_id,),
                ).fetchone()
                revision_no = int(prior[0]) + 1 if prior else 1
                supersedes_revision_id = prior[1] if prior else None
                pg.execute(
                    """INSERT INTO v4.source_revisions
                       (source_revision_id, logical_fact_id, revision_no, payload, digest,
                        effective_from, effective_to, provider_available_at, observed_at,
                        ingested_at, system_available_at, source_package_id,
                        source_package_source_key, source_fact_digest, supersedes_revision_id)
                       VALUES (%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (source_revision_id, logical_fact_id, revision_no, json.dumps(payload, ensure_ascii=False, sort_keys=True),
                     fact["fact_digest"], plan["trade_date"], plan["trade_date"],
                     plan["package_manifest"]["source_observed_at"], plan["package_manifest"]["source_observed_at"],
                     ingested, system_available, plan["package_id"], fact["source_key"], fact["fact_digest"],
                     supersedes_revision_id),
                )
            consumed = pg.execute(
                """SELECT source_revision_id,digest FROM v4.publication_consumed_sources
                    WHERE publication_id=%s AND source_key=%s FOR KEY SHARE""",
                (publication_id, fact["source_key"]),
            ).fetchone()
            if consumed:
                if consumed[0] != source_revision_id or str(consumed[1]).strip() != fact["fact_digest"]:
                    raise SourceIngestConflict("PUBLICATION_CONSUMED_SOURCE_CONFLICT")
            else:
                pg.execute(
                    """INSERT INTO v4.publication_consumed_sources
                       (publication_id, source_key, source_revision_id, digest)
                       VALUES (%s,%s,%s,%s)""",
                    (publication_id, fact["source_key"], source_revision_id, fact["fact_digest"]),
                )
            persisted_facts += 1
        pg.execute("RELEASE SAVEPOINT " + savepoint)
        return {"status": "ALREADY_PRESENT_IDENTICAL" if existing and persisted_facts else "ACCEPTED",
                "persisted": not bool(existing), "package_id": plan["package_id"],
                "source_revisions": persisted_facts, "publication_id": publication_id,
                "publication_revision": publication_revision}
    except Exception:
        pg.execute("ROLLBACK TO SAVEPOINT " + savepoint)
        pg.execute("RELEASE SAVEPOINT " + savepoint)
        raise


def persist_diagnostic_source_candidate(project_root: str | Path,
                                        plan: Mapping[str, Any]) -> dict[str, Any]:
    """Append a byte-bound, non-accepted daily source candidate to existing PG facts.

    This gives the daily pipeline a real PG landing point without turning a
    captured source into an accepted package, publication, or PIT authority.
    The exact input bytes are copied into the immutable fact so later readers
    no longer depend on the workspace receipt or source artifact remaining in
    place.
    """
    if not isinstance(plan, Mapping) or plan.get("contract_id") != CONTRACT_ID:
        raise SourceIngestError("SOURCE_INGEST_PLAN_CONTRACT_INVALID")
    if plan.get("status") == "ACCEPTED":
        raise SourceIngestError("ACCEPTED_SOURCE_PACKAGE_REQUIRES_PUBLICATION_BOUND_PERSISTENCE")
    if plan.get("status") != "DIAGNOSTIC_ONLY":
        raise SourceIngestError("SOURCE_CANDIDATE_STATUS_INVALID")
    root = Path(project_root).resolve()
    if root.drive.upper() != "G:":
        raise SourceIngestError("SOURCE_CANDIDATE_G_ROOT_REQUIRED")
    manifest = plan.get("package_manifest")
    facts = plan.get("source_facts")
    if (not isinstance(manifest, Mapping) or not isinstance(facts, list) or not facts
            or manifest.get("package_id") != plan.get("package_id")
            or manifest.get("package_sha256") != plan.get("package_sha256")):
        raise SourceIngestError("SOURCE_CANDIDATE_MANIFEST_BINDING_INVALID")
    captured = {}
    for fact in facts:
        if not isinstance(fact, Mapping) or not isinstance(fact.get("source_key"), str):
            raise SourceIngestError("SOURCE_CANDIDATE_FACT_INVALID")
        locator = fact.get("record_locator")
        if isinstance(locator, Mapping) and isinstance(locator.get("embedded_metadata"), Mapping):
            raw = _canonical(locator["embedded_metadata"])
            actual_sha = hashlib.sha256(raw).hexdigest()
            byte_count = len(raw)
        else:
            relative = locator.get("path") if isinstance(locator, Mapping) else None
            path, actual_sha, byte_count = _load_bound_file(
                root, {"path": relative, "sha256": fact.get("source_fact_sha256")},
                code="SOURCE_CANDIDATE_FACT")
            raw = path.read_bytes()
        if len(raw) != byte_count or actual_sha != fact.get("source_fact_sha256"):
            raise SourceIngestError("SOURCE_CANDIDATE_FACT_READBACK_MISMATCH")
        captured[fact["source_key"]] = {
            "source_fact_digest": fact.get("fact_digest"),
            "source_fact_sha256": actual_sha,
            "byte_count": byte_count,
            "record_count": fact.get("record_count"),
            "raw_base64": base64.b64encode(raw).decode("ascii"),
        }
    record = {
        "contract_id": "V4_DAILY_SOURCE_DIAGNOSTIC_CANDIDATE_PG_R1",
        "contract_version": "1.0.0",
        "candidate_status": "DIAGNOSTIC_ONLY",
        "acceptance_status": plan.get("acceptance_status"),
        "trade_date": plan.get("trade_date"),
        "package_id": plan.get("package_id"),
        "package_sha256": plan.get("package_sha256"),
        "package_manifest": dict(manifest),
        "source_facts": [dict(fact) for fact in facts],
        "source_bytes": captured,
        "tdx_source_packages": manifest.get("tdx_source_packages", []),
        "tdx_source_packages_sha256": manifest.get("tdx_source_packages_sha256"),
        "AS_RECORDED": False,
        "PIT_ELIGIBLE": False,
        "publication_id": None,
        "accepted_head": False,
    }
    from .v4_forward_pg_r1 import ForwardFactStore
    folder = "data/v4/historical_source_ingress_pg_r1"
    store = ForwardFactStore(
        root, folder, workspace_namespace="V4_STAGE00_SOURCE_INGRESS_DIAGNOSTIC_R1",
    )
    binding = store.append("daily_source_candidate", str(plan["package_id"]), record,
                           migration_timeout_seconds=120)
    readback = store.read(binding)
    if readback != record:
        raise SourceIngestConflict("SOURCE_CANDIDATE_PG_READBACK_MISMATCH")
    return {"contract_id": record["contract_id"], "candidate_status": "DIAGNOSTIC_ONLY",
            "trade_date": record["trade_date"], "package_id": record["package_id"],
            "package_sha256": record["package_sha256"], "source_fact_count": len(facts),
            "persisted": True, "readback": "PASS", "binding": binding}


def persist_source_ingest_plan(
    pg: Any,
    plan: Mapping[str, Any],
    *,
    publication_id: str,
    publication_revision: int,
    ingested_at: str,
    system_available_at: str,
) -> dict[str, Any]:
    """Persist a plan verified against the PG-approved issuer registry.

    The caller owns the surrounding transaction and its commit/rollback. This
    entry point performs no DSN lookup, commit, or publication Head mutation.
    """
    if not isinstance(plan, Mapping) or plan.get("contract_id") != CONTRACT_ID:
        raise SourceIngestError("SOURCE_INGEST_PLAN_CONTRACT_INVALID")
    if plan.get("status") != "ACCEPTED":
        return {"status": plan.get("status", "DATA_UNAVAILABLE"), "persisted": False}
    proof = _verify_independent_acceptance_authority(plan, pg=pg)
    return _persist_accepted_source_ingest_plan_transaction(
        pg, plan,
        publication_id=publication_id,
        publication_revision=publication_revision,
        ingested_at=ingested_at,
        system_available_at=system_available_at,
    )
