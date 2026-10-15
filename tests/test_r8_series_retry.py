import hashlib
import json
from contextlib import contextmanager

import pytest

from workbench_db import v4_series_pg_r1 as series
from workbench_service.current_v4_context import canonical


def existing(tmp_path,monkeypatch):
    path=(tmp_path/'series.pg.json').resolve();day='2026-10-14';digest='a'*64
    bar=dict(trade_date=day,close=10,volume=100)
    descriptor=dict(series_contract_id=series.CONTRACT,T0=day,source_digest=digest,
        release_id=hashlib.sha256((digest+':'+day+':'+str(path)).encode()).hexdigest(),bar_count=1,symbol_count=1)
    path.write_text(json.dumps(descriptor));original=path.read_bytes();verified=[]
    class Reader:
        def execute(self,query):return self
        def fetchall(self):return [('one',day,canonical(bar).decode())]
    @contextmanager
    def read(value):
        verified.append(value);yield Reader()
    monkeypatch.setattr(series,'verified_series_read',read)
    monkeypatch.setattr(series,'Builder',lambda *args,**kwargs:pytest.fail('retry must not create/write a PG builder'))
    return path,day,digest,bar,descriptor,original,verified


def test_exact_retry_verifies_database_content_and_leaves_descriptor_unchanged(tmp_path,monkeypatch):
    path,day,digest,bar,descriptor,original,verified=existing(tmp_path,monkeypatch)
    assert series.build(tmp_path,path,[('one',day,bar)],t0=day,source_digest=digest)==descriptor
    assert verified==[descriptor] and path.read_bytes()==original


@pytest.mark.parametrize('kind',['source','bar','missing','duplicate','future'])
def test_retry_rejects_changed_source_or_rows_without_rewriting(tmp_path,monkeypatch,kind):
    path,day,digest,bar,descriptor,original,verified=existing(tmp_path,monkeypatch)
    rows=[('one',day,bar)]
    if kind=='source':digest='b'*64
    elif kind=='bar':rows=[('one',day,dict(bar,close=11))]
    elif kind=='missing':rows=[]
    elif kind=='duplicate':rows*=2
    else:rows=[('one','2026-10-15',dict(bar,trade_date='2026-10-15'))]
    with pytest.raises(ValueError):series.build(tmp_path,path,rows,t0=day,source_digest=digest)
    assert path.read_bytes()==original
