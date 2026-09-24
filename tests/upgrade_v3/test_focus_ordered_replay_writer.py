from datetime import date
from types import SimpleNamespace as NS

import pytest

from scripts import replay_focus_ordered_chain as replay
from src.focus_tracker.replay import ReplayItem


def test_replay_preview_is_bounded_and_does_not_write(monkeypatch):
    items = (ReplayItem(date(2026, 9, 22), "old-22", 1),
             ReplayItem(date(2026, 9, 23), "old-23", 2))
    # Use a conventional context-manager object because the reader checks connection.
    class Repo:
        connection = NS(rollback=lambda: None)
        def __enter__(self): return self
        def __exit__(self, *_): return False
    monkeypatch.setattr(replay, "PostgresRepository", lambda **_: Repo())
    monkeypatch.setattr(replay, "pending_replay_chain", lambda _: items)

    result = replay.replay_chain(apply=False, max_days=2)
    assert result["trade_dates"] == ["2026-09-22", "2026-09-23"]
    assert result["revisions"] == [2, 3]
    assert result["write_count"] == 0
    with pytest.raises(ValueError, match="EXCEEDS_BOUND"):
        replay.replay_chain(apply=False, max_days=1)


def test_replay_apply_rebuilds_and_activates_dates_in_order(monkeypatch, tmp_path):
    pending = [ReplayItem(date(2026, 9, 22), "old-22", 1),
               ReplayItem(date(2026, 9, 23), "old-23", 1)]
    applied = []
    class Repo:
        connection = NS(rollback=lambda: None)
        def __enter__(self): return self
        def __exit__(self, *_): return False
    monkeypatch.setattr(replay, "PostgresRepository", lambda **_: Repo())
    monkeypatch.setattr(replay, "pending_replay_chain", lambda _: tuple(pending))
    def run_daily(*, trade_date, apply):
        assert apply is True
        applied.append(trade_date)
        pending.pop(0)
        return {"core_status": "ACTIVATED", "trade_date": trade_date.isoformat(),
                "planned_revision": len(applied) + 1}
    monkeypatch.setattr(replay, "run_daily", run_daily)
    monkeypatch.setattr(replay, "ROOT", tmp_path)

    result = replay.replay_chain(apply=True)
    assert applied == [date(2026, 9, 22), date(2026, 9, 23)]
    assert result["status"] == "PASS"
    assert result["remaining_replay_dates"] == []
    from pathlib import Path
    assert Path(result["receipt_path"]).is_file()
