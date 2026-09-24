from datetime import date
from types import SimpleNamespace as NS

import pytest

from scripts import run_focus_continuation_core_transaction as writer
from src.focus_tracker.contracts import FocusKey


DAY = date(2026, 9, 24)
FIRST = date(2026, 9, 23)


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, query, params=None):
        statement = str(query)
        self.last_statement = statement
        self.last_params = params
        self.connection.statements.append((statement, params))
        self.rowcount = 1 if statement.startswith("insert into workbench.focus_episodes") else 0
        if self.connection.fail_at and self.connection.fail_at in statement:
            raise RuntimeError("INJECTED_CONTINUATION_FAILURE")

    def fetchone(self):
        if "select first_trade_date,selection_contract_family" in self.last_statement:
            episode = self.last_params[0]
            return (DAY if episode == "episode-reentered" else FIRST,
                    "V3_SHORTLIST_FAMILY")
        return (FIRST,)


class FakeConnection:
    def __init__(self, fail_at=None):
        self.fail_at = fail_at
        self.statements = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class FakeRepository:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def setup_writer(monkeypatch, *, fail_at=None):
    connection = FakeConnection(fail_at)
    keys = [FocusKey("V3_SHORTLIST_STOCK", "STOCK", f"SH.60000{i}", "V3_SHORTLIST_FAMILY")
            for i in range(3)]
    phases = ("PERSISTENT", "EXITED", "REENTERED")
    memberships = ("CURRENT", "NONE", "CURRENT")
    episodes = ("episode-persistent", "episode-exited", "episode-reentered")
    decisions = [NS(key=key, phase=phase, membership=membership, episode_id=episode,
                    parent_episode_id="episode-old" if phase == "REENTERED" else None,
                    anchors=(("EXIT_EFFECTIVE", "anchor-exit"),) if phase == "EXITED" else
                    (("FIRST_FOCUS", "anchor-reentry"),) if phase == "REENTERED" else (),
                    reason="SOURCE_MEMBERSHIP")
                 for key, phase, membership, episode in zip(keys, phases, memberships, episodes)]
    observations = [NS(key=key, observation=NS(
        episode_id=episode, source_membership_state=membership, membership_phase=phase,
        validity_state="VALID", followup_state="POST_EXIT" if phase == "EXITED" else "ACTIVE_FOCUS",
        current_path_state="TREND_CONTINUE", lifetime_path_tags=(), quality_status="READY",
        fact_digest="f" * 64, evidence={"path_predicates": {}}))
        for key, phase, membership, episode in zip(keys, phases, memberships, episodes)]
    rows = tuple(NS(key=key, membership="CURRENT", source_item_key=f"source-{i}",
                    source_item_digest="d" * 64, source_contract_id="SOURCE_V1",
                    source_rank=i, source_focus_class="FOCUS", source_facts={})
                 for i, key in enumerate((keys[0], keys[2])))
    sources = NS(rows=rows, capabilities={"V3_SHORTLIST_STOCK": "COMPLETE"},
                 source_identity_digest="s" * 64, publication_id="publication-24")
    plan = NS(tracking_keys=tuple(keys), decisions=tuple(decisions), stock_path_requests=())
    payload = {"state_contract_id": "FOCUS_PATH_STATE_V1", "parameter_set_id": "parameters",
               "dependency_lock_hash": "l" * 64, "calendar_digest": "c" * 64,
               "normalized_artifact_sha256": "n" * 64}
    manifest = NS(sha256="m" * 64, payload=payload)
    closure = NS(input_digest="i" * 64)
    stock_facts = {key.entity_id: NS(close_price=10, return_since_start=0.1,
                                     drawdown_current=-0.02, input_digest="p" * 64,
                                     quality_status="READY") for key in keys}
    contexts = {(key, episode): NS(first_trade_date=DAY if phase == "REENTERED" else FIRST,
                                   source_contract_id="SOURCE_V1")
                for key, episode, phase in zip(keys, episodes, phases)}
    previous = NS(focus_run_id="focus-23", previous={
        keys[0]: NS(membership="CURRENT"), keys[1]: NS(membership="CURRENT"),
        keys[2]: NS(membership="NONE")})
    slot_calls = []
    monkeypatch.setattr(writer, "build_focus_daily_batch", lambda **_: (
        manifest, sources, plan, stock_facts, observations, (), closure))
    monkeypatch.setattr(writer, "_dsn", lambda: "unused")
    monkeypatch.setattr(writer, "PostgresRepository", lambda **_: FakeRepository(connection))
    monkeypatch.setattr(writer, "read_daily_head_plan", lambda *_args, **_kwargs: NS(
        status="NEXT_DAY", revision=1, predecessor_focus_run_id="focus-23"))
    monkeypatch.setattr(writer, "read_predecessor", lambda *_: previous)
    monkeypatch.setattr(writer, "read_accepted_sources", lambda *_: sources)
    monkeypatch.setattr(writer, "require_core_publication_ready", lambda **_: None)
    def slot(*_args, **_kwargs):
        slot_calls.append(1)
        return "NEW" if len(slot_calls) == 1 else "ALREADY_ACTIVATED"
    monkeypatch.setattr(writer, "inspect_run_slot", slot)
    monkeypatch.setattr(writer, "read_first_source_rows", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(writer, "resolve_tracking_contexts", lambda **_: contexts)
    monkeypatch.setattr(writer, "index_stock_path_facts", lambda **_: {
        (key.entity_id, contexts[(key, episode)].first_trade_date): stock_facts[key.entity_id]
        for key, episode in zip(keys, episodes)})
    monkeypatch.setattr(writer, "activate_core_head", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(writer, "rebuild_current_projection", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(writer, "verify_current_projection", lambda *_args, **_kwargs: True)
    return connection, keys, episodes


def _inserts(connection, table):
    return [params for statement, params in connection.statements
            if statement.startswith(f"insert into workbench.{table}")]


def test_continuation_persistent_exit_reentry_and_rollback(monkeypatch):
    connection, keys, episodes = setup_writer(monkeypatch)
    result = writer.publish_next_day(trade_date=DAY, expected_manifest_digest="m" * 64)
    assert result["status"] == "ROLLBACK_READY"
    assert result["observation_count"] == result["tracking_keys"] == 3
    assert connection.commits == 0 and connection.rollbacks >= 1
    assert len(_inserts(connection, "focus_episodes")) == 1
    assert _inserts(connection, "focus_episodes")[0][0] == episodes[2]
    transitions = _inserts(connection, "focus_episode_transitions")
    assert [(row[0], row[6], row[8]) for row in transitions] == [
        (episodes[0], "PERSISTENT", "CURRENT"),
        (episodes[1], "EXITED", "NONE"),
        (episodes[2], "REENTERED", "CURRENT")]
    assert len(_inserts(connection, "focus_episode_observations")) == 3
    assert {row[0] for row in _inserts(connection, "focus_episode_anchors")} == {
        "anchor-exit", "anchor-reentry"}


def test_continuation_failure_rolls_back_before_head_commit(monkeypatch):
    connection, _, _ = setup_writer(monkeypatch, fail_at="insert into workbench.focus_episode_observations")
    with pytest.raises(RuntimeError, match="INJECTED_CONTINUATION_FAILURE"):
        writer.publish_next_day(trade_date=DAY, expected_manifest_digest="m" * 64,
                                commit=True)
    assert connection.commits == 0 and connection.rollbacks >= 1


def test_continuation_projection_failure_rolls_back_head_activation(monkeypatch):
    connection, _, _ = setup_writer(monkeypatch)
    activated = []
    monkeypatch.setattr(writer, "activate_core_head", lambda *_args, **_kwargs: activated.append(True))
    monkeypatch.setattr(writer, "verify_current_projection", lambda *_args, **_kwargs: False)
    with pytest.raises(RuntimeError, match="projection verification failed"):
        writer.publish_next_day(trade_date=DAY, expected_manifest_digest="m" * 64,
                                commit=True)
    assert activated == [True]
    assert connection.commits == 0 and connection.rollbacks >= 1


def test_continuation_commits_only_after_projection_check(monkeypatch):
    connection, _, _ = setup_writer(monkeypatch)
    result = writer.publish_next_day(trade_date=DAY, expected_manifest_digest="m" * 64,
                                     commit=True)
    assert result["status"] == "ACTIVATED"
    assert connection.commits == 1


def test_reentry_writes_old_followup_and_new_episode_observations(monkeypatch):
    connection, keys, episodes = setup_writer(monkeypatch)
    build = writer.build_focus_daily_batch
    manifest, sources, plan, stock_facts, observations, baskets, closure = build()
    key = keys[2]
    old_episode = "episode-old-overlap"
    old_decision = NS(key=key, membership="NONE", phase="POST_EXIT",
                      episode_id=old_episode, parent_episode_id=None, anchors=(),
                      reason="PENDING_EPISODE_FOLLOW_UP")
    old_observation = NS(
        episode_id=old_episode, source_membership_state="NONE",
        membership_phase="POST_EXIT", validity_state="UNKNOWN",
        followup_state="PENDING_SETTLEMENT", current_path_state="DATA_UNAVAILABLE",
        lifetime_path_tags=(), quality_status="DATA_UNAVAILABLE",
        fact_digest="o" * 64, evidence={"path_predicates": {}})
    plan.episode_tracking = (*plan.decisions, old_decision)
    old_item = NS(key=key, observation=old_observation)
    monkeypatch.setattr(writer, "build_focus_daily_batch", lambda **_: (
        manifest, sources, plan, stock_facts, (*observations, old_item), baskets, closure))
    contexts = {(item.key, item.episode_id): NS(
        first_trade_date=DAY if item.phase == "REENTERED" else FIRST,
        source_contract_id="SOURCE_V1") for item in plan.episode_tracking}
    monkeypatch.setattr(writer, "resolve_tracking_contexts", lambda **_: contexts)
    path_facts = {(item.key.entity_id, contexts[(item.key, item.episode_id)].first_trade_date):
                  NS(close_price=10, return_since_start=0.1, drawdown_current=-0.02,
                     input_digest=("p" if item.phase == "REENTERED" else "q") * 64,
                     quality_status="READY") for item in plan.episode_tracking}
    monkeypatch.setattr(writer, "index_stock_path_facts", lambda **_: path_facts)

    result = writer.publish_next_day(trade_date=DAY,
                                     expected_manifest_digest="m" * 64)
    assert result["status"] == "ROLLBACK_READY"
    assert result["tracking_keys"] == 3
    assert result["tracking_episodes"] == result["observation_count"] == 4
    written = _inserts(connection, "focus_episode_observations")
    assert len(written) == 4
    assert {row[0] for row in written} >= {old_episode, episodes[2]}
    transitions = _inserts(connection, "focus_episode_transitions")
    assert old_episode not in {row[0] for row in transitions}
