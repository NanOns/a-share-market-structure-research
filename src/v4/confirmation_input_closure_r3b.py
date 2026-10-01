"""R3B provenance admission and scenario-scoped capability closure.

This module never infers an episode from today's reducer, and never substitutes
a composite safety flag for the four exact legacy inputs. Admission validates
evidence; it does not confer external acceptance or enable a formal consumer.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Mapping

from .state_identity import digest

CONTRACT_ID = "V4_11_EPISODE_SAFETY_LOO_INPUT_CLOSURE_R3B_V1"
EPISODE_PRODUCER = "PULLBACK_EPISODE_V1_CANDIDATE_01"
EPISODE_PARAMETERS = "V4_11_EXACT_LEGACY_EPISODE_PARAMETERS_R3B_V1"
FORBIDDEN_ROLES = frozenset({"V4_11_D0", "V4_10_D2", "FINAL_STATE", "FOCUS",
                             "SAME_DAY_DOWNSTREAM", "FUTURE_OUTCOME"})
SAFETY_BINDINGS = {
    "NOT_STRUCTURE_BREAK": {"field": "structure_break_v3", "producer": "STOCK_ATTENTION_PREVIEW_1",
        "function": "classify_stock_attention", "formula": "tri_and(close/ma20 < k, close_prior1/ma20_prior1 < k)",
        "parameters": ["stock_signals.STRUCTURE_BREAK.close_to_ma20_lt", "stock_signals.STRUCTURE_BREAK.consecutive_valid_sessions"]},
    "NOT_EXTENDED": {"field": "extended_v3", "producer": "STOCK_ATTENTION_PREVIEW_1",
        "function": "classify_stock_attention", "formula": "tri_and(bias20 >= bias20_gte, extension_z20 >= extension_z20_gte)",
        "parameters": ["stock_signals.risk.bias20_gte", "stock_signals.risk.extension_z20_gte"]},
    "NOT_FIRST_DAY_DAMAGE": {"field": "first_day_damage", "producer": "TODAY_RESEARCH_FACTOR_V3_3_CANDIDATE_01",
        "function": "calculate_today_facts", "formula": "close/ma20 < 0.97", "parameters": {"close_to_ma20_lt": .97}},
    "NOT_SEVERE_DROP": {"field": "severe_drop", "producer": "TODAY_RESEARCH_FACTOR_V3_3_CANDIDATE_01",
        "function": "calculate_today_facts", "formula": "tri_or(ret1_adj <= -0.08, logret1 <= -max(-log(1-0.04), 2*sigma20_prior))",
        "parameters": {"drop_floor_pct": .04, "drop_cap_pct": .08, "drop_z": 2.0}},
}
DIAGNOSTIC_FIELDS = {
    "pullback_episode_confirmed": "EXACT_ACCEPTED_FROZEN_PRIOR_SESSION_EPISODE_UNAVAILABLE",
    "current_with_loo_breadth_support": "SAME_DAY_LOO_FROZEN_ROLE_NOT_ADMITTED_FOR_FORMAL_D0",
}


class InputClosureError(ValueError):
    pass


def timestamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError, AttributeError) as exc:
        raise InputClosureError("AWARE_TIMESTAMP_REQUIRED") from exc
    if result.tzinfo is None:
        raise InputClosureError("AWARE_TIMESTAMP_REQUIRED")
    return result


def episode_identity(episode: Mapping[str, Any]) -> str:
    """Identity includes the upstream episode origin, never today's revision."""
    keys = ("security_id", "episode_start", "producer_contract_id", "parameter_set_id", "origin_publication_id")
    if any(not episode.get(k) for k in keys):
        raise InputClosureError("EPISODE_ORIGIN_IDENTITY_REQUIRED")
    return "V4_11_EPISODE:" + digest({key: episode[key] for key in keys})


