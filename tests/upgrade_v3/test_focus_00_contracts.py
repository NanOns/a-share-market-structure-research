from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.focus_tracker.contracts import FocusKey, anchor_id, canonical_bytes, episode_id
from src.focus_tracker.lifecycle import (Previous, auxiliary_anchors, plan_day,
                                         segment_id, source_attribute_transition, tracking_union)
from src.focus_tracker.predicates import Tri, evaluate
from src.focus_tracker.price_path import (AdjustmentEvent, Bar, due_date, path_metrics,
                                          reanchor_from_frozen_coefficients, reanchor_path)
from src.focus_tracker.states import classify_sector, classify_stock
from src.focus_tracker.outcomes import classify_outcome, followup_complete
from src.focus_tracker.predicates import compile_v3_3_invalidation


D1, D2, D3 = date(2026, 9, 21), date(2026, 9, 22), date(2026, 9, 23)
STOCK = FocusKey("V3_SHORTLIST_STOCK", "STOCK", "000001", "V3")
CANDIDATE = FocusKey("V3_3_TODAY_CANDIDATE", "STOCK", "000001", "V3_3")
SECTOR = FocusKey("V3_SECTOR_TRACK", "SECTOR", "BK001", "V3")
CAPS = {"V3_SHORTLIST_STOCK": "COMPLETE", "V3_SECTOR_TRACK": "COMPLETE",
        "V3_3_TODAY_CANDIDATE": "COMPLETE", "V3_SHORTLIST_INDIVIDUAL": "COMPLETE"}


def test_sources_have_separate_episode_ids_and_canonical_hash_input():
    assert episode_id(STOCK, D1) != episode_id(CANDIDATE, D1)
    assert episode_id(STOCK, D1) != episode_id(STOCK, D2)
    assert canonical_bytes({"b": Decimal("1.20"), "a": datetime(2026, 9, 21, tzinfo=timezone.utc)}) == canonical_bytes(
        {"a": datetime(2026, 9, 21, tzinfo=timezone.utc), "b": Decimal("1.20")})
    with pytest.raises(ValueError):
        canonical_bytes({"bad": float("nan")})


def test_upgrade_twice_is_one_episode_with_two_distinct_anchors():
    eid = episode_id(STOCK, D1)
    up1 = plan_day(trade_date=D2, current={STOCK: "CURRENT"},
                   previous={STOCK: Previous(STOCK, "EARLY", eid, D1)}, capabilities=CAPS)[0]
    down = plan_day(trade_date=D3, current={STOCK: "EARLY"},
                    previous={STOCK: Previous(STOCK, "CURRENT", eid, D1)}, capabilities=CAPS)[0]
    later = date(2026, 9, 24)
    up2 = plan_day(trade_date=later, current={STOCK: "CURRENT"},
                   previous={STOCK: Previous(STOCK, "EARLY", eid, D1)}, capabilities=CAPS)[0]
    assert (up1.phase, down.phase, up2.phase) == ("UPGRADED", "DOWNGRADED", "UPGRADED")
    assert up1.episode_id == down.episode_id == up2.episode_id == eid
    assert up1.anchors[0][1] != up2.anchors[0][1]


def test_complete_absence_exits_but_unavailable_source_does_not():
    eid = episode_id(SECTOR, D1)
    previous = {SECTOR: Previous(SECTOR, "CURRENT", eid, D1)}
    exit_decision = plan_day(trade_date=D2, current={}, previous=previous, capabilities=CAPS)[0]
    unavailable = plan_day(trade_date=D2, current={}, previous=previous,
                           capabilities={**CAPS, "V3_SECTOR_TRACK": "UNAVAILABLE"})[0]
    assert exit_decision.phase == "EXITED"
    assert exit_decision.anchors[0][0] == "EXIT_EFFECTIVE"
    assert unavailable.phase == "DATA_UNAVAILABLE"
    assert unavailable.anchors == ()


def test_reentry_new_episode_and_exit_stays_in_tracking_union():
    old = episode_id(STOCK, D1)
    decision = plan_day(trade_date=D3, current={STOCK: "EARLY"},
                        previous={STOCK: Previous(STOCK, "NONE", old, D1)}, capabilities=CAPS)[0]
    assert decision.phase == "REENTERED"
    assert decision.parent_episode_id == old
    assert decision.episode_id != old
    assert tracking_union(set(), {STOCK}, set()) == {STOCK}


def test_model_boundary_is_not_market_entry_or_exit():
    old = Previous(STOCK, "CURRENT", episode_id(STOCK, D1), D1)
    changed = FocusKey("V3_SHORTLIST_STOCK", "STOCK", "000001", "V4")
    decisions = plan_day(trade_date=D2, current={changed: "EARLY"},
                         previous={STOCK: old}, capabilities=CAPS)
    assert decisions[0].phase == "SOURCE_MODEL_BOUNDARY"


