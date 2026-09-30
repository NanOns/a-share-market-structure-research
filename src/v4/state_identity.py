"""V4_10_CANONICAL_JSON_R1_1: deterministic UTF-8, plain normalized JSON numbers."""
from decimal import Decimal
import hashlib
import json
import math

CANONICALIZATION = 'V4_10_CANONICAL_JSON_R1_1'
INTERFACE = 'V4_10_STATE_REDUCER_INTERFACE_R1_1'

def canonical(value):
    if value is None: return 'null'
    if type(value) is bool: return 'true' if value else 'false'
    if isinstance(value, str):
        if '\x00' in value: raise ValueError('JSON_NUL_FORBIDDEN')
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    if type(value) in (int, float, Decimal):
        number=Decimal(str(value))
        if not number.is_finite(): raise ValueError('FINITE_JSON_NUMBER_REQUIRED')
        if number==0:return '0'
        text=format(number,'f')
        return text.rstrip('0').rstrip('.') if '.' in text else text
    if isinstance(value,list):return '['+','.join(canonical(v) for v in value)+']'
    if isinstance(value,dict) and all(isinstance(k,str) for k in value):
        return '{'+','.join(canonical(k)+':'+canonical(value[k]) for k in sorted(value))+'}'
    raise ValueError('CANONICAL_JSON_TYPE_INVALID')

def digest(value):
    return hashlib.sha256(canonical(value).encode('utf8')).hexdigest()

def state_id(row):
    return 'V4_10:'+digest({k:v for k,v in row.items() if k!='publication_id'})
