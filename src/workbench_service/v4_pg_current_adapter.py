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
        parsed, field_map = _parse_owner_projection(page, owner_payloads)
        page_data = context.get("page_data", {})
        if page == "summary":
            events = page_data.get("summary_events", [])
            parsed["events"] = []
            for index, event in enumerate(events):
                payload = event.get("payload") if isinstance(event, dict) else None
                if not isinstance(payload, dict):
                    continue
                selected, paths, missing = _project_fields(
                    payload, ("effective_event", "primary_scenario", "counterevidence", "trade_date", "why_now"),
                    f"page_data.summary_events[{index}].payload",
                )
                parsed["events"].append({
                    "logical_event_id": event["logical_event_id"],
                    "observation_revision": event["observation_revision"],
                    "fields": selected,
                    "missing_fields": missing,
                })
                field_map.update(paths)
        elif page == "entity":
            parsed["lifecycle"] = []
            for index, row in enumerate(page_data.get("entity_lifecycle", [])):
                selected, paths, _ = _project_fields(
                    row, ("security_id", "security_type", "board", "listed_from", "listed_to",
                          "st_state", "trade_status", "trade_date", "effective_from", "effective_to",
                          "quality", "source_revision_id"),
                    f"page_data.entity_lifecycle[{index}]",
                )
                parsed["lifecycle"].append(selected)
                field_map.update(paths)
        uncovered = {
            group: (
                "NO_V4_PUBLICATION_BOUND_DAILY_PRICE_RELATION" if group == "RAW_DAILY" else
                "NO_V4_PUBLICATION_BOUND_IDENTITY_NAME_RELATION" if group == "identity_names" else
                page_data.get("uncovered", {}).get(group, "NO_PUBLICATION_BOUND_PG_RELATION_OR_PRODUCER")
            )
            for group in projection["uncovered_groups"]
        }
        return {
            "contract_id": CONTRACT_ID,
            "status": status,
            "candidate_only": True,
            "context": context,
            "page": page,
            "quality_status": "NOT_VERIFIABLE_PAGE_PARITY",
            "required_input_groups": list(projection["input_groups"]),
            "uncovered_input_groups": list(projection["uncovered_groups"]),
            "uncovered_reasons": uncovered,
            "owner_families": list(projection["owner_families"]),
            "unavailable_owner_families": unavailable_families,
            "payload": owner_payloads,
            "parsed_business_fields": parsed,
            "field_mapping": field_map,
        }


def _project_fields(row: dict[str, Any], fields: tuple[str, ...], source_path: str):
    """Project exact producer keys; never alias or synthesize absent fields."""
    values = {key: row[key] for key in fields if key in row}
    mapping = {key: f"{source_path}.{key}" for key in values}
    missing = {key: "OWNER_FIELD_NOT_PRESENT" for key in fields if key not in row}
    return values, mapping, missing


def _parse_owner_projection(page: str, owners: dict[str, Any]):
    """Parse only fields backed by the fixed, verified Owner payload contracts."""
    fields = PAGE_PROJECTIONS[page]["consumer_fields"]
    result: dict[str, Any] = {}
    mapping: dict[str, str] = {}
    if page == "radar" and "research_priority" in owners:
        payload = owners["research_priority"]
        if not isinstance(payload, dict):
            return result, mapping
        for group in ("stocks", "sectors"):
            data = payload.get(group)
            items = data.get("all_items") if isinstance(data, dict) else None
            if not isinstance(items, list):
                continue
            projected = []
            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                values, paths, _ = _project_fields(item, fields, f"{group}.all_items[{index}]")
                projected.append(values)
                mapping.update(paths)
            result[group] = projected
        result["rule"] = payload.get("rule")
    elif page in ("summary", "health") and "operational_risk" in owners:
        payload = owners["operational_risk"]
        families = payload.get("families") if isinstance(payload, dict) else None
        if isinstance(families, dict):
            result["risk_families"] = {}
            for family, value in sorted(families.items()):
                if not isinstance(value, dict):
                    continue
                selected, paths, _ = _project_fields(
                    value, ("status", "changes", "prior_state", "current_state"),
                    f"families.{family}",
                )
                result["risk_families"][family] = selected
                mapping.update(paths)
    if page in ("sector", "health") and "sector_lifecycle" in owners:
        rows = owners["sector_lifecycle"]
        if isinstance(rows, dict):
            rows = rows.get("payload")
        if isinstance(rows, list):
            projected = []
            for index, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                selected, paths, _ = _project_fields(
                    row, ("sector_id", "maturity", "health", "T0", "contract_id"),
                    f"sector_lifecycle.payload[{index}]",
                )
                projected.append(selected)
                mapping.update(paths)
            result["sector_lifecycle_supplement"] = projected
    return result, mapping
