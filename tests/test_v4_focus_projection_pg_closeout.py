import gzip
import hashlib
import json
import pytest

from workbench_db import v4_focus_projection_pg_closeout as focus_pg
from workbench_db import v4_operational_owner_pg_closeout as owner_pg
from workbench_db.v4_forward_pg_r1 import canonical, digest
from workbench_service.current_v4_context import SourceInvalid


def source(root, projection):
    path = root / 'source.json.gz'
    path.write_bytes(gzip.compress(json.dumps(projection).encode()))
    return dict(path=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                bytes=path.stat().st_size)


def install_pg_shaped_store(monkeypatch, root):
    rows_by_key = {}

    def append(root_arg, fact_token, t0, domain, binding, rows):
        rows_by_key[fact_token] = rows
        return dict(contract_id=owner_pg.CONTRACT, engine='postgresql',
                    schema='v4_test', kind=domain, fact_key=fact_token,
                    payload_sha256=digest(canonical(dict(contract_id='OWNER',T0=t0,rows=rows))),
                    database_identity={'database':'test','database_oid':'1','system_identifier':'test'})

    def inline(root_arg, descriptor):
        key=descriptor['fact_key']
        raw=canonical(descriptor)
        return dict(path=f'data/v4/operational_owner_pg_closeout_r1/{descriptor["kind"]}/{digest(key.encode())}.pg.json',
                    bytes=len(raw),sha256=digest(raw),pg_descriptor=descriptor)

    def read(root_arg, binding, head_token, t0, domain, source_binding, **kwargs):
        return rows_by_key[binding['fact_token']]

    monkeypatch.setattr(focus_pg,'append_owner_fact',append)
    monkeypatch.setattr(focus_pg,'inline_descriptor',inline)
    monkeypatch.setattr(focus_pg,'read_owner_fact',read)


def test_complete_projection_roundtrip_uses_postgresql_owner_fact(tmp_path, monkeypatch):
    projection=dict(episodes=[dict(episode_id='e',AS_RECORDED=False,PIT_ELIGIBLE=False,
        observations=[dict(trade_date='2026-10-09',price_path={'metrics':{'return_close':'0.123'}})],
        outcomes=[dict(trade_date='2026-10-09',target_trade_date=None,outcome_status='PENDING',metrics=None)])],events=[])
    source_binding=source(tmp_path,projection)
    install_pg_shaped_store(monkeypatch,tmp_path)
    binding,receipt=focus_pg.build(tmp_path,source_binding,t0='2026-10-09',head_token='a'*64)
    assert receipt['whole_payload_difference']==0
    assert receipt['storage_engine']=='postgresql'
    assert binding['pg_descriptor']['engine']=='postgresql'
    assert focus_pg.read(tmp_path,binding,t0='2026-10-09',head_token='a'*64)==projection
    with pytest.raises(SourceInvalid,match='CONTEXT_MISMATCH'):
        focus_pg.read(tmp_path,binding,t0='2026-10-09',head_token='b'*64)


@pytest.mark.parametrize('field,value',[('AS_RECORDED',True),('PIT_ELIGIBLE',True)])
def test_corrected_projection_cannot_claim_pit(tmp_path,monkeypatch,field,value):
    projection=dict(episodes=[dict(episode_id='e',observations=[],outcomes=[],**{field:value})],events=[])
    source_binding=source(tmp_path,projection)
    install_pg_shaped_store(monkeypatch,tmp_path)
    with pytest.raises(SourceInvalid,match='PIT_ESCALATION'):
        focus_pg.build(tmp_path,source_binding,t0='2026-10-09',head_token='a'*64)


def test_future_settlement_rejected(tmp_path,monkeypatch):
    projection=dict(episodes=[dict(episode_id='e',observations=[],outcomes=[dict(
        trade_date='2026-10-09',target_trade_date='2026-10-12')])],events=[])
    source_binding=source(tmp_path,projection)
    install_pg_shaped_store(monkeypatch,tmp_path)
    with pytest.raises(SourceInvalid,match='FUTURE_SETTLEMENT'):
        focus_pg.build(tmp_path,source_binding,t0='2026-10-09',head_token='a'*64)
