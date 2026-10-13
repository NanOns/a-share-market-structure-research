"""Isolated v0.3 consumer; never upgrades an accepted price owner implicitly."""
import hashlib
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from .exact_factor_transport_r1 import ExactFactorTransport
from .tdx_adjustment_v0_3 import adjust_ohlc

CONTRACT = 'V4_EXACT_OHLC_CONSUMER_R1'


def consume_exact_ohlc(row, wire, *, source_bytes, security_id, basis_date):
    """Read typed rational evidence and bind it to original event bytes and row date.

    Output remains a candidate with explicit quality/PIT labels. This function
    makes no authority, membership or historical first-available claim.
    """
    if not isinstance(source_bytes, bytes) or not source_bytes:
        raise ValueError('EXACT_SOURCE_BYTES_REQUIRED')
    source_digest = hashlib.sha256(source_bytes).hexdigest()
    factor = ExactFactorTransport.from_dict(wire, security_id=security_id,
        source_digest=source_digest, adjustment_basis_date=basis_date)
    if row.get('security_id') != security_id or row.get('trade_date') != factor.factor.trade_date:
        raise ValueError('EXACT_ROW_IDENTITY_MISMATCH')
    raw = {}
    for field in ('open','high','low','close'):
        value = row.get(field)
        # Float raw evidence has already lost the decimal source representation.
        if type(value) not in (str,int,Decimal):
            raise ValueError('EXACT_RAW_PRICE_INVALID')
        try: raw[field] = Decimal(value)
        except InvalidOperation as exc: raise ValueError('EXACT_RAW_PRICE_INVALID') from exc
        if not raw[field].is_finite() or raw[field] <= 0:
            raise ValueError('EXACT_RAW_PRICE_INVALID')
    if not raw['low'] <= min(raw['open'],raw['close']) <= max(raw['open'],raw['close']) <= raw['high']:
        raise ValueError('EXACT_RAW_OHLC_INVALID')
    prices = adjust_ohlc(raw,factor.factor)
    return dict(contract_id=CONTRACT, security_id=security_id,trade_date=row['trade_date'],
        adjustment_basis_date=basis_date,source_digest=source_digest,exact_factor=deepcopy(wire),
        prices={key:str(value) for key,value in prices.items()},
        quality='READY' if all(value>0 for value in prices.values()) else 'NONPOSITIVE_QFQ',
        knowledge_lineage='RECONSTRUCTED',PIT_ELIGIBLE=False,authority='ISOLATED_CANDIDATE_ONLY')
