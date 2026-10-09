"""Synthetic namespace regression; not publication/source acceptance."""
from workbench_service.operational_daily_server_v1 import successor_control
import pytest


def test_context_rejects_explicit_stale_token_before_any_source_read():
    from workbench_service.operational_successor_bff_v1 import OperationalSuccessorBFFV1
    class API:token='current'
    bff=OperationalSuccessorBFFV1(API(),None)
    with pytest.raises(ValueError,match='CONTEXT_TOKEN_MISMATCH'):
        bff.get('/api/v4/context',{'context_token':'old'})

def test_new_date_never_relabels_old_pit_permissions():
    class API:
        token='new'
        candidate={'observed_at':'2026-10-09T19:00:00+08:00'}
        def context(self):return dict(accepted_trade_date='2026-10-09',context_token='new',membership_observed_at='2026-10-09T09:00:00+08:00')
    old=dict(context={'accepted_trade_date':'2026-09-30'},context_token='old',production_permission={'state':False,'focus':False})
    result=successor_control(API(),old)
    assert result['accepted_trade_date']=='2026-10-09'
    assert result['legacy_strict_pit_context']['accepted_trade_date']=='2026-09-30'
    assert result['strict_pit_context_token']=='old' and result['context_token']=='new'
    assert result['production_permission']=={'state':False,'focus':False}
    assert result['control_date_source']=='USER_AUTHORIZED_OPERATIONAL_HEAD'
    assert result['data_updated_at']=='2026-10-09T19:00:00+08:00'
    assert old['context']=={'accepted_trade_date':'2026-09-30'}
