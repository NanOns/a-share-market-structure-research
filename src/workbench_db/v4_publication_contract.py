"""Versioned mapping from real V4 PG Owner families to current pages.

Pages are projections, not Owner identities.  Only the three Owner contracts
that have PG producers today are named here.  Their presence is capability
evidence; none is invented as a daily-publication prerequisite.
"""
from types import MappingProxyType


CONTRACT_ID = "V4_CURRENT_PUBLICATION_OWNER_PROJECTION_CONTRACT_R4"
CONTRACT_VERSION = "4.0.0"
MINIMUM_DAILY_PUBLICATION_CONTRACT_ID = "V4_DAILY_PUBLICATION_MINIMUM_R2"
MINIMUM_DAILY_PUBLICATION_CONTRACT = MappingProxyType({
    "contract_id": MINIMUM_DAILY_PUBLICATION_CONTRACT_ID,
    "version": "2.0.0",
    "required_owner_families": (),
    "required_base_fields": (
        "publication_id", "trade_date", "model_namespace_id", "revision_no",
        "database_identity", "computation_identity_sha256", "state_head_id", "state_logical_digest",
        "nonempty_source_manifest_contract", "verified_source_revision_rows",
        "accepted_source_package_authority", "bound_core_business_result",
    ),
    "acceptance_boundary": "METADATA_READY_IS_NOT_BUSINESS_PUBLISHABLE; CORE_RESULT_BINDING_REQUIRED; PG_READBACK_AND_HEAD_WRITE_SEPARATE",
})

OWNER_FAMILIES = MappingProxyType({
    "research_priority": MappingProxyType({
        "owner_contract_id": "V4_RESEARCH_PRIORITY_PG_OWNER_R1",
        "relation": "owner_payloads",
        "producer": "workbench_db.v4_operational_risk_pg_r1.prepare_priority",
        "daily_publication_required": False,
        "capability": "RESEARCH_PRIORITY_CONTEXT",
        "pages": ("radar",),
    }),
    "operational_risk": MappingProxyType({
        "owner_contract_id": "V4_OPERATIONAL_RISK_PG_OWNER_R1",
        "relation": "owner_payloads",
        "producer": "workbench_db.v4_operational_risk_pg_r1.prepare",
        "daily_publication_required": False,
        "capability": "THREE_FAMILY_OPERATIONAL_RISK",
        "pages": ("summary", "health"),
    }),
    "sector_lifecycle": MappingProxyType({
        "owner_contract_id": "V4_SECTOR_LIFECYCLE_PG_OWNER_R1",
        "relation": "owner_rows",
        "producer": "workbench_db.v4_sector_lifecycle_pg_r1.prepare",
        "daily_publication_required": False,
        "capability": "SECTOR_LIFECYCLE_SUPPLEMENT_ONLY",
        "pages": ("sector", "health"),
    }),
})

# These groups come from V4_CURRENT_ACCEPTED_READ_CONTRACT_V1.  The current PG
# Owner set does not prove parity for these inputs, so they stay unavailable.
PAGE_PROJECTIONS = MappingProxyType({
    "summary": MappingProxyType({
        "input_groups": ("events", "observations", "replay", "identity_names"),
        "owner_families": ("operational_risk",),
        "consumer_fields": ("effective_event", "primary_scenario", "counterevidence", "trade_date", "why_now"),
        "owner_field_paths": ("payload.families.*.status", "payload.families.*.changes[*].change"),
        "uncovered_groups": ("replay", "identity_names"),
    }),
    "radar": MappingProxyType({
        "input_groups": ("radar", "ledger", "replay", "identity_names"),
        "owner_families": ("research_priority",),
        "consumer_fields": ("entity_id", "signal_type", "eligibility_state", "priority_bucket", "trade_date"),
        "owner_field_paths": ("payload.stocks.all_items[*]", "payload.sectors.all_items[*]", "payload.rule"),
        "uncovered_groups": ("radar", "ledger", "replay", "identity_names"),
    }),
    "entity": MappingProxyType({
        "input_groups": ("RAW_DAILY", "IDENTITY_UNIVERSE", "states", "state_view", "events", "identity_names"),
        "owner_families": (),
        "consumer_fields": ("source_security_key", "close", "open", "high", "low", "trade_date", "list_date", "scenario", "state", "health", "maturity"),
        "owner_field_paths": (),
        "uncovered_groups": ("RAW_DAILY", "IDENTITY_UNIVERSE", "states", "state_view", "events", "identity_names"),
    }),
    "sector": MappingProxyType({
        "input_groups": ("membership",),
        "owner_families": ("sector_lifecycle",),
        "consumer_fields": ("sector_id", "sector_name", "member_count", "algorithm_state"),
        "owner_field_paths": ("payload[*].sector_id", "payload[*].maturity", "payload[*].health"),
        "uncovered_groups": ("membership",),
    }),
    "cohort": MappingProxyType({
        "input_groups": ("radar", "cohort", "maturity", "identity_names"),
        "owner_families": (),
        "consumer_fields": ("entity_id", "T0", "cohort_namespace", "enrollment_id", "evidence_class"),
        "owner_field_paths": (),
        "uncovered_groups": ("radar", "cohort", "maturity", "identity_names"),
    }),
    "settlement": MappingProxyType({
        "input_groups": ("outcomes", "settlement_receipt", "maturity"),
        "owner_families": (),
        "consumer_fields": ("enrollment_id", "horizon", "outcome_status", "due_date", "outcome_revision"),
        "owner_field_paths": (),
        "uncovered_groups": ("outcomes", "settlement_receipt", "maturity"),
    }),
    "health": MappingProxyType({
        "input_groups": ("replay", "maturity"),
        "owner_families": ("operational_risk", "sector_lifecycle"),
        "consumer_fields": ("component", "row_count", "quality", "freshness", "source_quality", "maturity"),
        "owner_field_paths": ("payload.families.*.status", "payload[*].health", "payload[*].maturity"),
        "uncovered_groups": ("replay", "maturity"),
    }),
})

