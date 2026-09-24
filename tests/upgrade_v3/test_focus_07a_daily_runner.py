from datetime import date

import pytest

from scripts import run_focus_daily
from src.focus_tracker.daily_head_plan import DailyHeadPlan


DAY = date(2026, 9, 23)
PREFLIGHT = {"manifest_sha256": "abc", "publication_id": "pub", "source_rows": 2,
             "tracking_keys": 2, "observation_count": 2}
INITIAL = DailyHeadPlan(DAY, 1, None, None, None, "INITIAL_DAY")
NEXT = DailyHeadPlan(DAY, 1, date(2026, 9, 22), "prior", None, "NEXT_DAY")


def test_next_day_preflight_uses_continuation_batch(monkeypatch):
    monkeypatch.setattr(run_focus_daily, "_head_plan", lambda _: NEXT)
    monkeypatch.setattr(run_focus_daily, "prepare",
                        lambda **_: pytest.fail("initial batch must not be built"))
    monkeypatch.setattr(run_focus_daily, "_prepare_next_day", lambda _: PREFLIGHT)
    monkeypatch.setattr(run_focus_daily, "publish_next_day",
                        lambda **_: pytest.fail("preflight published"))
    result = run_focus_daily.run(trade_date=DAY)
    assert result["head_plan_status"] == "NEXT_DAY"
    assert result["core_status"] == "PREFLIGHT_READY"


def test_preflight_does_not_publish_or_settle(monkeypatch):
    monkeypatch.setattr(run_focus_daily, "_head_plan", lambda _: INITIAL)
    monkeypatch.setattr(run_focus_daily, "prepare", lambda **_: PREFLIGHT)
    monkeypatch.setattr(run_focus_daily, "publish_initial_day",
                        lambda **_: pytest.fail("preflight published"))
    monkeypatch.setattr(run_focus_daily, "settle_outcomes",
                        lambda **_: pytest.fail("preflight settled"))
    result = run_focus_daily.run(trade_date=DAY)
    assert result["core_status"] == "PREFLIGHT_READY"
    assert result["outcome_status"] == "NOT_RUN"


def test_apply_settles_only_after_core_activation(monkeypatch):
    calls = []
    monkeypatch.setattr(run_focus_daily, "_head_plan", lambda _: INITIAL)
    monkeypatch.setattr(run_focus_daily, "prepare", lambda **_: PREFLIGHT)
    monkeypatch.setattr(run_focus_daily, "publish_initial_day",
                        lambda **_: calls.append("core"))
    monkeypatch.setattr(run_focus_daily, "settle_outcomes",
                        lambda **_: calls.append("outcome") or {"status": "NO_DUE_OUTCOMES"})
    result = run_focus_daily.run(trade_date=DAY, apply=True)
    assert calls == ["core", "outcome"]
    assert result["core_status"] == "ACTIVATED"


def test_outcome_failure_does_not_relabel_committed_core(monkeypatch):
    monkeypatch.setattr(run_focus_daily, "_head_plan", lambda _: INITIAL)
    monkeypatch.setattr(run_focus_daily, "prepare", lambda **_: PREFLIGHT)
    monkeypatch.setattr(run_focus_daily, "publish_initial_day", lambda **_: None)
    def fail(**_):
        raise RuntimeError("settlement unavailable")
    monkeypatch.setattr(run_focus_daily, "settle_outcomes", fail)
    result = run_focus_daily.run(trade_date=DAY, apply=True)
    assert result["core_status"] == "ACTIVATED"
    assert result["outcome_status"] == "DEGRADED"


def test_next_day_apply_uses_continuation_writer(monkeypatch):
    calls = []
    monkeypatch.setattr(run_focus_daily, "_head_plan", lambda _: NEXT)
    monkeypatch.setattr(run_focus_daily, "_prepare_next_day", lambda _: PREFLIGHT)
    monkeypatch.setattr(run_focus_daily, "publish_next_day",
                        lambda **_: calls.append("continuation") or {"status": "ACTIVATED"})
    monkeypatch.setattr(run_focus_daily, "settle_outcomes",
                        lambda **_: calls.append("outcome") or {"status": "NO_DUE_OUTCOMES"})
    result = run_focus_daily.run(trade_date=DAY, apply=True)
    assert calls == ["continuation", "outcome"]
    assert result["core_publication"]["status"] == "ACTIVATED"
