from copy import deepcopy
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
import json,math,struct
import pytest
from workbench_analysis.baostock_tolerance_candidate_r2 import decompose,float32_half_ulp,number,validate_policy

ROOT=Path(__file__).resolve().parents[2]
def policy():return json.loads((ROOT/'config/baostock_binding_tolerance_policy_r2_candidate.json').read_bytes())

def test_real_matrix_and_independent_arithmetic():
    m=json.loads((ROOT/'reports/audits/A06_R2_REAL_REPRESENTATIVE_MATRIX_R2.json').read_bytes())
    assert m['matched_rows']==15634
    for k in ['SH_MAIN','SZ_MAIN','STAR','CHINEXT','HIGH_PRICE','LOW_PRICE','SUSPENSION','RESUMPTION','NEW_LISTING','NORMAL_DATE','BOUNDARY_DATE','CORPORATE_ACTION']:assert m['coverage'][k]
    for x in m['rows']:
        if x['independent_fraction_differences']:
            for field,value in x['diagnosis']['differences'].items():
                assert Fraction(Decimal(value))==Fraction(x['independent_fraction_differences'][field])
        assert x['diagnosis']['strict_binding'] is False and x['diagnosis']['tdx_core_blocked'] is False

def test_conditional_ieee_bound_independent_known_bit_formula():
    for e in [0,1,6,20,26,30]:
        value=2**e
        assert float32_half_ulp(value)==Fraction(2)**(e-24)
    assert float32_half_ulp(0)==Fraction(1,2**150)

@pytest.mark.parametrize('field',['close','volume','amount','turn'])
def test_any_empirical_percentage_or_absolute_tolerance_rejected(field):
    p=policy();p['fields'][field]['tolerance']='0.005'
    with pytest.raises(ValueError):validate_policy(p)

@pytest.mark.parametrize('change',[dict(strict_binding_allowed=True),dict(canonical_authority=dict(OHLC=True,QFQ=False)),dict(may_block_tdx_core=True),dict(acceptance='INDEPENDENTLY_ACCEPTED')])
def test_no_supplemental_self_promotion(change):
    p=policy();p.update(change)
    with pytest.raises(ValueError):validate_policy(p)

@pytest.mark.parametrize('v',['NaN','Infinity','-Infinity','garbage',None])
def test_nonfinite_numbers_rejected(v):
    with pytest.raises(ValueError):number(v)

def test_difference_causes_not_absorbed_by_tolerance():
    local=dict(source_security_key='SH.600000',trade_date='2026-09-30',close=10,volume=100,amount=1000)
    source=dict(code='sh.600000',date='2026-09-30',close='10',volume='100',amount='1000',adjustflag='3',tradestatus='1')
    assert decompose(local,source)['classification']=='EXACT_UNIT_NORMALIZED_FINGERPRINT'
    for change,expected in [(dict(code='sz.000001'),'CALENDAR_IDENTITY_MISMATCH'),(dict(date='2026-09-29'),'CALENDAR_IDENTITY_MISMATCH'),(dict(adjustflag='2'),'ADJUSTMENT_BASIS_MISMATCH'),(dict(tradestatus='0'),'SUSPENDED_NONCOMPARABLE_BAR_SEMANTICS'),(dict(volume='10000'),'TRUE_DATA_CONFLICT_OR_UNPROVEN_PROVIDER_GENERATION')]:
        assert decompose(local,dict(source,**change))['classification']==expected
    assert decompose(local,source,source_revision_same=False)['classification']=='PROVIDER_REVISION'
