"""V4-03 accepted price basis identity. Affine coefficients are evidence only."""
from .factors.core import Bar,Observation

def parent_bar(row):
    """Preserve every accepted identity and affine evidence column."""
    d=str(row['trade_date']);d=d[:4]+'-'+d[4:6]+'-'+d[6:]
    return dict(date=d,security_id=row['canonical_security_id'],source_security_key=row.get('source_security_key'),
        **{k:float(row['qfq_'+k]) if row['qfq_'+k] is not None else None for k in ('open','high','low','close')},
        **{'raw_'+k:float(row['raw_'+k]) if row.get('raw_'+k) is not None else None for k in ('open','high','low','close')},
        amount=row['amount'],volume=row['volume'],quality=row['adjusted_quality'],mul=str(row['qfq_mul']),add=str(row['qfq_add']),
        price_basis=row['price_basis'],adjustment_source_revision=row['adjustment_source_revision'],trading_status=row['trading_status'])

def incremental_bar(row):
    return dict(**{k:float(row[k]) if row[k] is not None else None for k in ('open','high','low','close')},
        quality=row['adjustment_readiness'],mul=row['qfq_mul'],add=row['qfq_add'],price_basis=row['price_basis'],adjustment_source_revision=row['adjustment_source_revision'])

def basis_id(row):
    basis=row.get('price_basis');revision=row.get('adjustment_source_revision')
    return f'{basis}:{revision}' if basis and revision else None

def admission(row,target=None):
    if row.get('quality')!='READY' or not basis_id(row):return 'ADJUSTMENT_UNKNOWN'
    if target is not None and (not basis_id(target) or target.get('quality')!='READY'):return 'ADJUSTMENT_UNKNOWN'
    if target is not None and basis_id(row)!=basis_id(target):return 'MIXED_ADJUSTMENT_IDENTITY'
    if any(row.get(k) is None for k in ('open','high','low','close')):return 'ADJUSTMENT_UNKNOWN'
    return None

def observations(slots,security_id,accepted_states,source_digest=None):
    result=[];seen=False
    for r in slots:
        state=accepted_states.get((security_id,r['date']))
        raw=r.get('raw_actual_bar')
        if raw or state in ('ACTUAL_TRADED','SUSPENDED'):seen=True
        ready=state=='ACTUAL_TRADED' and raw and admission(r) is None
        if ready:
            bar=Bar(**{k:float(r[k]) for k in ('open','high','low','close','amount','volume')},adjustment_basis_id=basis_id(r),source_digest=source_digest or r['accepted_source_digest'])
            result.append(Observation(r['date'],'ACTUAL',bar))
        else:
            reason='ADJUSTMENT_UNKNOWN' if raw and admission(r) else 'CONFIRMED_SUSPENSION' if state=='SUSPENDED' else 'PRE_LISTING' if not seen else 'UNKNOWN'
            result.append(Observation(r['date'],reason))
    return result
