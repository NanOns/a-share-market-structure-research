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
        page_rows: list[dict[str, Any]] = []
        row_prefix = page
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
                    "field_states": _field_states(selected, missing, contract_known=True),
                })
                page_rows.append({"row": payload, "path": f"page_data.summary_events[{index}].payload", "verified": True})
                field_map.update(paths)
        elif page == "entity":
            parsed["lifecycle"] = []
            for index, row in enumerate(page_data.get("entity_lifecycle", [])):
                selected, paths, missing = _project_fields(
                    row, ("security_id", "security_type", "board", "listed_from", "listed_to",
                          "st_state", "trade_status", "trade_date", "effective_from", "effective_to",
                          "quality", "source_revision_id"),
                    f"page_data.entity_lifecycle[{index}]",
                )
                selected["missing_fields"] = missing
                selected["field_states"] = _field_states(selected, missing, contract_known=True)
                selected["trade_date"] = page_data.get("trade_date")
                field_map["trade_date"] = "page_data.trade_date"
                parsed["lifecycle"].append(selected)
                page_rows.append({"row": selected, "path": f"page_data.entity_lifecycle[{index}]", "verified": True,
                                  "eligible_fields": {"trade_date", "source_security_key", "list_date", "scenario", "state", "health", "maturity"}})
                field_map.update(paths)
            parsed["daily_core"] = []
            core_fields = ("security_id", "security_type", "trade_status", "open", "high", "low", "close",
                           "volume", "amount", "ma5", "ma20", "ma60", "history_status", "profile_payload",
                           "trade_date", "source_revision_id", "quality_status")
            for index, row in enumerate(page_data.get("daily_core_rows", [])):
                selected, paths, missing = _project_fields(
                    row, core_fields, f"page_data.daily_core_rows[{index}]",
                )
                selected["field_states"] = _field_states(selected, missing, contract_known=True)
                parsed["daily_core"].append(selected)
                page_rows.append({"row": selected, "path": f"page_data.daily_core_rows[{index}]", "verified": True,
                                  "eligible_fields": {"trade_date", "open", "high", "low", "close", "ma5", "ma20", "ma60", "history_status", "profile_payload"}})
                field_map.update(paths)
            lifecycle_by_id = {}
            for row in parsed["lifecycle"]:
                lifecycle_by_id.setdefault(row.get("security_id"), []).append(row)
            parsed["entities"] = []
            for row in parsed["daily_core"]:
                security_id = row.get("security_id")
                parsed["entities"].append({
                    "security_id": security_id,
                    "trade_date": trade_date,
                    "daily_core": row,
                    "lifecycle_candidates": lifecycle_by_id.get(security_id, []),
                    "identity_name_state": "DATA_MISSING",
                    "identity_name_reason": "NO_V4_PUBLICATION_BOUND_IDENTITY_NAME_RELATION",
                    "context_token": context["context_token"],
                })
        elif page == "radar":
            for group in ("stocks", "sectors"):
                for index, row in enumerate(parsed.get(group, [])):
                    page_rows.append({"row": row, "path": f"payload.research_priority.{group}.all_items[{index}]", "verified": True})
        elif page == "sector":
            rows = parsed.get("sector_lifecycle_supplement", [])
            for index, row in enumerate(rows):
                page_rows.append({"row": row, "path": f"payload.sector_lifecycle[{index}]", "verified": True})
            parsed["sector_membership"] = []
            for index, row in enumerate(rows):
                parsed["sector_membership"].append({
                    "sector_id": row.get("sector_id"),
                    "sector_name": None,
                    "member_count": None,
                    "algorithm_state": None,
                    "field_data_states": {
                        "sector_id": "DATA_MISSING",
                        "sector_name": "DATA_MISSING",
                        "member_count": "DATA_MISSING",
                        "algorithm_state": "DATA_MISSING",
                    },
                    "field_reasons": {
                        "sector_id": "SECTOR_MEMBERSHIP_FACTS_HAVE_NO_PUBLICATION_SOURCE_BINDING",
                        "sector_name": "NO_V4_PUBLICATION_BOUND_IDENTITY_NAME_RELATION",
                        "member_count": "NO_V4_PUBLICATION_BOUND_SECTOR_MEMBERSHIP_RELATION",
                        "algorithm_state": "NO_PUBLICATION_BOUND_ALGORITHM_STATE_RELATION",
                    },
                    "lifecycle_supplement": row,
                    "context_token": context["context_token"],
                })
        elif page == "health":
            for family, row in sorted(parsed.get("risk_families", {}).items()):
                page_rows.append({"row": row, "path": f"payload.operational_risk.families.{family}",
                                  "verified": True, "eligible_fields": set()})
            for index, row in enumerate(parsed.get("sector_lifecycle_supplement", [])):
                page_rows.append({"row": row, "path": f"payload.sector_lifecycle[{index}]",
                                  "verified": True, "eligible_fields": {"maturity"}})
        eligible_fields = {
            "summary": set(projection["consumer_fields"]),
            "radar": set(projection["consumer_fields"]),
            "entity": {"trade_date", "open", "high", "low", "close", "ma5", "ma20", "ma60",
                       "history_status", "profile_payload"},
            "sector": set(),
            "cohort": set(),
            "settlement": set(),
            "health": {"maturity"},
        }[page]
        field_source_gaps = {
            "open": page_data.get("uncovered", {}).get("entity_prices", "NO_V4_PUBLICATION_BOUND_DAILY_PRICE_RELATION"),
            "high": page_data.get("uncovered", {}).get("entity_prices", "NO_V4_PUBLICATION_BOUND_DAILY_PRICE_RELATION"),
            "low": page_data.get("uncovered", {}).get("entity_prices", "NO_V4_PUBLICATION_BOUND_DAILY_PRICE_RELATION"),
            "close": page_data.get("uncovered", {}).get("entity_prices", "NO_V4_PUBLICATION_BOUND_DAILY_PRICE_RELATION"),
            "source_security_key": "NO_V4_PUBLICATION_BOUND_IDENTITY_NAME_RELATION",
            "list_date": "NO_V4_PUBLICATION_BOUND_IDENTITY_NAME_RELATION",
            "scenario": "NO_PUBLICATION_BOUND_STATE_OR_SCENARIO_RELATION",
            "state": "NO_PUBLICATION_BOUND_STATE_OR_SCENARIO_RELATION",
            "health": "NO_PUBLICATION_BOUND_HEALTH_RESULT_RELATION",
            "maturity": "NO_PUBLICATION_BOUND_MATURITY_RESULT_RELATION",
            "ma5": page_data.get("uncovered", {}).get("entity_prices", "NO_PUBLICATION_BOUND_CORE_PROFILE_RELATION"),
            "ma20": page_data.get("uncovered", {}).get("entity_prices", "NO_PUBLICATION_BOUND_CORE_PROFILE_RELATION"),
            "ma60": page_data.get("uncovered", {}).get("entity_prices", "NO_PUBLICATION_BOUND_CORE_PROFILE_RELATION"),
            "history_status": page_data.get("uncovered", {}).get("entity_prices", "NO_PUBLICATION_BOUND_CORE_PROFILE_RELATION"),
            "profile_payload": page_data.get("uncovered", {}).get("entity_prices", "NO_PUBLICATION_BOUND_CORE_PROFILE_RELATION"),
            "sector_id": page_data.get("uncovered", {}).get("sector_membership", "SECTOR_MEMBERSHIP_FACTS_HAVE_NO_PUBLICATION_SOURCE_BINDING"),
            "sector_name": "NO_V4_PUBLICATION_BOUND_IDENTITY_NAME_RELATION",
            "member_count": "NO_V4_PUBLICATION_BOUND_SECTOR_MEMBERSHIP_RELATION",
            "algorithm_state": "NO_PUBLICATION_BOUND_ALGORITHM_STATE_RELATION",
            "component": "NO_PUBLICATION_BOUND_REPLAY_RELATION",
            "row_count": "NO_PUBLICATION_BOUND_REPLAY_RELATION",
            "quality": "NO_PUBLICATION_BOUND_REPLAY_RELATION",
            "freshness": "NO_PUBLICATION_BOUND_REPLAY_RELATION",
            "source_quality": "NO_PUBLICATION_BOUND_REPLAY_RELATION",
        }
        uncovered = {
            group: (
                "NO_V4_PUBLICATION_BOUND_DAILY_PRICE_RELATION" if group == "RAW_DAILY" else
                "NO_V4_PUBLICATION_BOUND_IDENTITY_NAME_RELATION" if group == "identity_names" else
                page_data.get("uncovered", {}).get(group, "NO_PUBLICATION_BOUND_PG_RELATION_OR_PRODUCER")
            )
            for group in projection["uncovered_groups"]
        }
        field_coverage = _field_coverage(
            projection["consumer_fields"], page_rows, target_t0=trade_date,
            no_row_reason=(
                "OWNER_FAMILY_UNAVAILABLE" if unavailable_families else
                "NO_PUBLICATION_BOUND_ROWS" if page in ("summary", "entity", "radar", "sector", "health") else
                "NO_PUBLICATION_BOUND_PG_RELATION"
            ),
            contract_known=page not in ("cohort", "settlement"),
            eligible_fields=eligible_fields,
            field_missing_reasons=field_source_gaps,
        )
        field_states = {field: item["status"] for field, item in field_coverage.items()}
        field_data_states = {
            field: (
                "PENDING_PG_HEAD" if item["missing_reason"] == "NO_ACCEPTED_PUBLICATION" else
                "NOT_PIT_ELIGIBLE" if "PIT" in str(item["missing_reason"] or "") else
                "NO_READER_PRIVILEGE" if "PRIVILEGE" in str(item["missing_reason"] or "") else
                "DATA_MISSING" if item["status"] in {"SOURCE_MISSING", "CONTRACT_UNKNOWN"} else
                "PARTIAL_DATA_VERIFIED" if item["status"] == "PARTIAL_PG_FIELD_VERIFIED" else
                "DATA_VERIFIED"
            )
            for field, item in field_coverage.items()
        }
        business_statuses = set(field_states.values())
        business_result_state = (
            "PG_FIELD_VERIFIED" if business_statuses == {"PG_FIELD_VERIFIED"} else
            "PARTIAL_PG_FIELD_VERIFIED" if "PG_FIELD_VERIFIED" in business_statuses or "PARTIAL_PG_FIELD_VERIFIED" in business_statuses else
            "CONTRACT_UNKNOWN" if "CONTRACT_UNKNOWN" in business_statuses else
            "SOURCE_MISSING"
        )
        # Per-row state is based on this row, never on a hit elsewhere in the page.
        if page in ("summary", "entity"):
            row_key = "events" if page == "summary" else "lifecycle"
            for index, item in enumerate(parsed.get(row_key, [])):
                row_fields = item.get("fields", item)
                row_field_names = tuple(item.get("field_states", {}).keys())
                row_coverage = _field_coverage(
                    row_field_names,
                    [{"row": row_fields, "path": f"{row_prefix}[{index}]", "verified": True}],
                    target_t0=trade_date, no_row_reason="NO_PUBLICATION_BOUND_ROWS", contract_known=True,
                    eligible_fields=set(row_field_names), field_missing_reasons=field_source_gaps,
                )
                item["field_coverage"] = row_coverage
                item["field_states"] = {field: value["status"] for field, value in row_coverage.items()}
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
            "field_states": field_states,
            "field_data_states": field_data_states,
            "field_coverage": field_coverage,
            "business_result_state": business_result_state,
        }


