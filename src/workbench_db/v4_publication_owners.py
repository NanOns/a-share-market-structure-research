"""Fixed-query readback for an existing immutable V4 sector-lifecycle Owner.

This Owner is a supplemental reconstructed maturity/health family. It is not
the sector-membership Owner and is not, by itself, sufficient to serve the
current sector page. Its hashed schema is quoted as a psycopg Identifier after
strict validation; relation and column names are fixed in this module.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from workbench_service.current_v4_context import canonical, digest
from .v4_publication_reader import PublicationReadError, PgPublicationReader


SECTOR_LIFECYCLE_OWNER_CONTRACT = "V4_SECTOR_LIFECYCLE_PG_OWNER_R1"
_SCHEMA = re.compile(r"^v4_[a-f0-9]{56}$")
_MAX_OWNER_ROWS = 200_000


def read_sector_lifecycle_owner(pg: Any, binding: Mapping[str, Any]) -> dict[str, Any]:
    """Read and verify one sector-lifecycle Owner in the caller's PG snapshot."""
    schema = binding.get("owner_schema")
    if (binding.get("owner_contract_id") != SECTOR_LIFECYCLE_OWNER_CONTRACT
            or binding.get("owner_relation") != "owner_rows"
            or not isinstance(schema, str) or not _SCHEMA.fullmatch(schema)):
        raise PublicationReadError("SECTOR_LIFECYCLE_OWNER_LOCATOR_INVALID")
    count = binding.get("row_count")
    if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= _MAX_OWNER_ROWS:
        raise PublicationReadError("SECTOR_LIFECYCLE_OWNER_ROW_COUNT_INVALID")
    try:
        from psycopg import sql
    except ImportError as exc:  # pragma: no cover - runtime packaging
        raise PublicationReadError("PG_DRIVER_UNAVAILABLE") from exc

    identity = PgPublicationReader._read_database_identity(pg)
    if identity != dict(binding.get("database_identity") or {}):
        raise PublicationReadError("PG_DATABASE_IDENTITY_MISMATCH")
    role_cursor = pg.execute(
        """SELECT r.rolsuper, r.rolbypassrls,
                  has_schema_privilege(current_user, %s, 'CREATE'),
                  (has_table_privilege(current_user, %s::regclass, 'INSERT') OR has_table_privilege(current_user, %s::regclass, 'UPDATE') OR has_table_privilege(current_user, %s::regclass, 'DELETE') OR has_table_privilege(current_user, %s::regclass, 'TRUNCATE')),
                  (has_table_privilege(current_user, %s::regclass, 'INSERT') OR has_table_privilege(current_user, %s::regclass, 'UPDATE') OR has_table_privilege(current_user, %s::regclass, 'DELETE') OR has_table_privilege(current_user, %s::regclass, 'TRUNCATE'))
             FROM pg_roles r WHERE r.rolname=current_user""",
        (schema, *([f"{schema}.owner_versions"] * 4), *([f"{schema}.owner_rows"] * 4)),
    )
    role = role_cursor.fetchone()
    if role is None or any(bool(value) for value in role):
        raise PublicationReadError("PG_READER_ROLE_HAS_OWNER_WRITE_PRIVILEGES")
    token, trade_date = binding.get("owner_version_token"), binding.get("owner_trade_date")
    if not isinstance(token, str) or not token.strip():
        raise PublicationReadError("SECTOR_LIFECYCLE_OWNER_TOKEN_INVALID")

    version_sql = sql.SQL(
        "SELECT digest,contract,sealed,row_count,database_identity, "
        "producer_sha256,parameter_digest,input_digest "
        "FROM {}.owner_versions WHERE token=%s AND T0=%s"
    ).format(sql.Identifier(schema))
    version = pg.execute(version_sql, (token, trade_date)).fetchone()
    if version is None:
        raise PublicationReadError("SECTOR_LIFECYCLE_OWNER_VERSION_MISSING")
    owner_digest, contract_id, sealed, actual_count, owner_database_identity, producer_sha, parameter_digest, input_digest = version
    if (owner_digest != binding.get("result_digest")
            or contract_id != SECTOR_LIFECYCLE_OWNER_CONTRACT
            or sealed is not True or actual_count != count
            or dict(owner_database_identity or {}) != identity):
        raise PublicationReadError("SECTOR_LIFECYCLE_OWNER_ATTESTATION_MISMATCH")

    rows_sql = sql.SQL(
        "SELECT sector_id,payload,payload_sha256 FROM {}.owner_rows "
        "WHERE token=%s AND T0=%s ORDER BY sector_id COLLATE \"C\" LIMIT %s"
    ).format(sql.Identifier(schema))
    rows = pg.execute(rows_sql, (token, trade_date, count + 1)).fetchall()
    if len(rows) != count:
        raise PublicationReadError("OWNER_READBACK_ROW_COUNT_MISMATCH")
    payload = []
    for sector_id, row_payload, row_digest in rows:
        if not isinstance(row_payload, Mapping) or row_payload.get("sector_id") != sector_id:
            raise PublicationReadError("SECTOR_LIFECYCLE_OWNER_ROW_IDENTITY_MISMATCH")
        if row_payload.get("T0") != str(trade_date) or row_payload.get("contract_id") != "SECTOR_LIFECYCLE_RECONSTRUCTED_V1":
            raise PublicationReadError("SECTOR_LIFECYCLE_OWNER_ROW_CONTRACT_MISMATCH")
        if digest(canonical(row_payload)) != row_digest:
            raise PublicationReadError("SECTOR_LIFECYCLE_OWNER_ROW_DIGEST_MISMATCH")
        payload.append(dict(row_payload))
    aggregate_material = {
        "owner_contract": SECTOR_LIFECYCLE_OWNER_CONTRACT,
        **dict([("token", token)]),
        "T0": str(trade_date),
        "producer_sha256": producer_sha,
        "parameter_digest": parameter_digest,
        "input_digest": input_digest,
        "rows": payload,
    }
    if digest(canonical(aggregate_material)) != owner_digest:
        raise PublicationReadError("SECTOR_LIFECYCLE_OWNER_AGGREGATE_DIGEST_MISMATCH")
    return {
        "database_identity": identity,
        "owner_schema": schema,
        "owner_relation": "owner_rows",
        "owner_version_token": token,
        "owner_trade_date": trade_date,
        "owner_contract_id": contract_id,
        "result_digest": owner_digest,
        "row_count": len(payload),
        "payload": payload,
    }
