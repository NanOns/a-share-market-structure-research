from datetime import date

import pytest

from src.focus_tracker.contracts import FocusKey, source_item_digest
from src.focus_tracker.daily_plan import PlannedDay
from src.focus_tracker.lifecycle import Decision
from src.focus_tracker.source_reader import AcceptedSources, SourceRow
from src.focus_tracker.tracking_context import resolve_tracking_contexts


FIRST = date(2026, 9, 23)
TODAY = date(2026, 9, 24)
KEY = FocusKey("V3_3_TODAY_CANDIDATE", "STOCK", "SH.600000", "V3_3")


def row(day=FIRST, facts=None):
    facts = facts or {"primary_category": "LAUNCH_CONFIRM"}
    return SourceRow(KEY, day, "CANDIDATE", "item-1",
                     source_item_digest("item-1", "contract-1", facts),
                     "contract-1", 1, None, facts)


def inputs(*, phase="POST_EXIT", current=()):
    decision = Decision(KEY, "NONE" if not current else "CANDIDATE", phase,
                        "episode-1", None, (), "SOURCE_MEMBERSHIP")
    plan = PlannedDay(TODAY, (decision,), (KEY,), (), (), "digest")
    sources = AcceptedSources(TODAY, "publication", None, None, {},
                              tuple(current), "source-digest")
    return plan, sources


def test_exited_key_uses_exact_frozen_episode_source():
    plan, sources = inputs()
    contexts = resolve_tracking_contexts(plan=plan,
                                         sources=sources,
                                         first_source_rows={"episode-1": row()})
    context = contexts[(KEY, "episode-1")]
    assert context.today_source_row is None
    assert context.first_trade_date == FIRST
    assert context.source_contract_id == "contract-1"


def test_missing_or_wrong_historical_identity_fails_closed():
    plan, sources = inputs()
    with pytest.raises(ValueError, match="accepted first source"):
        resolve_tracking_contexts(plan=plan, sources=sources,
                                  first_source_rows={})
    other = FocusKey("V3_3_TODAY_CANDIDATE", "STOCK", "SH.600001", "V3_3")
    original = row()
    wrong = SourceRow(other, original.trade_date, original.membership,
                      original.source_item_key, original.source_item_digest,
                      original.source_contract_id, original.source_rank,
                      original.source_focus_class, original.source_facts)
    with pytest.raises(ValueError, match="identity differs"):
        resolve_tracking_contexts(plan=plan, sources=sources,
                                  first_source_rows={"episode-1": wrong})


def test_new_episode_uses_today_source():
    current = row(TODAY)
    plan, sources = inputs(phase="NEW", current=(current,))
    contexts = resolve_tracking_contexts(plan=plan,
                                         sources=sources, first_source_rows={})
    assert contexts[(KEY, "episode-1")].today_source_row == current


def test_reentry_source_row_does_not_replace_old_episode_origin():
    current = row(TODAY, {"primary_category": "LAUNCH_CONFIRM", "current": True})
    old = Decision(KEY, "NONE", "POST_EXIT", "episode-old", None, (),
                   "PENDING_EPISODE_FOLLOW_UP")
    new = Decision(KEY, "CANDIDATE", "REENTERED", "episode-new", "episode-old",
                   (), "SOURCE_MEMBERSHIP")
    plan = PlannedDay(TODAY, (new,), (KEY,), (), (), "digest",
                      episode_tracking=(old, new))
    sources = AcceptedSources(TODAY, "publication", None, None, {},
                              (current,), "source-digest")
    contexts = resolve_tracking_contexts(
        plan=plan, sources=sources,
        first_source_rows={"episode-old": row(FIRST)})
    assert contexts[(KEY, "episode-old")].today_source_row is None
    assert contexts[(KEY, "episode-old")].first_trade_date == FIRST
    assert contexts[(KEY, "episode-new")].today_source_row == current
    assert contexts[(KEY, "episode-new")].first_trade_date == TODAY
