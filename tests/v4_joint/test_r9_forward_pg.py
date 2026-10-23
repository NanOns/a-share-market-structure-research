"""显式启用的共享开发 PG 回归；仅追加 v4_r9_forward_contract 测试事实。"""
import hashlib
import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from workbench_analysis.forward_r7 import make_observation_id
from workbench_db.forward_r7_store import ForwardR7Store, _configured_forward_dsn

pytestmark=pytest.mark.skipif(os.environ.get('R9_PG_E2E')!='1',reason='需显式启用 R9 开发 PG 追加测试')
SCHEMA='v4_r9_forward_contract'


def test_two_connections_out_of_order_commit_and_latest_revision(monkeypatch):
    dsn=_configured_forward_dsn(Path(__file__).resolve().parents[2])
    with psycopg.connect(dsn,connect_timeout=5) as pg:
        endpoint=pg.execute('SELECT current_database(),inet_server_port()').fetchone()
        assert endpoint==('market_research',5432)
        pg.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(sql.Identifier(SCHEMA)))
        pg.execute(sql.SQL('''CREATE TABLE IF NOT EXISTS {}.forward_facts(
            kind text NOT NULL,fact_key text NOT NULL,payload text NOT NULL,
            payload_sha256 text NOT NULL,source_sha256 text,
            ordinal bigint GENERATED ALWAYS AS IDENTITY,PRIMARY KEY(kind,fact_key))''').format(sql.Identifier(SCHEMA)))
    store=object.__new__(ForwardR7Store)
    store.root=Path(__file__).resolve().parents[2]
    store.dsn=dsn;store.schema=SCHEMA
    run=uuid4().hex
    query=sql.SQL('INSERT INTO {}.forward_facts(kind,fact_key,payload,payload_sha256) VALUES(%s,%s,%s,%s) RETURNING ordinal').format(sql.Identifier(SCHEMA))
    with psycopg.connect(dsn) as low,psycopg.connect(dsn) as high:
        low_ordinal=low.execute(query,('r9_watermark_probe',run+'-low','{}',hashlib.sha256(b'{}').hexdigest())).fetchone()[0]
        high_ordinal=high.execute(query,('r9_watermark_probe',run+'-high','{}',hashlib.sha256(b'{}').hexdigest())).fetchone()[0]
        assert low_ordinal<high_ordinal
        high.commit()
        cache={};before=store._matured_count_watermark()
        initial=store.read_matured_count(cache=cache)
        low.commit()
        after=store._matured_count_watermark()
        assert after[1]==before[1]+1 and after[2]==before[2]
        assert store.read_matured_count(cache=cache)==initial
        assert cache[('forward-r7-matured-count-v1',SCHEMA)]['watermark']==after
    row=dict(rule_id='SYNTHETIC_R9',rule_version='1.0.0',T0='2026-03-03',entity_type='STOCK',
        entity_id='SYN-'+run,status='MATCH',evidence_lane='RETROSPECTIVE_RESEARCH',
        evidence_class='RETROSPECTIVE_RESEARCH',capture_revision=1,revision=1,source_digest='a'*64,values={'close':10.0})
    observation=make_observation_id(row)
    daily=dict(identity_contract='V4_FORWARD_OBSERVATION_ID_R2',lane='RETROSPECTIVE_RESEARCH',rows=[row])
    def append(kind,key,payload):
        with store._connect() as pg:store._append_fact(pg,kind,run+key,payload)
    def schedule(revision,state):
        return dict(identity_contract='V4_FORWARD_SETTLEMENT_R2',lane='RETROSPECTIVE_RESEARCH',revision=revision,
                    items=[dict(observation_id=observation,horizon_sessions=1,due_date='2026-03-04',
                        schedule_status=state,settlement_revision=revision,
                        settlement={'status':state,'nominal_return':0.05 if state=='SETTLED' else None})])
    append('r7_daily_universe','-daily-1',daily)
    append('r7_settlement_schedule','-settlement-1',schedule(1,'SETTLED'))
    assert store.read_matured_count()==initial+1
    append('r7_settlement_schedule','-settlement-2',schedule(2,'SOURCE_GAP'))
    assert store.read_matured_count()==initial
    assert sum(item['count'] for item in store.read_settlement()['counts'] if item['status']=='SETTLED')==initial
    append('r7_settlement_schedule','-settlement-3',schedule(3,'SETTLED'))
    assert store.read_matured_count()==initial+1
    original=store._read_facts
    changed=[]
    def read_and_commit_new_capture(kind):
        rows=original(kind)
        if kind=='r7_daily_universe' and not changed:
            changed.append(True)
            newer=dict(row,capture_revision=2,revision=2,source_digest='b'*64)
            append('r7_daily_universe','-daily-2',dict(daily,rows=[newer]))
        return rows
    monkeypatch.setattr(store,'_read_facts',read_and_commit_new_capture)
    # A commit between the two reads cannot mix observation/settlement snapshots.
    assert store.read_matured_count()==initial+1
    monkeypatch.setattr(store,'_read_facts',original)
    assert store.read_matured_count()==initial
    with ThreadPoolExecutor(max_workers=3) as workers:
        assert list(workers.map(lambda _:store.read_matured_count(),range(6)))==[initial]*6
