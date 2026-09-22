"""DuckDB/PostgreSQL metadata adapters for sealed historical slices."""
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


class SliceRepository(Protocol):
    def existing(self, slice_id: str) -> tuple[Any, ...] | None: ...
    def dependency_exists(self, slice_id: str) -> bool: ...
    def seal(self, *, slice_id: str, domain: str, trade_date: str, contract_id: str, input_hash: str, dependency_hash: str, basis: Mapping[str, Any], row_count: int, logical_hash: str, storage_kind: str, storage_object_id: str, created_at: Any, object_payload: Mapping[str, Any], dependencies: Sequence[Mapping[str, str]]) -> None: ...


class DuckDBSliceRepository:
    def __init__(self, root: str | Path, database_path: str | Path | None = None):
        root = Path(root).resolve()
        self.database_path = Path(database_path).resolve() if database_path else root / "data/database/market_research.duckdb"

    def existing(self, slice_id: str) -> tuple[Any, ...] | None:
        with duckdb.connect(str(self.database_path), read_only=True) as con:
            return con.execute("select slice_id,domain,cast(trade_date as varchar),contract_id,input_hash,dependency_hash,basis_json,row_count,logical_hash,storage_kind,storage_object_id from analysis_slices where slice_id=?", [slice_id]).fetchone()

    def dependency_exists(self, slice_id: str) -> bool:
        with duckdb.connect(str(self.database_path), read_only=True) as con:
            return con.execute("select 1 from analysis_slices where slice_id=?", [slice_id]).fetchone() is not None

    def seal(self, **kwargs: Any) -> None:
        with duckdb.connect(str(self.database_path)) as con:
            con.execute("BEGIN TRANSACTION")
            try:
                _seal_duckdb(con, **kwargs)
                con.execute("COMMIT")
            except Exception:
                con.execute("ROLLBACK")
                raise


class PostgresSliceRepository:
    def __init__(self, repository: PostgresRepository):
        self.repository = repository

    def existing(self, slice_id: str) -> tuple[Any, ...] | None:
        if self.repository.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        with self.repository.connection.cursor() as cur:
            cur.execute(sql.SQL("select slice_id,domain,cast(trade_date as text),contract_id,input_hash,dependency_hash,basis_json,row_count,logical_hash,storage_kind,storage_object_id from {}.analysis_slices where slice_id=%s").format(sql.Identifier(self.repository.schema)), (slice_id,))
            return cur.fetchone()

    def dependency_exists(self, slice_id: str) -> bool:
        if self.repository.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        with self.repository.connection.cursor() as cur:
            cur.execute(sql.SQL("select 1 from {}.analysis_slices where slice_id=%s").format(sql.Identifier(self.repository.schema)), (slice_id,))
            return cur.fetchone() is not None

    def seal(self, **kwargs: Any) -> None:
        with self.repository.transaction() as con:
            _seal_postgres(con, self.repository.schema, **kwargs)


def _check_dependencies(exists, dependencies: Sequence[Mapping[str, str]]) -> None:
    for dependency in dependencies:
        if not exists(dependency["input_slice_id"]):
            raise ValueError(f"SLICE_DEPENDENCY_NOT_FOUND:{dependency['input_slice_id']}")


