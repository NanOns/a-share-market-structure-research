from __future__ import annotations

import pytest

from workbench_analysis.pullback_episode_v1 import trace_pullback_episode


def _days() -> list[dict]:
    days = []
    for i in range(8):
        days.append({"date": f"2026-01-{i + 1:02d}", "has_actual_bar": True,
                     "anchor_cutoff": "2026-01-08", "price_basis": "TDX_NATIVE_AFFINE_QFQ",
                     "session_index": i,
                     "is_synthetic_fill": False, "high": 11.0, "close": 10.8,
                     "ma20": 10.0, "amount": 100.0, "structure_break": False,
                     "strong_seed": False, "slope20_prior": 0.01,
                     "r2_20_prior": 0.8, "clv": 0.7,
                     "reclaim_ma5": False, "touch_reclaim10": False,
                     "intraday_reject_high20": False})
    days[4].update(strong_seed=True, high=11.5, close=11.3)
    days[5].update(high=12.0, close=11.5)
    days[6].update(high=11.7, close=11.0, amount=60.0)
    days[7].update(high=11.7, close=11.2, amount=120.0, reclaim_ma5=True)
    return days


def test_ordered_pullback_uses_separate_contraction_and_confirmation_amounts() -> None:
    trace = trace_pullback_episode(_days())
    assert trace[4]["state"] == "ADVANCING"
    assert trace[5]["peak_date"] == "2026-01-06"
    assert trace[6]["state"] == "PULLING_BACK"
    assert trace[7]["state"] == "CONFIRMED"
    assert trace[7]["confirmed"] is True
    evidence = trace[7]["evidence"]
    assert evidence["pullback_contraction"] == 0.6
    assert evidence["confirm_amount_ratio"] == 2.0
    assert evidence["short_pullback_sample"] is True


def test_new_high_resets_old_episode_before_confirmation() -> None:
    days = _days()
    days[7]["high"] = 12.0
    trace = trace_pullback_episode(days)
    assert trace[7]["state"] == "RESET_NEW_HIGH"
    assert trace[7]["confirmed"] is False


def test_left_censored_and_gap_do_not_create_new_seed() -> None:
    days = _days()
    days[0]["strong_seed"] = True
    trace = trace_pullback_episode(days)
    assert trace[0]["state"] == "LEFT_CENSORED"
    days = _days()
    days[6]["has_actual_bar"] = False
    days[6]["structure_break"] = True
    trace = trace_pullback_episode(days)
    assert trace[6]["state"] == "DATA_GAP"
    assert trace[6]["reason"] == "STRUCTURE_DAMAGED_KNOWN_WITH_DATA_GAP"
    assert trace[7]["confirmed"] is False


def test_anchor_and_master_session_identity_fail_closed() -> None:
    days = _days()
    days[3]["anchor_cutoff"] = "2026-01-03"
    with pytest.raises(ValueError, match="EPISODE_PRICE_ANCHOR_MISMATCH"):
        trace_pullback_episode(days)
    days = _days()
    days[3]["session_index"] = 5
    with pytest.raises(ValueError, match="EPISODE_MASTER_SESSION_GAP"):
        trace_pullback_episode(days)
    days = _days()
    days[4]["strong_seed"] = "true"
    with pytest.raises(ValueError, match="EPISODE_SIGNAL_TYPE_INVALID"):
        trace_pullback_episode(days)


def test_event_and_pullback_window_limits_are_inclusive() -> None:
    assert trace_pullback_episode(_days(), max_event_sessions=4)[7]["state"] == "CONFIRMED"
    assert trace_pullback_episode(_days(), max_event_sessions=3)[7]["state"] == "EXPIRED"
    assert trace_pullback_episode(_days(), max_pullback_sessions=1)[7]["state"] == "EXPIRED"


def test_unknown_initial_seed_requires_known_false_before_new_event() -> None:
    days = _days()
    days[0]["strong_seed"] = None
    days[1]["strong_seed"] = True
    trace = trace_pullback_episode(days)
    assert trace[0]["state"] == "DATA_GAP"
    assert trace[1]["state"] == "DATA_GAP"
    assert trace[2]["state"] == "IDLE"
    assert trace[4]["state"] == "ADVANCING"


def test_equal_peak_uses_latest_date_and_damage_precedes_peak_reset() -> None:
    days = _days()
    days[5]["high"] = 11.5
    trace = trace_pullback_episode(days)
    assert trace[5]["peak_date"] == "2026-01-06"
    days = _days()
    days[7]["high"] = 12.5
    days[7]["structure_break"] = True
    trace = trace_pullback_episode(days)
    assert trace[7]["state"] == "INVALIDATED"
    assert trace[7]["confirmed"] is False


def test_same_input_is_deterministic_and_terminal_cannot_repeat_confirmation() -> None:
    days = _days()
    for day in days:
        day["anchor_cutoff"] = "2026-01-09"
    next_day = dict(days[-1], date="2026-01-09", session_index=8,
                    high=11.5, close=11.3, amount=120.0,
                    strong_seed=False, reclaim_ma5=True)
    days.append(next_day)
    first = trace_pullback_episode(days)
    second = trace_pullback_episode(days)
    assert first == second
    assert sum(row["confirmed"] for row in first) == 1
    assert first[-1]["state"] == "IDLE"
