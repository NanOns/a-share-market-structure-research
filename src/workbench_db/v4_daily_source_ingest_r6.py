"""Fail-closed source-package planning for the live V4 daily freeze (R6).

The current operational producer freezes its exact inputs to immutable files.
This adapter verifies those bytes and plans a PG package/revision transaction;
it does not connect to PG or promote an unaccepted freeze.  In particular,
the current executor's AS_RECORDED=False / PIT_ELIGIBLE=False freeze remains
diagnostic until a matching, independently accepted readiness receipt exists.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping


CONTRACT_ID = "V4_DAILY_SOURCE_INGEST_ADAPTER_R6"
CONTRACT_VERSION = "1.0.0"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_NAMES = ("tdx", "native_baostock", "runtime_manifest")


class SourceIngestError(ValueError):
    pass


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

    An accepted package requires a separate immutable acceptance receipt that
    binds both the freeze digest and readiness digest, confirms the exact T0,
    and explicitly marks PIT qualification. The current operational executor
    emits no such receipt, so its freezes can only produce diagnostic plans.
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
                or readiness_doc.get("target_session") != target.isoformat()
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

    readiness = freeze.get("source_readiness")
    # The executor freeze does not inline the gate receipt. Accept only an
    # independently hash-bound receipt with exact artifact and target identity.
    accepted = False
    receipt_status = "ACCEPTANCE_RECEIPT_MISSING" if acceptance_receipt is None else "ACCEPTANCE_RECEIPT_REJECTED"
    acceptance_id = None
    if isinstance(acceptance_receipt, Mapping):
        receipt = dict(acceptance_receipt)
        receipt_digest = receipt.pop("receipt_sha256", None)
        calculated = hashlib.sha256(_canonical(receipt)).hexdigest()
        accepted = (
            receipt_digest == calculated
            and receipt.get("contract_id") == "V4_DAILY_SOURCE_ACCEPTANCE_RECEIPT_R1"
            and receipt.get("trade_date") == target.isoformat()
            and receipt.get("source_freeze_sha256") == freeze_sha
            and readiness_sha is not None
            and receipt.get("source_readiness_sha256") == readiness_sha
            and receipt.get("source_ready") is True
            and receipt.get("as_recorded") is True
            and receipt.get("pit_eligible") is True
            and isinstance(readiness_doc, Mapping)
            and readiness_doc.get("source_ready") is True
            and readiness_doc.get("AS_RECORDED") is True
            and readiness_doc.get("PIT_ELIGIBLE") is True
            and freeze.get("AS_RECORDED") is True
            and freeze.get("PIT_ELIGIBLE") is True
            and isinstance(receipt.get("accepted_at"), str)
        )
        if accepted:
            receipt_status = "ACCEPTANCE_RECEIPT_VERIFIED"
            accepted_at = _utc_timestamp(receipt["accepted_at"], "ACCEPTANCE_TIME_INVALID")
            acceptance_id = receipt.get("acceptance_id")
            if not isinstance(acceptance_id, str) or not acceptance_id.strip():
                accepted = False
            elif datetime.fromisoformat(accepted_at) < datetime.fromisoformat(
                    _utc_timestamp(freeze.get("observed_at"), "SOURCE_OBSERVATION_TIME_INVALID")):
                accepted = False
            else:
                for fact in sources.values():
                    fact["acceptance_receipt_id"] = acceptance_id
                    fact["fact_digest"] = hashlib.sha256(_canonical({
                        key: value for key, value in fact.items() if key != "fact_digest"
                    })).hexdigest()
        else:
            receipt_status = "ACCEPTANCE_RECEIPT_REJECTED"
    package_manifest = {
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "trade_date": target.isoformat(),
        "source_freeze_path": source_freeze["path"],
        "source_freeze_sha256": freeze_sha,
        "source_freeze_bytes": freeze_bytes,
        "source_freeze_contract_id": freeze["contract_id"],
        "source_observed_at": _utc_timestamp(freeze.get("observed_at"), "SOURCE_OBSERVATION_TIME_INVALID"),
        "source_readiness_sha256": readiness_sha,
        "source_fact_bindings": [sources[key] for key in sorted(sources)],
        "price_basis": "TDX_GBBQ_UNCHANGED",
        "adjustment_factor_role": freeze.get("factor_role"),
        "acceptance_receipt_id": acceptance_id,
        "accepted_scope": "ACCEPTED_SOURCE_PACKAGE" if accepted else "DIAGNOSTIC_ONLY",
    }
    package_sha = hashlib.sha256(_canonical(package_manifest)).hexdigest()
    package_id = f"v4-daily-r6-{target.strftime('%Y%m%d')}-{package_sha[:24]}"
    return {
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "trade_date": target.isoformat(),
        "package_id": package_id,
        "package_sha256": package_sha,
        "package_manifest": package_manifest,
        "source_facts": [sources[key] for key in sorted(sources)],
        "status": "ACCEPTED" if accepted else "DIAGNOSTIC_ONLY",
        "capture_status": "CAPTURED",
        "acceptance_status": receipt_status,
        "readiness_status": "ACCEPTANCE_RECEIPT_VERIFIED" if accepted else receipt_status,
        "write_mode": "PLAN_ONLY_NO_DATABASE_IO",
        "source_readiness_embedded": readiness_doc is not None,
    }


def persist_source_ingest_plan(
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
    if not isinstance(publication_id, str) or not publication_id.strip():
        raise SourceIngestError("PUBLICATION_ID_REQUIRED")
    if isinstance(publication_revision, bool) or not isinstance(publication_revision, int) or publication_revision <= 0:
        raise SourceIngestError("PUBLICATION_REVISION_INVALID")
    ingested = _utc_timestamp(ingested_at, "INGESTED_TIME_INVALID")
    system_available = _utc_timestamp(system_available_at, "SYSTEM_AVAILABLE_TIME_INVALID")
    if system_available < max(ingested, plan["package_manifest"]["source_observed_at"]):
        raise SourceIngestError("SOURCE_SYSTEM_CLOCK_ORDER_INVALID")
    cursor = pg.execute(
        """SELECT package_id, package_sha256 FROM v4.source_packages
            WHERE package_id=%s FOR KEY SHARE""",
        (plan["package_id"],),
    )
    existing = cursor.fetchone()
    if existing:
        actual_id, actual_sha = existing[0], str(existing[1]).strip()
        if actual_id != plan["package_id"] or actual_sha != plan["package_sha256"]:
            return {"status": "CONFLICTING_REPLAY", "persisted": False}
        # Continue exact revision/consumed-source validation; an existing
        # package alone does not prove that the publication lineage is present.
    manifest = plan["package_manifest"]
    if manifest.get("accepted_scope") != "ACCEPTED_SOURCE_PACKAGE":
        return {"status": "REJECTED", "persisted": False}
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
    persisted_facts = 0
    for fact in plan["source_facts"]:
        logical_fact_id = fact["logical_fact_id"]
        pg.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (logical_fact_id,))
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
                return {"status": "CONFLICTING_REPLAY", "persisted": False}
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
                WHERE publication_id=%s AND revision=%s AND source_key=%s FOR KEY SHARE""",
            (publication_id, publication_revision, fact["source_key"]),
        ).fetchone()
        if consumed:
            if consumed[0] != source_revision_id or str(consumed[1]).strip() != fact["fact_digest"]:
                return {"status": "CONFLICTING_REPLAY", "persisted": False}
        else:
            pg.execute(
                """INSERT INTO v4.publication_consumed_sources
                   (publication_id, revision, source_key, source_revision_id, digest)
                   VALUES (%s,%s,%s,%s,%s)""",
                (publication_id, publication_revision, fact["source_key"], source_revision_id, fact["fact_digest"]),
            )
        persisted_facts += 1
    return {"status": "ALREADY_PRESENT_IDENTICAL" if existing and persisted_facts else "ACCEPTED",
            "persisted": not bool(existing), "package_id": plan["package_id"],
            "source_revisions": persisted_facts, "publication_id": publication_id,
            "publication_revision": publication_revision}
