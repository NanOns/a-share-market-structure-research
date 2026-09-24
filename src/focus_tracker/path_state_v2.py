"""FOCUS_PATH_STATE_V2: preserve confirmed facts under unresolved priority."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .predicates import Tri
from .states import PathDecision, classify_sector, classify_stock


CONTRACT_ID = "FOCUS_PATH_STATE_V2"
RESOLUTION_STATES = frozenset({"READY", "PARTIAL", "AMBIGUOUS", "UNAVAILABLE"})
STOCK_PRIORITY = (
    "STRUCTURE_DAMAGED", "TOO_EXTENDED", "PULLBACK_HEALTHY",
    "PULLBACK_UNCONFIRMED", "BREAKOUT_CONFIRMED", "TREND_ACCELERATING",
    "SECTOR_DIVERGENCE", "WEAKENING", "WAIT_CONFIRMATION", "EXITED_FOLLOW_UP",
)
SECTOR_PRIORITY = (
    "SECTOR_STRUCTURE_DAMAGED", "SECTOR_ACCELERATING",
    "SECTOR_HEALTHY_PULLBACK", "SECTOR_DIFFUSION_WEAKENING",
    "SECTOR_ROTATION", "SECTOR_EARLY_WAIT", "SECTOR_PERSISTENT",
    "SECTOR_EXITED_FOLLOW_UP",
)


@dataclass(frozen=True)
class PathDecisionV2:
    resolved_primary_state: str | None
    best_confirmed_state: str | None
    higher_priority_unresolved: tuple[str, ...]
    path_resolution: str
    confirmed_secondary_states: tuple[str, ...]
    predicate_evidence: dict[str, str]
    validity_state: str
    lifetime_path_tags: tuple[str, ...]
    secondary_tags: tuple[str, ...]


def resolve_evidence_v2(*, evidence: Mapping[str, str],
                        priority_groups: tuple[tuple[str, ...], ...]) -> tuple[
                            str | None, str | None, tuple[str, ...], str, tuple[str, ...]]:
    """Resolve evidence by priority tiers; equal-tier TRUEs remain ambiguous."""
    allowed = {"TRUE", "FALSE", "UNKNOWN", "NOT_APPLICABLE"}
    if any(value not in allowed for value in evidence.values()):
        if evidence in ({"actual_bar": "UNKNOWN"}, {"coverage": "UNKNOWN"}):
            return None, None, (), "UNAVAILABLE", ()
        else:
            raise ValueError("invalid path predicate evidence")
    if evidence in ({"actual_bar": "UNKNOWN"}, {"coverage": "UNKNOWN"}):
        return None, None, (), "UNAVAILABLE", ()

    ordered = tuple(name for group in priority_groups for name in group)
    if len(ordered) != len(set(ordered)):
        raise ValueError("duplicate predicate in path priority contract")
    predicate_names = set(evidence) - {"actual_bar", "coverage"}
    if predicate_names != set(ordered):
        raise ValueError("path evidence does not match priority contract")

    confirmed = tuple(name for name in ordered if evidence[name] == "TRUE")
    best: str | None = None
    unresolved: list[str] = []
    resolved: str | None = None
    resolution: str | None = None
    for group in priority_groups:
        true_in_group = tuple(name for name in group if evidence[name] == "TRUE")
        unknown_in_group = tuple(name for name in group if evidence[name] == "UNKNOWN")
        if true_in_group:
            best = true_in_group[0] if len(true_in_group) == 1 else None
            if unresolved:
                resolution = "PARTIAL"
            elif len(true_in_group) > 1:
                resolution = "AMBIGUOUS"
            else:
                resolution = "READY"
                resolved = true_in_group[0]
            break
        unresolved.extend(unknown_in_group)

    if resolution is None:
        if unresolved:
            resolution = "UNAVAILABLE"
        else:
            resolution = "READY"
    if resolution not in RESOLUTION_STATES:
        raise ValueError("invalid path resolution")
    return resolved, best, tuple(unresolved), resolution, confirmed


def resolve_v2(decision: PathDecision) -> PathDecisionV2:
    """Resolve ordered V1 predicate evidence without changing accepted V1 rows."""
    evidence_names = set(decision.evidence)
    if evidence_names in ({"actual_bar"}, {"coverage"}):
        groups: tuple[tuple[str, ...], ...] = ()
    else:
        sector = bool(evidence_names & set(SECTOR_PRIORITY))
        priority = SECTOR_PRIORITY if sector else STOCK_PRIORITY
        extras = evidence_names - set(priority) - {"actual_bar", "coverage"}
        if extras:
            raise ValueError("path evidence has unregistered predicates")
        groups = tuple((name,) for name in priority if name in evidence_names)
    resolved, best, unresolved, resolution, confirmed = resolve_evidence_v2(
        evidence=decision.evidence, priority_groups=groups)
    return PathDecisionV2(resolved, best, unresolved, resolution,
                          confirmed, dict(decision.evidence),
                          decision.validity_state, decision.lifetime_path_tags,
                          decision.secondary_tags)


def classify_stock_v2(facts: Mapping[str, Any], *, invalidation: Tri,
                      applicable: frozenset[str],
                      prior_lifetime_tags: frozenset[str] = frozenset()) -> PathDecisionV2:
    return resolve_v2(classify_stock(facts, invalidation=invalidation,
                                     applicable=applicable,
                                     prior_lifetime_tags=prior_lifetime_tags))


def classify_sector_v2(facts: Mapping[str, Any], *, invalidation: Tri,
                       applicable: frozenset[str]) -> PathDecisionV2:
    return resolve_v2(classify_sector(facts, invalidation=invalidation,
                                      applicable=applicable))
