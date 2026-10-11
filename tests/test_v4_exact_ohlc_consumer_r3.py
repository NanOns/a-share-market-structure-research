from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
from fractions import Fraction
import pytest
from adjustment.exact_factor_transport_r1 import ExactFactorTransport
from adjustment.exact_ohlc_consumer_r1 import consume_exact_ohlc
from adjustment.tdx_adjustment_v0_3 import XrxdEvent,build_affine_factors

SOURCE=b'isolated event bytes: dividend 4.63 and 2; bonus 4.8'
SID='SH.688553'
DATES=[20250414,20261009]

def fixture():
    events=[XrxdEvent(SID,20250613,Decimal('4.63')),
            XrxdEvent(SID,20260617,Decimal('2'),bonus_transfer_per_10=Decimal('4.8'))]
    factor=build_affine_factors(DATES,events)[DATES[0]]
    wire=ExactFactorTransport(SID,DATES[1],sha256(SOURCE).hexdigest(),factor).to_dict()
    row=dict(security_id=SID,trade_date=DATES[0],open='15.13',high='16',low='14',close='15.13')
    return row,wire

def consume(row,wire,source=SOURCE):
    return consume_exact_ohlc(row,wire,source_bytes=source,security_id=SID,basis_date=DATES[1])

def test_real_row_consumer_independent_decimal_oracle():
    row,wire=fixture();result=consume(row,wire)
    # Independent chronological event-price composition, integer cents HALF_UP.
    for field,raw in ((name,row[name]) for name in ('open','high','low','close')):
        p=(Decimal(raw)-Decimal('0.463')-Decimal('0.2'))/Decimal('1.48')
        assert result['prices'][field]==str(p.quantize(Decimal('.01'),rounding='ROUND_HALF_UP'))
    assert result['prices']['close']=='9.78'
    assert not result['PIT_ELIGIBLE'] and result['authority']=='ISOLATED_CANDIDATE_ONLY'

@pytest.mark.parametrize('field',['qfq_mul','qfq_add','hfq_mul','hfq_add'])
def test_missing_exact_never_reconstructed_from_decimal(field):
    row,wire=fixture();del wire['coefficients'][field]
    with pytest.raises(ValueError,match='EXACT_COEFFICIENT_MISSING'):consume(row,wire)

@pytest.mark.parametrize('bad',[None,[],{},True,'0'])
def test_invalid_coefficient_shapes_failclosed(bad):
    row,wire=fixture();wire['coefficients']['qfq_mul']=bad
    with pytest.raises(ValueError,match='EXACT_COEFFICIENT_INVALID'):consume(row,wire)

@pytest.mark.parametrize('date',[True,20250230,20261301,0,'20250414'])
def test_invalid_wire_date_failclosed(date):
    row,wire=fixture();wire['trade_date']=date
    with pytest.raises(ValueError,match='EXACT_FACTOR_DATE_INVALID'):consume(row,wire)

def test_source_and_row_identity_failclosed():
    row,wire=fixture()
    with pytest.raises(ValueError,match='SOURCE_MISMATCH'):consume(row,wire,b'changed event bytes')
    row['trade_date']=20250415
    with pytest.raises(ValueError,match='ROW_IDENTITY'):consume(row,wire)

@pytest.mark.parametrize('price',[15.13,'NaN','Infinity','0','-1'])
def test_raw_source_precision_or_price_invalid(price):
    row,wire=fixture();row['close']=price
    with pytest.raises(ValueError,match='RAW_PRICE_INVALID'):consume(row,wire)

def test_future_factor_and_negative_multiplier_failclosed():
    row,wire=fixture();wire['trade_date']=20261012
    with pytest.raises(ValueError,match='IDENTITY_INVALID'):consume(row,wire)
    row,wire=fixture();wire['coefficients']['qfq_mul']['numerator']=-1
    with pytest.raises(ValueError,match='COEFFICIENT_INVALID'):consume(row,wire)

def test_bad_ohlc_and_nonpositive_quality():
    row,wire=fixture();row['high']='1'
    with pytest.raises(ValueError,match='RAW_OHLC_INVALID'):consume(row,wire)
    row,wire=fixture();row.update(open='.1',high='.1',low='.1',close='.1')
    assert consume(row,wire)['quality']=='NONPOSITIVE_QFQ'
