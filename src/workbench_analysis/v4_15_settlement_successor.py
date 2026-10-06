"""Additive Forward contract projection; historical algorithms/artifacts stay intact."""
import math
from types import FunctionType
from . import v4_15_settlement as historical

def finite(value):
    return type(value) in (int,float) and math.isfinite(value)

def validate_affine(coeff):
    return isinstance(coeff,dict) and set(coeff)=={'alpha','beta'} and finite(coeff['alpha']) and coeff['alpha']>0 and finite(coeff['beta'])

def valid_row(row,basis,identity):
    return (row.get('verified_adjustment') is True and row.get('evaluation_basis_date')==basis
            and row.get('adjustment_identity')==identity and validate_affine(row.get('transform_coefficients')))

def price_path(reference,rows,basis_date):
    invalid=dict(R_N=None,MFE_N=None,MAE_N=None,PATH_MDD_CLOSE_N=None,evaluation_basis_date=basis_date,
                 actual_count=0,reason_codes=['INVALID_AFFINE_OR_BASIS'],outcome_status='ADJUSTMENT_UNKNOWN')
    if not rows:return historical.price_path(reference,rows,basis_date)
    endpoint=rows[-1]
    identity=endpoint.get('adjustment_identity')
    if not isinstance(identity,str) or not identity:return invalid
    t0=endpoint.get('T0_transform_coefficients',endpoint.get('transform_coefficients'))
    if not finite(reference) or not validate_affine(t0):return invalid
    p0=t0['alpha']*reference+t0['beta']
    if not finite(p0) or p0<=0:return invalid
    for row in rows:
        if row.get('status')=='CONFIRMED_SUSPENSION' and row is not endpoint:
            if row.get('verified_identity') is not True or row.get('verified_adjustment') is not True or row.get('evaluation_basis_date')!=basis_date:return invalid
            continue
        if not valid_row(row,basis_date,identity):return invalid
        coeff=row['transform_coefficients']
        for key in ('close','high','low'):
            if row.get(key) is not None and (not finite(row[key]) or not finite(coeff['alpha']*row[key]+coeff['beta'])):return invalid
    if endpoint.get('terminal_value') is not None and not finite(endpoint['terminal_value']):return invalid
    return historical.price_path(reference,rows,basis_date)

def benchmark(basket,rows_by_member,absolute_return,evaluation_basis_date=None):
    import copy
    rows=copy.deepcopy(rows_by_member)
    for member in basket['members']:
        row=rows.get(member['security_id'],{})
        coeff=row.get('transform_coefficients');t0=row.get('T0_transform_coefficients',coeff)
        valid=validate_affine(coeff) and validate_affine(t0)
        if valid:
            p0=t0['alpha']*member['reference']+t0['beta']
            valid=finite(p0) and p0>0
        if member.get('adjustment_identity') is not None:
            valid=valid and row.get('adjustment_identity')==member['adjustment_identity']
        for key in ('close','terminal_value'):
            if row.get(key) is not None:valid=valid and finite(row[key])
        if valid and row.get('close') is not None:valid=finite(coeff['alpha']*row['close']+coeff['beta'])
        if not valid:row=dict(row,verified_adjustment=False)
        rows[member['security_id']]=row
    out=historical.benchmark(basket,rows,absolute_return,evaluation_basis_date)
    relative=out.pop('relative_return')
    out.update(benchmark_members=[m['security_id'] for m in basket['members']],initial_weights={m['security_id']:m['weight'] for m in basket['members']},
        fixed_shares={m['security_id']:m['fixed_shares'] for m in basket['members']},benchmark_constituent_policy=basket['constituent_policy'],
        benchmark_valuation_coverage=out['benchmark_endpoint_coverage'],benchmark_marked_weight=0,
        quote_age=None,quote_trade_date=None,marked_reason='PARAMETER_GATE_NOT_FROZEN',runtime_schema_version='1.1')
    if basket['kind']=='SECTOR':
        out.update(sector_benchmark_id=basket['benchmark_id'],sector_members=out['benchmark_members'],relative_sector_return=relative,
                   relative_sector_return_marked=None,MFE_CLOSE=None,MAE_CLOSE=None)
    else:out['relative_market_return']=relative
    return out

class SettlementRuntime(historical.SettlementRuntime):
    # Reuse accepted formula/control/revision code with the explicit successor validators.
    old=historical.SettlementRuntime.settle
    settle=FunctionType(old.__code__,dict(old.__globals__,price_path=price_path,benchmark=benchmark),old.__name__,old.__defaults__,old.__closure__)
