"""Explain whether a source model's invalidation rule can be evaluated."""
from __future__ import annotations

from typing import Any, Mapping

from .contracts import digest
from .predicates import CONTRACT_ID as INVALIDATION_CONTRACT, Tri


CONTRACT_ID = "FOCUS_VALIDITY_CAPABILITY_V1"
NO_FORMAL_RULE = frozenset({"V3_SHORTLIST_STOCK", "V3_SHORTLIST_INDIVIDUAL",
                           "V3_SECTOR_TRACK"})


def _unknown_reasons(evidence: Any) -> set[str]:
    if not isinstance(evidence, Mapping):
        return set()
    reasons = set()
    if evidence.get("result") == Tri.UNKNOWN.value and isinstance(evidence.get("reason"), str):
        reasons.add(evidence["reason"])
    for child in evidence.get("children", ()):
        reasons.update(_unknown_reasons(child))
    if "child" in evidence:
        reasons.update(_unknown_reasons(evidence["child"]))
    return reasons


def validity_capability(*, source_family: str, invalidation: Tri,
                        invalidation_evidence: Mapping[str, Any] | None = None,
                        unavailable_reason: str | None = None) -> dict[str, Any]:
    """Return source rule capability separately from the three-valued result."""
    if not isinstance(invalidation, Tri):
        raise ValueError("validity capability requires three-valued invalidation")
    if source_family in NO_FORMAL_RULE:
        if invalidation != Tri.UNKNOWN or invalidation_evidence is not None:
            raise ValueError("V3 source has no executable invalidation rule")
        state, reasons, rule = "NOT_APPLICABLE", ["NO_FORMAL_SOURCE_RULE"], None
    elif source_family == "V3_3_TODAY_CANDIDATE":
        rule = INVALIDATION_CONTRACT
        if invalidation == Tri.UNKNOWN:
            state = "UNAVAILABLE"
            reasons = sorted(_unknown_reasons(invalidation_evidence))
            if unavailable_reason:
                reasons = sorted(set(reasons) | {unavailable_reason})
            if not reasons:
                reasons = ["PREDICATE_EVIDENCE_UNAVAILABLE"]
        else:
            if unavailable_reason:
                raise ValueError("known invalidation conflicts with unavailable reason")
            if (not isinstance(invalidation_evidence, Mapping) or
                    invalidation_evidence.get("contract_id") != INVALIDATION_CONTRACT or
                    invalidation_evidence.get("result") != invalidation.value or
                    not isinstance(invalidation_evidence.get("ast_digest"), str) or
                    len(invalidation_evidence["ast_digest"]) != 64):
                raise ValueError("applicable invalidation evidence incomplete")
            state, reasons = "APPLICABLE", []
    else:
        raise ValueError("unregistered validity capability source")
    identity = {"contract_id": CONTRACT_ID, "source_family": source_family,
                "status": state, "reason_codes": reasons,
                "rule_contract_id": rule,
                "invalidation_result": invalidation.value,
                "ast_digest": (invalidation_evidence or {}).get("ast_digest")}
    return {**identity, "digest": digest(identity)}
