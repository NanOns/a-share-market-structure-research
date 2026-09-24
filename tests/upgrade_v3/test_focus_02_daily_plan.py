from datetime import date

import pytest

from src.focus_tracker import basket_resolution
from src.focus_tracker.basket_resolution import resolve_baskets
from src.focus_tracker.contracts import FocusKey
from src.focus_tracker.daily_plan import build_day_plan
from src.focus_tracker.lifecycle import Previous
from src.focus_tracker.previous_reader import read_predecessor
from src.focus_tracker.sector_basket import SectorBasket
from src.focus_tracker.source_reader import AcceptedSources, SourceRow


DAY = date(2026, 9, 22)
EARLIER = date(2026, 9, 18)


def _key(family, entity_type, entity_id, contract="v1"):
    return FocusKey(family, entity_type, entity_id, contract)


def _sources(*items):
    rows = tuple(SourceRow(key, DAY, membership, "row", "a" * 64,
                           "contract", None, None, {}) for key, membership in items)
    return AcceptedSources(DAY, "publication", "research", "bundle",
                           {"V3_SHORTLIST_STOCK": "COMPLETE",
                            "V3_SHORTLIST_INDIVIDUAL": "COMPLETE",
                            "V3_SECTOR_TRACK": "COMPLETE",
                            "V3_3_TODAY_CANDIDATE": "COMPLETE"},
                           rows, "b" * 64)


def test_cross_source_same_stock_keeps_two_decisions_one_shared_path():
    first = _key("V3_SHORTLIST_STOCK", "STOCK", "SH.600001")
    second = _key("V3_3_TODAY_CANDIDATE", "STOCK", "SH.600001")
    planned = build_day_plan(sources=_sources((first, "CURRENT"), (second, "CANDIDATE")),
                             previous={}, pending_followup=set(), due_outcomes=set())
    assert len(planned.decisions) == 2
    assert len(planned.stock_path_requests) == 1
    assert planned.stock_path_requests[0].start_trade_date == DAY


def test_exited_pending_episode_remains_in_fact_union():
    key = _key("V3_SHORTLIST_STOCK", "STOCK", "SH.600001")
    previous = {key: Previous(key, "NONE", "episode", EARLIER)}
    planned = build_day_plan(sources=_sources(), previous=previous,
                             pending_followup={key}, due_outcomes=set())
    assert planned.decisions[0].phase == "POST_EXIT"
    assert planned.stock_path_requests[0].start_trade_date == EARLIER


def test_selection_contract_boundary_rekeys_without_losing_pending_entity():
    old = _key("V3_SHORTLIST_STOCK", "STOCK", "SH.600001", "old")
    new = _key("V3_SHORTLIST_STOCK", "STOCK", "SH.600001", "new")
    planned = build_day_plan(sources=_sources((new, "CURRENT")),
                             previous={old: Previous(old, "CURRENT", "old-episode", EARLIER)},
                             pending_followup={old}, due_outcomes=set())
    assert planned.decisions[0].phase == "SOURCE_MODEL_BOUNDARY"
    assert planned.tracking_keys == (new,)


def test_predecessor_reader_rejects_replay_required_head():
    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def execute(self, *_):
            return None

        def fetchone(self):
            return (EARLIER, "run", "REPLAY_REQUIRED")

    class Connection:
        def cursor(self):
            return Cursor()

    class Repository:
        connection = Connection()
        schema = "workbench"

    with pytest.raises(ValueError, match="requires replay"):
        read_predecessor(Repository(), DAY)


def test_sector_entry_basket_stays_frozen_while_contemporary_changes(monkeypatch):
    key = _key("V3_SECTOR_TRACK", "SECTOR", "sector-1")
    old = SectorBasket("sector-1", ("a", "b"), "BOUND_RELATION_REVISION",
                       "scope:1", "old-digest")
    latest = SectorBasket("sector-1", ("b", "c"), "BOUND_RELATION_REVISION",
                          "scope:2", "new-digest")
    monkeypatch.setattr(basket_resolution, "read_accepted_entry_basket",
                        lambda repository, episode_id: old)
    planned = build_day_plan(sources=_sources((key, "CURRENT")),
                             previous={key: Previous(key, "CURRENT", "episode-1", EARLIER)},
                             pending_followup=set(), due_outcomes=set())
    baskets = resolve_baskets(repository=object(), plan=planned,
                              contemporary={"sector-1": latest})
    assert baskets.entry_frozen_by_episode["episode-1"] == old
    assert baskets.contemporary_by_sector["sector-1"] == latest


def test_new_sector_episode_freezes_current_publication_basket():
    key = _key("V3_SECTOR_TRACK", "SECTOR", "sector-1")
    current = SectorBasket("sector-1", ("a", "b"), "BOUND_RELATION_REVISION",
                           "scope:1", "digest")
    planned = build_day_plan(sources=_sources((key, "EARLY")),
                             previous={}, pending_followup=set(), due_outcomes=set())
    baskets = resolve_baskets(repository=object(), plan=planned,
                              contemporary={"sector-1": current})
    episode = planned.decisions[0].episode_id
    assert baskets.entry_frozen_by_episode[episode] == current
