"""Typed exact candidate Focus coordinates; existing accepted path stays intact."""
from decimal import Decimal
from fractions import Fraction
import hashlib
from adjustment.exact_factor_transport_r1 import ExactFactorTransport
from adjustment.tdx_adjustment_v0_3 import _round_exact_price
from .price_path import Bar,path_metrics

CONTRACT='V4_FOCUS_EXACT_PATH_CANDIDATE_R3'

def exact_path(*,sessions,rows,source_bytes,security_id,basis_date):
    if not sessions or sessions!=sorted(set(sessions)):raise ValueError('EXACT_PATH_SESSION_ORDER')
    if not isinstance(source_bytes,bytes) or not source_bytes:raise ValueError('EXACT_PATH_SOURCE_REQUIRED')
    source_digest=hashlib.sha256(source_bytes).hexdigest();typed={}
    for day in sessions:
        row=rows.get(day)
        if row is None or row.get('has_actual_bar') is not True:return None
        transport=ExactFactorTransport.from_dict(row.get('exact_factor'),security_id=security_id,
            source_digest=source_digest,adjustment_basis_date=basis_date)
        if transport.factor.trade_date!=int(day.strftime('%Y%m%d')):raise ValueError('EXACT_PATH_ROW_DATE_MISMATCH')
        typed[day]=transport.factor
    anchor=typed[sessions[-1]];a_t,b_t=anchor.exact_qfq_mul,anchor.exact_qfq_add;result=[]
    for day in sessions:
        factor=typed[day];values=[]
        for name in ('open','high','low','close'):
            raw=rows[day].get('raw_'+name)
            if type(raw) not in (str,int,Decimal):raise ValueError('EXACT_PATH_RAW_PRECISION_REQUIRED')
            raw=Decimal(raw)
            if not raw.is_finite() or raw<=0:raise ValueError('EXACT_PATH_RAW_INVALID')
            values.append(_round_exact_price((factor.exact_qfq_mul*Fraction(raw)+factor.exact_qfq_add-b_t)/a_t))
        if any(value<=0 for value in values) or not values[2]<=min(values[0],values[3])<=max(values[0],values[3])<=values[1]:
            raise ValueError('EXACT_PATH_ADJUSTED_OHLC_INVALID')
        result.append(Bar(day,*values))
    return result

def exact_path_receipt(**kwargs):
    path=exact_path(**kwargs)
    return dict(contract_id=CONTRACT,status='READY' if path else 'SOURCE_INCOMPLETE',
        metrics={key:str(value) for key,value in path_metrics(path).items()} if path else None,
        knowledge_lineage='RECONSTRUCTED',PIT_ELIGIBLE=False,production_accepted=False)
