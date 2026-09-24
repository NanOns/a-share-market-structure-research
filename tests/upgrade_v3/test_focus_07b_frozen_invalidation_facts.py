from datetime import date
from types import SimpleNamespace

from src.focus_tracker.frozen_invalidation_facts import (derive_frozen_facts,
                                                         insert_episode_facts,
                                                         verify_episode_facts)


def source(category, factor=None, recovery=None):
    return SimpleNamespace(
        key=SimpleNamespace(source_family="V3_3_TODAY_CANDIDATE"),
        source_item_digest="d" * 64, trade_date=date(2026, 9, 23),
        source_facts={"primary_category": category,
                      "factor_evidence": factor or {},
                      "scanner_evidence": {"recovery_turn": recovery or {}}})


def test_only_explicit_launch_threshold_is_frozen():
    facts = {f.key: f for f in derive_frozen_facts(
        source("LAUNCH_CONFIRM", {"phh20": 12.5, "ma20": 11}))}
    assert facts["frozen_phh20"].value == "12.5"
    assert facts["frozen_trend_key_low"].value is None
    assert facts["frozen_trend_key_low"].reason == "SOURCE_OPERAND_UNAVAILABLE"
    pg_fact = {f.key: f for f in derive_frozen_facts(
        source("LAUNCH_CONFIRM", {"phh20": {"$binary64": "4029000000000000"}}))}
    assert pg_fact["frozen_phh20"].value == "12.5"


def test_missing_threshold_does_not_fall_back_to_unrelated_low():
    facts = {f.key: f for f in derive_frozen_facts(
        source("STRONG_PULLBACK", {"ma20": 10, "phh20": 12}))}
    assert facts["frozen_pullback_invalid_low"].value is None


def test_recovery_ma_identity_requires_unique_true_branch():
    unique = {f.key: f for f in derive_frozen_facts(
        source("RECOVERY_TURN", recovery={"r5": True, "r20": False}))}
    ambiguous = {f.key: f for f in derive_frozen_facts(
        source("RECOVERY_TURN", recovery={"r5": True, "r20": True}))}
    assert unique["reclaimed_ma_kind"].value == "MA5"
    assert ambiguous["reclaimed_ma_kind"].value is None


class FactCursor:
    def __init__(self):
        self.revision = 1
        self.versions = {}
        self.legacy = {}
        self.result = []
    def execute(self, query, params=None):
        statement = str(query)
        if "select accepted_revision" in statement:
            self.one = (self.revision,)
        elif "select fact_key,fact_value" in statement and "revisions" in statement:
            episode, day, revision = params
            self.result = [(key, *value) for (ep, d, rev, key), value in self.versions.items()
                           if (ep, d, rev) == (episode, day, revision)]
        elif "select fact_key,fact_value" in statement:
            episode = params[0]
            self.result = [(key, *value) for (ep, key), value in self.legacy.items()
                           if ep == episode]
        elif "insert into workbench.focus_episode_frozen_fact_revisions" in statement:
            episode, day, revision, key, *values = params
            self.versions[(episode, day, revision, key)] = tuple(values)
        elif "insert into workbench.focus_episode_frozen_facts" in statement:
            episode, key, *values = params
            self.legacy[(episode, key)] = tuple(values)
    def fetchone(self): return self.one
    def fetchall(self): return self.result


def test_same_day_revision_keeps_old_frozen_facts_and_selects_accepted_revision():
    first = source("LAUNCH_CONFIRM", {"phh20": 12.5})
    revised = source("LAUNCH_CONFIRM", {"phh20": 13.25})
    cur = FactCursor()
    insert_episode_facts(cur, episode_id="episode-1", row=first,
                         source_revision=1, insert_legacy=True)
    legacy_before = dict(cur.legacy)
    insert_episode_facts(cur, episode_id="episode-1", row=revised,
                         source_revision=2, insert_legacy=False)

    cur.revision = 1
    verify_episode_facts(cur, episode_id="episode-1", first_row=first)
    cur.revision = 2
    verify_episode_facts(cur, episode_id="episode-1", first_row=revised)
    assert cur.legacy == legacy_before
    assert len(cur.versions) == 8
