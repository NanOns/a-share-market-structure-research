"""Real PG chunk ordering and corruption gates; no numeric acceptance claim."""
import json
import pytest
from workbench_db.v4_period_pg_r1 import prepare,read,OWNER
from workbench_db.v4_native import connection
from workbench_db.v4_forward_pg_r1 import ForwardFactStore

def test_all_rows_survive_bound_chunks_and_read_is_read_only(tmp_path,monkeypatch):
    rows=[{'sequence':i,'value':None if i%3==0 else str(i)} for i in range(2003)]
    payload=dict(contract_id=OWNER,T0='2026-09-28',domain='period_raw',head_token='head',source_bindings={},rows=rows)
    ref=prepare(tmp_path,payload,'full')
    def forbid(*args,**kwargs):raise AssertionError('Read attempted migration DDL')
    monkeypatch.setattr(ForwardFactStore,'__init__',forbid)
    assert read(tmp_path,ref,payload['T0'],payload['domain'],'head')==rows
    with pytest.raises(ValueError,match='CONTEXT_MISMATCH'):
        read(tmp_path,ref,'2026-09-29',payload['domain'],'head')
    descriptor=json.loads((tmp_path/ref['path']).read_bytes())
    with connection(descriptor['schema']) as pg:
        manifest=json.loads(pg.execute('SELECT payload FROM forward_facts WHERE fact_key=%s',(descriptor['fact_key'],)).fetchone()[0])
        assert manifest['row_count']==2003 and len(manifest['chunks'])==3
        chunk=json.loads((tmp_path/manifest['chunks'][1]['path']).read_bytes())
        pg.execute('ALTER TABLE forward_facts DISABLE TRIGGER forward_append_only')
        pg.execute("UPDATE forward_facts SET payload='{}' WHERE fact_key=%s",(chunk['fact_key'],))
        pg.execute('ALTER TABLE forward_facts ENABLE TRIGGER forward_append_only')
    with pytest.raises(ValueError,match='DIGEST_MISMATCH'):
        read(tmp_path,ref,payload['T0'],payload['domain'],'head')
