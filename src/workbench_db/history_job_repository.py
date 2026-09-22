"""Backend-neutral state boundary for the HISTORY_ANALYSIS state machine."""
from __future__ import annotations

import json
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Protocol

import duckdb

from .config_store import default_database_path


class HistoryJobStore(Protocol):
    def publication_source_identity(self, publication_id: str) -> tuple[str, str | None]: ...
    def job_by_key(self, job_key: str) -> dict[str, Any] | None: ...
    def job(self, job_id: str) -> dict[str, Any] | None: ...
    def upsert_job(self, *, job_id: str, job_key: str | None, status: str, payload: Mapping[str, Any]) -> None: ...
    def update_job(self, job_id: str, *, status: str | None = None, payload: Mapping[str, Any] | None = None) -> None: ...
    def upsert_attempt(self, *, job_id: str, attempt: int, status: str, payload: Mapping[str, Any]) -> None: ...
    def latest_attempt(self, job_id: str) -> dict[str, Any] | None: ...
    def next_attempt(self, job_id: str) -> int: ...
    def update_attempt(self, job_id: str, attempt: int, *, status: str | None = None, payload: Mapping[str, Any] | None = None) -> None: ...
    def append_event(self, *, job_id: str, attempt: int, status: str, details: Mapping[str, Any] | None = None) -> int: ...
    def latest_event(self, job_id: str) -> dict[str, Any] | None: ...
    def active_history_jobs(self, job_kind: str) -> list[str]: ...
    def slice_domain(self, slice_id: str) -> str | None: ...


class HistoryJobRepository(Protocol):
    @contextmanager
    def transaction(self) -> Iterator[HistoryJobStore]: ...


