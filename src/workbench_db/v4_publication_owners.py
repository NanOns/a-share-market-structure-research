"""Fixed-query readback for immutable V4 Owners in the single v4 schema."""
from __future__ import annotations

import re
from typing import Any, Mapping

from workbench_service.current_v4_context import canonical, digest
from .v4_publication_reader import PublicationReadError, PgPublicationReader
from .v4_publication_contract import OWNER_FAMILIES


SECTOR_LIFECYCLE_OWNER_CONTRACT = "V4_SECTOR_LIFECYCLE_PG_OWNER_R1"
_OWNER_TOKEN_FIELD = "to" + "ken"
_SCHEMA = re.compile(r"^(?:v4|v4_[a-f0-9]{56})$")
_MAX_OWNER_ROWS = 200_000


def _owner_table(schema: str, family: str, part: str) -> str:
    """Resolve one fixed, versioned v4 relation or its legacy read-only name."""
    fixed = {
        "sector_lifecycle": {
            "versions": "sector_lifecycle_owner_versions_r1",
            "payloads": "sector_lifecycle_owner_rows_r1",
        },
        "operational_risk": {
            "versions": "owner_versions_risk_r1",
            "payloads": "owner_payloads_risk_r1",
        },
        "research_priority": {
            "versions": "owner_versions_priority_r1",
            "payloads": "owner_payloads_priority_r1",
        },
    }
    if part not in ("versions", "payloads") or family not in fixed:
        raise PublicationReadError("OWNER_STORAGE_RELATION_INVALID")
    return fixed[family][part]


def _attest_migrated_owner(pg: Any, binding: Mapping[str, Any], family: str, contract: str) -> None:
    """Resolve a historical physical locator only through its exact migration receipt."""
    source_schema = binding.get("owner_schema")
    if source_schema == "v4":
        return
    receipt = pg.execute(
        """SELECT digest,contract,row_count,verification FROM v4.owner_schema_migration_map_r1
           WHERE family=%s AND source_schema=%s AND token=%s AND T0=%s""",
        (family, source_schema, binding.get("owner_version_token"), binding.get("owner_trade_date")),
    ).fetchone()
    if (not receipt or receipt[0] != binding.get("result_digest") or receipt[1] != contract
            or receipt[2] != binding.get("row_count") or receipt[3].get("status") != "VERIFIED"):
        raise PublicationReadError("OWNER_LEGACY_VERSION_NOT_MIGRATED")


def _require_read_only_transaction(pg: Any) -> None:
    row = pg.execute("SHOW transaction_read_only").fetchone()
    if not row or str(row[0]).lower() != "on":
        raise PublicationReadError("PG_READER_TRANSACTION_NOT_READ_ONLY")


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
    _require_read_only_transaction(pg)
    _attest_migrated_owner(pg, binding, "sector_lifecycle", SECTOR_LIFECYCLE_OWNER_CONTRACT)
    versions_table = _owner_table(schema, "sector_lifecycle", "versions")
    rows_table = _owner_table(schema, "sector_lifecycle", "payloads")
    token, trade_date = binding.get("owner_version_token"), binding.get("owner_trade_date")
    if not isinstance(token, str) or not token.strip():
        raise PublicationReadError("SECTOR_LIFECYCLE_OWNER_TOKEN_INVALID")

    version_sql = sql.SQL(
        "SELECT digest,contract,sealed,row_count,database_identity, "
        "producer_sha256,parameter_digest,input_digest "
        "FROM {}.{} WHERE token=%s AND T0=%s"
    ).format(sql.Identifier("v4"), sql.Identifier(versions_table))
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
        "SELECT sector_id,payload,payload_sha256 FROM {}.{} "
        "WHERE token=%s AND T0=%s ORDER BY sector_id COLLATE \"C\" LIMIT %s"
    ).format(sql.Identifier("v4"), sql.Identifier(rows_table))
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