def _seal_duckdb(con: Any, *, slice_id: str, domain: str, trade_date: str, contract_id: str, input_hash: str, dependency_hash: str, basis: Mapping[str, Any], row_count: int, logical_hash: str, storage_kind: str, storage_object_id: str, created_at: Any, object_payload: Mapping[str, Any], dependencies: Sequence[Mapping[str, str]]) -> None:
    _check_dependencies(lambda value: con.execute("select 1 from analysis_slices where slice_id=?", [value]).fetchone() is not None, dependencies)
    con.execute("insert into storage_objects(storage_object_id,payload_json) values (?,?) on conflict(storage_object_id) do nothing", [storage_object_id, _json(object_payload)])
    stored = con.execute("select payload_json from storage_objects where storage_object_id=?", [storage_object_id]).fetchone()
    payload = stored[0] if isinstance(stored[0], dict) else json.loads(stored[0]) if stored else {}
    if not stored or payload.get("logical_hash") != logical_hash:
        raise ValueError("ANALYSIS_OBJECT_IDENTITY_CONFLICT")
    con.execute("insert into analysis_slices values (?,?,?,?,?,?,?,?,?,?,?,?)", [slice_id, domain, date.fromisoformat(trade_date), contract_id, input_hash, dependency_hash, _json(dict(basis)), row_count, logical_hash, storage_kind, storage_object_id, created_at])
    for dependency in dependencies:
        con.execute("insert into analysis_slice_dependencies values (?,?,?,?)", [slice_id, dependency["input_domain"], date.fromisoformat(dependency["input_date"]), dependency["input_slice_id"]])
    daily_basis = basis.get("daily_basis")
    if isinstance(daily_basis, Mapping):
        required = ("universe_basis", "price_basis", "capabilities_json")
        if any(key not in daily_basis for key in required):
            raise ValueError("SLICE_DAILY_BASIS_FIELD_MISSING")
        con.execute("insert into analysis_daily_basis values (?,?,?,?,?,?,?,?)", [slice_id, daily_basis["universe_basis"], daily_basis.get("membership_snapshot_id"), daily_basis["price_basis"], daily_basis.get("adjustment_as_of"), daily_basis.get("source_observed_at"), daily_basis.get("coverage"), _json(daily_basis["capabilities_json"])])


def _seal_postgres(con: Any, schema: str, *, slice_id: str, domain: str, trade_date: str, contract_id: str, input_hash: str, dependency_hash: str, basis: Mapping[str, Any], row_count: int, logical_hash: str, storage_kind: str, storage_object_id: str, created_at: Any, object_payload: Mapping[str, Any], dependencies: Sequence[Mapping[str, str]]) -> None:
    def query(text: str) -> sql.Composed:
        return sql.SQL(text).format(schema=sql.Identifier(schema))
    with con.cursor() as cur:
        for dependency in dependencies:
            cur.execute(query("select 1 from {schema}.analysis_slices where slice_id=%s"), (dependency["input_slice_id"],))
            if cur.fetchone() is None:
                raise ValueError(f"SLICE_DEPENDENCY_NOT_FOUND:{dependency['input_slice_id']}")
        cur.execute(query("insert into {schema}.storage_objects(storage_object_id,payload_json) values (%s,%s::jsonb) on conflict(storage_object_id) do nothing"), (storage_object_id, _json(object_payload)))
        cur.execute(query("select payload_json from {schema}.storage_objects where storage_object_id=%s"), (storage_object_id,))
        stored = cur.fetchone()
        payload = stored[0] if isinstance(stored[0], dict) else json.loads(stored[0]) if stored else {}
        if not stored or payload.get("logical_hash") != logical_hash:
            raise ValueError("ANALYSIS_OBJECT_IDENTITY_CONFLICT")
        cur.execute(query("insert into {schema}.analysis_slices (slice_id,domain,trade_date,contract_id,input_hash,dependency_hash,basis_json,row_count,logical_hash,storage_kind,storage_object_id,created_at) values (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s)"), (slice_id, domain, trade_date, contract_id, input_hash, dependency_hash, _json(dict(basis)), row_count, logical_hash, storage_kind, storage_object_id, created_at))
        for dependency in dependencies:
            cur.execute(query("insert into {schema}.analysis_slice_dependencies (slice_id,input_domain,input_date,input_slice_id) values (%s,%s,%s,%s)"), (slice_id, dependency["input_domain"], dependency["input_date"], dependency["input_slice_id"]))
        daily_basis = basis.get("daily_basis")
        if isinstance(daily_basis, Mapping):
            required = ("universe_basis", "price_basis", "capabilities_json")
            if any(key not in daily_basis for key in required):
                raise ValueError("SLICE_DAILY_BASIS_FIELD_MISSING")
            cur.execute(query("insert into {schema}.analysis_daily_basis (slice_id,universe_basis,membership_snapshot_id,price_basis,adjustment_as_of,source_observed_at,coverage,capabilities_json) values (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)"), (slice_id, daily_basis["universe_basis"], daily_basis.get("membership_snapshot_id"), daily_basis["price_basis"], daily_basis.get("adjustment_as_of"), daily_basis.get("source_observed_at"), daily_basis.get("coverage"), _json(daily_basis["capabilities_json"])))


__all__ = ["DuckDBSliceRepository", "PostgresSliceRepository", "SliceRepository"]