def test_boundary_only_old_is_unknown_and_only_new_is_baseline():
    old = Previous(STOCK, "CURRENT", episode_id(STOCK, D1), D1)
    boundary_caps = {**CAPS, "V3_SHORTLIST_STOCK": "CONTRACT_BOUNDARY"}
    missing = plan_day(trade_date=D2, current={}, previous={STOCK: old},
                       capabilities=boundary_caps)[0]
    fresh = FocusKey("V3_SHORTLIST_STOCK", "STOCK", "000002", "V4")
    baseline = plan_day(trade_date=D2, current={fresh: "EARLY"}, previous={},
                        capabilities=boundary_caps)[0]
    assert missing.phase == "BOUNDARY_UNKNOWN"
    assert baseline.phase == "MODEL_BASELINE"
    assert baseline.anchors[0][0] == "FIRST_FOCUS"


def test_ast_unknown_is_not_false_and_missing_bar_breaks_consecutive():
    ast = {"op": "OR", "args": [
        {"op": "EQ", "field": "structure_break", "mode": "CURRENT_FIELD", "value": True},
        {"op": "CONSECUTIVE", "sessions": 2, "predicate":
            {"op": "LT", "field": "close", "mode": "CURRENT_FIELD",
             "anchor": "platform", "anchor_mode": "FROZEN_SIGNAL_VALUE"}},
    ]}
    result, evidence = evaluate(ast, trade_date=D3, sessions=[D1, D2, D3],
                                facts_by_date={D2: {"has_actual_bar": False},
                                               D3: {"has_actual_bar": True, "close": 9, "structure_break": False}},
                                frozen_signal={"platform": 10}, frozen_episode={})
    assert result is Tri.UNKNOWN
    assert evidence["result"] == "UNKNOWN"


def test_reanchored_path_uses_same_adjustment_basis_and_trading_calendar():
    sessions = [D1, D2, D3]
    bars = {D1: Bar(D1, Decimal("10"), Decimal("11"), Decimal("9"), Decimal("10")),
            D2: Bar(D2, Decimal("10"), Decimal("11"), Decimal("9"), Decimal("10")),
            D3: Bar(D3, Decimal("5"), Decimal("5.5"), Decimal("4.5"), Decimal("5"))}
    adjusted = reanchor_path(sessions=sessions, bars=bars,
                             events=[AdjustmentEvent(D3, Decimal("2"), Decimal("0"))])
    assert [bar.close for bar in adjusted] == [Decimal("5.00"), Decimal("5.00"), Decimal("5.00")]
    assert path_metrics(adjusted)["return_close"] == 0
    assert due_date(sessions, D1, 1) == D2
    assert due_date(sessions, D1, 5) is None
    assert reanchor_path(sessions=sessions, bars={D1: bars[D1], D3: bars[D3]}, events=[]) is None


def test_frozen_coefficients_remove_future_adjustment_from_prior_observation():
    def row(close, a):
        return {"raw_open": close, "raw_high": close, "raw_low": close,
                "raw_close": close, "qfq_mul": a, "qfq_add": "0",
                "adjustment_status": "VERIFIED_REPRODUCIBLE_TDX_NATIVE",
                "adjustment_version": "tdx-affine-qfq-v0.2", "has_actual_bar": True}
    rows = {D1: row("10", "0.5"), D2: row("10", "0.5"), D3: row("5", "1")}
    prior = reanchor_from_frozen_coefficients(sessions=[D1, D2], rows=rows)
    current = reanchor_from_frozen_coefficients(sessions=[D1, D2, D3], rows=rows)
    assert [x.close for x in prior] == [Decimal("10.00"), Decimal("10.00")]
    assert [x.close for x in current] == [Decimal("5.00")] * 3


def test_still_listed_but_invalidated_is_orthogonal_to_membership():
    decision = classify_stock({"has_actual_bar": True, "close": 10},
                              invalidation=Tri.TRUE,
                              applicable=frozenset({"STRUCTURE_DAMAGED"}))
    assert decision.validity_state == "INVALIDATED"
    assert decision.current_path_state == "STRUCTURE_DAMAGED"
    assert plan_day(trade_date=D2, current={STOCK: "CURRENT"},
                    previous={STOCK: Previous(STOCK, "CURRENT", episode_id(STOCK, D1), D1)},
                    capabilities=CAPS)[0].phase == "PERSISTENT"


def test_unknown_higher_priority_does_not_become_false():
    decision = classify_stock({"has_actual_bar": True, "source_extended": True},
                              invalidation=Tri.UNKNOWN,
                              applicable=frozenset({"STRUCTURE_DAMAGED", "TOO_EXTENDED"}))
    assert decision.current_path_state == "DATA_UNAVAILABLE"
    assert decision.validity_state == "UNKNOWN"


