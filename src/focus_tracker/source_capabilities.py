"""Versioned source-contract path applicability; no runtime field inference."""
from __future__ import annotations

from .contracts import SOURCE_AUTHORITY_CONTRACT, digest


CONTRACT_ID = "FOCUS_SOURCE_PATH_CAPABILITIES_V3"

STOCK_PREDICATES = (
    "STRUCTURE_DAMAGED", "TOO_EXTENDED", "PULLBACK_HEALTHY",
    "PULLBACK_UNCONFIRMED", "BREAKOUT_CONFIRMED", "TREND_ACCELERATING",
    "SECTOR_DIVERGENCE", "WEAKENING", "WAIT_CONFIRMATION",
    "EXITED_FOLLOW_UP",
)
SECTOR_PREDICATES = (
    "SECTOR_STRUCTURE_DAMAGED", "SECTOR_ACCELERATING",
    "SECTOR_HEALTHY_PULLBACK", "SECTOR_DIFFUSION_WEAKENING",
    "SECTOR_ROTATION", "SECTOR_EARLY_WAIT", "SECTOR_PERSISTENT",
    "SECTOR_EXITED_FOLLOW_UP",
)


_MAPPING = {
    ("V3_SHORTLIST_STOCK", "RESEARCH_V3_PREVIEW_6_CURRENT_FOCUS_COMPLETE"):
        frozenset({"EXITED_FOLLOW_UP"}),
    ("V3_SHORTLIST_INDIVIDUAL", "RESEARCH_V3_PREVIEW_6_CURRENT_FOCUS_COMPLETE"):
        frozenset({"EXITED_FOLLOW_UP"}),
    ("V3_3_TODAY_CANDIDATE", "TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_03_FULL_LOO"):
        frozenset({"STRUCTURE_DAMAGED", "PULLBACK_HEALTHY",
                   "EXITED_FOLLOW_UP"}),
    ("V3_SECTOR_TRACK", "RESEARCH_V3_PREVIEW_6_CURRENT_FOCUS_COMPLETE"):
        frozenset({"SECTOR_PERSISTENT",
                   "SECTOR_EXITED_FOLLOW_UP"}),
}

# Required operands match the executable expressions in states.py. Values may
# be None for a market/source gap; a missing provider key is a contract error.
PATH_REQUIRED_FACTS = {
    "STRUCTURE_DAMAGED": frozenset({"invalidation"}),
    "TOO_EXTENDED": frozenset({"source_extended"}),
    "PULLBACK_HEALTHY": frozenset({"drawdown_current", "close", "ma20",
                                   "structure_break", "invalidation"}),
    "PULLBACK_UNCONFIRMED": frozenset({"drawdown_current", "close", "ma20",
                                       "confirmation", "invalidation"}),
    "BREAKOUT_CONFIRMED": frozenset({"launch_confirm"}),
    "TREND_ACCELERATING": frozenset({"trend_continue", "r5", "rps20_delta3",
                                      "primary_sector_current"}),
    "SECTOR_DIVERGENCE": frozenset({"primary_sector_current",
                                      "relative_to_entry_sector"}),
    "WEAKENING": frozenset({"close", "ma20", "rps20_last_3", "invalidation"}),
    "WAIT_CONFIRMATION": frozenset({"early_or_setup", "waiting_evaluable"}),
    "EXITED_FOLLOW_UP": frozenset({"exited"}),
    "SECTOR_STRUCTURE_DAMAGED": frozenset({"invalidation"}),
    "SECTOR_ACCELERATING": frozenset({"source_membership", "sret1", "srel",
                                       "swidth", "prior_swidth", "retention"}),
    "SECTOR_HEALTHY_PULLBACK": frozenset({"source_membership", "sdd", "srel",
                                           "invalidation"}),
    "SECTOR_DIFFUSION_WEAKENING": frozenset({"signal_swidth", "swidth",
                                              "retention", "invalidation"}),
    "SECTOR_ROTATION": frozenset({"role_rotation_confirmed"}),
    "SECTOR_EARLY_WAIT": frozenset({"source_membership", "waiting_evaluable"}),
    "SECTOR_PERSISTENT": frozenset({"source_membership"}),
    "SECTOR_EXITED_FOLLOW_UP": frozenset({"exited"}),
}

_STOCK_PROVIDERS = frozenset({"has_actual_bar", "close", "drawdown_current",
                              "mfe", "ma20", "r5", "invalidation", "exited",
                              "session_state"})
PROVIDER_SETS = {
    "V3_SHORTLIST_STOCK": _STOCK_PROVIDERS,
    "V3_SHORTLIST_INDIVIDUAL": _STOCK_PROVIDERS,
    "V3_3_TODAY_CANDIDATE": _STOCK_PROVIDERS | {"structure_break"},
    "V3_SECTOR_TRACK": frozenset({"source_membership", "coverage_ready",
                                   "sret1", "swidth", "invalidation", "exited"}),
}


def _required(source_family: str, path: str) -> frozenset[str]:
    gate = ({"coverage_ready", "source_membership"}
            if source_family == "V3_SECTOR_TRACK" else {"has_actual_bar"})
    return PATH_REQUIRED_FACTS[path] | gate


def applicable_path_predicates(source_family: str,
                               source_contract_id: str) -> frozenset[str]:
    try:
        applicable = _MAPPING[(source_family, source_contract_id)]
    except KeyError as exc:
        raise ValueError("unregistered Focus source/path contract") from exc
    allowed = set(SECTOR_PREDICATES if source_family == "V3_SECTOR_TRACK"
                  else STOCK_PREDICATES)
    if set(applicable) - allowed:
        raise ValueError("CAPABILITY_CONTRACT_BROKEN:UNKNOWN_PATH")
    providers = PROVIDER_SETS[source_family]
    for path in applicable:
        if _required(source_family, path) - providers:
            raise ValueError("CAPABILITY_CONTRACT_BROKEN:" + path)
    return applicable


def require_runtime_fact_providers(source_family: str, source_contract_id: str,
                                   facts: dict[str, object], *,
                                   invalidation_supplied: bool) -> None:
    """Preflight the executable row, distinguishing absent providers from nulls."""
    provided = set(facts)
    if invalidation_supplied:
        provided.add("invalidation")
    for path in applicable_path_predicates(source_family, source_contract_id):
        missing = _required(source_family, path) - provided
        if missing:
            raise ValueError("CAPABILITY_CONTRACT_BROKEN:" + path + ":" +
                             ",".join(sorted(missing)))


def capability_evidence(source_family: str, source_contract_id: str) -> dict[str, object]:
    applicable = applicable_path_predicates(source_family, source_contract_id)
    all_predicates = (SECTOR_PREDICATES if source_family == "V3_SECTOR_TRACK"
                      else STOCK_PREDICATES)
    states = {name: "APPLICABLE" if name in applicable else "NOT_APPLICABLE"
              for name in all_predicates}
    requirements = {name: sorted(_required(source_family, name))
                    for name in sorted(applicable)}
    providers = sorted(PROVIDER_SETS[source_family])
    return {"contract_id": CONTRACT_ID,
            "source_authority_contract_id": SOURCE_AUTHORITY_CONTRACT,
            "source_family": source_family,
            "source_contract_id": source_contract_id,
            "predicates": states,
            "required_facts": requirements,
            "registered_providers": providers,
            "digest": digest({"contract": CONTRACT_ID,
                              "source_family": source_family,
                              "source_contract_id": source_contract_id,
                              "predicates": states,
                              "required_facts": requirements,
                              "registered_providers": providers})}
