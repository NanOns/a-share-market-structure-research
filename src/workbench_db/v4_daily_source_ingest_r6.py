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
from zoneinfo import ZoneInfo
from pathlib import Path
import re
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


CONTRACT_ID = "V4_DAILY_SOURCE_INGEST_ADAPTER_R6"
CONTRACT_VERSION = "1.1.0"
ACCEPTANCE_CONTRACT_ID = "V4_DAILY_SOURCE_ACCEPTANCE_RECEIPT_R2"
ACCEPTANCE_AUTHORITY_REGISTRY = Path(__file__).resolve().parents[2] / "config" / "v4_daily_source_acceptance_authorities_r1.json"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_NAMES = ("tdx", "native_baostock", "runtime_manifest")


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


def _verify_independent_acceptance_authority(plan: Mapping[str, Any]) -> _IndependentAcceptanceProof:
    """Verify an Ed25519 receipt against the repository-pinned issuer registry.

    The registry is intentionally empty until an independent issuer is
    separately approved and its public key is installed. A caller-supplied
    public key or self-hash is never treated as trust material.
    """
    receipt = plan.get("acceptance_receipt")
    if not isinstance(receipt, Mapping):
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_RECEIPT_REQUIRED")
    try:
        registry = json.loads(ACCEPTANCE_AUTHORITY_REGISTRY.read_bytes())
    except (OSError, ValueError) as exc:
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_AUTHORITY_UNAVAILABLE") from exc
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
        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(issuer["public_key_b64"], validate=True))
        public_key.verify(base64.b64decode(signature_text, validate=True), _canonical(signed))
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
        "as_recorded": True,
        "pit_eligible": True,
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
    if accepted_at > signed_at or signed_at > pit_cutoff_at or observed_at is None or observed_at > pit_cutoff_at:
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_TIME_ORDER_INVALID")
    target = date.fromisoformat(str(plan.get("trade_date")))
    cutoff = datetime.fromisoformat(pit_cutoff_at.replace("Z", "+00:00")).astimezone(ZoneInfo("Asia/Shanghai"))
    if cutoff.date() != target or cutoff.time() > time(15, 0):
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_CUTOFF_NOT_SAME_DAY")
    _receipt_id = receipt.get("acceptance_id")
    if not isinstance(_receipt_id, str) or not _receipt_id.strip():
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_RECEIPT_ID_INVALID")
    return _IndependentAcceptanceProof(
        hashlib.sha256(_canonical(dict(plan))).hexdigest(), _receipt_id,
        str(issuer_id), receipt_sha,
    )


def verify_source_package_manifest_authority(manifest: Mapping[str, Any]) -> dict[str, str]:
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
    verified = _verify_independent_acceptance_authority(plan)
    if (proof.get("receipt_sha256") != verified.receipt_sha256
            or proof.get("issuer_id") != verified.authority_id
            or proof.get("contract_id") != ACCEPTANCE_CONTRACT_ID):
        raise SourceIngestError("INDEPENDENT_ACCEPTANCE_PERSISTED_PROOF_MISMATCH")
    return {"issuer_id": verified.authority_id, "receipt_sha256": verified.receipt_sha256}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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
        universe_ids = [str(row.get("security_id") or "").strip().upper()
                        for row in universe_doc["securities"] if isinstance(row, Mapping)]
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
        "source_fact_bindings": bindings,
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
    proof = _verify_independent_acceptance_authority(plan)
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


def persist_source_ingest_plan(
    pg: Any,
    plan: Mapping[str, Any],
    *,
    publication_id: str,
    publication_revision: int,
    ingested_at: str,
    system_available_at: str,
) -> dict[str, Any]:
    """Public persistence entry point, blocked until independent authority exists.

    Neither this adapter nor its caller-supplied mappings can verify an
    independent acceptance authority today. In particular, a hand-built plan
    with ``status=ACCEPTED`` must not reach any SQL write.
    """
    if not isinstance(plan, Mapping) or plan.get("contract_id") != CONTRACT_ID:
        raise SourceIngestError("SOURCE_INGEST_PLAN_CONTRACT_INVALID")
    if plan.get("status") != "ACCEPTED":
        return {"status": plan.get("status", "DATA_UNAVAILABLE"), "persisted": False}
    raise SourceIngestError("INDEPENDENT_ACCEPTANCE_AUTHORITY_UNAVAILABLE")
