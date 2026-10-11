from copy import deepcopy
import hashlib
import json
import subprocess
import types
from pathlib import Path
import psycopg
import pytest
from psycopg import sql
from workbench_db.v4_history_pg_r1 import build,read
from workbench_db.v4_native import connection
from workbench_db.v4_snapshot_pg_r1 import Builder,read as read_snapshot
from workbench_db.v4_series_pg_r1 import build as build_series,range_rows

def bar(day='2026-10-08',prices=None):
    return dict(trade_date=day,raw_ohlc=prices or [1,2,1,2],qfq_ohlc=prices or [1,2,1,2],amount=10,volume=5,symbol='SH.600000')

def test_history_idempotency_context_and_immutability(tmp_path):
    rows=[dict(security_id='S1',bars=[bar()])]
    binding=build(tmp_path,rows,head_token='a'*64,t0='2026-10-09',source_digest='b'*64)
    assert build(tmp_path,rows,head_token='a'*64,t0='2026-10-09',source_digest='b'*64)==binding
    assert read(tmp_path,binding,'2026-10-09','S1')==rows[0]['bars']
    assert read(tmp_path,binding,'2026-10-09','missing') is None
    with pytest.raises(ValueError,match='CONTEXT'):read(tmp_path,binding,'2026-10-08','S1')
    changed=deepcopy(binding);changed['head_token']='c'*64
    with pytest.raises(ValueError,match='IDENTITY'):read(tmp_path,changed,'2026-10-09','S1')
    with pytest.raises(psycopg.Error,match='IMMUTABLE'):
        with connection(binding['schema']) as pg:pg.execute('UPDATE history SET payload=%s',('{}',))
    with pytest.raises(psycopg.Error,match='IMMUTABLE'):
        with connection(binding['schema']) as pg:pg.execute('INSERT INTO history VALUES(%s,%s,%s)',(binding['version'],'new','[]'))
    with pytest.raises(ValueError,match='CONFLICT'):build(tmp_path,[dict(security_id='S1',bars=[bar(prices=[2,3,2,3])])],head_token='a'*64,t0='2026-10-09',source_digest='b'*64)

def test_history_rejects_future_and_non_pg(tmp_path):
    with pytest.raises(ValueError,match='FUTURE'):build(tmp_path,[dict(security_id='S',bars=[bar('2026-10-10')])],head_token='a'*64,t0='2026-10-09',source_digest='b'*64)
    with pytest.raises(ValueError,match='NO_FALLBACK'):read(tmp_path,dict(engine='sqlite3'),'2026-10-09','S')

def test_snapshot_native_sql_json_and_immutable_read(tmp_path):
    db=Builder(tmp_path,'snapshot-test')
    try:
        db.executescript('CREATE TABLE objects(domain text,id text,name text,symbol text,state text,payload text,PRIMARY KEY(domain,id));CREATE TABLE aliases(alias text,id text,PRIMARY KEY(alias,id));CREATE TABLE members(sector text,security text,PRIMARY KEY(sector,security));CREATE TABLE metadata(key text PRIMARY KEY,value text);')
        for ident,value in [('one',2),('two',10),('unknown',None)]:
            db.execute('INSERT INTO objects VALUES(?,?,?,?,?,?)',('stocks',ident,'股票','SH.600000','UNKNOWN',json.dumps(dict(fields=dict(close=dict(value=value))))))
        db.executemany('INSERT OR IGNORE INTO aliases VALUES(?,?)',[('one','one'),('one','one')])
        meta=dict(release_id='snapshot-test',context=dict(accepted_trade_date='2026-10-09'))
        descriptor=db.seal(meta);db.commit()
    finally:db.close()
    with read_snapshot(descriptor) as reader:
        rows=reader.execute("SELECT id FROM objects ORDER BY (json_extract(payload,'$.fields.close.value'))::numeric ASC NULLS FIRST,id").fetchall()
        assert rows==[('unknown',),('one',),('two',)]
        assert reader.execute('SELECT count(*) FROM aliases').fetchone()[0]==1
    with pytest.raises(psycopg.Error,match='IMMUTABLE'):
        with connection(descriptor['schema']) as pg:pg.execute('DELETE FROM objects')
    with pytest.raises(ValueError,match='IDENTITY'):
        with read_snapshot(dict(descriptor,logical_digest='0'*64)):pass

def test_series_date_order_focus_forward_contract(tmp_path):
    path=tmp_path/'series.pg.json'
    rows=[('S','2026-10-09',bar('2026-10-09')),('S','2026-10-08',bar())]
    binding=build_series(tmp_path,path,rows,t0='2026-10-09',source_digest='c'*64)
    assert [r[0] for r in range_rows(path,'S','2026-10-08','2026-10-09')]==['2026-10-08','2026-10-09']
    with pytest.raises(ValueError,match='CONTEXT'):range_rows(path,'S','2026-10-08','2026-10-10')
    with pytest.raises(psycopg.Error,match='IMMUTABLE'):
        with connection(binding['schema']) as pg:pg.execute("INSERT INTO bars VALUES('S','2026-10-07','{}')")

@pytest.mark.parametrize('suffix,text',[
    ('.md','中文\r\nSH.600000\nSEC-0123456789ABCDEF\nSZ.000001'),
    ('.sql',"CASE security_id WHEN '600000' THEN 1 END\r\nstock_code IN ('000001')\nSH.600000"),
    ('.json','{"security_codes":[600000,"000001"],"a":"SH.600000"}'),
    ('.yaml','\n'.join(['中文 SH.600000 SEC-0123456789ABCDEF']*10000)),
    ('.md','SH.600000'),('.md','\nSH.600000\r\nSZ.000001\n'),
],ids=['unicode_crlf_md','sql_filters','json_identifiers','dense_yaml_10000','boundary_zero','boundary_newlines'])
def test_scanner_complete_frozen_oracle(tmp_path,suffix,text):
    from scripts import scan_no_symbol_specific_runtime_logic as current
    root=Path(__file__).resolve().parents[1]
    source=subprocess.check_output(['git','show','fbd23a6b:scripts/scan_no_symbol_specific_runtime_logic.py'],cwd=root)
    old=types.ModuleType('frozen_scanner');exec(compile(source,'frozen_scanner','exec'),old.__dict__)
    p=tmp_path/('case'+suffix);p.write_bytes(text.encode())
    assert current.scan_file(p,root=tmp_path,category='EVIDENCE')==old.scan_file(p,root=tmp_path,category='EVIDENCE')
