from decimal import Decimal as D
from validation.phase0_2b import classify, fit_ab, FIELDS

def test_cash_offset_and_multiplicative_difference():
    raw = dict(zip(FIELDS, (10, 20, 5, 15)))
    for a,b,want in [(1,-2,'BASIS_DIFFERENCE_IN_CASH_ADJUSTMENT_CHAIN'),
                     (2,0,'MULTIPLICATIVE_EVENT_CHAIN_DIFFERENCE')]:
        fit = fit_ab(raw, {f:D(v)*a+b for f,v in raw.items()})
        assert classify(1,0,fit,{'raw_match':True}) == want

def test_nonaffine_cannot_refute_local():
    fit = fit_ab(dict(zip(FIELDS,(10,20,5,15))), dict(zip(FIELDS,(9,21,4,12))))
    assert classify(1,0,fit,{'raw_match':True}) == 'EXTERNAL_NON_AFFINE_OR_DATA_INCONSISTENT'
