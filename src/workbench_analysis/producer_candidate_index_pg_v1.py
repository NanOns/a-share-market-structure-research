"""Build the exact-daily candidate index for direct PG Owner handoff."""
from __future__ import annotations

from pathlib import Path

def build_review_and_display_candidates(root, day, candidate, capture_result,
                                        *, candidate_binding, research_replay=False):
    """Run exact-daily optional producers and return a current-T0 index document.

    The returned document is passed directly to the existing PG Owner writer.
    This path deliberately has no local-index read or write operation.
    """
    from .producer_bootstrap_v1 import (
        optional_step, produce_daily_sector, produce_daily_state,
        produce_first_observed_state,
    )
    from .market_source_acquisition import official_sessions
    from .strict_source_candidate_v2 import freeze_for_review
    from .full_market_state_publisher_v1 import build as publish_state

    root = Path(root)
    if not isinstance(candidate, dict) or candidate.get('contract_id') != 'V4_OPERATIONAL_INCREMENTAL_SUCCESSOR_V1':
        raise ValueError('PG_OPERATIONAL_CANDIDATE_REQUIRED_NO_FILE_FALLBACK')
    if candidate.get('accepted_trade_date') != day:
        raise ValueError('PG_OPERATIONAL_CANDIDATE_T0_MISMATCH')
    sector = optional_step(produce_daily_sector, root, day, candidate)
    state = optional_step(produce_daily_state, root, day, candidate)
    publisher = optional_step(publish_state, root, candidate=candidate, candidate_binding=candidate_binding,
                              trade_date=day, revision="daily-r1")
    first_observed = optional_step(produce_first_observed_state, root, day,
                                   candidate)
    strict = (optional_step(freeze_for_review, root,
                            capture_binding=capture_result["candidate"],
                            candidate=candidate, candidate_binding=candidate_binding, trade_date=day,
                            research_replay=research_replay)
              if capture_result.get("candidate") else
              dict(status="CANDIDATE_FAILED", reason="INITIAL_CAPTURE_FAILED",
                   production=False))

    sessions = official_sessions(root)
    entry = dict(head=candidate_binding,
                 next_session=next((value for value in sessions if value > day), None),
                 production=False)
    for key, value in (("sector", sector), ("full_state", state),
                       ("strict_source", strict), ("source_capture", capture_result)):
        if value.get("candidate"):
            entry[key] = value["candidate"]
        else:
            entry[key + "_failure"] = value.get("reason")
    index = dict(contract_id="PRODUCER_CANDIDATE_INDEX_V2", sessions={day: entry})
    return dict(sector=sector, full_state=state, state_publisher=publisher,
                state_publisher_quarantine=dict(status="NOT_RUN_NO_LOCAL_INDEX_SIDE_EFFECT",
                                                production=False),
                first_observed_state=first_observed, strict_source=strict,
                index=dict(contract_id="PRODUCER_CANDIDATE_INDEX_V2", T0=day,
                           source="IN_MEMORY_TO_PG_OWNER", persisted=False),
                index_document=index)
