"""Candidate-only v0.3 rational transport bound to immutable event-source bytes."""
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
import re
from .tdx_adjustment_v0_3 import AdjustmentFactor, ADJUSTMENT_VERSION

CONTRACT='V4_EXACT_FACTOR_TRANSPORT_R1'

@dataclass(frozen=True)
class ExactFactorTransport:
    security_id: str
    adjustment_basis_date: int
    source_digest: str
    factor: AdjustmentFactor

    def to_dict(self):
        if not re.fullmatch('[a-f0-9]{64}',self.source_digest): raise ValueError('EXACT_SOURCE_DIGEST_REQUIRED')
        if not self.security_id or self.factor.trade_date>self.adjustment_basis_date: raise ValueError('EXACT_FACTOR_IDENTITY_INVALID')
        values=self.factor.exact_coefficients()
        return dict(contract_id=CONTRACT,adjustment_version=ADJUSTMENT_VERSION,security_id=self.security_id,
            trade_date=self.factor.trade_date,adjustment_basis_date=self.adjustment_basis_date,source_digest=self.source_digest,
            coefficients={k:dict(numerator=Fraction(v).numerator,denominator=Fraction(v).denominator) for k,v in values.items()})

    @classmethod
    def from_dict(cls,value,*,security_id,source_digest,adjustment_basis_date):
        if value.get('contract_id')!=CONTRACT or value.get('adjustment_version')!=ADJUSTMENT_VERSION: raise ValueError('EXACT_TRANSPORT_CONTRACT_MISMATCH')
        if (value.get('security_id'),value.get('source_digest'),value.get('adjustment_basis_date'))!=(security_id,source_digest,adjustment_basis_date): raise ValueError('EXACT_TRANSPORT_SOURCE_MISMATCH')
        names=('qfq_mul','qfq_add','hfq_mul','hfq_add');coefficients=value.get('coefficients',{})
        if set(coefficients)!=set(names): raise ValueError('EXACT_COEFFICIENT_MISSING')
        exact=[]
        for name in names:
            cell=coefficients[name];n=cell.get('numerator');d=cell.get('denominator')
            if type(n) is not int or type(d) is not int or d<=0 or max(n.bit_length(),d.bit_length())>4096: raise ValueError('EXACT_COEFFICIENT_INVALID')
            exact.append(Fraction(n,d))
        if exact[0]<=0 or exact[2]<=0: raise ValueError('EXACT_COEFFICIENT_INVALID')
        if type(value.get('trade_date')) is not int: raise ValueError('EXACT_FACTOR_DATE_INVALID')
        with localcontext() as ctx:
            ctx.prec=40;decimals=[Decimal(v.numerator)/Decimal(v.denominator) for v in exact]
        result=cls(security_id,adjustment_basis_date,source_digest,AdjustmentFactor(value['trade_date'],*decimals,*exact))
        result.to_dict()
        return result
