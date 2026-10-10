"""Explicit negative fixtures, separate from real-owner acceptance."""
from pathlib import Path
from types import SimpleNamespace
import json,sqlite3
import pytest
from workbench_service.core_product_bff_r1 import CoreProductBFFR1

class ChartFixture(CoreProductBFFR1):
    def envelope(self,day,**payload):return dict(context={'trade_date':day},**payload)
    def pack(self,day):return self.manifest,{}
    def source(self,domain,day):return [{'security_id':'SEC-X','period_type':'WEEKLY','period_status':'CLOSED_ONLY_READY','calendar_count':2,'suspended_count':0}]

def fixture_bff(tmp_path,bars):
    dbpath=tmp_path/'history.sqlite'
    with sqlite3.connect(dbpath) as db:
        db.execute('CREATE TABLE history(security TEXT,payload TEXT)')
        db.execute('INSERT INTO history VALUES (?,?)',('SEC-X',json.dumps(bars)))
    bff=ChartFixture(SimpleNamespace(root=tmp_path,candidate={'owners':{'2026-10-09':{'period_raw':{'sha256':'fixture'},'period_adjusted':{'sha256':'fixture'}}}}),None)
    bff.manifest={'history_index':{'path':'history.sqlite'},'source_bindings':{'history':{'sha256':'fixture'}}}
    return bff

def bar(day,prices,amount=100,volume=10):
    return dict(trade_date=day,raw_ohlc=prices,qfq_ohlc=prices,amount=amount,volume=volume)

def test_week_end_uses_formal_owner_not_always_forming(tmp_path):
    bff=fixture_bff(tmp_path,[bar('2026-10-08',[10,12,9,11]),bar('2026-10-09',[11,13,10,12])])
    _,data=bff.chart('2026-10-09','SEC-X',{'period':'W','price_basis':'RAW'})
    last=data['items'][-1]
    assert (last['open'],last['high'],last['low'],last['close'],last['volume'],last['amount'])==(10,13,9,12,20,200)
    assert last['period_status']=='CLOSED_ONLY_READY'

def test_future_bar_fails_closed(tmp_path):
    bff=fixture_bff(tmp_path,[bar('2026-10-12',[10,11,9,10])])
    with pytest.raises(ValueError,match='FUTURE_CHART_BAR'):bff.chart('2026-10-09','SEC-X',{})

def test_unknown_adjustment_does_not_draw_fake_price(tmp_path):
    bff=fixture_bff(tmp_path,[bar('2026-10-09',None)])
    _,data=bff.chart('2026-10-09','SEC-X',{'price_basis':'QFQ'})
    assert data['items'][0]['close'] is None
    assert data['items'][0]['quality']=='UNKNOWN'

def test_negative_chart_paging_rejected(tmp_path):
    bff=fixture_bff(tmp_path,[bar('2026-10-09',[10,11,9,10])])
    with pytest.raises(ValueError,match='INVALID_QUERY_BOUND'):bff.chart('2026-10-09','SEC-X',{'offset':-1})
