"""New small real PG correction controls; old history suites are not rerun."""
from copy import deepcopy
import pytest
from workbench_db.v4_history_pg_r1 import build,read
from workbench_db.v4_history_corrections_pg_v2 import prepare
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.r43_owner_replay import ref

def fixture(root):
    bars=[dict(trade_date='2025-04-14',raw_ohlc=[10.,11.,9.,10.],qfq_ohlc=[9.77,10.32,9.67,10.13],amount=105.625,volume=123)]
    source=root/'source.json';atomic_json(root,source,dict(rows=[dict(security_id='FIXTURE',bars=bars)]))
    base=build(root,[dict(security_id='FIXTURE',bars=bars)],head_token='a'*64,t0='2026-09-28',source_digest=ref(root,source)['sha256'])
    patch=dict(security_id='FIXTURE',trade_date='2025-04-14',previous=bars[0]['qfq_ohlc'],current=[9.78,10.32,9.67,10.13])
    return base,patch,dict(old_source=ref(root,source)),bars

def test_corrected_native_history_preserves_old_version_and_raw_amount_volume(tmp_path):
    base,patch,sources,bars=fixture(tmp_path)
    descriptor=prepare(tmp_path,base,[patch],sources)
    value=read(tmp_path,descriptor,'2026-09-28','FIXTURE')
    assert value[0]['qfq_ohlc']==patch['current']
    assert {k:value[0][k] for k in ('raw_ohlc','amount','volume','trade_date')}=={k:bars[0][k] for k in ('raw_ohlc','amount','volume','trade_date')}
    assert read(tmp_path,base,'2026-09-28','FIXTURE')==bars

def test_correction_cannot_apply_to_different_actual_pg_predecessor_value(tmp_path):
    base,patch,sources,_=fixture(tmp_path);patch['previous']=[0.,0.,0.,0.]
    descriptor=prepare(tmp_path,base,[patch],sources)
    with pytest.raises(ValueError,match='PREDECESSOR_VALUE_MISMATCH'):read(tmp_path,descriptor,'2026-09-28','FIXTURE')