def validate_episode(episode: Mapping[str, Any], *, target_date: str, cutoff: str,
                     source_publications: Mapping[str, Mapping[str, Any]],
                     prior_session_date: str) -> None:
    """Validate immutable prior-session state and exact episode producer lineage.

    `source_publications` must be a caller's sealed byte-verified producer set;
    a supplied publication id alone is insufficient. This check does not make
    the candidate legacy episode an externally accepted upstream producer.
    """
    target = date.fromisoformat(target_date)
    knowledge = timestamp(cutoff)
    if knowledge > datetime.now(timezone.utc):
        raise InputClosureError("FUTURE_KNOWLEDGE_CUTOFF")
    if episode.get("producer_contract_id") != EPISODE_PRODUCER:
        raise InputClosureError("WRONG_EPISODE_PRODUCER")
    if episode.get("parameter_set_id") != EPISODE_PARAMETERS:
        raise InputClosureError("WRONG_EPISODE_PARAMETER_SET")
    if episode.get("episode_id") != episode_identity(episode):
        raise InputClosureError("FAKE_EPISODE_ID")
    start = date.fromisoformat(episode["episode_start"])
    prior_date = date.fromisoformat(episode["prior_session_trade_date"])
    if start > prior_date or prior_date >= target:
        raise InputClosureError("FUTURE_OR_SAME_DAY_EPISODE")
    if prior_date != date.fromisoformat(prior_session_date):
        raise InputClosureError("EPISODE_MUST_BIND_IMMEDIATE_PRIOR_MASTER_SESSION")
    if episode.get("prior_session_status") not in ("IDLE", "ADVANCING", "PULLING_BACK", "CONFIRMED",
            "INVALIDATED", "RESET_NEW_HIGH", "EXPIRED", "DATA_GAP", "LEFT_CENSORED"):
        raise InputClosureError("EXACT_PRIOR_SESSION_STATUS_REQUIRED")
    if timestamp(episode["system_available_at"]) > knowledge:
        raise InputClosureError("FUTURE_EPISODE")
    ids = episode.get("source_publication_ids", [])
    if not ids or len(set(ids)) != len(ids) or episode["origin_publication_id"] not in ids:
        raise InputClosureError("EPISODE_SOURCE_PUBLICATIONS_REQUIRED")
    prior_id = episode.get("prior_session_publication_id")
    if prior_id not in ids or prior_id not in source_publications:
        raise InputClosureError("PRIOR_SESSION_EPISODE_PUBLICATION_REQUIRED")
    for source_id in ids:
        source = source_publications.get(source_id)
        if not source or source.get("publication_id") != source_id:
            raise InputClosureError("UNBOUND_EPISODE_SOURCE_PUBLICATION")
        if source.get("time_role") in FORBIDDEN_ROLES:
            raise InputClosureError("EPISODE_DOWNSTREAM_FEEDBACK_REJECTED")
        if date.fromisoformat(source["trade_date"]) >= target:
            raise InputClosureError("SAME_DAY_REVISION_CANNOT_BECOME_PRIOR_EPISODE")
        if timestamp(source["system_available_at"]) > knowledge:
            raise InputClosureError("FUTURE_EPISODE_SOURCE")
    prior = source_publications[prior_id]
    if prior["trade_date"] != episode["prior_session_trade_date"]:
        raise InputClosureError("PRIOR_EPISODE_DATE_MISMATCH")
    if prior.get("producer_contract_id") != EPISODE_PRODUCER:
        raise InputClosureError("WRONG_PRIOR_EPISODE_PRODUCER")
    if prior.get("parameter_set_id") != EPISODE_PARAMETERS:
        raise InputClosureError("WRONG_PRIOR_EPISODE_PARAMETER_SET")
    matching = [row for row in prior.get("rows", []) if row.get("security_id") == episode["security_id"]
                and row.get("episode_id") == episode["episode_id"]]
    if len(matching) != 1 or matching[0].get("state") != episode["prior_session_status"]:
        raise InputClosureError("FAKE_EPISODE_OR_PRIOR_STATE")
    if episode.get("knowledge_cutoff") != cutoff:
        raise InputClosureError("EPISODE_KNOWLEDGE_CUTOFF_MISMATCH")
    payload = {key: value for key, value in episode.items() if key != "publication_id"}
    if episode.get("publication_id") != "V4_11_EPISODE_PUBLICATION:" + digest(payload):
        raise InputClosureError("EPISODE_PUBLICATION_DIGEST_MISMATCH")


