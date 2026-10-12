"""Actual PG repeatable-read reuse, identity drift and post-scope tamper checks."""
import json
import pytest
from workbench_db.v4_series_pg_r1 import build,range_rows,verified_series_scope,verified_series_read
from workbench_db.v4_native import connection
from workbench_db import v4_snapshot_pg_r2 as snapshot

@pytest.fixture
def series(tmp_path):
    path=tmp_path/'series.pg.json'
    bar=dict(trade_date='2026-10-09',raw_ohlc=[10,12,9,11],qfq_ohlc=[10,12,9,11],amount=100,volume=10,symbol='SCOPE')
    descriptor=build(tmp_path,path,[('S','2026-10-09',bar)],t0='2026-10-09',source_digest='d'*64)
    return path,bar,descriptor

def test_one_actual_verification_per_projection_and_nested_scope(series,monkeypatch):
    path,bar,descriptor=series;calls=[];original=snapshot.verify
    def verify(pg,d):calls.append(pg.info.backend_pid);return original(pg,d)
    monkeypatch.setattr(snapshot,'verify',verify)
    with verified_series_scope():
        with verified_series_read(descriptor) as first:
            assert range_rows(path,'S','2026-10-09','2026-10-09')==[('2026-10-09',bar)]
            with verified_series_scope():
                with verified_series_read(descriptor) as nested:assert nested.pg is first.pg
        assert len(calls)==1
    assert first.pg.closed
    with verified_series_scope():assert range_rows(path,'S','2026-10-09','2026-10-09')==[('2026-10-09',bar)]
    assert len(calls)==2

def test_descriptor_drift_is_rechecked_inside_projection(series):
    path,bar,descriptor=series
    with verified_series_scope():
        assert range_rows(path,'S','2026-10-09','2026-10-09')
        path.write_text(json.dumps(dict(descriptor,bar_count=descriptor['bar_count']+1)),encoding='utf8')
        with pytest.raises(ValueError,match='DESCRIPTOR_IDENTITY_MISMATCH'):range_rows(path,'S','2026-10-09','2026-10-09')

def test_verified_snapshot_consistency_and_new_scope_tamper_rejection(series):
    path,bar,descriptor=series
    # Prepare this isolated adversarial fixture before holding an AccessShare lock.
    with connection(descriptor['schema']) as other:
        other.execute('ALTER TABLE bars DISABLE TRIGGER immutable_snapshot')
    with verified_series_scope():
        assert range_rows(path,'S','2026-10-09','2026-10-09')==[('2026-10-09',bar)]
        with connection(descriptor['schema']) as other:
            other.execute("UPDATE bars SET payload='{}'")
        assert range_rows(path,'S','2026-10-09','2026-10-09')==[('2026-10-09',bar)]
    with verified_series_scope():
        with pytest.raises(ValueError,match='CONTENT_IDENTITY_MISMATCH'):range_rows(path,'S','2026-10-09','2026-10-09')
