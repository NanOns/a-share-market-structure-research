"""Opt-in adapter from current V4 read entry names to a PG candidate context.

This adapter is deliberately not wired into the default 28765 handler. It is a
single entry point for a future explicit candidate injection (or in-process
integration test) and has no artifact, SQLite, or Authority-file fallback.
"""
from __future__ import annotations

from typing import Any

from workbench_db.v4_publication_reader import PgPublicationReader, PublicationReadError
from workbench_db.v4_publication_contract import PAGE_PROJECTIONS


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
        page = ENDPOINT_MODULES.get(endpoint)
        if page is None:
            raise PublicationReadError("PG_CURRENT_ENDPOINT_UNSUPPORTED")
        context = self.reader.read_context(
            trade_date=trade_date,
            model_namespace_id=model_namespace_id,
            expected_context_token=expected_context_token,
            resolve_payloads=True,
        )
        payloads = context.get("module_payloads")
        if not isinstance(payloads, dict):
            raise PublicationReadError("PG_CURRENT_OWNER_PAYLOADS_UNAVAILABLE")
        projection = PAGE_PROJECTIONS[page]
        owner_payloads = {
            family: payloads[family]
            for family in projection["owner_families"]
            if family in payloads
        }
        unavailable_families = sorted(set(projection["owner_families"]) - set(owner_payloads))
        status = "DEGRADED" if owner_payloads else "PENDING"
        return {
            "contract_id": CONTRACT_ID,
            "status": status,
            "candidate_only": True,
            "context": context,
            "page": page,
            "quality_status": "NOT_VERIFIABLE_PAGE_PARITY",
            "required_input_groups": list(projection["input_groups"]),
            "uncovered_input_groups": list(projection["uncovered_groups"]),
            "owner_families": list(projection["owner_families"]),
            "unavailable_owner_families": unavailable_families,
            "payload": owner_payloads,
        }
