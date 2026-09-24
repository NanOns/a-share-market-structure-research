"""Evaluate frozen V3.3 theses with current accepted market facts."""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping, Sequence

from .materialize import VerifiedNormalizedSlice
from .predicate_facts_by_date import (build_predicate_facts_by_date,
                                      reanchor_frozen_price,
                                      RPS20_DELTA3_PROVIDER_CONTRACT)
from .predicates import Tri, evaluate
from .v33_scanner_facts import bridge_scanner_facts


CONTRACT_ID = "FOCUS_V33_TRACKED_INVALIDATION_V3"


def evaluate_tracked_v33_invalidation(*, ast: Mapping[str, Any], frozen: Mapping[str, Any],
                                      first_row, today_source_row,
                                      scanner_evidence: Mapping[str, Any] | None,
                                      security_id: str, trade_date: date,
                                      first_trade_date: date, sessions: Sequence[date],
                                      required_fields: frozenset[str],
                                      normalized: VerifiedNormalizedSlice
                                      ) -> tuple[Tri, dict[str, Any], dict[str, Any]]:
    """Keep evaluating a tracked episode after it leaves today's source rows.

    Only current scanner-derived facts depend on today's source membership.
    Frozen thesis operands and price-derived daily facts remain evaluable from
    their accepted identities and verified local normalized inputs.
    """
    structure_break = None
    if today_source_row is not None:
        if not isinstance(scanner_evidence, Mapping):
            raise ValueError("current scanner evidence missing for V3.3 source row")
        bridge = bridge_scanner_facts(evidence=scanner_evidence,
                                      security_id=security_id,
                                      trade_date=trade_date)
        structure_break = bridge["structure_break_v3"]
    fact_rows, fact_digest = build_predicate_facts_by_date(
        normalized=normalized, security_id=security_id, trade_date=trade_date,
        sessions=sessions, required_fields=required_fields,
        structure_break_v3=structure_break)
    frozen_for_evaluation = dict(frozen)
    source_factor = first_row.source_facts.get("factor_evidence")
    compatible_basis = (isinstance(source_factor, dict) and
                        source_factor.get("price_basis") == "TDX_NATIVE_AFFINE_QFQ")
    for frozen_key in ("frozen_phh20", "frozen_pullback_invalid_low",
                       "frozen_trend_key_low"):
        frozen_for_evaluation[frozen_key] = (
            reanchor_frozen_price(
                normalized=normalized, security_id=security_id,
                signal_day=first_trade_date, trade_date=trade_date,
                value=frozen.get(frozen_key)) if compatible_basis else None)
    result, evidence = evaluate(
        ast, trade_date=trade_date, sessions=sessions,
        facts_by_date=fact_rows, frozen_signal=frozen_for_evaluation,
        frozen_episode={})
    metadata = {"contract_id": CONTRACT_ID,
                "fact_digest": fact_digest,
                "structure_break_v3": structure_break,
                "scanner_source_status": ("AVAILABLE" if today_source_row is not None
                                          else "SOURCE_ROW_ABSENT"),
                "provider_gaps": ([RPS20_DELTA3_PROVIDER_CONTRACT]
                                  if "rps20_delta3" in required_fields else []),
                "required_fields": sorted(required_fields)}
    return result, evidence, metadata
