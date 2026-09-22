"""Small, transactional PostgreSQL write boundary for operations metadata.

The boundary is intentionally not wired into the service yet.  Callers must
provide the surrounding transaction and the cutover stage decides when these
writes may replace DuckDB writes.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
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

    @contextmanager
    def transaction(self):
        with self.repository.transaction():
            yield self

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

    def upsert_lease(self, *, lease_id: str, payload: Mapping[str, Any]) -> None:
        query = sql.SQL(
            "insert into {schema}.leases(lease_id,payload_json) values (%s,%s::jsonb) "
            "on conflict(lease_id) do update set payload_json=excluded.payload_json"
        ).format(schema=sql.Identifier(self.repository.schema))
        with self._connection().cursor() as cur:
            cur.execute(query, (lease_id, _payload(payload)))

    def lease(self, lease_id: str) -> dict[str, Any] | None:
        query = sql.SQL("select lease_id,payload_json from {schema}.leases where lease_id=%s").format(
            schema=sql.Identifier(self.repository.schema)
        )
        with self._connection().cursor() as cur:
            cur.execute(query, (lease_id,))
            row = cur.fetchone()
        if not row:
            return None
        payload = row[1] if isinstance(row[1], dict) else json.loads(row[1] or "{}")
        return {"lease_id": str(row[0]), "payload": payload}

    def upsert_cleanup_job(self, *, cleanup_job_id: str, payload: Mapping[str, Any]) -> None:
        query = sql.SQL(
            "insert into {schema}.cleanup_jobs(cleanup_job_id,payload_json) values (%s,%s::jsonb) "
            "on conflict(cleanup_job_id) do nothing"
        ).format(schema=sql.Identifier(self.repository.schema))
        with self._connection().cursor() as cur:
            cur.execute(query, (cleanup_job_id, _payload(payload)))

    def cleanup_job(self, cleanup_job_id: str) -> dict[str, Any] | None:
        query = sql.SQL("select cleanup_job_id,payload_json from {schema}.cleanup_jobs where cleanup_job_id=%s").format(
            schema=sql.Identifier(self.repository.schema)
        )
        with self._connection().cursor() as cur:
            cur.execute(query, (cleanup_job_id,))
            row = cur.fetchone()
        if not row:
            return None
        payload = row[1] if isinstance(row[1], dict) else json.loads(row[1] or "{}")
        return {"cleanup_job_id": str(row[0]), "payload": payload}

    def database_references(self) -> set[str]:
        query = sql.SQL("""
            select s.storage_object_id
            from {schema}.publication_analysis_snapshots p
            join {schema}.analysis_snapshots a on a.snapshot_id=p.snapshot_id and a.status='SUCCESS'
            join {schema}.analysis_snapshot_entries e on e.snapshot_id=a.snapshot_id
            join {schema}.analysis_slices s on s.slice_id=e.slice_id
            where s.storage_object_id is not null
        """).format(schema=sql.Identifier(self.repository.schema))
        with self._connection().cursor() as cur:
            cur.execute(query)
            return {str(row[0]) for row in cur.fetchall() if row[0]}

    def analysis_object_dates(self) -> dict[str, str]:
        query = sql.SQL("""
            select storage_object_id, cast(max(trade_date) as text)
            from {schema}.analysis_slices
            where storage_object_id is not null
            group by storage_object_id
        """).format(schema=sql.Identifier(self.repository.schema))
        with self._connection().cursor() as cur:
            cur.execute(query)
            return {str(row[0]): str(row[1]) for row in cur.fetchall() if row[0]}

    def active_job_references(self) -> set[str]:
        refs: set[str] = set()
        with self._connection().cursor() as cur:
            cur.execute(sql.SQL("select payload_json from {}.jobs where status in ('QUEUED','RUNNING','INTERRUPTED')").format(sql.Identifier(self.repository.schema)))
            rows = cur.fetchall()
        slice_ids: list[str] = []
        for (raw,) in rows:
            payload = raw if isinstance(raw, dict) else json.loads(raw or "{}")
            pending = payload.get("pending_storage_object_ids", [])
            if isinstance(pending, list):
                refs.update(str(value) for value in pending)
            completed = payload.get("completed_slice_ids", [])
            if isinstance(completed, list):
                slice_ids.extend(str(value) for value in completed)
        if slice_ids:
            with self._connection().cursor() as cur:
                cur.execute(
                    sql.SQL("select storage_object_id from {}.analysis_slices where slice_id = any(%s) and storage_object_id is not null").format(sql.Identifier(self.repository.schema)),
                    (slice_ids,),
                )
                refs.update(str(row[0]) for row in cur.fetchall() if row[0])
        return refs

    def active_lease_references(self) -> set[str]:
        now = datetime.now(timezone.utc)
        refs: set[str] = set()
        with self._connection().cursor() as cur:
            cur.execute(sql.SQL("select payload_json from {}.leases").format(sql.Identifier(self.repository.schema)))
            rows = cur.fetchall()
        for (raw,) in rows:
            payload = raw if isinstance(raw, dict) else json.loads(raw or "{}")
            if payload.get("state") != "ACTIVE":
                continue
            expires = payload.get("expires_at_utc") or payload.get("lease_until_utc")
            try:
                active = expires and datetime.fromisoformat(str(expires).replace("Z", "+00:00")) > now
            except ValueError:
                active = False
            if active and isinstance(payload.get("storage_object_ids"), list):
                refs.update(str(value) for value in payload["storage_object_ids"])
        return refs

    def payload_rows(self, table: str) -> list[dict[str, Any]]:
        allowed = {"config_versions", "storage_objects", "backup_catalog", "cleanup_jobs"}
        if table not in allowed:
            raise ValueError("OPERATIONS_TABLE_NOT_ALLOWED")
        query = sql.SQL("select payload_json from {schema}.{table} order by 1").format(
            schema=sql.Identifier(self.repository.schema), table=sql.Identifier(table)
        )
        with self._connection().cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
        return [row[0] if isinstance(row[0], dict) else json.loads(row[0] or "{}") for row in rows]

    def metadata_counts(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for table in ("storage_objects", "backup_catalog"):
            query = sql.SQL("select count(*) from {schema}.{table}").format(
                schema=sql.Identifier(self.repository.schema), table=sql.Identifier(table)
            )
            with self._connection().cursor() as cur:
                cur.execute(query)
                result[table] = int(cur.fetchone()[0])
        with self._connection().cursor() as cur:
            cur.execute(sql.SQL("select count(*) from {}.jobs where status in ('QUEUED','RUNNING','INTERRUPTED')").format(sql.Identifier(self.repository.schema)))
            result["active_jobs"] = int(cur.fetchone()[0])
        return result


__all__ = ["PostgresWriteRepository"]
