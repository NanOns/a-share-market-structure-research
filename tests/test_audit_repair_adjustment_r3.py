from decimal import Decimal,localcontext
from fractions import Fraction
import random
import json
from pathlib import Path
from adjustment.tdx_adjustment_v0_3 import XrxdEvent,build_affine_factors,_round_exact_price

def oracle(price,events):
    value=Fraction(price)
    for e in events:
        value=(value*10-Fraction(e.cash_dividend_per_10)+Fraction(e.rights_price)*Fraction(e.rights_ratio_per_10))/(10+Fraction(e.bonus_transfer_per_10)+Fraction(e.rights_ratio_per_10))
    n,d=abs(value.numerator)*100,value.denominator
    q,r=divmod(n,d);q+=int(r*2>=d)
    return Decimal(('-' if value<0 else '')+f'{q//100}.{q%100:02d}')

def test_real_multi_event_tie_is_context_independent():
    events=[XrxdEvent('SH.688553',20250613,Decimal('4.63')),XrxdEvent('SH.688553',20260617,Decimal('2.00'),bonus_transfer_per_10=Decimal('4.8'))]
    for precision in (6,28,40,80):
        with localcontext() as c:
            c.prec=precision
            factor=build_affine_factors([20250414,20261009],events)[20250414]
            assert factor.qfq_price('15.13')==Decimal('9.78')
            assert factor.exact_qfq_mul*Fraction('15.13')+factor.exact_qfq_add==Fraction(391,40)

def test_signed_ties_and_non_ties():
    for value,expected in [('9.775','9.78'),('-9.775','-9.78'),('9.77499','9.77'),('-9.77499','-9.77')]:
        assert _round_exact_price(Fraction(value))==Decimal(expected)

def test_independent_chronological_multi_event_oracle():
    rng=random.Random(239)
    for case in range(250):
        events=[XrxdEvent('S',20250102+i,Decimal(rng.randrange(500))/100,Decimal(rng.randrange(1000))/100,Decimal(rng.randrange(200))/100,Decimal(rng.randrange(100))/100,i) for i in range(4)]
        factors=build_affine_factors([20250101,20250103,20250106],events)
        for day,factor in factors.items():
            raw=Decimal(rng.randrange(100,100000))/100
            assert factor.qfq_price(raw)==oracle(raw,[e for e in events if day<e.ex_day<=20250106])

def test_all_seven_stock_sixteen_frozen_counterexamples():
    root=Path(__file__).resolve().parents[1]
    source=root/'docs/audits/full_system_audit_r2_20261011_58faf74e/b2_rounding_counterexamples.json'
    rows=json.loads(source.read_bytes())['rows']
    assert len(rows)==16 and len({r['sid'] for r in rows})==7
    for row in rows:
        events=[XrxdEvent(e['security_id'],e['event_date'],Decimal(str(e['cash_dividend'])),Decimal(str(e['rights_price'])),Decimal(str(e['bonus_transfer'])),Decimal(str(e['rights_ratio'])),e['source_record_index']) for e in row['events']]
        day=int(row['trade_date'].replace('-',''))
        factor=build_affine_factors([day,20261009],events)[day]
        assert float(factor.qfq_price(str(row['raw_price'])))==row['exact_rational']
        assert factor.qfq_price(str(row['raw_price']))==oracle(str(row['raw_price']),events)
