"""Append optional V4 PG Owner bindings before a publication Head is sealed."""
from __future__ import annotations

import re
from typing import Any, Mapping

from workbench_service.current_v4_context import canonical, digest
from .v4_publication_contract import CONTRACT_ID as MODULE_CONTRACT_ID, OWNER_FAMILIES


class PublicationModuleWriteError(ValueError):
    pass


def persist_publication_module_results(pg: Any, candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Insert immutable Owner associations in the caller transaction, without commit or Head mutation."""
    from .v4_native import configured_dsn
    from psycopg.conninfo import conninfo_to_dict
    from psycopg.types.json import Jsonb

    try:
        configured_writer = conninfo_to_dict(configured_dsn()).get("user")
    except Exception as exc:
        raise PublicationModuleWriteError("PG_MODULE_WRITER_DSN_REQUIRED_NO_READER_FALLBACK") from exc
    if not configured_writer:
        raise PublicationModuleWriteError("PG_MODULE_WRITER_ROLE_REQUIRED")
    if not isinstance(candidate, Mapping):
        raise PublicationModuleWriteError("PG_MODULE_CANDIDATE_REQUIRED")
    body = dict(candidate)
    candidate_digest = body.pop("candidate_digest", None)
    if (not isinstance(candidate_digest, str)
            or digest(canonical(body)) != candidate_digest
            or candidate.get("module_contract_id") != MODULE_CONTRACT_ID
            or candidate.get("metadata_readiness_status") != "SOURCE_AND_IDENTITY_VALIDATED"
            or candidate.get("status") != "METADATA_CANDIDATE_READY"):
        raise PublicationModuleWriteError("PG_MODULE_CANDIDATE_IDENTITY_INVALID")
    module_rows = candidate.get("module_results")
    if not isinstance(module_rows, list):
        raise PublicationModuleWriteError("PG_MODULE_RESULT_SET_INVALID")
    if digest(canonical(module_rows)) != candidate.get("module_results_digest"):
        raise PublicationModuleWriteError("PG_MODULE_RESULT_DIGEST_MISMATCH")
    if not module_rows:
        return {"status": "NO_OPTIONAL_OWNER_BINDINGS", "row_count": 0,
                "write_mode": "NO_DATABASE_WRITE", "head_changed": False, "committed": False}

    expected_identity = candidate.get("database_identity")
    if not isinstance(expected_identity, Mapping):
        raise PublicationModuleWriteError("PG_MODULE_DATABASE_IDENTITY_REQUIRED")
    try:
        read_only = str(pg.execute("SHOW transaction_read_only").fetchone()[0]).lower()
        role = pg.execute(
            """SELECT current_user,r.rolsuper,r.rolcreaterole,r.rolcreatedb,r.rolreplication,r.rolbypassrls,
                      has_schema_privilege(current_user,'v4','CREATE'),
                      has_table_privilege(current_user,'v4.publication_module_results','INSERT'),
                      (has_table_privilege(current_user,'v4.publication_module_results','UPDATE')
                       OR has_table_privilege(current_user,'v4.publication_module_results','DELETE')
                       OR has_table_privilege(current_user,'v4.publication_module_results','TRUNCATE'))
                 FROM pg_roles r WHERE r.rolname=current_user"""
        ).fetchone()
        from .v4_publication_reader import PgPublicationReader
        actual_identity = PgPublicationReader._read_database_identity(pg)
    except Exception as exc:
        raise PublicationModuleWriteError("PG_MODULE_WRITER_CONTEXT_UNVERIFIABLE") from exc
    if read_only in {"on", "true", "1"}:
        raise PublicationModuleWriteError("PG_MODULE_WRITE_TRANSACTION_MUST_BE_WRITABLE")
    if (role is None or role[0] != configured_writer
            or any(bool(value) for value in role[1:7])
            or not bool(role[7]) or bool(role[8])):
        raise PublicationModuleWriteError("PG_MODULE_WRITER_ROLE_INVALID")
    if actual_identity != dict(expected_identity):
        raise PublicationModuleWriteError("PG_MODULE_DATABASE_IDENTITY_MISMATCH")

    publication_id = candidate.get("publication_id")
    trade_date = candidate.get("trade_date")
    revision_no = candidate.get("revision_no")
    try:
        pg.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                   ("v4-module-results:" + str(publication_id),))
        publication = pg.execute(
            """SELECT trade_date,revision_no,source_manifest_sha256,status,accepted_at
                 FROM v4.publications WHERE publication_id=%s""", (publication_id,),
        ).fetchone()
        if (publication is None or publication[0].isoformat() != trade_date
                or int(publication[1]) != revision_no
                or str(publication[2]).strip() != str(candidate.get("source_manifest_sha256")).strip()
                or publication[3] != "ACCEPTED" or publication[4] is None):
            raise PublicationModuleWriteError("PG_MODULE_PUBLICATION_NOT_ACCEPTED_OR_IDENTITY_MISMATCH")
        if pg.execute("SELECT 1 FROM v4.publication_heads WHERE publication_id=%s", (publication_id,)).fetchone():
            raise PublicationModuleWriteError("V4_PUBLICATION_MODULE_SET_SEALED")
        existing = pg.execute(
            """SELECT module_key,module_contract_id,database_identity,owner_schema,owner_relation,
                      owner_version_token,owner_trade_date,owner_contract_id,result_digest,row_count,
                      quality_status,as_recorded,pit_eligible
                 FROM v4.publication_module_results WHERE publication_id=%s ORDER BY module_key""",
            (publication_id,),
        ).fetchall()
    except PublicationModuleWriteError:
        raise
    except Exception as exc:
        raise PublicationModuleWriteError("PG_MODULE_BINDING_SCHEMA_OR_READ_FAILURE") from exc

    normalized = sorted(module_rows, key=lambda item: item["module_key"])
    for row in normalized:
        module = row.get("module_key")
        family = OWNER_FAMILIES.get(module)
        if (family is None
                or row.get("module_contract_id") != MODULE_CONTRACT_ID
                or dict(row.get("database_identity") or {}) != dict(expected_identity)
                or row.get("owner_schema") != "v4"
                or row.get("owner_relation") != family["relation"]
                or row.get("owner_contract_id") != family["owner_contract_id"]
                or not isinstance(row.get("owner_version_token"), str)
                or not row["owner_version_token"].strip()
                or row.get("owner_trade_date") != trade_date
                or not isinstance(row.get("result_digest"), str)
                or re.fullmatch(r"[a-f0-9]{64}", row["result_digest"]) is None
                or isinstance(row.get("row_count"), bool)
                or not isinstance(row.get("row_count"), int) or row["row_count"] < 0
                or not isinstance(row.get("quality_status"), str) or not row["quality_status"].strip()
                or not isinstance(row.get("as_recorded"), bool)
                or not isinstance(row.get("pit_eligible"), bool)):
            raise PublicationModuleWriteError("PG_MODULE_RESULT_ROW_IDENTITY_INVALID")
    if existing:
        def normalized_pg_row(row):
            values = list(row)
            if hasattr(values[6], "isoformat"):
                values[6] = values[6].isoformat()
            if isinstance(values[2], Mapping):
                values[2] = dict(values[2])
            return tuple(values)
        expected = [(
            row["module_key"], row["module_contract_id"], dict(row["database_identity"]), row["owner_schema"],
            row["owner_relation"], row["owner_version_token"], row["owner_trade_date"], row["owner_contract_id"],
            row["result_digest"], row["row_count"], row["quality_status"], row["as_recorded"], row["pit_eligible"],
        ) for row in normalized]
        if [normalized_pg_row(row) for row in existing] != expected:
            raise PublicationModuleWriteError("PG_MODULE_BINDING_APPEND_ONLY_CONFLICT")
        return {"status": "EXISTING_BINDINGS_VERIFIED", "row_count": len(existing),
                "write_mode": "CALLER_TRANSACTION_NO_COMMIT", "head_changed": False, "committed": False}

    insert_sql = """INSERT INTO v4.publication_module_results
        (publication_id,module_key,module_contract_id,database_identity,owner_schema,owner_relation,
         owner_version_token,owner_trade_date,owner_contract_id,result_digest,row_count,quality_status,as_recorded,pit_eligible)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
    try:
        for row in normalized:
            pg.execute(insert_sql, (
                publication_id, row["module_key"], row["module_contract_id"], Jsonb(dict(row["database_identity"])),
                row["owner_schema"], row["owner_relation"], row["owner_version_token"], row["owner_trade_date"],
                row["owner_contract_id"], row["result_digest"], row["row_count"], row["quality_status"],
                row["as_recorded"], row["pit_eligible"],
            ))
        readback = pg.execute(
            """SELECT module_key,module_contract_id,database_identity,owner_schema,owner_relation,
                      owner_version_token,owner_trade_date,owner_contract_id,result_digest,row_count,
                      quality_status,as_recorded,pit_eligible
                 FROM v4.publication_module_results WHERE publication_id=%s ORDER BY module_key""",
            (publication_id,),
        ).fetchall()
    except PublicationModuleWriteError:
        raise
    except Exception as exc:
        raise PublicationModuleWriteError("PG_MODULE_BINDING_INSERT_OR_READBACK_FAILED") from exc
    expected = [(
        row["module_key"], row["module_contract_id"], dict(row["database_identity"]), row["owner_schema"],
        row["owner_relation"], row["owner_version_token"], row["owner_trade_date"], row["owner_contract_id"],
        row["result_digest"], row["row_count"], row["quality_status"], row["as_recorded"], row["pit_eligible"],
    ) for row in normalized]
    def normalized_pg_row(row):
        values = list(row)
        if hasattr(values[6], "isoformat"):
            values[6] = values[6].isoformat()
        if isinstance(values[2], Mapping):
            values[2] = dict(values[2])
        return tuple(values)
    if [normalized_pg_row(row) for row in readback] != expected:
        raise PublicationModuleWriteError("PG_MODULE_BINDING_READBACK_MISMATCH")
    return {"status": "OWNER_BINDINGS_INSERTED_NOT_HEAD_ACCEPTED", "row_count": len(readback),
            "write_mode": "CALLER_TRANSACTION_NO_COMMIT", "head_changed": False, "committed": False}
