import json
import sqlite3
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
    # Build the adapter around a real SQLite price index, inject a future
    # unsupported action: it must not poison an earlier observation.
    from types import SimpleNamespace
    path = tmp_path / 'bars.sqlite'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE bars(security,day,payload)')
        for day, close in [('2026-09-28', '10'), ('2026-09-30', '11')]:
            db.execute('INSERT INTO bars VALUES(?,?,?)', ('A', day, json.dumps(dict(symbol='SH.600000',raw_ohlc=[close]*4))))
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
