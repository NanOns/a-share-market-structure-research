"""Versioned exact arithmetic candidate for real operational Core inputs."""
from decimal import Decimal,ROUND_HALF_UP
from fractions import Fraction
from datetime import date
from adjustment.tdx_adjustment_v0_3 import build_affine_factors,xrxd_from_gbbq

CONTRACT='V4_OPERATIONAL_CORE_EXACT_AFFINE_CANDIDATE_R3'

def transform_window(raw,events,dispositions,target):
    cutoff=int(date.fromisoformat(target).strftime('%Y%m%d'))
    days=[row[0] for row in raw]
    for day in days:
        if type(day)is not int:raise ValueError('EXACT_CORE_RAW_DAY_IDENTITY_INVALID')
        date.fromisoformat(str(day)[:4]+'-'+str(day)[4:6]+'-'+str(day)[6:])
    if days!=sorted(set(days)):raise ValueError('EXACT_CORE_RAW_DAY_IDENTITY_INVALID')
    relevant=[event for event in events if event.event_date<=cutoff]
    blocked=[event for event in relevant if dispositions.get(str(event.category),{}).get(
        'formal_disposition','UNKNOWN_PRICE_IMPACT') in ('PRICE_AFFECTING_UNSUPPORTED','UNKNOWN_PRICE_IMPACT')]
    factors=build_affine_factors(days+[cutoff],[xrxd_from_gbbq(event) for event in relevant if event.category==1])
    rows=[]
    for day,o,h,l,c,amount,volume,_ in raw:
        if day>cutoff:continue
        if any(type(value)is not int for value in (o,h,l,c)):
            raise ValueError('EXACT_CORE_NATIVE_PRICE_CENTS_REQUIRED')
        if min(o,h,l,c)<=0 or not l<=min(o,c)<=max(o,c)<=h:
            raise ValueError('EXACT_CORE_RAW_OHLC_INVALID')
        barriers=[event for event in blocked if day<event.event_date]
        factor=factors[day]
        adjusted=None if barriers else [float(factor.qfq_price(Decimal(value)/100)) for value in (o,h,l,c)]
        text=str(day)
        rows.append(dict(trade_date=text[:4]+'-'+text[4:6]+'-'+text[6:],raw_ohlc=[value/100 for value in (o,h,l,c)],
            raw_ohlc_cents=[o,h,l,c],qfq_ohlc=adjusted,amount=amount,volume=volume,
            qfq_mul=str(factor.qfq_mul),qfq_add=str(factor.qfq_add),
            exact_coefficients=factor.exact_coefficients(),adjustment_basis_date=cutoff,
            exact_adjustment_contract=CONTRACT,
            blocked_events=[dict(date=event.event_date,category=event.category) for event in barriers]))
    return rows

def independent_affine(raw_price,bar_date,events,target):
    """Chronological rational price recurrence; no factor-builder dependency."""
    price=Fraction(str(raw_price))
    for event in sorted(events,key=lambda value:(value.event_date,value.source_record_index)):
        if event.category!=1 or not bar_date<event.event_date<=target:continue
        cash,rights_price,bonus,rights=[Fraction(Decimal(str(value)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
            for value in (event.c1,event.c2,event.c3,event.c4)]
        denominator=10+bonus+rights
        if denominator<=0:raise ValueError('EXACT_CORE_INVALID_ACTION_DENOMINATOR')
        price=(10*price-cash+rights*rights_price)/denominator
    cents,remainder=divmod(abs(price.numerator)*100,price.denominator)
    cents+=int(remainder*2>=price.denominator)
    return float(Decimal(('-' if price<0 and cents else '')+str(cents//100)+'.'+str(cents%100).zfill(2)))
