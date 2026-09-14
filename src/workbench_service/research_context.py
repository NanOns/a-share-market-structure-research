"""Read-only V3 research context resolution.

The context reader never starts a build and never installs the research-run
schema.  A database without a completed run therefore degrades to an
explicit NOT_BUILT response instead of creating a misleading identity.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date
import hashlib
import json
from typing import Any, Callable, Iterator

import duckdb


CONTRACT_ID = "RESEARCH_V3_API_PREVIEW_1"


class ResearchContextError(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def context_id_for(*, run_id: str | None, publication_id: str, local_date: str | None, mode: str, snapshot_id: str | None = None, algorithm_version: str | None = None) -> str:
    payload = {
        "contract": CONTRACT_ID,
        "run_id": run_id,
        "publication_id": str(publication_id),
        "local_date": local_date,
        "mode": str(mode).upper(),
        "snapshot_id": snapshot_id,
        "algorithm_version": algorithm_version,
    }
    return "ctx-" + hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()[:32]


def _date(value: Any, *, field: str = "trade_date") -> str:
    try:
        return date.fromisoformat(str(value)).isoformat()
    except (TypeError, ValueError) as exc:
        raise ResearchContextError(f"{field.upper()}_INVALID") from exc


class ResearchContextReader:
    """Resolve only immutable COMPLETE run identities."""

    def __init__(self, connection_provider: Callable[[], Any] | None = None):
        self.connection_provider = connection_provider

    @contextmanager
    def _connection(self, connection: duckdb.DuckDBPyConnection | None = None) -> Iterator[duckdb.DuckDBPyConnection]:
        if connection is not None:
            yield connection
            return
        if self.connection_provider is None:
            raise ResearchContextError("RESEARCH_CONNECTION_REQUIRED")
        with self.connection_provider() as provided:
            yield provided

    @staticmethod
    def _complete_rows(connection: duckdb.DuckDBPyConnection) -> list[tuple[Any, ...]]:
        try:
            return connection.execute(
                """SELECT run_id,input_key,trade_date,publication_id,snapshot_id,
                          algorithm_version,status
                   FROM research_runs WHERE status='COMPLETE'
                   ORDER BY completed_at DESC,created_at DESC,run_id DESC"""
            ).fetchall()
        except duckdb.CatalogException:
            return []

    @staticmethod
    def _ready(row: tuple[Any, ...], mode: str) -> dict[str, Any]:
        run_id, _input_key, trade_date, publication_id, snapshot_id, algorithm_version, status = row
        local_date = str(trade_date)
        return {
            "context_id": context_id_for(
                run_id=str(run_id), publication_id=str(publication_id), local_date=local_date,
                mode=mode, snapshot_id=str(snapshot_id), algorithm_version=str(algorithm_version),
            ),
            "status": "READY",
            "run_id": str(run_id),
            "mode": mode,
            "local_date": local_date,
            "online_date": None,
            "publication_id": str(publication_id),
            "snapshot_id": str(snapshot_id),
            "algorithm_version": str(algorithm_version),
            "capabilities": {"research": "READY", "local": "READY", "online": "NOT_REQUESTED"},
        }

    @staticmethod
    def _not_built(publication_id: str, local_date: str, mode: str) -> dict[str, Any]:
        return {
            "context_id": context_id_for(run_id=None, publication_id=publication_id, local_date=local_date, mode=mode),
            "status": "NOT_BUILT",
            "mode": mode,
            "local_date": local_date,
            "online_date": None,
            "publication_id": publication_id,
            "capabilities": {"research": "NOT_BUILT", "local": "READY", "online": "NOT_REQUESTED"},
        }

    def resolve_request(self, publication_id: str, trade_date: Any, mode: str = "CLOSE", connection: duckdb.DuckDBPyConnection | None = None) -> dict[str, Any]:
        publication_id = str(publication_id or "").strip()
        if not publication_id:
            raise ResearchContextError("PUBLICATION_ID_REQUIRED")
        local_date = _date(trade_date)
        mode = str(mode or "CLOSE").upper()
        if mode not in {"CLOSE", "LIVE"}:
            raise ResearchContextError("MODE_UNSUPPORTED")
        with self._connection(connection) as current:
            if mode == "LIVE":
                return self._not_built(publication_id, local_date, mode)
            rows = self._complete_rows(current)
        for row in rows:
            if str(row[3]) == publication_id and str(row[2]) == local_date:
                return self._ready(row, mode)
        return self._not_built(publication_id, local_date, mode)

    def resolve_id(self, context_id: str, connection: duckdb.DuckDBPyConnection | None = None) -> dict[str, Any]:
        context_id = str(context_id or "").strip()
        if not context_id:
            raise ResearchContextError("CONTEXT_ID_REQUIRED")
        with self._connection(connection) as current:
            for row in self._complete_rows(current):
                context = self._ready(row, "CLOSE")
                if context["context_id"] == context_id:
                    return context
        raise ResearchContextError("CONTEXT_NOT_FOUND")


__all__ = ["CONTRACT_ID", "ResearchContextError", "ResearchContextReader", "context_id_for"]
