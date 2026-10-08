"""Accepted A-share .day unit contract; no scaling or factor inference."""
import math
from .current_v4_context import SourceInvalid

CONTRACT='R2_RAW_AMOUNT_VOLUME_PROJECTION_V1'

def cells(row,day,volume_unit,amount_unit):
    if row['trade_date']!=day:raise SourceInvalid('RAW_TURNOVER_DATE_MISMATCH')
    if (volume_unit,amount_unit)!=('SHARES','CNY'):raise SourceInvalid('RAW_TURNOVER_UNIT_CONTRACT_REQUIRED')
    result={}
    for field,unit in [('amount','CNY'),('volume','SHARES')]:
        value=row.get(field)
        valid=not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value) and value>=0
        if field=='volume':valid=valid and isinstance(value,int)
        result[field]=dict(value=value if valid else None,quality='KNOWN' if valid else 'UNKNOWN',
            reason=None if valid else 'RAW_SOURCE_INVALID_NONNEGATIVE_FINITE_'+field.upper(),
            unit=unit,contract_id=CONTRACT,max_source_date=day,coordinate_basis='RAW_UNADJUSTED',
            window_identity=dict(start=day,end=day,actual_count=1))
    return result
