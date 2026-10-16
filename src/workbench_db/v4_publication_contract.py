"""Versioned effective contract for current V4 publication modules.

Requiredness is fixed by this code contract; callers cannot downgrade a module
by passing an arbitrary mapping. A bound result may still preserve UNKNOWN or
DEGRADED field quality. Historical source windows are allowed only when the
module's own versioned input contract declares them; the published Owner result
itself is always for the publication T0.
"""

from types import MappingProxyType


CONTRACT_ID = "V4_CURRENT_PUBLICATION_MODULE_CONTRACT_R2"
CONTRACT_VERSION = "2.0.0"

_ENDPOINTS = {
    "summary": "/api/v4/current/summary",
    "radar": "/api/v4/current/radar",
    "entity": "/api/v4/current/entity",
    "sector": "/api/v4/current/sector",
    "cohort": "/api/v4/current/cohort",
    "settlement": "/api/v4/current/settlement",
    "health": "/api/v4/current/health",
}

_INPUT_GROUPS = {
    "summary": ("events", "observations", "replay", "identity_names"),
    "radar": ("radar", "ledger", "replay", "identity_names"),
    "entity": ("RAW_DAILY", "IDENTITY_UNIVERSE", "states", "state_view", "events", "identity_names"),
    "sector": ("membership",),
    "cohort": ("radar", "cohort", "maturity", "identity_names"),
    "settlement": ("outcomes", "settlement_receipt", "maturity"),
    "health": ("replay", "maturity"),
}

_MODULES = {
    key: MappingProxyType({
        "requiredness": "REQUIRED",
        "endpoint": _ENDPOINTS[key],
        "input_groups": _INPUT_GROUPS[key],
        "owner_trade_date_policy": "PUBLICATION_T0",
        "source_window_policy": "MODULE_CONTRACT_DECLARED",
        "quality_policy": "PRESERVE_OWNER_QUALITY_NO_PROMOTION",
    })
    for key in _ENDPOINTS
}

MODULES = MappingProxyType(_MODULES)


def effective_module_contract():
    """Return a JSON-serializable, versioned copy for plans and read contexts."""
    return {
        "contract_id": CONTRACT_ID,
        "version": CONTRACT_VERSION,
        "modules": {
            key: {
                **dict(value),
                "input_groups": list(value["input_groups"]),
            }
            for key, value in MODULES.items()
        },
    }


def required_module_keys():
    return tuple(MODULES)
