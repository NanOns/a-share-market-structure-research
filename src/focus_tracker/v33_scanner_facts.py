"""Exact-contract V3.3 scanner facts for Focus; no signal reimplementation."""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from .contracts import digest


CONTRACT_ID = "FOCUS_V33_SCANNER_FACT_BRIDGE_V1"
SOURCE_SCANNER_CONTRACT = "TODAY_RESEARCH_SCANNER_V3_3_CANDIDATE_01"
BRANCHES = ("launch", "pullback", "setup_watch", "recovery_turn",
            "trend_continue", "trend_continue_stock_only")


def bridge_scanner_facts(*, evidence: Mapping[str, Any],
                         security_id: str, trade_date: date) -> dict[str, Any]:
    """Use only a locked scanner check with complete, coherent identity.

    An absent check stays unknown. Contradictory copies across scanner branches
    are a source integrity error, rather than a majority vote.
    """
    if (evidence.get("contract_id") != SOURCE_SCANNER_CONTRACT or
            evidence.get("security_id") != security_id or
            evidence.get("trade_date") != trade_date.isoformat()):
        raise ValueError("V3.3 scanner identity mismatch")
    known: set[bool] = set()
    checked: list[str] = []
    for name in BRANCHES:
        branch = evidence.get(name)
        if not isinstance(branch, dict):
            continue
        checks = branch.get("checks")
        if not isinstance(checks, dict) or "NOT_STRUCTURE_BREAK" not in checks:
            continue
        value = checks["NOT_STRUCTURE_BREAK"]
        if value is not None and not isinstance(value, bool):
            raise ValueError("nonboolean scanner structure check")
        if value is not None:
            known.add(value)
        checked.append(name)
    if len(known) > 1:
        raise ValueError("conflicting V3.3 structure checks")
    structure_break = (not next(iter(known))) if known else None
    return {"contract_id": CONTRACT_ID,
            "source_scanner_contract_id": SOURCE_SCANNER_CONTRACT,
            "source_evidence_digest": digest(dict(evidence)),
            "checked_branches": checked,
            "structure_break_v3": structure_break,
            "quality": "READY" if known else "UNKNOWN"}
