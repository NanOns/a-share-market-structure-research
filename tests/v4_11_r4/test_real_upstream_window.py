from datetime import date,timedelta
from pathlib import Path
import pytest
from src.v4.confirmation_d2_upstream_r4 import derive,owner_packages
from scripts import build_v4_11_real_dag_r4b as builder

def test_core_window_basis_not_coefficient_digest():
    slots=[]
    for i in range(80):
        close=10+i/100
        slots.append(dict(date=(date(2026,6,1)+timedelta(days=i)).isoformat(),open=close,high=close+1,low=close-1,close=close,amount=100000000.,volume=1000000.,quality='READY',mul=str(1+i/100),add=str(-i/20),price_basis='TDX_NATIVE_AFFINE_QFQ',adjustment_source_revision='FROZEN_VECTOR_BASIS',has_actual_bar=True,raw_actual_bar=True,accepted_trading_status='ACTUAL_TRADED',**{'raw_'+k:close for k in ('open','high','low','close')}))
    calc=dict(security_id='VECTOR_ONLY',trade_date=slots[-1]['date'],window=slots,values={'rps5_delta3':None})
    _,evidence=derive(calc,Path(__file__).resolve().parents[2])
    ma60=evidence['core_factors']['ma60']
    assert ma60['quality_state']=='OBSERVED'
    assert ma60['value']==pytest.approx(sum(10+i/100 for i in range(20,80))/60,abs=1e-12)
    assert ma60['actual_count']==60
    assert all(r['state']=='ACTUAL' for r in evidence['observation_states'])

def test_r4b_rejects_unpassed_parity_before_target_generation(monkeypatch):
    monkeypatch.setattr(builder,'read',lambda path:dict(gate='FAIL',sealed=True))
    with pytest.raises(ValueError,match='R4A_PASS_SEALED_PREREQUISITE'):
        builder.prepare_target_facts()
