"""Append-only PG storage and independently rechecked readback for V4 Universe.

This module does not open connections or commit transactions. Writers require
the caller's explicit PG writer connection; readers require an already active
READ ONLY + REPEATABLE READ transaction. Neither caller mappings nor fixture
snapshots can construct the sealed readback capability.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from .v4_market_universe_completeness_r1 import (
    CONTRACT_ID, CONTRACT_VERSION, MarketUniverseError,
    evaluate_market_universe_completeness,
)

_SHA = re.compile(r"^[0-9a-f]{64}$")
_PROOF = object()
READBACK_CONTRACT_ID = "V4_UNIVERSE_PG_READBACK_R2"
READBACK_CONTRACT_VERSION = "1.0.0"


class UniversePgError(ValueError):
    pass


@dataclass(frozen=True)
class VerifiedUniverseReadback:
    readback_contract_id: str
    readback_contract_version: str
    publication_id: str
    publication_revision: int
    trade_date: str
    source_manifest_sha256: str
    source_package_id: str
    source_package_sha256: str
    source_fact_sha256: str
    logical_fact_id: str
    fact_digest: str
    acceptance_receipt_id: str
    acceptance_receipt_sha256: str
    acceptance_authority_id: str
    universe_id: str
    universe_contract_id: str
    universe_contract_version: str
    universe_sha256: str
    raw_artifact_sha256: str
    expected_count: int
    core_count: int
    coverage_ratio: float
    reconciliation_sha256: str
    readback_receipt_sha256: str
    status: str
    _proof: object = field(repr=False, compare=False)


def is_verified_universe_readback(value: Any) -> bool:
    if not isinstance(value, VerifiedUniverseReadback) or value._proof is not _PROOF:
        return False
    if (value.readback_contract_id != READBACK_CONTRACT_ID
            or value.readback_contract_version != READBACK_CONTRACT_VERSION
            or value.universe_contract_id != CONTRACT_ID
            or value.universe_contract_version != CONTRACT_VERSION):
        return False
    return value.readback_receipt_sha256 == _sha(_receipt_material(value))


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _receipt_material(value: VerifiedUniverseReadback) -> dict[str, Any]:
    return {key: getattr(value, key) for key in (
        "readback_contract_id", "readback_contract_version",
        "publication_id", "publication_revision", "trade_date", "source_manifest_sha256",
        "source_package_id", "source_package_sha256", "source_fact_sha256", "logical_fact_id",
        "fact_digest", "acceptance_receipt_id", "acceptance_receipt_sha256", "acceptance_authority_id",
        "universe_id", "universe_contract_id", "universe_contract_version", "universe_sha256",
        "raw_artifact_sha256", "expected_count", "core_count", "coverage_ratio",
        "reconciliation_sha256", "status",
    )}


def _strict_day(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if not isinstance(value, str):
        raise UniversePgError("UNIVERSE_TRADE_DATE_INVALID")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise UniversePgError("UNIVERSE_TRADE_DATE_INVALID") from exc
    if parsed.isoformat() != value:
        raise UniversePgError("UNIVERSE_TRADE_DATE_NONCANONICAL")
    return value


def build_universe_persistence_plan(*, publication_id: str, publication_revision: int,
                                    trade_date: str, source_manifest_sha256: str,
                                    accepted_source_package_plan: Mapping[str, Any],
                                    raw_snapshot_bytes: bytes, snapshot: Mapping[str, Any],
                                    core_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Build a deterministic append plan bound to an independently signed fact.

    The source package's `security_universe` locator must bind the exact raw
    artifact digest as well as the canonical Universe digest and row count.
    No database calls are made here and this is not evidence of persistence.
    """
    target = _strict_day(trade_date)
    if (not isinstance(publication_id, str) or not publication_id.strip()
            or isinstance(publication_revision, bool) or not isinstance(publication_revision, int)
            or publication_revision <= 0 or not _SHA.fullmatch(str(source_manifest_sha256))):
        raise UniversePgError("UNIVERSE_PUBLICATION_IDENTITY_INVALID")
    if not isinstance(raw_snapshot_bytes, bytes) or not raw_snapshot_bytes:
        raise UniversePgError("UNIVERSE_RAW_ARTIFACT_BYTES_REQUIRED")
    raw_sha = hashlib.sha256(raw_snapshot_bytes).hexdigest()
    try:
        decoded = json.loads(raw_snapshot_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UniversePgError("UNIVERSE_RAW_ARTIFACT_JSON_INVALID") from exc
    if decoded != dict(snapshot):
        raise UniversePgError("UNIVERSE_RAW_ARTIFACT_SNAPSHOT_MISMATCH")
    if not isinstance(accepted_source_package_plan, Mapping) or accepted_source_package_plan.get("status") != "ACCEPTED":
        raise UniversePgError("UNIVERSE_ACCEPTED_SOURCE_PACKAGE_REQUIRED")
    from .v4_daily_source_ingest_r6 import _verify_independent_acceptance_authority
    try:
        acceptance = _verify_independent_acceptance_authority(accepted_source_package_plan)
    except Exception as exc:
        raise UniversePgError("UNIVERSE_INDEPENDENT_ACCEPTANCE_REQUIRED") from exc
    if (accepted_source_package_plan.get("trade_date") != target
            or not acceptance.receipt_sha256 or not acceptance.authority_id):
        raise UniversePgError("UNIVERSE_ACCEPTED_PACKAGE_T0_OR_AUTHORITY_MISMATCH")
    facts = accepted_source_package_plan.get("source_facts")
    fact = next((row for row in facts if isinstance(row, Mapping) and row.get("source_key") == "security_universe"), None) if isinstance(facts, list) else None
    if not isinstance(fact, Mapping):
        raise UniversePgError("UNIVERSE_INDEPENDENT_SOURCE_FACT_MISSING")
    locator = fact.get("record_locator")
    if (not isinstance(locator, Mapping) or fact.get("source_fact_sha256") != raw_sha
            or locator.get("universe_id") != snapshot.get("universe_id")
            or locator.get("universe_sha256") != snapshot.get("universe_sha256")
            or locator.get("record_count") != len(snapshot.get("securities", ()))
            or fact.get("target_trade_date", target) != target):
        raise UniversePgError("UNIVERSE_SOURCE_FACT_BINDING_MISMATCH")
    result = evaluate_market_universe_completeness(
        trade_date=target, universe_snapshot=snapshot, core_rows=core_rows,
        accepted_source_package_plan=accepted_source_package_plan,
    )
    if result.get("status") != "PASS":
        raise UniversePgError("UNIVERSE_COMPLETENESS_NOT_PASS:" + str(result.get("reason")))
    reconciliation = result["reconciliation"]
    body = {
        "contract_id": CONTRACT_ID, "contract_version": CONTRACT_VERSION,
        "publication_id": publication_id, "publication_revision": publication_revision,
        "trade_date": target, "source_manifest_sha256": source_manifest_sha256,
        "source_package_id": accepted_source_package_plan.get("package_id"),
        "package_sha256": accepted_source_package_plan.get("package_sha256"),
        "acceptance_receipt_id": acceptance.authority_receipt_id,
        "acceptance_receipt_sha256": acceptance.receipt_sha256,
        "acceptance_authority_id": acceptance.authority_id,
        "source_key": "security_universe", "source_fact_sha256": fact["source_fact_sha256"],
        "logical_fact_id": fact["logical_fact_id"], "fact_digest": fact["fact_digest"],
        "raw_artifact_sha256": raw_sha, "universe_id": result["universe_id"],
        "universe_sha256": result["universe_sha256"],
        "exchange_scope": sorted(snapshot["exchange_scope"]),
        "expected_count": result["expected_count"], "core_count": result["core_count"],
        "coverage_ratio": result["coverage_ratio"],
        "snapshot_rows": sorted(snapshot["securities"], key=lambda x: str(x["security_id"]).encode("utf-8")),
        "reconciliation_rows": reconciliation,
        "reconciliation_sha256": _sha(reconciliation),
        "category_counts": result["category_counts"], "status": "PASS",
    }
    body["persistence_identity_sha256"] = _sha(body)
    return body


def persist_universe_snapshot(pg: Any, plan: Mapping[str, Any]) -> dict[str, Any]:
    """Append snapshot, source binding, and reconciliation in caller transaction."""
    if not isinstance(plan, Mapping) or plan.get("contract_id") != CONTRACT_ID or plan.get("status") != "PASS":
        raise UniversePgError("UNIVERSE_PERSISTENCE_PLAN_INVALID")
    if plan.get("persistence_identity_sha256") != _sha({k: v for k, v in plan.items() if k != "persistence_identity_sha256"}):
        raise UniversePgError("UNIVERSE_PERSISTENCE_PLAN_DIGEST_MISMATCH")
    from .v4_native import configured_dsn
    try:
        from psycopg.conninfo import conninfo_to_dict
        configured_writer = conninfo_to_dict(configured_dsn()).get("user")
    except Exception as exc:
        raise UniversePgError("UNIVERSE_WRITER_DSN_REQUIRED_NO_READER_FALLBACK") from exc
    if not configured_writer:
        raise UniversePgError("UNIVERSE_WRITER_ROLE_REQUIRED")
    try:
        read_only = pg.execute("SHOW transaction_read_only").fetchone()[0]
    except Exception as exc:
        raise UniversePgError("UNIVERSE_WRITE_TRANSACTION_UNVERIFIABLE") from exc
    if str(read_only).lower() in {"on", "true", "1"}:
        raise UniversePgError("UNIVERSE_WRITE_TRANSACTION_MUST_BE_WRITABLE")
    try:
        role=pg.execute("""SELECT current_user,r.rolsuper,r.rolcreaterole,r.rolcreatedb,r.rolreplication,r.rolbypassrls,
            has_schema_privilege(current_user,'v4','CREATE'),
            has_table_privilege(current_user,'v4.market_universe_snapshots','INSERT'),
            has_table_privilege(current_user,'v4.market_universe_snapshot_rows','INSERT'),
            has_table_privilege(current_user,'v4.market_universe_reconciliation_rows','INSERT'),
            (has_table_privilege(current_user,'v4.market_universe_snapshots','UPDATE') OR has_table_privilege(current_user,'v4.market_universe_snapshots','DELETE') OR has_table_privilege(current_user,'v4.market_universe_snapshots','TRUNCATE')),
            (has_table_privilege(current_user,'v4.market_universe_snapshot_rows','UPDATE') OR has_table_privilege(current_user,'v4.market_universe_snapshot_rows','DELETE') OR has_table_privilege(current_user,'v4.market_universe_snapshot_rows','TRUNCATE')),
            (has_table_privilege(current_user,'v4.market_universe_reconciliation_rows','UPDATE') OR has_table_privilege(current_user,'v4.market_universe_reconciliation_rows','DELETE') OR has_table_privilege(current_user,'v4.market_universe_reconciliation_rows','TRUNCATE'))""").fetchone()
        publication=pg.execute("SELECT trade_date,revision_no,source_manifest_sha256,status FROM v4.publications WHERE publication_id=%s",(plan["publication_id"],)).fetchone()
        authority=pg.execute("""SELECT sp.manifest,sp.accepted_scope,sp.package_sha256,f.source_fact_sha256,
            f.logical_fact_id,f.fact_digest,f.record_locator,f.record_count,f.acceptance_receipt_id
            FROM v4.source_packages sp JOIN v4.source_package_facts f USING(package_id)
            WHERE sp.package_id=%s AND f.source_key='security_universe'""",(plan["source_package_id"],)).fetchone()
        consumed=pg.execute("""SELECT 1 FROM v4.publications p
            JOIN v4.publication_consumed_sources cs ON cs.publication_id=p.publication_id
            JOIN v4.source_revisions sr ON sr.source_revision_id=cs.source_revision_id
            WHERE p.publication_id=%s AND p.revision_no=%s AND p.trade_date=%s
              AND p.source_manifest_sha256=%s AND cs.source_key='security_universe'
              AND sr.source_package_id=%s AND sr.source_package_source_key='security_universe'
              AND sr.source_fact_digest=%s AND cs.digest=%s LIMIT 1""",
            (plan["publication_id"],plan["publication_revision"],plan["trade_date"],
             plan["source_manifest_sha256"],plan["source_package_id"],plan["fact_digest"],plan["fact_digest"])).fetchone()
    except Exception as exc:
        raise UniversePgError("UNIVERSE_WRITER_ROLE_OR_AUTHORITY_UNVERIFIABLE") from exc
    if (role is None or role[0]!=configured_writer or any(bool(value) for value in role[1:7])
            or not all(bool(value) for value in role[7:10]) or any(bool(value) for value in role[10:])):
        raise UniversePgError("UNIVERSE_WRITER_ROLE_INVALID")
    if (publication is None or publication[0].isoformat()!=plan["trade_date"]
            or int(publication[1])!=plan["publication_revision"]
            or str(publication[2]).strip()!=plan["source_manifest_sha256"]
            or publication[3]!="CANDIDATE" or consumed is None):
        raise UniversePgError("UNIVERSE_PUBLICATION_MUST_BE_MATCHING_CANDIDATE")
    if (authority is None or authority[1]!="ACCEPTED_SOURCE_PACKAGE"
            or str(authority[2]).strip()!=plan["package_sha256"]
            or str(authority[3]).strip()!=plan["source_fact_sha256"]
            or authority[4]!=plan["logical_fact_id"] or str(authority[5]).strip()!=plan["fact_digest"]
            or authority[6].get("universe_sha256")!=plan["universe_sha256"]
            or authority[7]!=plan["expected_count"] or authority[8]!=plan["acceptance_receipt_id"]):
        raise UniversePgError("UNIVERSE_PG_SOURCE_AUTHORITY_MISMATCH")
    manifest=authority[0]
    try:
        from .v4_daily_source_ingest_r6 import _verify_independent_acceptance_authority
        package_plan={"status":"ACCEPTED","trade_date":plan["trade_date"],"package_id":plan["source_package_id"],
            "package_sha256":str(authority[2]).strip(),"package_manifest":manifest,
            "source_facts":manifest.get("source_fact_bindings"),
            "acceptance_receipt":(manifest.get("acceptance_proof") or {}).get("receipt")}
        proof=_verify_independent_acceptance_authority(package_plan)
    except Exception as exc:
        raise UniversePgError("UNIVERSE_PG_ACCEPTANCE_SIGNATURE_INVALID") from exc
    if (proof.receipt_sha256!=plan["acceptance_receipt_sha256"]
            or proof.authority_id!=plan["acceptance_authority_id"]
            or proof.authority_receipt_id!=plan["acceptance_receipt_id"]):
        raise UniversePgError("UNIVERSE_PG_ACCEPTANCE_PROOF_PLAN_MISMATCH")
    try:
        exists = pg.execute("""SELECT persistence_identity_sha256 FROM v4.market_universe_snapshots
            WHERE publication_id=%s AND publication_revision=%s""",
            (plan["publication_id"], plan["publication_revision"])).fetchone()
    except Exception as exc:
        raise UniversePgError("UNIVERSE_PG_SCHEMA_NOT_INSTALLED") from exc
    if exists:
        if str(exists[0]).strip() != plan["persistence_identity_sha256"]:
            raise UniversePgError("UNIVERSE_APPEND_ONLY_IDENTITY_CONFLICT")
        return {"status": "IDEMPOTENT_REPLAY", "persisted": False, "identity_sha256": plan["persistence_identity_sha256"]}
    pg.execute("""INSERT INTO v4.market_universe_snapshots
        (publication_id,publication_revision,trade_date,source_manifest_sha256,source_package_id,
         acceptance_receipt_id,acceptance_receipt_sha256,acceptance_authority_id,source_fact_sha256,logical_fact_id,fact_digest,
         raw_artifact_sha256,universe_id,universe_contract_id,universe_contract_version,universe_sha256,
         exchange_scope,expected_count,core_count,coverage_ratio,reconciliation_sha256,category_counts,
         persistence_identity_sha256,status,captured_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PASS',clock_timestamp())""",
        (plan["publication_id"],plan["publication_revision"],plan["trade_date"],plan["source_manifest_sha256"],
         plan["source_package_id"],plan["acceptance_receipt_id"],plan["acceptance_receipt_sha256"],plan["acceptance_authority_id"],
         plan["source_fact_sha256"],plan["logical_fact_id"],plan["fact_digest"],plan["raw_artifact_sha256"],
         plan["universe_id"],CONTRACT_ID,CONTRACT_VERSION,plan["universe_sha256"],plan["exchange_scope"],
         plan["expected_count"],plan["core_count"],plan["coverage_ratio"],plan["reconciliation_sha256"],
         json.dumps(plan["category_counts"],sort_keys=True),plan["persistence_identity_sha256"]))
    for row in plan["snapshot_rows"]:
        pg.execute("""INSERT INTO v4.market_universe_snapshot_rows
            (publication_id,publication_revision,security_id,asset_class,share_class,exchange,status,source_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (plan["publication_id"],plan["publication_revision"],row["security_id"],row["asset_class"],
             row["share_class"],row["exchange"],row["status"],row["source_id"]))
    for row in plan["reconciliation_rows"]:
        pg.execute("""INSERT INTO v4.market_universe_reconciliation_rows
            (publication_id,publication_revision,security_id,source_present,core_present,
             expected_in_denominator,category,asset_class,share_class,exchange,status,source_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (plan["publication_id"],plan["publication_revision"],row["security_id"],row["source_present"],
             row["core_present"],row["expected_in_denominator"],row["category"],row["asset_class"],
             row["share_class"],row["exchange"],row["status"],row["source_id"]))
    return {"status": "UNIVERSE_APPENDED", "persisted": True,
            "identity_sha256": plan["persistence_identity_sha256"],
            "snapshot_rows": len(plan["snapshot_rows"]), "reconciliation_rows": len(plan["reconciliation_rows"]),
            "transaction_owner": "CALLER_NO_AUTOCOMMIT"}


def read_universe_snapshot(pg: Any, *, publication_id: str, publication_revision: int,
                           trade_date: str, source_manifest_sha256: str,
                           core_rows: Sequence[Mapping[str, Any]]) -> VerifiedUniverseReadback:
    """Read PG rows in the caller's READ ONLY RR snapshot and recompute proof."""
    target = _strict_day(trade_date)
    try:
        isolation = pg.execute("SHOW transaction_isolation").fetchone()[0]
        read_only = pg.execute("SHOW transaction_read_only").fetchone()[0]
    except Exception as exc:
        raise UniversePgError("UNIVERSE_READ_TRANSACTION_UNVERIFIABLE") from exc
    if str(isolation).lower().replace("_", " ") != "repeatable read" or str(read_only).lower() not in {"on", "true", "1"}:
        raise UniversePgError("UNIVERSE_READ_TRANSACTION_MUST_BE_REPEATABLE_READ_ONLY")
    try:
        from .v4_native import attest_read_role
        attest_read_role(pg, "v4")
        header = pg.execute("""SELECT trade_date,source_manifest_sha256,source_package_id,acceptance_receipt_id,
            acceptance_receipt_sha256,acceptance_authority_id,source_fact_sha256,logical_fact_id,fact_digest,
            raw_artifact_sha256,universe_id,universe_contract_id,universe_contract_version,universe_sha256,exchange_scope,
            expected_count,core_count,coverage_ratio,reconciliation_sha256,category_counts,
            persistence_identity_sha256,status FROM v4.market_universe_snapshots
            WHERE publication_id=%s AND publication_revision=%s""", (publication_id,publication_revision)).fetchone()
        if header is None:
            raise UniversePgError("UNIVERSE_PG_SNAPSHOT_MISSING")
        snapshot_rows = pg.execute("""SELECT security_id,asset_class,share_class,exchange,status,source_id
            FROM v4.market_universe_snapshot_rows WHERE publication_id=%s AND publication_revision=%s
            ORDER BY security_id""", (publication_id,publication_revision)).fetchall()
        recon_rows = pg.execute("""SELECT security_id,source_present,core_present,expected_in_denominator,
            category,asset_class,share_class,exchange,status,source_id
            FROM v4.market_universe_reconciliation_rows WHERE publication_id=%s AND publication_revision=%s
            ORDER BY security_id""", (publication_id,publication_revision)).fetchall()
        pub = pg.execute("SELECT trade_date,revision_no,source_manifest_sha256 FROM v4.publications WHERE publication_id=%s", (publication_id,)).fetchone()
        fact = pg.execute("""SELECT f.package_id,f.source_key,f.logical_fact_id,f.fact_digest,f.source_fact_sha256,
            f.record_locator,sp.package_sha256,sp.accepted_scope,sp.manifest,f.acceptance_receipt_id
            FROM v4.source_package_facts f JOIN v4.source_packages sp USING(package_id)
            WHERE f.package_id=%s AND f.source_key='security_universe' AND f.logical_fact_id=%s AND f.fact_digest=%s""",
            (header[2],header[6],header[7])).fetchone()
        consumed=pg.execute("""SELECT 1 FROM v4.publications p
            JOIN v4.publication_consumed_sources cs ON cs.publication_id=p.publication_id
            JOIN v4.source_revisions sr ON sr.source_revision_id=cs.source_revision_id
            WHERE p.publication_id=%s AND p.revision_no=%s AND p.trade_date=%s
              AND p.source_manifest_sha256=%s AND cs.source_key='security_universe'
              AND sr.source_package_id=%s AND sr.source_package_source_key='security_universe'
              AND sr.source_fact_digest=%s AND cs.digest=%s LIMIT 1""",
            (publication_id,publication_revision,target,source_manifest_sha256,header[2],header[8],header[8])).fetchone()
    except UniversePgError:
        raise
    except Exception as exc:
        raise UniversePgError("UNIVERSE_PG_READBACK_UNAVAILABLE") from exc
    if (pub is None or consumed is None or pub[0].isoformat()!=target or int(pub[1])!=publication_revision
            or str(pub[2]).strip()!=source_manifest_sha256
            or header[0].isoformat()!=target or str(header[1]).strip()!=source_manifest_sha256
            or header[11]!=CONTRACT_ID or header[12]!=CONTRACT_VERSION or header[21]!="PASS"):
        raise UniversePgError("UNIVERSE_PG_PUBLICATION_BINDING_MISMATCH")
    if (fact is None or fact[0]!=header[2] or fact[1]!="security_universe" or fact[2]!=header[7]
            or str(fact[3]).strip()!=str(header[8]).strip()
            or str(fact[4]).strip()!=str(header[6]).strip()
            or fact[9]!=header[3]
            or fact[7]!="ACCEPTED_SOURCE_PACKAGE"):
        raise UniversePgError("UNIVERSE_PG_SOURCE_FACT_BINDING_MISMATCH")
    locator=fact[5]
    if (not isinstance(locator,Mapping) or str(fact[4]).strip()!=str(header[9]).strip()
            or locator.get("universe_sha256")!=str(header[13]).strip()
            or locator.get("record_count")!=len(snapshot_rows)):
        raise UniversePgError("UNIVERSE_PG_SOURCE_LOCATOR_MISMATCH")
    entries=[dict(zip(("security_id","asset_class","share_class","exchange","status","source_id"),r)) for r in snapshot_rows]
    entries.sort(key=lambda x: x["security_id"].encode("utf-8"))
    reconciliation=[dict(zip(("security_id","source_present","core_present","expected_in_denominator","category","asset_class","share_class","exchange","status","source_id"),r)) for r in recon_rows]
    reconciliation.sort(key=lambda x: x["security_id"].encode("utf-8"))
    snapshot={"contract_id":CONTRACT_ID,"contract_version":CONTRACT_VERSION,"trade_date":target,
              "universe_id":header[10],"exchange_scope":list(header[14]),"securities":entries,"universe_sha256":str(header[13]).strip()}
    canonical_universe=hashlib.sha256(_canonical({"contract_id":CONTRACT_ID,"contract_version":CONTRACT_VERSION,
        "trade_date":target,"universe_id":header[10],"exchange_scope":sorted(header[14]),
        "securities":sorted(entries,key=lambda x:x["security_id"])})).hexdigest()
    if canonical_universe!=str(header[13]).strip():
        raise UniversePgError("UNIVERSE_PG_ROW_DIGEST_MISMATCH")
    manifest=fact[8]
    try:
        from .v4_daily_source_ingest_r6 import _verify_independent_acceptance_authority
        package_plan={"status":"ACCEPTED","trade_date":target,"package_id":header[2],
            "package_sha256":str(fact[6]).strip(),"package_manifest":manifest,
            "source_facts":manifest.get("source_fact_bindings"),
            "acceptance_receipt":(manifest.get("acceptance_proof") or {}).get("receipt")}
        acceptance=_verify_independent_acceptance_authority(package_plan)
        result=evaluate_market_universe_completeness(trade_date=target,universe_snapshot=snapshot,
            core_rows=core_rows,accepted_source_package_plan=package_plan)
    except Exception as exc:
        raise UniversePgError("UNIVERSE_PG_INDEPENDENT_ACCEPTANCE_INVALID:" + str(exc)) from exc
    if result.get("status")!="PASS":
        raise UniversePgError("UNIVERSE_PG_RECOMPUTE_NOT_PASS")
    if (_sha(reconciliation)!=str(header[18]).strip() or reconciliation!=result["reconciliation"]
            or result["expected_count"]!=int(header[15]) or len(core_rows)!=int(header[16])
            or float(result["coverage_ratio"])!=float(header[17])):
        raise UniversePgError("UNIVERSE_PG_RECONCILIATION_MISMATCH")
    if (acceptance.receipt_sha256!=str(header[4]).strip() or acceptance.authority_id!=header[5]
            or acceptance.authority_receipt_id!=header[3]):
        raise UniversePgError("UNIVERSE_PG_ACCEPTANCE_RECEIPT_BINDING_MISMATCH")
    persisted_material={
        "contract_id":CONTRACT_ID,"contract_version":CONTRACT_VERSION,
        "publication_id":publication_id,"publication_revision":publication_revision,
        "trade_date":target,"source_manifest_sha256":source_manifest_sha256,
        "source_package_id":header[2],"package_sha256":str(fact[6]).strip(),
        "acceptance_receipt_id":acceptance.authority_receipt_id,
        "acceptance_receipt_sha256":acceptance.receipt_sha256,
        "acceptance_authority_id":acceptance.authority_id,"source_key":"security_universe",
        "source_fact_sha256":str(header[6]).strip(),"logical_fact_id":header[7],
        "fact_digest":str(header[8]).strip(),"raw_artifact_sha256":str(header[9]).strip(),
        "universe_id":header[10],"universe_sha256":str(header[13]).strip(),
        "exchange_scope":sorted(header[14]),"expected_count":int(header[15]),
        "core_count":int(header[16]),"coverage_ratio":float(header[17]),
        "snapshot_rows":entries,"reconciliation_rows":reconciliation,
        "reconciliation_sha256":str(header[18]).strip(),"category_counts":header[19],"status":"PASS",
    }
    if _sha(persisted_material)!=str(header[20]).strip():
        raise UniversePgError("UNIVERSE_PG_PERSISTENCE_IDENTITY_MISMATCH")
    receipt={"readback_contract_id":READBACK_CONTRACT_ID,"readback_contract_version":READBACK_CONTRACT_VERSION,
        "publication_id":publication_id,"publication_revision":publication_revision,"trade_date":target,
        "source_manifest_sha256":source_manifest_sha256,"source_package_id":header[2],
        "source_package_sha256":str(fact[6]).strip(),"source_fact_sha256":str(header[6]).strip(),
        "logical_fact_id":header[7],"fact_digest":str(header[8]).strip(),
        "acceptance_receipt_id":acceptance.authority_receipt_id,
        "acceptance_receipt_sha256":acceptance.receipt_sha256,"acceptance_authority_id":acceptance.authority_id,
        "universe_id":header[10],"universe_contract_id":header[11],"universe_contract_version":header[12],
        "universe_sha256":str(header[13]).strip(),"raw_artifact_sha256":str(header[9]).strip(),
        "expected_count":int(header[15]),"core_count":int(header[16]),"coverage_ratio":float(header[17]),
        "reconciliation_sha256":str(header[18]).strip(),"status":"PASS"}
    return VerifiedUniverseReadback(**receipt,readback_receipt_sha256=_sha(receipt),_proof=_PROOF)
