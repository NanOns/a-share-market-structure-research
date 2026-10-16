"""Opt-in adapter from current V4 read entry names to a PG candidate context.

This adapter is deliberately not wired into the default 28765 handler. It is a
single entry point for a future explicit candidate injection (or in-process
integration test) and has no artifact, SQLite, or Authority-file fallback.
"""
from __future__ import annotations

from typing import Any

from workbench_db.v4_publication_reader import PgPublicationReader, PublicationReadError


CONTRACT_ID = "V4_PG_CURRENT_ENDPOINT_ADAPTER_R1"
ENDPOINT_MODULES = {
    "/api/v4/current/summary": "summary",
    "/api/v4/current/radar": "radar",
    "/api/v4/current/entity": "entity",
    "/api/v4/current/sector": "sector",
    "/api/v4/current/cohort": "cohort",
    "/api/v4/current/settlement": "settlement",
    "/api/v4/current/health": "health",
}


class PgV4CurrentAdapter:
    """Serve one endpoint from one fully read-back PG publication snapshot."""

    def __init__(self, reader: PgPublicationReader):
        if not isinstance(reader, PgPublicationReader):
            raise TypeError("PG_PUBLICATION_READER_REQUIRED")
        self.reader = reader

    def read_endpoint(
        self,
        endpoint: str,
        *,
        trade_date: str,
        model_namespace_id: str,
        expected_context_token: str | None = None,
    ) -> dict[str, Any]:
        module = ENDPOINT_MODULES.get(endpoint)
        if module is None:
            raise PublicationReadError("PG_CURRENT_ENDPOINT_UNSUPPORTED")
        context = self.reader.read_context(
            trade_date=trade_date,
            model_namespace_id=model_namespace_id,
            expected_context_token=expected_context_token,
            resolve_payloads=True,
        )
        payloads = context.get("module_payloads")
        if not isinstance(payloads, dict) or module not in payloads:
            raise PublicationReadError("PG_CURRENT_MODULE_PAYLOAD_UNAVAILABLE")
        return {
            "contract_id": CONTRACT_ID,
            "status": "READY_CURRENT_ACCEPTED",
            "candidate_only": True,
            "context": context,
            "module": module,
            "payload": payloads[module],
        }
