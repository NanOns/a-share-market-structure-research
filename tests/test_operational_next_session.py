import json
from datetime import datetime
from workbench_analysis import operational_next_session_v1 as gate


def test_unfinished_session_preserves_last_good_head(tmp_path, monkeypatch):
    p = tmp_path / 'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    p.parent.mkdir(parents=True)
    raw = b'{"accepted_trade_date":"2026-10-08"}'
    p.write_bytes(raw)
    monkeypatch.setattr(gate, 'calendar', lambda root: dict(session_dates=['2026-10-08', '2026-10-09', '2026-10-12'],
                                                         binding={}, sources=[], status='FIXTURE_TEST_ONLY'))
    result = gate.next_session_gate(tmp_path, datetime.fromisoformat('2026-10-09T14:59:00+08:00'))
    assert result['status'] == 'WAIT_PROVIDER'
    assert result['last_good_trade_date'] == '2026-10-08'
    after = gate.next_session_gate(tmp_path, datetime.fromisoformat('2026-10-09T15:01:00+08:00'))
    assert after['status'] == 'BLOCKED_EXACT_REASON'
    assert after['publication_permission'] is False
    assert p.read_bytes() == raw