def test_weakening_precedes_sideways_secondary_tag():
    decision = classify_stock({"has_actual_bar": True, "close": 9, "ma20": 10,
                               "range5_high_low": Decimal("0.05"),
                               "five_consecutive_actual_bars": True},
                              invalidation=Tri.FALSE,
                              applicable=frozenset({"WEAKENING"}))
    assert decision.current_path_state == "WEAKENING"
    assert decision.secondary_tags == ("SIDEWAYS_RANGE",)


def test_sector_exit_and_path_damage_remain_separate():
    decision = classify_sector({"coverage_ready": True, "source_membership": "NONE", "exited": True},
                               invalidation=Tri.FALSE,
                               applicable=frozenset({"SECTOR_STRUCTURE_DAMAGED", "SECTOR_EXITED_FOLLOW_UP"}))
    assert decision.current_path_state == "SECTOR_EXITED_FOLLOW_UP"
    assert decision.validity_state == "VALID"


def test_compiled_invalidation_preserves_unknown_frozen_price():
    ast = compile_v3_3_invalidation("LAUNCH_CONFIRM", {})
    result, _ = evaluate(ast, trade_date=D2, sessions=[D1, D2],
                         facts_by_date={D1: {"has_actual_bar": True, "close": 9},
                                        D2: {"has_actual_bar": True, "close": 9,
                                             "structure_break_v3": False}},
                         frozen_signal={}, frozen_episode={})
    assert result is Tri.UNKNOWN


def test_outcome_uses_fixed_session_and_audited_gap_statuses():
    base = dict(calendar=[D1, D2, D3], anchor_date=D1, horizon=1,
                as_of_date=D2, target_input_accepted=True,
                target_input_sealed=True, anchor_actual_bar=True)
    gap = classify_outcome(**base, target_data_state="INFERRED_GAP",
                           gap_audit_digest="a" * 64)
    unaudited_gap = classify_outcome(**base, target_data_state="INFERRED_GAP")
    suspended = classify_outcome(**base, target_data_state="CONFIRMED_SUSPENSION",
                                 audited_suspension=True)
    observed = classify_outcome(**base, target_data_state="BAR", path_complete=True)
    assert (gap.status, suspended.status, observed.status) == ("DATA_GAP", "SUSPENDED", "OBSERVED")
    assert (unaudited_gap.status, unaudited_gap.terminal) == ("PENDING", False)
    assert all(x.target_trade_date == D2 for x in (gap, suspended, observed))
    assert not classify_outcome(**{**base, "target_input_sealed": False},
                                target_data_state="INFERRED_GAP").terminal
    assert classify_outcome(**base, target_data_state="DELISTED_OR_INACTIVE",
                            audited_delisting=True).status == "DELISTED"


def test_completed_episode_leaves_daily_pool_only_after_all_mandatory_outcomes():
    assert not followup_complete(source_membership_exited=True,
                                 outcome_statuses=["OBSERVED", "PENDING"],
                                 pending_revision=False, unaudited_gap=False)
    assert followup_complete(source_membership_exited=True,
                             outcome_statuses=["OBSERVED", "DATA_GAP", "SUSPENDED"],
                             pending_revision=False, unaudited_gap=False)
    assert not followup_complete(source_membership_exited=False,
                                 outcome_statuses=["OBSERVED"],
                                 pending_revision=False, unaudited_gap=False)


def test_invalidation_and_later_sector_support_do_not_change_membership():
    old = Previous(STOCK, "CURRENT", episode_id(STOCK, D1), D1,
                   validity="VALID", had_sector_support=False)
    anchors = auxiliary_anchors(previous=old, trade_date=D2,
                                invalidation=Tri.TRUE, current_sector_support=True)
    assert {kind for kind, _ in anchors} == {"INVALIDATION", "FIRST_SUPPORTED"}
    assert plan_day(trade_date=D2, current={STOCK: "CURRENT"},
                    previous={STOCK: old}, capabilities=CAPS)[0].phase == "PERSISTENT"


def test_scenario_change_and_same_day_revision_do_not_split_episode():
    old = Previous(CANDIDATE, "CANDIDATE", episode_id(CANDIDATE, D1), D1)
    first = plan_day(trade_date=D2, current={CANDIDATE: "CANDIDATE"},
                     previous={CANDIDATE: old}, capabilities=CAPS)
    replay = plan_day(trade_date=D2, current={CANDIDATE: "CANDIDATE"},
                      previous={CANDIDATE: old}, capabilities=CAPS)
    assert first == replay
    assert first[0].episode_id == old.episode_id
    assert source_attribute_transition("LAUNCH_CONFIRM", "TREND_CONTINUE") == "SCENARIO_CHANGED"
    assert segment_id(old.episode_id, "INTERPRETATION", D2, "V3_3", "FOCUS_PATH_STATE_V1")
