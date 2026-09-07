from decimal import Decimal
import numpy as np
import pandas as pd
import pytest
from normalize.phase1 import normalize, DAY_DTYPE, exact_adjust_cents, decimal_prices
from adjustment.tdx_adjustment import XrxdEvent, build_affine_factors

def test_raw_preservation_and_inferred_gap_semantics():
    rows=np.zeros(2,dtype=DAY_DTYPE); rows['date']=[20260105,20260107]
    for f in ('open','high','low','close'): rows[f]=[1000,1200]
    rows['volume']=[123,456]; rows['amount']=[1230,5472]
    table,ctx,stats=normalize('SH.600519',rows,np.array([20260105,20260106,20260107]),[])
    p=table.to_pandas()
    assert p.raw_close.iloc[0]==Decimal('10.00')
    assert p.missing_state.iloc[1]=='INFERRED_GAP'
    assert not p.is_synthetic_fill.iloc[1] and not p.tradable.iloc[1]
    assert p.raw_close.iloc[1] is None and p.adj_high.iloc[1] is None
    assert pd.isna(ctx.close.iloc[1]) and pd.isna(ctx.amount.iloc[1])
    assert p.raw_volume.iloc[0]==123

def test_negative_decimal_storage():
    assert decimal_prices([-123,123],[True,True]).to_pylist()==[Decimal('-1.23'),Decimal('1.23')]

def test_vector_rounding_matches_decimal_engine():
    rng=np.random.default_rng(42)
    for cash,bonus in [('276.73','0'),('3.05','10'),('999.99','3.17')]:
        e=XrxdEvent('SZ.000001',20260106,Decimal(cash),bonus_transfer_per_10=Decimal(bonus))
        f=build_affine_factors([20260105,20260106],[e])[20260105]
        raw=np.r_[np.arange(1,5000),rng.integers(1,200000,2000)]
        actual=exact_adjust_cents(raw,f)
        expected=np.array([int(f.qfq_price(Decimal(int(v))/100)*100) for v in raw])
        assert np.array_equal(actual,expected)

def test_future_exday_and_future_bar_excluded():
    rows=np.zeros(3,dtype=DAY_DTYPE); rows['date']=[20260105,20260106,20260107]
    for f in ('open','high','low','close'): rows[f]=1000
    e=XrxdEvent('SZ.000001',20260107,Decimal('50'))
    table,_,_=normalize('SZ.000001',rows,np.array([20260105,20260106]),[e])
    assert table['adj_close'].to_pylist()==[Decimal('10'),Decimal('10')]

def test_off_calendar_raw_preserved_but_not_in_factor_window():
    rows=np.zeros(3,dtype=DAY_DTYPE); rows['date']=[20260105,20260106,20260107]
    for f in ('open','high','low','close'): rows[f]=1000
    table,context,stats=normalize('SZ.000001',rows,np.array([20260105,20260107]),[])
    assert table.num_rows==3
    assert context.date.tolist()==[20260105,20260107]
    assert stats['off_master_calendar_count']==1
    assert table['raw_close'].to_pylist()==[Decimal('10')]*3

def test_interval_reuse_matches_full_engine_with_suspension_events():
    dates=np.array([20260105,20260106,20260109,20260112])
    rows=np.zeros(len(dates),dtype=DAY_DTYPE); rows['date']=dates
    for field in ('open','high','low','close'): rows[field]=[1011,1033,988,1107]
    events=[XrxdEvent('SZ.000001',20260107,Decimal('3.33'),bonus_transfer_per_10=Decimal('2')),
            XrxdEvent('SZ.000001',20260108,Decimal('1.77')),
            XrxdEvent('SZ.000001',20260112,rights_price=Decimal('5'),rights_ratio_per_10=Decimal('3'))]
    sessions=np.array([20260105,20260106,20260107,20260108,20260109,20260112])
    table,_,_=normalize('SZ.000001',rows,sessions,events)
    full=build_affine_factors(map(int,dates),events)
    actual=[r for r in table.to_pylist() if r['tradable']]
    for i,row in enumerate(actual):
        f=full[int(dates[i])]
        assert Decimal(row['qfq_mul'])==f.qfq_mul
        assert Decimal(row['qfq_add'])==f.qfq_add
        assert row['adj_close']==f.qfq_price(Decimal(int(rows['close'][i]))/100)
