"""Read-only accepted-day six-dimension Focus observation rehearsal."""
from __future__ import annotations

from collections import Counter

from src.focus_tracker.daily_builder import build_focus_daily_batch


def build_observation_batch(*, evaluation_basis="HISTORICAL_RECONSTRUCTED",
                            expected_trade_date=None):
    return build_focus_daily_batch(evaluation_basis=evaluation_basis,
                                   expected_trade_date=expected_trade_date)


def main() -> int:
    manifest, sources, plan, facts, observations, baskets, closure = build_observation_batch()
    trade_date = sources.trade_date
    values = [item.observation for item in observations]
    print({"trade_date": str(trade_date), "evaluation_basis": "HISTORICAL_RECONSTRUCTED",
           "observations": len(values),
           "family": dict(Counter(item.evidence["key"]["family"] for item in values)),
           "validity": dict(Counter(item.validity_state for item in values)),
           "validity_capability": dict(Counter(
               item.evidence["validity_capability"]["status"] for item in values)),
           "path": dict(Counter(item.current_path_state for item in values)),
           "followup": dict(Counter(item.followup_state for item in values)),
           "stock_path_gaps": {
               "gap_sessions": sum(fact.gap_count for fact in facts),
               "suspended_sessions": sum(fact.suspended_sessions for fact in facts),
               "unverified_gap_sessions": sum(fact.unverified_gap_count for fact in facts),
               "ready_after_suspension": sum(
                   fact.quality_status == "READY" and fact.suspended_sessions > 0
                   for fact in facts)},
           "closure_digest": closure.input_digest,
           "writes": 0})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
