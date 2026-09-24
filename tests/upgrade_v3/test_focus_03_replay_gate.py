from datetime import date

import pytest

from src.focus_tracker.replay import require_replay_clear


class _Cursor:
    def __init__(self, pending=None):
        self.pending = pending
        self.query = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, params):
        self.query = query
        self.params = params

    def fetchone(self):
        return self.pending


class _Connection:
    def __init__(self, pending=None):
        self.current = _Cursor(pending)

    def cursor(self):
        return self.current


class _Repository:
    schema = "workbench"

    def __init__(self, pending=None):
        self.connection = _Connection(pending)


def test_replay_gate_composes_schema_and_date_cutoff():
    repo = _Repository()

    require_replay_clear(repo, before_trade_date=date(2026, 9, 23))

    assert repo.connection.current.params == (
        "FOCUS_SOURCE_AUTHORITY_V1", date(2026, 9, 23))
    assert "focus_trade_date_heads" in str(repo.connection.current.query)


def test_replay_gate_rejects_first_pending_earlier_head():
    repo = _Repository((date(2026, 9, 22),))

    with pytest.raises(ValueError, match="2026-09-22"):
        require_replay_clear(repo, before_trade_date=date(2026, 9, 23))
