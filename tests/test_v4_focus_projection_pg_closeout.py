import gzip
import hashlib
import json
import pytest
from workbench_db.v4_focus_projection_pg_closeout import build,read
from workbench_service.current_v4_context import SourceInvalid

def source(root,projection):
    path=root/'source.json.gz'
    path.write_bytes(gzip.compress(json.dumps(projection).encode()))
    return dict(path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)

def test_complete_projection_roundtrip_and_context_rejection(tmp_path):
    projection=dict(episodes=[dict(episode_id='e',AS_RECORDED=False,PIT_ELIGIBLE=False,
        observations=[dict(trade_date='2026-10-09',price_path={'metrics':{'return_close':'0.123'}})],
        outcomes=[dict(trade_date='2026-10-09',target_trade_date=None,outcome_status='PENDING',metrics=None)])],events=[])
    binding,receipt=build(tmp_path,source(tmp_path,projection),t0='2026-10-09',head_token='a'*64)
    assert receipt['whole_payload_difference']==0
    assert read(tmp_path,binding,t0='2026-10-09',head_token='a'*64)==projection
    with pytest.raises(SourceInvalid,match='CONTEXT_MISMATCH'):
        read(tmp_path,binding,t0='2026-10-09',head_token='b'*64)

@pytest.mark.parametrize('field,value',[('AS_RECORDED',True),('PIT_ELIGIBLE',True)])
def test_corrected_projection_cannot_claim_pit(tmp_path,field,value):
    projection=dict(episodes=[dict(episode_id='e',observations=[],outcomes=[],**{field:value})],events=[])
    with pytest.raises(SourceInvalid,match='PIT_ESCALATION'):
        build(tmp_path,source(tmp_path,projection),t0='2026-10-09',head_token='a'*64)

def test_future_settlement_rejected(tmp_path):
    projection=dict(episodes=[dict(episode_id='e',observations=[],outcomes=[dict(trade_date='2026-10-09',target_trade_date='2026-10-12')])],events=[])
    with pytest.raises(SourceInvalid,match='FUTURE_SETTLEMENT'):
        build(tmp_path,source(tmp_path,projection),t0='2026-10-09',head_token='a'*64)
