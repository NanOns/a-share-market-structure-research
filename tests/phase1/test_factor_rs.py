import pandas as pd
import numpy as np
import pytest
from factors.engine import add_rs

def test_universe_and_same_date_only():
    rows=[]
    for date,n in [(1,101),(2,99)]:
        for i in range(n+1):
            r={'date':date,'universe_status':'IN_NORMAL_UNIVERSE' if i<n else 'OUTSIDE_NORMAL_UNIVERSE'}
            for k in (5,10,20,60):
                r.update({f'RET{k}':i/100 if i<n else 999,f'RET{k}__valid_sample_count':k+1,f'RET{k}__quality_flag':'OK'})
            rows.append(r)
    out=add_rs(pd.DataFrame(rows))
    assert out.loc[0,'RS5']==pytest.approx(-.5)
    assert out.loc[0,'rs_valid_universe_count_5']==101
    assert out.loc[out.date==2,'RS5'].isna().all()

def test_null_returns_do_not_enter_benchmark():
    rows=[]
    for i in range(100):
        r={'date':1,'universe_status':'IN_NORMAL_UNIVERSE'}
        for n in (5,10,20,60): r.update({f'RET{n}':np.nan if i==0 else .1,f'RET{n}__valid_sample_count':n+1,f'RET{n}__quality_flag':'OK'})
        rows.append(r)
    out=add_rs(pd.DataFrame(rows))
    assert out.RS5.isna().all()
    assert (out.rs_valid_universe_count_5==99).all()