def _project_fields(row: dict[str, Any], fields: tuple[str, ...], source_path: str):
    """Project exact producer keys; never alias or synthesize absent fields."""
    values = {key: row[key] for key in fields if key in row}
    mapping = {key: f"{source_path}.{key}" for key in values}
    missing = {key: "OWNER_FIELD_NOT_PRESENT" for key in fields if key not in row}
    return values, mapping, missing


def _field_states(selected: dict[str, Any], missing: dict[str, Any], *, contract_known: bool):
    state = "PG_FIELD_VERIFIED" if selected else "PROJECTION_READY"
    states = {field: state for field in selected if field not in {"missing_fields", "field_states"}}
    missing_state = "SOURCE_MISSING" if contract_known else "CONTRACT_UNKNOWN"
    states.update({field: missing_state for field in missing})
    return states


def _field_coverage(fields, rows, *, target_t0, no_row_reason, contract_known,
                    eligible_fields=None, field_missing_reasons=None):
    """Report row-level coverage; a single hit never implies page-wide coverage."""
    coverage = {}
    eligible_fields = set(fields) if eligible_fields is None else set(eligible_fields)
    field_missing_reasons = field_missing_reasons or {}
    for field in fields:
        eligible = present = verified = 0
        reasons = set()
        source_paths = []
        if field not in eligible_fields:
            no_field_source = field_missing_reasons.get(field, no_row_reason)
            coverage[field] = {
                "present_rows": 0,
                "eligible_rows": 0,
                "verified_rows": 0,
                "missing_reason": no_field_source,
                "source_paths": [],
                "status": "CONTRACT_UNKNOWN" if not contract_known else "SOURCE_MISSING",
            }
            continue
        for entry in rows:
            entry_fields = entry.get("eligible_fields")
            if entry_fields is not None and field not in entry_fields:
                continue
            row = entry.get("row", {})
            row_t0 = row.get("T0", row.get("trade_date")) if isinstance(row, dict) else None
            if row_t0 is not None and str(row_t0) != str(target_t0):
                reasons.add("T0_MISMATCH")
                continue
            eligible += 1
            if isinstance(row, dict) and field in row:
                present += 1
                if entry.get("verified") is True:
                    verified += 1
                    if isinstance(entry.get("path"), str):
                        source_paths.append(f"{entry['path']}.{field}")
            else:
                reasons.add("FIELD_NOT_PRESENT_IN_ROW")
        if eligible == 0:
            status = "CONTRACT_UNKNOWN" if not contract_known else "SOURCE_MISSING"
            missing_reason = next(iter(sorted(reasons)), field_missing_reasons.get(field, no_row_reason))
        elif verified == eligible:
            status = "PG_FIELD_VERIFIED"
            missing_reason = None
        elif verified:
            status = "PARTIAL_PG_FIELD_VERIFIED"
            missing_reason = "FIELD_NOT_PRESENT_IN_ALL_ELIGIBLE_ROWS"
        else:
            status = "SOURCE_MISSING"
            missing_reason = next(iter(sorted(reasons)), "FIELD_NOT_VERIFIED")
        coverage[field] = {
            "present_rows": present,
            "eligible_rows": eligible,
            "verified_rows": verified,
            "missing_reason": missing_reason,
            "source_paths": source_paths,
            "status": status,
        }
    return coverage


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
