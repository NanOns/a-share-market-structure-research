import json
import pytest
from workbench_db.v4_native import connection
from workbench_db.v4_series_pg_r1 import build,range_rows
from workbench_db.v4_journal_pg_r1 import JournalConnection,open_read


def test_series_entire_bar_content_verified(tmp_path):
    path=tmp_path/'series.pg.json'
    bar=dict(trade_date='2026-10-09',raw_ohlc=[1,2,1,2],qfq_ohlc=[1,2,1,2],amount=10,volume=5,symbol='ENGINEERING')
    descriptor=build(tmp_path,path,[('one','2026-10-09',bar)],t0='2026-10-09',source_digest='a'*64)
    assert descriptor['series_contract_id']=='V4_PG_DATED_SERIES_R2'
    assert range_rows(path,'one','2026-10-01','2026-10-09')[0][1]==bar
    with connection(descriptor['schema']) as pg:
        pg.execute('ALTER TABLE bars DISABLE TRIGGER immutable_snapshot');pg.execute("UPDATE bars SET payload='{}'")
    with pytest.raises(ValueError,match='CONTENT_IDENTITY_MISMATCH'):
        range_rows(path,'one','2026-10-01','2026-10-09')


@pytest.mark.parametrize('table',['days','day_inputs'])
def test_journal_entire_day_and_input_content_verified(tmp_path,table):
    path=tmp_path/'journal.pg.json';db=JournalConnection(path,tmp_path,'R4_R2_ENGINEERING_JOURNAL')
    try:
        db.execute('INSERT INTO days VALUES(?,?,?)',('2026-10-09','a'*64,'[]'))
        db.execute('INSERT INTO day_inputs VALUES(?,?)',('2026-10-09','{}'))
        db.execute("INSERT OR REPLACE INTO metadata VALUES('head',?)",('ONE',));db.commit()
    finally:db.close()
    descriptor=json.loads(path.read_bytes())
    with open_read(path) as reader:assert reader.execute('SELECT count(*) FROM days').fetchone()==(1,)
    with connection(descriptor['schema']) as pg:
        pg.execute('ALTER TABLE '+table+' DISABLE TRIGGER immutable_snapshot');pg.execute('DELETE FROM '+table)
    with pytest.raises(ValueError,match='CONTENT_IDENTITY_MISMATCH'):
        with open_read(path):pass
