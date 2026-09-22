"""PostgreSQL adapter for the HISTORY_ANALYSIS job state machine.

This boundary owns only the relational job state (``jobs``,
``job_attempts`` and ``job_events``).  It deliberately does not decide when
the live service may switch away from DuckDB; the cutover gate still requires
the service path to use this adapter and a separate end-to-end rehearsal.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator, Mapping

from psycopg import sql

from .postgres_repository import PostgresRepository


def _json(value: Mapping[str, Any] | None) -> str:
    return json.dumps(value or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value in (None, ""):
        return {}
    return json.loads(value)


class PostgresHistoryJobRepository:
    """Parameterized CRUD and event sequencing for history jobs.

    Methods operate on the already-open :class:`PostgresRepository`.  Callers
    should group a state transition in ``transaction()`` so the job, attempt
    and event rows commit or roll back together.
    """

    def __init__(self, repository: PostgresRepository):
        self.repository = repository

    def _connection(self):
        if self.repository.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        return self.repository.connection

    def _table(self, name: str) -> sql.Identifier:
        return sql.Identifier(self.repository.schema, name)

    @contextmanager
    def transaction(self) -> Iterator["PostgresHistoryJobRepository"]:
        with self.repository.transaction():
            yield self

    def upsert_job(self, *, job_id: str, job_key: str | None, status: str, payload: Mapping[str, Any]) -> None:
        query = sql.SQL(
            "insert into {}(job_id,job_key,status,payload_json) values (%s,%s,%s,%s::jsonb) "
            "on conflict(job_id) do update set job_key=excluded.job_key,status=excluded.status,payload_json=excluded.payload_json"
        ).format(self._table("jobs"))
        with self._connection().cursor() as cur:
            cur.execute(query, (job_id, job_key, status, _json(payload)))

    def job(self, job_id: str) -> dict[str, Any] | None:
        query = sql.SQL("select job_id,job_key,status,payload_json from {} where job_id=%s").format(self._table("jobs"))
        with self._connection().cursor() as cur:
            cur.execute(query, (job_id,))
            row = cur.fetchone()
        if not row:
            return None
        return {"job_id": str(row[0]), "job_key": row[1], "status": str(row[2]), "payload": _payload(row[3])}

    def publication_source_identity(self, publication_id: str) -> tuple[str, str | None]:
        query = sql.SQL("select cast(trade_date as text),source_identity_sha256 from {} where publication_id=%s and status='SUCCESS'").format(self._table("publications"))
        with self._connection().cursor() as cur:
            cur.execute(query, (publication_id,))
            row = cur.fetchone()
        if not row:
            raise KeyError("PUBLICATION_NOT_FOUND")
        return str(row[0]), str(row[1]) if row[1] is not None else None

    def job_by_key(self, job_key: str) -> dict[str, Any] | None:
        query = sql.SQL("select job_id,job_key,status,payload_json from {} where job_key=%s").format(self._table("jobs"))
        with self._connection().cursor() as cur:
            cur.execute(query, (job_key,))
            row = cur.fetchone()
        if not row:
            return None
        return {"job_id": str(row[0]), "job_key": row[1], "status": str(row[2]), "payload": _payload(row[3])}

    def update_job(self, job_id: str, *, status: str | None = None, payload: Mapping[str, Any] | None = None) -> None:
        assignments: list[sql.Composed] = []
        values: list[Any] = []
        if status is not None:
            assignments.append(sql.SQL("status=%s")); values.append(status)
        if payload is not None:
            assignments.append(sql.SQL("payload_json=%s::jsonb")); values.append(_json(payload))
        if not assignments:
            return
        values.append(job_id)
        query = sql.SQL("update {} set {} where job_id=%s").format(self._table("jobs"), sql.SQL(",").join(assignments))
        with self._connection().cursor() as cur:
            cur.execute(query, values)

    def upsert_attempt(self, *, job_id: str, attempt: int, status: str, payload: Mapping[str, Any]) -> None:
        query = sql.SQL(
            "insert into {}(job_id,attempt,status,payload_json) values (%s,%s,%s,%s::jsonb) "
            "on conflict(job_id,attempt) do update set status=excluded.status,payload_json=excluded.payload_json"
        ).format(self._table("job_attempts"))
        with self._connection().cursor() as cur:
            cur.execute(query, (job_id, attempt, status, _json(payload)))

    def latest_attempt(self, job_id: str) -> dict[str, Any] | None:
        query = sql.SQL("select attempt,status,payload_json from {} where job_id=%s order by attempt desc limit 1").format(self._table("job_attempts"))
        with self._connection().cursor() as cur:
            cur.execute(query, (job_id,))
            row = cur.fetchone()
        if not row:
            return None
        return {"attempt": int(row[0]), "status": str(row[1]), "payload": _payload(row[2])}

    def next_attempt(self, job_id: str) -> int:
        query = sql.SQL("select coalesce(max(attempt),0)+1 from {} where job_id=%s").format(self._table("job_attempts"))
        with self._connection().cursor() as cur:
            cur.execute(query, (job_id,))
            return int(cur.fetchone()[0])

    def update_attempt(self, job_id: str, attempt: int, *, status: str | None = None, payload: Mapping[str, Any] | None = None) -> None:
        assignments: list[sql.Composed] = []
        values: list[Any] = []
        if status is not None:
            assignments.append(sql.SQL("status=%s")); values.append(status)
        if payload is not None:
            assignments.append(sql.SQL("payload_json=%s::jsonb")); values.append(_json(payload))
        if not assignments:
            return
        values.extend([job_id, attempt])
        query = sql.SQL("update {} set {} where job_id=%s and attempt=%s").format(self._table("job_attempts"), sql.SQL(",").join(assignments))
        with self._connection().cursor() as cur:
            cur.execute(query, values)

    def append_event(self, *, job_id: str, attempt: int, status: str, details: Mapping[str, Any] | None = None) -> int:
        """Append an event and return its per-attempt sequence number.

        ``ON CONFLICT DO NOTHING`` makes the insert safe when two workers
        race.  A retry recomputes the next sequence under PostgreSQL's normal
        read-committed visibility without committing a partial state change.
        """
        query_max = sql.SQL("select coalesce(max(sequence),0)+1 from {} where job_id=%s and attempt=%s").format(self._table("job_events"))
        query_insert = sql.SQL(
            "insert into {}(job_id,attempt,sequence,event_time_utc,payload_json) values (%s,%s,%s,%s,%s::jsonb) on conflict(job_id,attempt,sequence) do nothing"
        ).format(self._table("job_events"))
        event_payload = {"status": status, **dict(details or {})}
        for _ in range(8):
            with self._connection().cursor() as cur:
                cur.execute(query_max, (job_id, attempt))
                sequence = int(cur.fetchone()[0])
                cur.execute(query_insert, (job_id, attempt, sequence, datetime.now(timezone.utc), _json(event_payload)))
                if cur.rowcount == 1:
                    return sequence
        raise RuntimeError("JOB_EVENT_SEQUENCE_CONFLICT")

    def events(self, job_id: str) -> list[dict[str, Any]]:
        query = sql.SQL("select attempt,sequence,event_time_utc,payload_json from {} where job_id=%s order by attempt,sequence").format(self._table("job_events"))
        with self._connection().cursor() as cur:
            cur.execute(query, (job_id,))
            rows = cur.fetchall()
        return [{"attempt": int(row[0]), "sequence": int(row[1]), "event_time_utc": row[2], "payload": _payload(row[3])} for row in rows]

    def latest_event(self, job_id: str) -> dict[str, Any] | None:
        query = sql.SQL("select attempt,sequence,event_time_utc,payload_json from {} where job_id=%s order by attempt desc,sequence desc limit 1").format(self._table("job_events"))
        with self._connection().cursor() as cur:
            cur.execute(query, (job_id,))
            row = cur.fetchone()
        if not row:
            return None
        return {"attempt": int(row[0]), "sequence": int(row[1]), "event_time_utc": row[2], "payload": _payload(row[3])}

    def active_history_jobs(self, job_kind: str = "HISTORY_ANALYSIS") -> list[str]:
        query = sql.SQL(
            "select job_id from {} where status in ('QUEUED','RUNNING','INTERRUPTED') and payload_json->>'job_kind'=%s order by job_id"
        ).format(self._table("jobs"))
        with self._connection().cursor() as cur:
            cur.execute(query, (job_kind,))
            return [str(row[0]) for row in cur.fetchall()]

    def slice_domain(self, slice_id: str) -> str | None:
        query = sql.SQL("select domain from {} where slice_id=%s").format(self._table("analysis_slices"))
        with self._connection().cursor() as cur:
            cur.execute(query, (slice_id,))
            row = cur.fetchone()
        return str(row[0]) if row else None

    def delete_job(self, job_id: str) -> None:
        """Delete a rehearsal job's children and parent in one transaction."""
        with self._connection().cursor() as cur:
            for table in ("job_events", "job_attempts", "jobs"):
                cur.execute(sql.SQL("delete from {} where job_id=%s").format(self._table(table)), (job_id,))


__all__ = ["PostgresHistoryJobRepository"]