class DuckDBHistoryJobStore:
    def __init__(self, connection: duckdb.DuckDBPyConnection):
        self.connection = connection

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)

    @staticmethod
    def _payload(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else json.loads(value or "{}")

    def publication_source_identity(self, publication_id: str) -> tuple[str, str | None]:
        row = self.connection.execute("select cast(trade_date as varchar),source_identity_sha256 from publications where publication_id=? and status='SUCCESS'", [publication_id]).fetchone()
        if not row:
            raise KeyError("PUBLICATION_NOT_FOUND")
        return str(row[0]), str(row[1]) if row[1] is not None else None

    def job_by_key(self, job_key: str) -> dict[str, Any] | None:
        return self._job(self.connection.execute("select job_id,job_key,status,payload_json from jobs where job_key=?", [job_key]).fetchone())

    def job(self, job_id: str) -> dict[str, Any] | None:
        return self._job(self.connection.execute("select job_id,job_key,status,payload_json from jobs where job_id=?", [job_id]).fetchone())

    def _job(self, row: Any) -> dict[str, Any] | None:
        if not row:
            return None
        return {"job_id": str(row[0]), "job_key": row[1], "status": str(row[2]), "payload": self._payload(row[3])}

    def upsert_job(self, *, job_id: str, job_key: str | None, status: str, payload: Mapping[str, Any]) -> None:
        self.connection.execute("insert into jobs values (?,?,?,?) on conflict(job_id) do update set job_key=excluded.job_key,status=excluded.status,payload_json=excluded.payload_json", [job_id, job_key, status, self._json(payload)])

    def update_job(self, job_id: str, *, status: str | None = None, payload: Mapping[str, Any] | None = None) -> None:
        if status is not None and payload is not None:
            self.connection.execute("update jobs set status=?,payload_json=? where job_id=?", [status, self._json(payload), job_id])
        elif status is not None:
            self.connection.execute("update jobs set status=? where job_id=?", [status, job_id])
        elif payload is not None:
            self.connection.execute("update jobs set payload_json=? where job_id=?", [self._json(payload), job_id])

    def upsert_attempt(self, *, job_id: str, attempt: int, status: str, payload: Mapping[str, Any]) -> None:
        self.connection.execute("insert into job_attempts values (?,?,?,?) on conflict(job_id,attempt) do update set status=excluded.status,payload_json=excluded.payload_json", [job_id, attempt, status, self._json(payload)])

    def latest_attempt(self, job_id: str) -> dict[str, Any] | None:
        row = self.connection.execute("select attempt,status,payload_json from job_attempts where job_id=? order by attempt desc limit 1", [job_id]).fetchone()
        if not row:
            return None
        return {"attempt": int(row[0]), "status": str(row[1]), "payload": self._payload(row[2])}

    def next_attempt(self, job_id: str) -> int:
        return int(self.connection.execute("select coalesce(max(attempt),0)+1 from job_attempts where job_id=?", [job_id]).fetchone()[0])

    def update_attempt(self, job_id: str, attempt: int, *, status: str | None = None, payload: Mapping[str, Any] | None = None) -> None:
        if status is not None and payload is not None:
            self.connection.execute("update job_attempts set status=?,payload_json=? where job_id=? and attempt=?", [status, self._json(payload), job_id, attempt])
        elif status is not None:
            self.connection.execute("update job_attempts set status=? where job_id=? and attempt=?", [status, job_id, attempt])
        elif payload is not None:
            self.connection.execute("update job_attempts set payload_json=? where job_id=? and attempt=?", [self._json(payload), job_id, attempt])

    def append_event(self, *, job_id: str, attempt: int, status: str, details: Mapping[str, Any] | None = None) -> int:
        payload = self._json({"status": status, **dict(details or {})})
        for _ in range(8):
            sequence = int(self.connection.execute("select coalesce(max(sequence),0)+1 from job_events where job_id=? and attempt=?", [job_id, attempt]).fetchone()[0])
            try:
                self.connection.execute("insert into job_events values (?,?,?,?,?) on conflict(job_id,attempt,sequence) do nothing", [job_id, attempt, sequence, datetime.now(timezone.utc), payload])
                return sequence
            except duckdb.TransactionException:
                self.connection.rollback()
                time.sleep(0.01)
        raise RuntimeError("JOB_EVENT_SEQUENCE_CONFLICT")

    def latest_event(self, job_id: str) -> dict[str, Any] | None:
        row = self.connection.execute("select attempt,sequence,event_time_utc,payload_json from job_events where job_id=? order by attempt desc,sequence desc limit 1", [job_id]).fetchone()
        if not row:
            return None
        return {"attempt": int(row[0]), "sequence": int(row[1]), "event_time_utc": row[2], "payload": self._payload(row[3])}

    def active_history_jobs(self, job_kind: str) -> list[str]:
        rows = self.connection.execute("select job_id from jobs where status in ('QUEUED','RUNNING','INTERRUPTED') and json_extract_string(payload_json,'$.job_kind')=? order by job_id", [job_kind]).fetchall()
        return [str(row[0]) for row in rows]

    def slice_domain(self, slice_id: str) -> str | None:
        row = self.connection.execute("select domain from analysis_slices where slice_id=?", [slice_id]).fetchone()
        return str(row[0]) if row else None


class DuckDBHistoryJobRepository:
    """Compatibility adapter with bounded lock retry for local jobs."""

    def __init__(self, root: str | Path, database_path: str | Path | None = None):
        root = Path(root).resolve()
        self.database_path = Path(database_path).resolve() if database_path is not None else default_database_path(root)

    @contextmanager
    def transaction(self) -> Iterator[DuckDBHistoryJobStore]:
        last_error: duckdb.IOException | None = None
        for _ in range(50):
            try:
                with duckdb.connect(str(self.database_path)) as connection:
                    yield DuckDBHistoryJobStore(connection)
                return
            except duckdb.IOException as exc:
                last_error = exc
                time.sleep(0.02)
        assert last_error is not None
        raise last_error


__all__ = ["HistoryJobRepository", "HistoryJobStore", "DuckDBHistoryJobRepository", "DuckDBHistoryJobStore"]
