from copy import deepcopy
from decimal import Decimal
from dataclasses import replace
from adjustment.tdx_adjustment_v0_3 import XrxdEvent,build_affine_factors
from adjustment.exact_factor_transport_r1 import ExactFactorTransport
import pytest

def transport():
    events=[XrxdEvent('SH.688553',20250613,Decimal('4.63')),XrxdEvent('SH.688553',20260617,Decimal('2'),bonus_transfer_per_10=Decimal('4.8'))]
    return ExactFactorTransport('SH.688553',20261009,'a'*64,build_affine_factors([20250414,20261009],events)[20250414])

def test_typed_transport_preserves_exact_tie_and_source():
    original=transport();wire=original.to_dict()
    decoded=ExactFactorTransport.from_dict(wire,security_id=original.security_id,source_digest=original.source_digest,adjustment_basis_date=original.adjustment_basis_date)
    assert decoded.factor.qfq_price('15.13')==Decimal('9.78')
    assert decoded.factor.exact_coefficients()==original.factor.exact_coefficients()
    with pytest.raises(ValueError,match='SOURCE'):ExactFactorTransport.from_dict(wire,security_id=original.security_id,source_digest='b'*64,adjustment_basis_date=original.adjustment_basis_date)

@pytest.mark.parametrize('name',['qfq_mul','qfq_add','hfq_mul','hfq_add'])
def test_missing_exact_refuses_decimal_degradation(name):
    factor=replace(transport().factor,**{'exact_'+name:None})
    with pytest.raises(ValueError,match='EXACT_COEFFICIENT_MISSING'):factor.exact_coefficients()
    method=factor.qfq_price if name.startswith('qfq') else factor.hfq_price
    with pytest.raises(ValueError,match='EXACT_COEFFICIENT_MISSING'):method('15.13')

@pytest.mark.parametrize('bad',[0,-1,True,'37'])
def test_invalid_typed_denominator_refused(bad):
    value=transport();wire=value.to_dict();wire['coefficients']['qfq_mul']['denominator']=bad
    with pytest.raises(ValueError,match='INVALID'):ExactFactorTransport.from_dict(wire,security_id=value.security_id,source_digest=value.source_digest,adjustment_basis_date=value.adjustment_basis_date)
