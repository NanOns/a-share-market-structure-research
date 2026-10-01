"""Mechanism diagnostics only; an undocumented provider error is never tolerated."""
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import struct


def number(value):
    try:
        d = Decimal(str(value))
        if not d.is_finite():
            raise ValueError('NON_FINITE_SOURCE_NUMBER')
        return d
    except (InvalidOperation, TypeError) as exc:
        raise ValueError('INVALID_SOURCE_NUMBER') from exc


def float32_half_ulp(value):
    """An IEEE-754 storage bound, conditional on nearest rounding at encoding.

    This is not a provider-generation error bound and cannot authorize binding.
    """
    x = float(number(value))
    bits = struct.unpack('<I', struct.pack('<f', x))[0]
    if bits == 0:
        return Fraction(1, 2**150)
    if x < 0 or bits >= 0x7f800000:
        raise ValueError('UNSUPPORTED_FLOAT32_AMOUNT')
    center = Fraction(struct.unpack('<f', struct.pack('<I', bits))[0])
    before = Fraction(struct.unpack('<f', struct.pack('<I', bits-1))[0])
    after = Fraction(struct.unpack('<f', struct.pack('<I', bits+1))[0])
    return max(center-before, after-center)/2


def decompose(local, source, *, source_revision_same=None):
    identity = local['source_security_key'].lower() == source['code'].lower()
    if not identity or local['trade_date'] != source['date']:
        return dict(classification='CALENDAR_IDENTITY_MISMATCH',strict_binding=False,tdx_core_blocked=False)
    if source.get('adjustflag') != '3':
        return dict(classification='ADJUSTMENT_BASIS_MISMATCH',strict_binding=False,tdx_core_blocked=False)
    if source_revision_same is False:
        return dict(classification='PROVIDER_REVISION',strict_binding=False,tdx_core_blocked=False)
    if source.get('tradestatus') == '0':
        return dict(classification='SUSPENDED_NONCOMPARABLE_BAR_SEMANTICS',strict_binding=False,tdx_core_blocked=False)
    differences = {k: number(local[k])-number(source[k]) for k in ('close','volume','amount')}
    if all(x == 0 for x in differences.values()):
        category = 'EXACT_UNIT_NORMALIZED_FINGERPRINT'
    elif differences['volume'] == 0 and differences['close'] == 0 and abs(Fraction(differences['amount'])) <= float32_half_ulp(local['amount']):
        category = 'ROUNDING_STORAGE_COMPATIBLE_NOT_PROVIDER_GENERATION_PROVEN'
    else:
        category = 'TRUE_DATA_CONFLICT_OR_UNPROVEN_PROVIDER_GENERATION'
    return dict(classification=category,differences={k:str(v) for k,v in differences.items()},
        amount_ieee754_nearest_storage_half_ulp=str(float32_half_ulp(local['amount'])),
        unit_conversion=dict(close='CNY/share identity',volume='shares identity',amount='CNY identity',turn='percent points / 100'),
        provider_generation_rounding_proven=False,strict_binding=False,
        supplemental_capability='UNKNOWN_BINDING_TOLERANCE_NOT_ACCEPTED',tdx_core_blocked=False)


def validate_policy(policy):
    if policy.get('contract_id') != 'BAOSTOCK_BINDING_TOLERANCE_POLICY_R2_CANDIDATE':
        raise ValueError('TOLERANCE_POLICY_VERSION_INVALID')
    if policy.get('strict_binding_allowed') is not False or policy.get('acceptance') != 'PENDING_INDEPENDENT_EXTERNAL_REAUDIT':
        raise ValueError('SUPPLEMENTAL_SELF_PROMOTION')
    if policy.get('canonical_authority') != dict(OHLC=False,QFQ=False) or policy.get('may_block_tdx_core') is not False:
        raise ValueError('SUPPLEMENTAL_AUTHORITY_OVERCLAIM')
    fields = policy['fields']
    if set(fields) != {'close','volume','amount','turn'}:
        raise ValueError('TOLERANCE_FIELDS_INVALID')
    for name, field in fields.items():
        if field['tolerance'] is not None or field['generation_rounding_proven'] is not False:
            raise ValueError('UNDOCUMENTED_TOLERANCE_FORBIDDEN:'+name)
    return dict(status='PASS_FAIL_CLOSED_CANDIDATE',strict_binding_allowed=False)
