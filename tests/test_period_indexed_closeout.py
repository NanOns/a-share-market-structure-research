"""Whole-field equivalence against the unchanged accepted period kernel."""
from datetime import date,timedelta
import pytest
from workbench_analysis.exact_period_consumer_r3 import derive_exact_periods
from workbench_analysis.period_indexed_closeout import parent_digest_factory
from workbench_analysis.v4_12_structure_io import canonical,digest

@pytest.mark.parametrize('state',['UNKNOWN','DATA_GAP','SUSPENDED'])
@pytest.mark.parametrize('damage',[False,True])
def test_indexed_calendar_preserves_every_numeric_status_and_parent_field(state,damage):
    first=date(2026,8,31);sessions=[(first+timedelta(days=n)).isoformat() for n in range(46) if (first+timedelta(days=n)).weekday()<5]
    member={'security_id':'SEC-ENGINEERING','source_security_key':'SH.600000'}
    missing={'2026-09-03','2026-09-30','2026-10-02'}
    days=[day for day in sessions if '2026-09-01'<=day<='2026-10-09' and day not in missing]
    history=[dict(trade_date=day,raw_ohlc=[10+n,12+n,9+n,11+n],
        qfq_ohlc=None if damage and n==3 else [8+n,10+n,7+n,9+n],
        amount=1000.125+n,volume=10.0 if n%2 else 10) for n,day in enumerate(days)]
    args=(member,history,{day:state for day in missing},sessions,'2026-10-09','2026-10-31')
    original=derive_exact_periods(*args)
    optimized=derive_exact_periods(*args,indexed_calendar=True)
    assert canonical(original)==canonical(optimized)

def test_exact_parent_hash_retains_numeric_types_and_changed_values():
    fast=parent_digest_factory()
    for value in (0,0.0,False,None,'0',1,1.0):
        parent={'rows':[{'amount':value,'security_id':'SEC'}]}
        assert fast(parent)==digest(parent)
    parent={'rows':[{'amount':1}, {'amount':2}]}
    assert fast(parent)==digest(parent)
    parent['rows'][0]['amount']=3
    assert fast(parent)==digest(parent)
