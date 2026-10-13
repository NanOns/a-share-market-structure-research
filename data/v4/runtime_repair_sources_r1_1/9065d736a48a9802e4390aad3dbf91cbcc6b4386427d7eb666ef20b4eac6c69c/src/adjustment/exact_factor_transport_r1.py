"""Candidate-only v0.3 rational transport bound to immutable event-source bytes."""
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from datetime import datetime
import re
from .tdx_adjustment_v0_3 import AdjustmentFactor, ADJUSTMENT_VERSION

CONTRACT='V4_EXACT_FACTOR_TRANSPORT_R1'

def _identity(security_id, source_digest, basis_date, trade_date):
    if not isinstance(source_digest,str) or not re.fullmatch('[a-f0-9]{64}',source_digest):
        raise ValueError('EXACT_SOURCE_DIGEST_REQUIRED')
    if not isinstance(security_id,str) or not re.fullmatch(r'(SH|SZ|BJ)\.[0-9]{6}',security_id):
        raise ValueError('EXACT_FACTOR_IDENTITY_INVALID')
    for date in (basis_date,trade_date):
        if type(date) is not int or not 10000101<=date<=99991231:
            raise ValueError('EXACT_FACTOR_DATE_INVALID')
        try: datetime.strptime(str(date),'%Y%m%d')
        except ValueError as exc: raise ValueError('EXACT_FACTOR_DATE_INVALID') from exc
    if trade_date>basis_date: raise ValueError('EXACT_FACTOR_IDENTITY_INVALID')

@dataclass(frozen=True)
class ExactFactorTransport:
    security_id: str
    adjustment_basis_date: int
    source_digest: str
    factor: AdjustmentFactor

    def to_dict(self):
        _identity(self.security_id,self.source_digest,self.adjustment_basis_date,self.factor.trade_date)
        values=self.factor.exact_coefficients()
        fractions={k:Fraction(v) for k,v in values.items()}
        if fractions['qfq_mul']<=0 or fractions['hfq_mul']<=0 or any(max(v.numerator.bit_length(),v.denominator.bit_length())>4096 for v in fractions.values()):
            raise ValueError('EXACT_COEFFICIENT_INVALID')
        return dict(contract_id=CONTRACT,adjustment_version=ADJUSTMENT_VERSION,security_id=self.security_id,
            trade_date=self.factor.trade_date,adjustment_basis_date=self.adjustment_basis_date,source_digest=self.source_digest,
            coefficients={k:dict(numerator=Fraction(v).numerator,denominator=Fraction(v).denominator) for k,v in values.items()})

    @classmethod
    def from_dict(cls,value,*,security_id,source_digest,adjustment_basis_date):
        if not isinstance(value,dict): raise ValueError('EXACT_TRANSPORT_CONTRACT_MISMATCH')
        _identity(security_id,source_digest,adjustment_basis_date,value.get('trade_date'))
        if value.get('contract_id')!=CONTRACT or value.get('adjustment_version')!=ADJUSTMENT_VERSION: raise ValueError('EXACT_TRANSPORT_CONTRACT_MISMATCH')
        if (value.get('security_id'),value.get('source_digest'),value.get('adjustment_basis_date'))!=(security_id,source_digest,adjustment_basis_date): raise ValueError('EXACT_TRANSPORT_SOURCE_MISMATCH')
        names=('qfq_mul','qfq_add','hfq_mul','hfq_add');coefficients=value.get('coefficients',{})
        if not isinstance(coefficients,dict) or set(coefficients)!=set(names): raise ValueError('EXACT_COEFFICIENT_MISSING')
        exact=[]
        for name in names:
            cell=coefficients[name]
            if not isinstance(cell,dict) or set(cell)!={'numerator','denominator'}: raise ValueError('EXACT_COEFFICIENT_INVALID')
            n=cell.get('numerator');d=cell.get('denominator')
            if type(n) is not int or type(d) is not int or d<=0 or max(n.bit_length(),d.bit_length())>4096: raise ValueError('EXACT_COEFFICIENT_INVALID')
            exact.append(Fraction(n,d))
        if exact[0]<=0 or exact[2]<=0: raise ValueError('EXACT_COEFFICIENT_INVALID')
        if type(value.get('trade_date')) is not int: raise ValueError('EXACT_FACTOR_DATE_INVALID')
        with localcontext() as ctx:
            ctx.prec=40;decimals=[Decimal(v.numerator)/Decimal(v.denominator) for v in exact]
        result=cls(security_id,adjustment_basis_date,source_digest,AdjustmentFactor(value['trade_date'],*decimals,*exact))
        result.to_dict()
        return result
