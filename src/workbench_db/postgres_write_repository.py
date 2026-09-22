"""Small, transactional PostgreSQL write boundary for operations metadata.

The boundary is intentionally not wired into the service yet.  Callers must
provide the surrounding transaction and the cutover stage decides when these
writes may replace DuckDB writes.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from psycopg import sql

from .postgres_repository import PostgresRepository


def _payload(value: Mapping[str, Any] | None) -> str:
    return json.dumps(value or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


class PostgresWriteRepository:
    """Parameterized, idempotent operations/catalog writes."""

    def __init__(self, repository: PostgresRepository):
        self.repository = repository

    def _connection(self):
        if self.repository.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        return self.repository.connection

    def upsert_job(self, *, job_id: str, job_key: str | None, status: str, payload: Mapping[str, Any] | None = None) -> None:
        query = sql.SQL(
            "insert into {schema}.jobs(job_id,job_key,status,payload_json) values (%s,%s,%s,%s::jsonb) "
            "on conflict(job_id) do update set job_key=excluded.job_key,status=excluded.status,payload_json=excluded.payload_json"
        ).format(schema=sql.Identifier(self.repository.schema))
        with self._connection().cursor() as cur:
            cur.execute(query, (job_id, job_key, status, _payload(payload)))

    def job(self, job_id: str) -> dict[str, Any] | None:
        query = sql.SQL("select job_id,job_key,status,payload_json from {schema}.jobs where job_id=%s").format(schema=sql.Identifier(self.repository.schema))
        with self._connection().cursor() as cur:
            cur.execute(query, (job_id,))
            row = cur.fetchone()
        if not row:
            return None
        payload = row[3] if isinstance(row[3], dict) else json.loads(row[3] or "{}")
        return {"job_id": str(row[0]), "job_key": row[1], "status": str(row[2]), "payload": payload}

    def upsert_storage_object(self, *, storage_object_id: str, payload: Mapping[str, Any]) -> None:
        query = sql.SQL(
            "insert into {schema}.storage_objects(storage_object_id,payload_json) values (%s,%s::jsonb) "
            "on conflict(storage_object_id) do update set payload_json=excluded.payload_json"
        ).format(schema=sql.Identifier(self.repository.schema))
        with self._connection().cursor() as cur:
            cur.execute(query, (storage_object_id, _payload(payload)))

    def storage_object(self, storage_object_id: str) -> dict[str, Any] | None:
        query = sql.SQL("select storage_object_id,payload_json from {schema}.storage_objects where storage_object_id=%s").format(schema=sql.Identifier(self.repository.schema))
        with self._connection().cursor() as cur:
            cur.execute(query, (storage_object_id,))
            row = cur.fetchone()
        if not row:
            return None
        payload = row[1] if isinstance(row[1], dict) else json.loads(row[1] or "{}")
        return {"storage_object_id": str(row[0]), "payload": payload}

    def storage_objects(self) -> list[dict[str, Any]]:
        query = sql.SQL("select storage_object_id,payload_json from {schema}.storage_objects order by storage_object_id").format(
            schema=sql.Identifier(self.repository.schema)
        )
        with self._connection().cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
        return [
            {
                "storage_object_id": str(row[0]),
                "payload": row[1] if isinstance(row[1], dict) else json.loads(row[1] or "{}"),
            }
            for row in rows
        ]


__all__ = ["PostgresWriteRepository"]
