"""Optional post-selection turnover enrichment for P12-14.

This module intentionally contains no network client.  It validates already
normalized source rows against a frozen local daily fingerprint so online data
cannot silently acquire a historical date or alter V3.3 selection/ranking.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Mapping

from workbench_analysis.turnover_context_v3_3 import build_turnover_context


CONTRACT_ID = "P12_14_EASTMONEY_CANDIDATE_TURNOVER_V1"
SUPPORTED_MARKETS = {"SH", "SZ"}


@dataclass(frozen=True)
class LocalDailyFingerprint:
    security_id: str
    trade_date: str
    raw_close: float
    raw_amount: float
    raw_volume: float


def select_enrichment_ids(candidate_ids: Iterable[str]) -> list[str]:
    """Keep every supported row from the already-filtered V3.3 candidate set."""
    selected: list[str] = []
    seen: set[str] = set()
    for value in candidate_ids:
        security_id = str(value or "")
        if security_id in seen:
            continue
        seen.add(security_id)
        market = security_id.split(".", 1)[0] if "." in security_id else ""
        if market not in SUPPORTED_MARKETS:
            continue
        selected.append(security_id)
    return selected


def apply_turnover_enhancement(candidates: Iterable[Mapping[str, object]], evidence: Iterable[Mapping[str, object]]) -> list[dict]:
    """Compatibility entrypoint backed by the versioned context algorithm."""
    result = build_turnover_context(candidates, evidence)
    for row in result["items"]:
        row["turnover_enhancement_status"] = row["semantic_status"]
        row["turnover_usage"] = "CONTEXT_AND_OPTIONAL_LOCKED_SLOT_ORDER"
    return result["items"]


def _close(left: float, right: float, *, rel: float, abs_: float) -> bool:
    return abs(left - right) <= max(abs_, rel * max(abs(left), abs(right)))


def bind_turnover_row(
    source_row: Mapping[str, object] | None,
    local: LocalDailyFingerprint,
) -> dict:
    """Bind a latest-only source row to a local session or fail closed.

    Price, amount, and volume form the date fingerprint because the source batch
    response has no trustworthy quote date.  Turnover never participates in the
    V3.3 candidate decision in this contract.
    """
    base = {
        "contract_id": CONTRACT_ID,
        "security_id": local.security_id,
        "trade_date": local.trade_date,
        "turnover_rate": None,
        "turnover_basis": "UNKNOWN",
        "basis_verification": "UNKNOWN",
        "session_binding_status": "UNVERIFIED",
        "use_scope": "POST_SELECTION_EVIDENCE_AND_QUALIFIED_UNRANKED_SECONDARY_ORDER",
    }
    if local.security_id.split(".", 1)[0] not in SUPPORTED_MARKETS:
        return {**base, "capability_status": "UNSUPPORTED_MARKET", "reason": "MARKET_NOT_SUPPORTED"}
    if not source_row:
        return {**base, "capability_status": "SOURCE_FAILED", "reason": "SOURCE_ROW_MISSING"}
    if str(source_row.get("security_id") or "") != local.security_id:
        return {**base, "capability_status": "UNAVAILABLE", "reason": "SECURITY_ID_MISMATCH"}
    try:
        price = float(source_row["price"])
        amount = float(source_row["amount"])
        volume = float(source_row["volume"])
        turnover = float(source_row["turnover_rate"])
    except (KeyError, TypeError, ValueError):
        return {**base, "capability_status": "UNAVAILABLE", "reason": "REQUIRED_FIELD_INVALID"}
    if not all(isfinite(v) for v in (price, amount, volume, turnover)) or not (0 <= turnover <= 1):
        return {**base, "capability_status": "UNAVAILABLE", "reason": "VALUE_OUT_OF_RANGE"}
    quote_time = str(source_row.get("quote_time") or "")
    quote_digits = "".join(value for value in quote_time if value.isdigit())
    if len(quote_digits) >= 8 and quote_digits[:8] != local.trade_date.replace("-", ""):
        return {**base, "capability_status": "UNAVAILABLE", "reason": "SOURCE_SESSION_DATE_MISMATCH"}
    session_binding = "SESSION_VERIFIED" if len(quote_digits) >= 14 and quote_digits[:8] == local.trade_date.replace("-", "") and quote_digits[8:14] >= "150000" else "FINGERPRINT_ONLY"
    matched = (
        _close(price, local.raw_close, rel=0.0005, abs_=0.011)
        and _close(amount, local.raw_amount, rel=0.002, abs_=100.0)
        and _close(volume, local.raw_volume, rel=0.002, abs_=100.0)
    )
    if not matched:
        return {**base, "capability_status": "UNAVAILABLE", "reason": "LOCAL_SESSION_FINGERPRINT_MISMATCH"}
    return {
        **base,
        "capability_status": "BOUND",
        "reason": "LOCAL_SESSION_FINGERPRINT_MATCH",
        "turnover_rate": turnover,
        "observed_at_utc": source_row.get("observed_at_utc"),
        "source_quote_time": source_row.get("quote_time"),
        "source_id": source_row.get("source_id"),
        "source_contract_id": source_row.get("source_contract_id"),
        "field_map_version": source_row.get("field_map_version"),
        "turnover_basis": source_row.get("normalized_turnover_basis") or source_row.get("turnover_basis") or base["turnover_basis"],
        "basis_verification": source_row.get("basis_verification") or "DECLARED_ONLY",
        "session_binding_status": source_row.get("session_binding_status") or session_binding,
        "source_identity_sha256": source_row.get("source_identity_sha256"),
    }
