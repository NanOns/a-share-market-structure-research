from copy import deepcopy
from dataclasses import asdict
import math
import pytest
from src.v4.adjustment_basis_r4 import admission,basis_id,observations
from src.v4.factors.core import compute_core

def bar(day='2026-09-24',**changes):
    row=dict(date=day,open=10.,high=12.,low=9.,close=11.,amount=100.,volume=10.,raw_actual_bar=True,price_basis='TDX_NATIVE_AFFINE_QFQ',adjustment_source_revision='accepted-source',quality='READY',mul='1',add='0',accepted_source_digest='source')
    row.update(changes);return row

def oracle(row,target):
    # Deliberately independent; do not import adapter admission helpers here.
    if row.get('quality')!='READY' or not row.get('price_basis') or not row.get('adjustment_source_revision'):return 'ADJUSTMENT_UNKNOWN'
    if not target.get('price_basis') or not target.get('adjustment_source_revision') or target.get('quality')!='READY':return 'ADJUSTMENT_UNKNOWN'
    if (row['price_basis'],row['adjustment_source_revision'])!=(target['price_basis'],target['adjustment_source_revision']):return 'MIXED_ADJUSTMENT_IDENTITY'
    return None

@pytest.mark.parametrize('changes,expected',[
    ({'mul':'2','add':'-3'},None),({'price_basis':'other'},'MIXED_ADJUSTMENT_IDENTITY'),
    ({'adjustment_source_revision':'other'},'MIXED_ADJUSTMENT_IDENTITY'),
    ({'adjustment_source_revision':None},'ADJUSTMENT_UNKNOWN'),({'quality':'UNKNOWN'},'ADJUSTMENT_UNKNOWN')])
def test_independent_admission(changes,expected):
    target=bar();row=bar(**changes)
    assert oracle(row,target)==expected==admission(row,target)

def history(mixed=False,gap=False):
    slots=[bar(f'2026-09-{d:02d}',mul=str(d),add=str(-d),close=float(d)) for d in range(1,9)]
    states={('stock',r['date']):'ACTUAL_TRADED' for r in slots}
    states['stock','2026-09-06']='SUSPENDED'
    slots[5]=dict(date='2026-09-06',raw_actual_bar=False)
    if mixed:slots[3]['adjustment_source_revision']='other'
    if gap:states['stock','2026-09-06']='UNKNOWN'
    return observations(slots,'stock',states)

def test_confirmed_suspension_crossing_accepted_rule():
    result=compute_core(history(),'stock')
    assert result['ma5'].value==(3+4+5+7+8)/5
    assert result['ma5'].suspended_count==1
    assert result['ret5'].value==8/3-1

def test_unexplained_gap_fails_closed():
    assert compute_core(history(gap=True),'stock')['ma5'].unknown_reason=='UNEXPLAINED_DATA_GAP'

def test_actual_basis_change_unknown():
    assert compute_core(history(mixed=True),'stock')['ma5'].unknown_reason=='MIXED_ADJUSTMENT_IDENTITY'

def test_affine_evidence_not_basis():
    assert basis_id(bar(mul='3',add='-2'))==basis_id(bar())
