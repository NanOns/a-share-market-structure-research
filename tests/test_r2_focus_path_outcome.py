import json
from datetime import date
from decimal import Decimal

import pytest

from focus_tracker.v4_path_adapter import AcceptedPaths, enriched_project
from focus_tracker.v4_journal import append
from workbench_service.current_v4_context import SourceInvalid, digest


class Paths:
    calendar = ['2026-09-28', '2026-09-29', '2026-09-30']

    def path(self, sid, start, end):
        return dict(quality='READY', metrics=dict(return_close='0.1', drawdown_current='0', mfe='0.1'),
                    close='11', anchor_actual_bar=True, target_state='BAR')


def row(day, pre='TRUE', validity='UNKNOWN'):
    return dict(entity_id='A', trade_date=day, raw_qualification=dict(PREWATCH=pre, CONFIRMED='FALSE'),
                publication_id=day, validity=validity)


def test_exit_followup_due_settlement_and_reentry_are_separate():
    days = {d: [row(d, pre)] for d, pre in zip(Paths.calendar, ['TRUE', 'FALSE', 'TRUE'])}
    projection = enriched_project(days, Paths())
    first, second = projection['episodes']
    assert second['parent_episode_id'] == first['episode_id']
    assert first['observations'][-1]['event'] == 'POST_EXIT_OBSERVATION'
    assert first['observations'][-1]['trade_date'] == '2026-09-30'
    assert first['outcomes'][0]['outcome_status'] == 'OBSERVED'
    assert first['outcomes'][1]['outcome_status'] == 'PENDING'
    assert first['observations'][0]['path_state'] is None
    assert first['observations'][0]['best_confirmed_state'] == 'WAIT_CONFIRMATION'
    assert first['observations'][0]['path_resolution'] == 'PARTIAL'
    assert second['outcomes'][0]['outcome_status'] == 'PENDING'


def test_invalidated_episode_closes_and_settles_independently():
    days = {d: [row(d, validity='INVALID' if i == 1 else 'UNKNOWN')] for i, d in enumerate(Paths.calendar)}
    projection = enriched_project(days, Paths())
    first = projection['episodes'][0]
    assert first['end_date'] == '2026-09-29'
    assert first['observations'][1]['path_state'] == 'STRUCTURE_DAMAGED'
    assert any(a['kind'] == 'INVALIDATION' for a in first['anchors'])
    assert first['outcomes'][0]['outcome_status'] == 'OBSERVED'


def test_missing_suspension_and_future_corporate_action(tmp_path, monkeypatch):
    # Build the adapter around a real native PG price index, inject a future
    # unsupported action: it must not poison an earlier observation.
    from types import SimpleNamespace
    from workbench_db.v4_series_pg_r1 import build
    path = tmp_path / 'bars.pg.json'
    build(tmp_path,path,(("A",day,dict(trade_date=day,symbol='SH.600000',raw_ohlc=[close]*4))
                        for day,close in [('2026-09-28','10'),('2026-09-30','11')]),
          t0='2026-09-30',source_digest=digest(b'R2_PATH_FROZEN_TEST_BARS'))
    p = AcceptedPaths.__new__(AcceptedPaths)
    p.series=path;p.calendar=Paths.calendar;p.bindings={};p.cache={};p.status={}
    from collections import defaultdict
    p.events=defaultdict(list, {'SH.600000':[SimpleNamespace(event_date=20261009,category=99)]})
    p.dispositions={}
    assert p.path('A','2026-09-28','2026-09-30')['quality']=='DATA_UNAVAILABLE'
    p.cache={};p.status={'2026-09-29':{'A':dict(status='SUSPENDED',actual_bar_present=False,status_conflict=False)}}
    fact=p.path('A','2026-09-28','2026-09-30')
    assert fact['quality']=='READY'
    assert Decimal(fact['metrics']['return_close'])==Decimal('0.1')
    assert fact['suspended_dates']==['2026-09-29']
    p.cache={};p.events['SH.600000'][0].event_date=20260930
    assert p.path('A','2026-09-28','2026-09-30')['quality']=='DATA_UNAVAILABLE'


def test_accepted_path_normalizes_legacy_stable_id_in_memory():
    from focus_tracker.v4_path_adapter import _resolve_series_identity
    bars={'2026-09-28':dict(symbol='SEC-A'),'2026-09-30':dict(symbol='SH.600000')}
    assert _resolve_series_identity(bars,'SEC-A','SH.600000')=='SH.600000'
    assert [row['symbol'] for row in bars.values()]==['SH.600000','SH.600000']
    with pytest.raises(SourceInvalid,match='IDENTITY_MISMATCH'):
        _resolve_series_identity({'2026-09-28':dict(symbol='SZ.000001')},'SEC-A','SH.600000')


def test_dated_owner_updates_preserve_history_and_reject_kernel_change(tmp_path,monkeypatch):
    class Dated(Paths):
        def __init__(self,root,inputs):self.inputs=inputs
        def path(self,sid,start,end):
            result=super().path(sid,start,end)
            result['metrics']['return_close']=self.inputs['owner']
            return result
    monkeypatch.setattr('focus_tracker.v4_path_adapter.AcceptedPaths',Dated)
    bindings=[]
    for day in Paths.calendar:
        path=tmp_path/(day+'.json');path.write_text(json.dumps({'rows':[row(day)]}))
        bindings.append(dict(path=path.name,sha256=digest(path.read_bytes())))
    journal=tmp_path/'journal.pg.json'
    inputs=dict(owner='0.1',implementation={'kernel':{'sha256':'old'}})
    first=append(journal,tmp_path,bindings[0],None,path_inputs=inputs)
    updated=dict(owner='0.2',implementation=inputs['implementation'])
    second=append(journal,tmp_path,bindings[1],first['head'],path_inputs=updated)
    from workbench_db.v4_journal_pg_r1 import open_read
    with open_read(journal) as db:
        projection=json.loads(db.execute("SELECT value FROM metadata WHERE key='projection'").fetchone()[0])
    observations=projection['episodes'][0]['observations']
    assert observations[0]['price_path']['metrics']['return_close']=='0.1'
    assert observations[1]['price_path']['metrics']['return_close']=='0.2'
    with pytest.raises(SourceInvalid,match='DAY_INPUT_REVISION'):
        append(journal,tmp_path,bindings[1],second['head'],path_inputs=inputs)
    with pytest.raises(SourceInvalid,match='KERNEL_UPGRADE'):
        append(journal,tmp_path,bindings[2],second['head'],path_inputs=dict(owner='0.3',implementation={'kernel':{'sha256':'new'}}))
