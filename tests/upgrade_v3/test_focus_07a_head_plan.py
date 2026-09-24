from datetime import date

import pytest

from src.focus_tracker.daily_head_plan import classify_head_plan


DAY = date(2026, 9, 24)
PRIOR = (date(2026, 9, 23), "focus-prior", "VALID")


def test_initial_and_next_day_are_distinct():
    initial = classify_head_plan(trade_date=DAY, prior=None, same_day=None,
                                 oldest_replay=None)
    next_day = classify_head_plan(trade_date=DAY, prior=PRIOR, same_day=None,
                                  oldest_replay=None)
    assert (initial.status, initial.revision) == ("INITIAL_DAY", 1)
    assert (next_day.status, next_day.predecessor_focus_run_id) == (
        "NEXT_DAY", "focus-prior")


def test_same_day_revision_keeps_previous_date_predecessor():
    plan = classify_head_plan(trade_date=DAY, prior=PRIOR,
                              same_day=("focus-old", 2, "VALID"), oldest_replay=None)
    assert plan.status == "REVISION_REQUIRED"
    assert plan.revision == 3
    assert plan.predecessor_focus_run_id == "focus-prior"
    assert plan.accepted_focus_run_id == "focus-old"


def test_replay_and_invalid_predecessor_fail_closed():
    with pytest.raises(ValueError, match="REPLAY_REQUIRED"):
        classify_head_plan(trade_date=DAY, prior=PRIOR, same_day=None,
                           oldest_replay=date(2026, 9, 23))
    with pytest.raises(ValueError, match="PREDECESSOR_HEAD_NOT_VALID"):
        classify_head_plan(trade_date=DAY,
                           prior=(PRIOR[0], PRIOR[1], "REPLAY_REQUIRED"),
                           same_day=None, oldest_replay=None)