PAGE_PG_RELATIONS = MappingProxyType({
    "summary": MappingProxyType({
        "events": "v4.event_observations WHERE publication_id = selected publication_id",
        "fields": "payload.effective_event, payload.primary_scenario, payload.counterevidence, payload.trade_date, payload.why_now",
        "coverage": "DIRECT_PUBLICATION_BOUND_ROWS; FIELD_PRESENCE_REPORTED_PER_ROW",
    }),
    "entity": MappingProxyType({
        "lifecycle": "v4.security_lifecycle_facts JOIN publication_consumed_sources ON source_revision_id",
        "fields": "security_id, security_type, board, listed_from, listed_to, st_state, trade_status, effective dates, quality",
        "coverage": "SOURCE_BOUND_LIFECYCLE_ONLY; DAILY_PRICES_AND_IDENTITY_NAMES_UNAVAILABLE",
    }),
    "radar": MappingProxyType({
        "priority": "hashed Owner owner_payloads via v4.publication_module_results",
        "coverage": "SUPPLEMENTAL_PRIORITY; FORMAL_LEDGER_AND_REPLAY_UNAVAILABLE",
    }),
    "sector": MappingProxyType({
        "lifecycle": "hashed Owner owner_rows via v4.publication_module_results",
        "coverage": "SUPPLEMENTAL_MATURITY; MEMBERSHIP_RELATION_NOT_BOUND_TO_PUBLICATION",
    }),
    "cohort": MappingProxyType({"coverage": "NO_PUBLICATION_BOUND_COHORT_RELATION"}),
    "settlement": MappingProxyType({"coverage": "NO_PUBLICATION_BOUND_SETTLEMENT_RELATION"}),
    "health": MappingProxyType({
        "owners": "operational_risk owner_payloads; sector_lifecycle owner_rows",
        "coverage": "OWNER_SUPPLEMENTS_ONLY; REPLAY_AND_MATURITY_UNAVAILABLE",
    }),
})

MODULES = OWNER_FAMILIES


def effective_module_contract():
    """Return a JSON-serializable contract copy for plans and read contexts."""
    return {
        "contract_id": CONTRACT_ID,
        "version": CONTRACT_VERSION,
        "owner_families": {
            key: {**dict(value), "pages": list(value["pages"])}
            for key, value in OWNER_FAMILIES.items()
        },
        "page_projections": {
            key: {
                **dict(value),
                "input_groups": list(value["input_groups"]),
                "owner_families": list(value["owner_families"]),
                "uncovered_groups": list(value["uncovered_groups"]),
                "consumer_fields": list(value["consumer_fields"]),
                "owner_field_paths": list(value["owner_field_paths"]),
            }
            for key, value in PAGE_PROJECTIONS.items()
        },
        "minimum_daily_publication": dict(MINIMUM_DAILY_PUBLICATION_CONTRACT),
        "page_pg_relations": {key: dict(value) for key, value in PAGE_PG_RELATIONS.items()},
    }


def required_module_keys():
    """No real PG Owner family is proven to be a global daily prerequisite."""
    return tuple(key for key, value in OWNER_FAMILIES.items() if value["daily_publication_required"])


def supported_owner_keys():
    return tuple(OWNER_FAMILIES)
