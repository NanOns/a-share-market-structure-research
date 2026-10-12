import gzip
import json
import pytest
from workbench_analysis.focus_replay_history_r1 import read_history
from market_calendar.trading_calendar import StockTimeline
from normalize.universe_recent import qualifies_normal_universe

def test_bounded_payload_preserves_complete_timeline_and_missing_bar(tmp_path):
    source=[dict(security_id='A',bars=[dict(trade_date=day,raw_ohlc=[i]*4,amount=i)
             for i,day in enumerate(['2025-01-01','2026-09-28','2026-09-30','2026-10-09'],1)])]
    path=tmp_path/'history.jsonl.gz'
    path.write_bytes(gzip.compress(b'\n'.join(json.dumps(r).encode() for r in source)))
    window=['2026-09-28','2026-09-29','2026-09-30']
    histories,timelines=read_history(path,window)
    assert histories['A']==source[0]['bars'][1:3]
    assert timelines['A']==frozenset([20250101,20260928,20260930,20261009])
    full=StockTimeline('A',20250101,20261009,4,timelines['A'])
    qualified,evidence=qualifies_normal_universe(full,[20260928,20260929,20260930])
    assert evidence['recent_valid_bar_count']==2
    assert len(histories['A'])==2

def test_duplicate_security_is_rejected_without_silent_merge(tmp_path):
    path=tmp_path/'history.jsonl.gz'
    row=json.dumps(dict(security_id='A',bars=[])).encode()
    path.write_bytes(gzip.compress(row+b'\n'+row))
    with pytest.raises(ValueError,match='DUPLICATE_SECURITY'):read_history(path,[])