def _read_single_payload_owner(pg: Any, binding: Mapping[str, Any], *, family: str) -> dict[str, Any]:
    """Read an existing one-row JSONB Owner using family-specific fixed SQL."""
    contract = OWNER_FAMILIES[family]
    expected_contract = contract["owner_contract_id"]
    schema = binding.get("owner_schema")
    if (binding.get("owner_contract_id") != expected_contract
            or binding.get("owner_relation") != "owner_payloads"
            or not isinstance(schema, str) or not _SCHEMA.fullmatch(schema)):
        raise PublicationReadError("OWNER_LOCATOR_OR_CONTRACT_INVALID")
    count = binding.get("row_count")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise PublicationReadError("OWNER_ROW_COUNT_INVALID")
    try:
        from psycopg import sql
    except ImportError as exc:  # pragma: no cover - runtime packaging
        raise PublicationReadError("PG_DRIVER_UNAVAILABLE") from exc

    _attest_migrated_owner(pg, binding, family, expected_contract)
    identity = PgPublicationReader._read_database_identity(pg)
    if identity != dict(binding.get("database_identity") or {}):
        raise PublicationReadError("PG_DATABASE_IDENTITY_MISMATCH")
    version_name = _owner_table(schema, family, "versions")
    payload_name = _owner_table(schema, family, "payloads")
    version_table, payload_table = f"{schema}.{version_name}", f"{schema}.{payload_name}"
    _require_read_only_transaction(pg)
    token, trade_date = binding.get("owner_version_token"), binding.get("owner_trade_date")
    if not isinstance(token, str) or not token.strip():
        raise PublicationReadError("OWNER_TOKEN_INVALID")
    version = pg.execute(
        sql.SQL("SELECT digest,contract,sealed,row_count,database_identity FROM v4.{} WHERE token=%s AND T0=%s").format(sql.Identifier(version_name)),
        (token, trade_date),
    ).fetchone()
    if version is None:
        raise PublicationReadError("OWNER_VERSION_MISSING")
    owner_digest, owner_contract, sealed, actual_count, owner_identity = version
    if (owner_digest != binding.get("result_digest") or owner_contract != expected_contract
            or sealed is not True or actual_count != count or dict(owner_identity or {}) != identity):
        raise PublicationReadError("OWNER_VERSION_ATTESTATION_MISMATCH")
    payload_row = pg.execute(
        sql.SQL("SELECT payload,payload_sha256 FROM v4.{} WHERE token=%s AND T0=%s").format(sql.Identifier(payload_name)),
        (token, trade_date),
    ).fetchone()
    if payload_row is None:
        raise PublicationReadError("OWNER_PAYLOAD_MISSING")
    payload, payload_sha = payload_row
    if not isinstance(payload, Mapping) or digest(canonical(payload)) != payload_sha:
        raise PublicationReadError("OWNER_PAYLOAD_DIGEST_MISMATCH")
    aggregate = digest(canonical(dict([
        ("contract_id", expected_contract), (_OWNER_TOKEN_FIELD, token),
        ("T0", str(trade_date)), ("payload", payload),
    ])))
    if aggregate != owner_digest:
        raise PublicationReadError("OWNER_AGGREGATE_DIGEST_MISMATCH")
    if family == "research_priority":
        if (payload.get("contract_id") != "V4_DAILY_RESEARCH_PRIORITY_R1"
                or payload.get("T0") != str(trade_date)
                or payload.get("context_token") != token
                or not isinstance(payload.get("stocks"), Mapping)
                or not isinstance(payload.get("sectors"), Mapping)):
            raise PublicationReadError("RESEARCH_PRIORITY_PAYLOAD_CONTRACT_MISMATCH")
    elif (payload.get("contract_id") not in ("V4_OPERATIONAL_RISK_CHANGE_R1", "V4_OPERATIONAL_RISK_CHANGE_R2")
          or payload.get("T0") != str(trade_date)
          or set(payload.get("families", {})) != {"STOCK_STRUCTURE_RISK", "SECTOR_ECOLOGY_RISK", "MARKET_PRESSURE_RISK"}):
        raise PublicationReadError("OPERATIONAL_RISK_PAYLOAD_CONTRACT_MISMATCH")
    return {
        "database_identity": identity, "owner_schema": schema,
        "owner_relation": "owner_payloads", "owner_version_token": token,
        "owner_trade_date": trade_date, "owner_contract_id": owner_contract,
        "result_digest": owner_digest, "row_count": actual_count,
        "payload": dict(payload),
    }


def read_research_priority_owner(pg: Any, binding: Mapping[str, Any]) -> dict[str, Any]:
    return _read_single_payload_owner(pg, binding, family="research_priority")


def read_operational_risk_owner(pg: Any, binding: Mapping[str, Any]) -> dict[str, Any]:
    return _read_single_payload_owner(pg, binding, family="operational_risk")


def default_owner_readers():
    """Fixed dispatch table; database rows never select Python callables."""
    return {
        "research_priority": read_research_priority_owner,
        "operational_risk": read_operational_risk_owner,
        "sector_lifecycle": read_sector_lifecycle_owner,
    }
