"""Database adapters for immutable analysis-result metadata.

The Parquet object remains a managed file.  This boundary owns only the
relational identity, dependency and binding rows, allowing the coordinator to
use the same contract with DuckDB during rollback and PostgreSQL at cutover.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any, Iterator, Mapping, Protocol, Sequence

import duckdb
from psycopg import sql

from .postgres_repository import PostgresRepository


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


class ResultObjectRepository(Protocol):
    def persist(
        self,
        *,
        slice_id: str,
        result_object_id: str,
        domain: str,
        schema_version: str,
        semantic_contract: str,
        value_hash: str,
        logical_hash: str,
        row_count: int,
        storage_kind: str,
        created_at: Any,
        object_path: str,
        relative_path: str,
        columns: Sequence[str],
        primary_key: Sequence[str],
        value_semantics: Mapping[str, Any],
        basis: Mapping[str, Any],
        identity_evidence: Mapping[str, Any],
        dependencies: Sequence[Mapping[str, str]],
        trade_date: str,
        contract_id: str,
        input_hash: str,
        dependency_hash: str,
        daily_basis: Mapping[str, Any] | None,
    ) -> bool: ...


class DuckDBResultObjectRepository:
    def __init__(self, root: str | Path, database_path: str | Path | None = None):
        root = Path(root).resolve()
        self.database_path = Path(database_path).resolve() if database_path else root / "data/database/market_research.duckdb"

    @contextmanager
    def _connection(self) -> Iterator[duckdb.DuckDBPyConnection]:
        with duckdb.connect(str(self.database_path)) as connection:
            yield connection

    def persist(self, **kwargs: Any) -> bool:
        with self._connection() as connection:
            return _persist_duckdb(connection, **kwargs)


class PostgresResultObjectRepository:
    def __init__(self, repository: PostgresRepository):
        self.repository = repository

    def persist(self, **kwargs: Any) -> bool:
        with self.repository.transaction() as connection:
            return _persist_postgres(connection, self.repository.schema, **kwargs)


def _storage_payload(**kwargs: Any) -> dict[str, Any]:
    return {
        "storage_object_id": kwargs["result_object_id"],
        "result_object_id": kwargs["result_object_id"],
        "path": kwargs["object_path"],
        "relative_path": kwargs["relative_path"],
        "kind": "ANALYSIS_RESULT_OBJECT",
        "storage_kind": kwargs["storage_kind"],
        "domain": kwargs["domain"],
        "schema_version": kwargs["schema_version"],
        "semantic_contract": kwargs["semantic_contract"],
        "value_hash": kwargs["value_hash"],
        "logical_hash": kwargs["logical_hash"],
        "columns": list(kwargs["columns"]),
        "primary_key": list(kwargs["primary_key"]),
        "value_semantics": dict(kwargs["value_semantics"]),
        "row_count": kwargs["row_count"],
        "state": "ACTIVE",
        "referenced": True,
        "registered_at_utc": kwargs["created_at"].isoformat(),
    }


def _validate_existing(existing: Any, kwargs: Mapping[str, Any]) -> None:
    basis = existing[4] if isinstance(existing[4], dict) else json.loads(existing[4])
    if (existing[0], existing[2], existing[3], basis, int(existing[5]), existing[6], existing[7], existing[8]) != (
        kwargs["domain"], kwargs["input_hash"], kwargs["dependency_hash"], dict(kwargs["basis"]), int(kwargs["row_count"]), kwargs["logical_hash"], kwargs["storage_kind"], kwargs["result_object_id"]
    ):
        raise ValueError("SLICE_IDENTITY_CONFLICT")


def _persist_duckdb(connection: duckdb.DuckDBPyConnection, **kwargs: Any) -> bool:
    existing = connection.execute(
        "SELECT domain, contract_id, input_hash, dependency_hash, basis_json, row_count, logical_hash, storage_kind, storage_object_id FROM analysis_slices WHERE slice_id=?",
        [kwargs["slice_id"]],
    ).fetchone()
    if existing:
        _validate_existing(existing, kwargs)
        return True
    connection.execute("BEGIN TRANSACTION")
    try:
        connection.execute("INSERT INTO analysis_result_objects VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(result_object_id) DO NOTHING", [kwargs["result_object_id"], kwargs["domain"], kwargs["schema_version"], kwargs["semantic_contract"], kwargs["value_hash"], kwargs["row_count"], kwargs["storage_kind"], kwargs["created_at"]])
        stored = connection.execute("SELECT domain, schema_version, semantic_contract, value_hash, row_count, storage_kind FROM analysis_result_objects WHERE result_object_id=?", [kwargs["result_object_id"]]).fetchone()
        if not stored or tuple(stored) != tuple(kwargs[key] for key in ("domain", "schema_version", "semantic_contract", "value_hash", "row_count", "storage_kind")):
            raise ValueError("RESULT_OBJECT_IDENTITY_CONFLICT")
        payload = _storage_payload(**kwargs)
        connection.execute("INSERT INTO storage_objects(storage_object_id,payload_json) VALUES (?, ?) ON CONFLICT(storage_object_id) DO NOTHING", [kwargs["result_object_id"], _json(payload)])
        stored_payload = connection.execute("SELECT payload_json FROM storage_objects WHERE storage_object_id=?", [kwargs["result_object_id"]]).fetchone()
        if not stored_payload or json.loads(stored_payload[0]).get("value_hash") != kwargs["value_hash"]:
            raise ValueError("RESULT_OBJECT_IDENTITY_CONFLICT")
        for dependency in kwargs["dependencies"]:
            if not connection.execute("SELECT 1 FROM analysis_slices WHERE slice_id=?", [dependency["input_slice_id"]]).fetchone():
                raise ValueError(f"RESULT_DEPENDENCY_NOT_FOUND:{dependency['input_slice_id']}")
        connection.execute("INSERT INTO analysis_slices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [kwargs["slice_id"], kwargs["domain"], date.fromisoformat(kwargs["trade_date"]), kwargs["contract_id"], kwargs["input_hash"], kwargs["dependency_hash"], _json(dict(kwargs["basis"])), kwargs["row_count"], kwargs["logical_hash"], kwargs["storage_kind"], kwargs["result_object_id"], kwargs["created_at"]])
        for dependency in kwargs["dependencies"]:
            connection.execute("INSERT INTO analysis_slice_dependencies VALUES (?, ?, ?, ?)", [kwargs["slice_id"], dependency["input_domain"], date.fromisoformat(dependency["input_date"]), dependency["input_slice_id"]])
        daily_basis = kwargs.get("daily_basis")
        if isinstance(daily_basis, Mapping):
            required = ("universe_basis", "price_basis", "capabilities_json")
            if any(key not in daily_basis for key in required):
                raise ValueError("RESULT_DAILY_BASIS_FIELD_MISSING")
            connection.execute("INSERT INTO analysis_daily_basis VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [kwargs["slice_id"], daily_basis["universe_basis"], daily_basis.get("membership_snapshot_id"), daily_basis["price_basis"], daily_basis.get("adjustment_as_of"), daily_basis.get("source_observed_at"), daily_basis.get("coverage"), _json(daily_basis["capabilities_json"])])
        connection.execute("INSERT INTO analysis_slice_result_bindings VALUES (?, ?, ?)", [kwargs["slice_id"], kwargs["result_object_id"], _json(kwargs["identity_evidence"])])
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    return False


def _persist_postgres(connection: Any, schema: str, **kwargs: Any) -> bool:
    def q(text: str) -> sql.Composed:
        return sql.SQL(text).format(schema=sql.Identifier(schema))

    with connection.cursor() as cur:
        cur.execute(q("SELECT domain, contract_id, input_hash, dependency_hash, basis_json, row_count, logical_hash, storage_kind, storage_object_id FROM {schema}.analysis_slices WHERE slice_id=%s"), (kwargs["slice_id"],))
        existing = cur.fetchone()
        if existing:
            _validate_existing(existing, kwargs)
            return True
        cur.execute(q("INSERT INTO {schema}.analysis_result_objects (result_object_id,domain,schema_version,semantic_contract,value_hash,row_count,storage_kind,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (result_object_id) DO NOTHING"), tuple(kwargs[key] for key in ("result_object_id", "domain", "schema_version", "semantic_contract", "value_hash", "row_count", "storage_kind", "created_at")))
        cur.execute(q("SELECT domain,schema_version,semantic_contract,value_hash,row_count,storage_kind FROM {schema}.analysis_result_objects WHERE result_object_id=%s"), (kwargs["result_object_id"],))
        stored = cur.fetchone()
        if not stored or tuple(stored) != tuple(kwargs[key] for key in ("domain", "schema_version", "semantic_contract", "value_hash", "row_count", "storage_kind")):
            raise ValueError("RESULT_OBJECT_IDENTITY_CONFLICT")
        payload = _storage_payload(**kwargs)
        cur.execute(q("INSERT INTO {schema}.storage_objects(storage_object_id,payload_json) VALUES (%s,%s::jsonb) ON CONFLICT (storage_object_id) DO NOTHING"), (kwargs["result_object_id"], _json(payload)))
        cur.execute(q("SELECT payload_json FROM {schema}.storage_objects WHERE storage_object_id=%s"), (kwargs["result_object_id"],))
        stored_payload = cur.fetchone()
        if not stored_payload or (stored_payload[0] if isinstance(stored_payload[0], dict) else json.loads(stored_payload[0])).get("value_hash") != kwargs["value_hash"]:
            raise ValueError("RESULT_OBJECT_IDENTITY_CONFLICT")
        for dependency in kwargs["dependencies"]:
            cur.execute(q("SELECT 1 FROM {schema}.analysis_slices WHERE slice_id=%s"), (dependency["input_slice_id"],))
            if not cur.fetchone():
                raise ValueError(f"RESULT_DEPENDENCY_NOT_FOUND:{dependency['input_slice_id']}")
        cur.execute(q("INSERT INTO {schema}.analysis_slices (slice_id,domain,trade_date,contract_id,input_hash,dependency_hash,basis_json,row_count,logical_hash,storage_kind,storage_object_id,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s)"), (kwargs["slice_id"], kwargs["domain"], kwargs["trade_date"], kwargs["contract_id"], kwargs["input_hash"], kwargs["dependency_hash"], _json(dict(kwargs["basis"])), kwargs["row_count"], kwargs["logical_hash"], kwargs["storage_kind"], kwargs["result_object_id"], kwargs["created_at"]))
        for dependency in kwargs["dependencies"]:
            cur.execute(q("INSERT INTO {schema}.analysis_slice_dependencies (slice_id,input_domain,input_date,input_slice_id) VALUES (%s,%s,%s,%s)"), (kwargs["slice_id"], dependency["input_domain"], dependency["input_date"], dependency["input_slice_id"]))
        daily_basis = kwargs.get("daily_basis")
        if isinstance(daily_basis, Mapping):
            required = ("universe_basis", "price_basis", "capabilities_json")
            if any(key not in daily_basis for key in required):
                raise ValueError("RESULT_DAILY_BASIS_FIELD_MISSING")
            cur.execute(q("INSERT INTO {schema}.analysis_daily_basis (slice_id,universe_basis,membership_snapshot_id,price_basis,adjustment_as_of,source_observed_at,coverage,capabilities_json) VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)"), (kwargs["slice_id"], daily_basis["universe_basis"], daily_basis.get("membership_snapshot_id"), daily_basis["price_basis"], daily_basis.get("adjustment_as_of"), daily_basis.get("source_observed_at"), daily_basis.get("coverage"), _json(daily_basis["capabilities_json"])))
        cur.execute(q("INSERT INTO {schema}.analysis_slice_result_bindings (slice_id,result_object_id,identity_evidence) VALUES (%s,%s,%s::jsonb)"), (kwargs["slice_id"], kwargs["result_object_id"], _json(kwargs["identity_evidence"])))
    return False


__all__ = ["DuckDBResultObjectRepository", "PostgresResultObjectRepository", "ResultObjectRepository"]
