"""Versioned source-contract path applicability; no runtime field inference."""
from __future__ import annotations

from .contracts import SOURCE_AUTHORITY_CONTRACT, digest


CONTRACT_ID = "FOCUS_SOURCE_PATH_CAPABILITIES_V1"

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
        frozenset({"PULLBACK_HEALTHY", "PULLBACK_UNCONFIRMED",
                   "SECTOR_DIVERGENCE", "WEAKENING", "WAIT_CONFIRMATION",
                   "EXITED_FOLLOW_UP"}),
    ("V3_SHORTLIST_INDIVIDUAL", "RESEARCH_V3_PREVIEW_6_CURRENT_FOCUS_COMPLETE"):
        frozenset({"PULLBACK_HEALTHY", "PULLBACK_UNCONFIRMED",
                   "WEAKENING", "WAIT_CONFIRMATION", "EXITED_FOLLOW_UP"}),
    ("V3_3_TODAY_CANDIDATE", "TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_03_FULL_LOO"):
        frozenset({"STRUCTURE_DAMAGED", "PULLBACK_HEALTHY",
                   "PULLBACK_UNCONFIRMED", "BREAKOUT_CONFIRMED",
                   "TREND_ACCELERATING", "SECTOR_DIVERGENCE", "WEAKENING",
                   "WAIT_CONFIRMATION", "EXITED_FOLLOW_UP"}),
    ("V3_SECTOR_TRACK", "RESEARCH_V3_PREVIEW_6_CURRENT_FOCUS_COMPLETE"):
        frozenset({"SECTOR_ACCELERATING", "SECTOR_HEALTHY_PULLBACK",
                   "SECTOR_DIFFUSION_WEAKENING", "SECTOR_ROTATION",
                   "SECTOR_EARLY_WAIT", "SECTOR_PERSISTENT",
                   "SECTOR_EXITED_FOLLOW_UP"}),
}


def applicable_path_predicates(source_family: str,
                               source_contract_id: str) -> frozenset[str]:
    try:
        return _MAPPING[(source_family, source_contract_id)]
    except KeyError as exc:
        raise ValueError("unregistered Focus source/path contract") from exc


def capability_evidence(source_family: str, source_contract_id: str) -> dict[str, object]:
    applicable = applicable_path_predicates(source_family, source_contract_id)
    all_predicates = (SECTOR_PREDICATES if source_family == "V3_SECTOR_TRACK"
                      else STOCK_PREDICATES)
    states = {name: "APPLICABLE" if name in applicable else "NOT_APPLICABLE"
              for name in all_predicates}
    return {"contract_id": CONTRACT_ID,
            "source_authority_contract_id": SOURCE_AUTHORITY_CONTRACT,
            "source_family": source_family,
            "source_contract_id": source_contract_id,
            "predicates": states,
            "digest": digest({"contract": CONTRACT_ID,
                              "source_family": source_family,
                              "source_contract_id": source_contract_id,
                              "predicates": states})}