def validate_dependency_graph(graph: Mapping[str, Any], *, target_date: str, cutoff: str) -> dict[str, Any]:
    """Verify all nodes, including disconnected nodes, before any LOO admission."""
    target = date.fromisoformat(target_date)
    knowledge = timestamp(cutoff)
    if knowledge > datetime.now(timezone.utc):
        raise InputClosureError("FUTURE_KNOWLEDGE_CUTOFF")
    nodes = graph.get("nodes", [])
    by_id = {node["node_id"]: node for node in nodes}
    if not nodes or len(by_id) != len(nodes) or graph.get("root") not in by_id:
        raise InputClosureError("LOO_GRAPH_IDENTITY_INVALID")
    visiting, visited = set(), set()

    def visit(node_id):
        if node_id in visiting:
            raise InputClosureError("LOO_CIRCULAR_DEPENDENCY_DETECTED")
        if node_id in visited:
            return
        node = by_id.get(node_id)
        if node is None:
            raise InputClosureError("LOO_DEPENDENCY_NODE_MISSING")
        visiting.add(node_id)
        for dependency in node.get("dependencies", []):
            visit(dependency)
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in by_id:
        visit(node_id)
    for node in nodes:
        if node.get("time_role") in FORBIDDEN_ROLES or node.get("stage") in ("V4-11 D0", "V4-10 D2", "Focus"):
            raise InputClosureError("LOO_SAME_DAY_FEEDBACK_REJECTED")
        if node.get("pure_upstream") is not True:
            raise InputClosureError("LOO_PURE_UPSTREAM_PROOF_REQUIRED")
        if date.fromisoformat(node["trade_date"]) > target or timestamp(node["system_available_at"]) > knowledge:
            raise InputClosureError("LOO_FUTURE_INPUT_REJECTED")
        if not node.get("producer_contract_id") or not node.get("parameter_set_id") or not node.get("publication_id"):
            raise InputClosureError("LOO_VERSIONED_PUBLICATION_REQUIRED")
    return {"acyclic": True, "pure_upstream": True, "target_day_cutoff_known": True,
            "consumes_V4_11_D0": False, "consumes_V4_10_D2_current": False, "consumes_Focus": False,
            "same_day_feedback": False, "graph_digest": digest(dict(graph)), "node_count": len(nodes),
            "formal_candidate_admission": False,
            "reason": "GRAPH_PROOF_ALONE_DOES_NOT_CHANGE_FROZEN_DIAGNOSTIC_TIME_ROLE"}


def scenario_capability_matrix(*, r3a_sealed: bool = False) -> dict[str, dict[str, Any]]:
    basic = "FORMAL_CANDIDATE" if r3a_sealed else "BLOCKED_UPSTREAM"
    return {
        "LAUNCH_CONFIRM": {"capability": basic, "reason": "R3A_SEALED_TARGET_FACT_SET" if r3a_sealed else "WAIT_R3A_SEAL"},
        "RECOVERY_TURN": {"capability": basic, "reason": "R3A_SEALED_TARGET_FACT_SET" if r3a_sealed else "WAIT_R3A_SEAL"},
        "STRONG_PULLBACK": {"capability": "DIAGNOSTIC_ONLY", "reason": DIAGNOSTIC_FIELDS["pullback_episode_confirmed"]},
        "TREND_CONTINUE": {"capability": "DIAGNOSTIC_ONLY", "reason": DIAGNOSTIC_FIELDS["current_with_loo_breadth_support"]},
    }


def require_formal_scenario(scenario: str, matrix: Mapping[str, Mapping[str, Any]]) -> None:
    if scenario not in matrix or matrix[scenario].get("capability") != "FORMAL_CANDIDATE":
        raise InputClosureError("DIAGNOSTIC_OR_BLOCKED_SCENARIO_CANNOT_ENTER_FORMAL_D0")


def safety_predicates(facts: Mapping[str, Any]) -> dict[str, bool | None]:
    """Retain exact predicate identity and NULL; no COMMON_SAFETY fallback."""
    predicates = {}
    for predicate, binding in SAFETY_BINDINGS.items():
        fact = facts.get(binding["field"])
        value = fact.get("value") if isinstance(fact, Mapping) and fact.get("quality") == "KNOWN" else None
        predicates[predicate] = not value if type(value) is bool else None
    return predicates


def diagnostic_fact(field: str, *, trade_date: str, cutoff: str, source_publication_id: str) -> dict[str, Any]:
    if field not in DIAGNOSTIC_FIELDS:
        raise InputClosureError("DIAGNOSTIC_FIELD_NOT_REGISTERED")
    return {"value": None, "quality": "UNKNOWN", "acceptance": "DIAGNOSTIC_ONLY",
            "reason": DIAGNOSTIC_FIELDS[field], "unit": "boolean", "trade_date": trade_date,
            "time_role": "TARGET_SESSION_D0" if field == "pullback_episode_confirmed" else "SAME_DAY_DOWNSTREAM",
            "system_available_at": cutoff, "source_publication_id": source_publication_id,
            "producer_contract_id": CONTRACT_ID}
