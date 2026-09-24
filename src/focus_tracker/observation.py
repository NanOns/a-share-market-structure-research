"""FOCUS-03 six-dimensional observation assembly from frozen, explicit facts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import digest
from .lifecycle import Decision
from .materialize import StockFact
from .predicates import Tri
from .source_capabilities import applicable_path_predicates, capability_evidence
from .session_gap_semantics import CONTRACT_ID as SESSION_GAP_CONTRACT
from .path_state_v2 import CONTRACT_ID as PATH_CONTRACT_V2, resolve_v2
from .states import CONTRACT_ID as PATH_CONTRACT, classify_sector, classify_stock
from .validity_capability import validity_capability


CONTRACT_ID = "FOCUS_OBSERVATION_ASSEMBLY_V2"


@dataclass(frozen=True)
class Observation:
    episode_id: str
    source_membership_state: str
    membership_phase: str
    validity_state: str
    followup_state: str
    current_path_state: str
    lifetime_path_tags: tuple[str, ...]
    secondary_tags: tuple[str, ...]
    quality_status: str
    fact_digest: str
    evidence: dict[str, Any]


def _followup(decision: Decision, *, pending_settlement: bool,
              settlement_complete: bool) -> str:
    if pending_settlement and settlement_complete:
        raise ValueError("conflicting settlement status")
    if decision.membership not in {"NONE", "UNKNOWN"}:
        if settlement_complete:
            raise ValueError("active source membership cannot complete follow-up")
        return "ACTIVE_FOCUS"
    if decision.membership == "UNKNOWN":
        return "SOURCE_UNAVAILABLE"
    if settlement_complete:
        return "FOLLOW_UP_COMPLETED"
    return "PENDING_SETTLEMENT" if pending_settlement else "POST_EXIT"


def assemble_observation(*, decision: Decision, source_contract_id: str,
                         stock_fact: StockFact | None,
                         predicate_facts: Mapping[str, Any],
                         invalidation: Tri,
                         pending_settlement: bool = False,
                         settlement_complete: bool = False,
                         prior_lifetime_tags: frozenset[str] = frozenset()) -> Observation:
    """Assemble without interpreting source text or inventing absent factors.

    `predicate_facts` must be computed by versioned, auditable fact contracts.
    This layer only joins them to the shared price fact and applies the frozen
    path priorities. Sector callers supply coverage/width facts explicitly.
    """
    if decision.episode_id is None:
        raise ValueError("observation requires an episode")
    if not isinstance(invalidation, Tri):
        raise ValueError("three-valued invalidation required")
    applicable = applicable_path_predicates(decision.key.source_family,
                                            source_contract_id)
    if decision.key.entity_type == "STOCK":
        if stock_fact is None or stock_fact.security_id != decision.key.entity_id:
            raise ValueError("stock fact identity mismatch")
        facts = {"has_actual_bar": stock_fact.quality_status == "READY",
                 "close": stock_fact.close_price,
                 "drawdown_current": stock_fact.drawdown_current,
                 "mfe": stock_fact.mfe, **predicate_facts}
        # The verified price materializer alone owns BAR and path values.
        facts.update(has_actual_bar=stock_fact.quality_status == "READY",
                     close=stock_fact.close_price,
                     drawdown_current=stock_fact.drawdown_current,
                     mfe=stock_fact.mfe)
        path = classify_stock(facts, invalidation=invalidation,
                              applicable=applicable,
                              prior_lifetime_tags=prior_lifetime_tags)
        price_identity = stock_fact.input_digest
    else:
        if stock_fact is not None:
            raise ValueError("sector observation cannot use a stock fact")
        facts = dict(predicate_facts)
        facts["source_membership"] = decision.membership
        path = classify_sector(facts, invalidation=invalidation,
                               applicable=applicable)
        price_identity = None
    path_v2 = resolve_v2(path)
    followup = _followup(decision, pending_settlement=pending_settlement,
                         settlement_complete=settlement_complete)
    capability = validity_capability(
        source_family=decision.key.source_family, invalidation=invalidation,
        invalidation_evidence=predicate_facts.get("invalidation_evidence"),
        unavailable_reason=predicate_facts.get("invalidation_unavailable_reason"))
    if ((capability["status"] == "APPLICABLE") !=
            (path.validity_state in {"VALID", "INVALIDATED"})):
        raise ValueError("validity capability/result contradiction")
    evidence = {"contract_id": CONTRACT_ID, "path_contract_id": PATH_CONTRACT,
                "path_state_v2": {
                    "contract_id": PATH_CONTRACT_V2,
                    "resolved_primary_state": path_v2.resolved_primary_state,
                    "best_confirmed_state": path_v2.best_confirmed_state,
                    "higher_priority_unresolved": list(path_v2.higher_priority_unresolved),
                    "path_resolution": path_v2.path_resolution,
                    "confirmed_secondary_states": list(path_v2.confirmed_secondary_states),
                    "predicate_evidence": path_v2.predicate_evidence,
                },
                "source_capability": capability_evidence(decision.key.source_family,
                                                          source_contract_id),
                "key": {"family": decision.key.source_family,
                        "entity_type": decision.key.entity_type,
                        "entity_id": decision.key.entity_id},
                "decision_reason": decision.reason,
                "price_input_digest": price_identity,
                "price_path_gaps": ({"session_gap_contract_id": SESSION_GAP_CONTRACT,
                                     "gap_count": stock_fact.gap_count,
                                     "suspended_sessions": stock_fact.suspended_sessions,
                                     "unverified_gap_count": stock_fact.unverified_gap_count,
                                     "suspended_dates": [day.isoformat()
                                                         for day in stock_fact.suspended_dates],
                                     "unverified_gap_dates": [day.isoformat()
                                                              for day in stock_fact.unverified_gap_dates]}
                                    if stock_fact is not None else None),
                "predicate_facts": facts,
                "invalidation": invalidation.value,
                "validity_capability": capability,
                "path_predicates": path.evidence,
                "secondary_tags": path.secondary_tags,
                "settlement": {"pending": pending_settlement,
                               "complete": settlement_complete}}
    quality = "READY" if path.current_path_state not in {
        "DATA_UNAVAILABLE"} else "DATA_UNAVAILABLE"
    return Observation(decision.episode_id, decision.membership, decision.phase,
                       path.validity_state, followup, path.current_path_state,
                       path.lifetime_path_tags, path.secondary_tags, quality,
                       digest(evidence), evidence)
