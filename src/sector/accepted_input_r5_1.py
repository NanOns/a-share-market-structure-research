"""V4_08_ACCEPTED_INPUT_ADAPTER_R5_2: context-bound bytes, no fallback IO."""
from datetime import datetime
import gzip
import hashlib
import json
import math
from pathlib import Path
from v4.canonical_governance_hash import canonical_json_file_sha256

CONTRACT_ID = 'V4_08_ACCEPTED_INPUT_ADAPTER_R5_2'


def day(value):
    value = str(value)
    return f'{value[:4]}-{value[4:6]}-{value[6:]}' if len(value) == 8 else value


def bound_file(root, binding):
    root = Path(root).resolve()
    path = (root / binding['path']).resolve()
    if not path.is_relative_to(root):
        raise ValueError('ACCEPTED_PATH_OUTSIDE_WORKSPACE')
    if hashlib.sha256(path.read_bytes()).hexdigest() != binding['sha256']:
        raise ValueError('ACCEPTED_SOURCE_DIGEST_MISMATCH')
    return path


def load_rows(root, binding, target=None):
    path = bound_file(root, binding)
    if path.suffix == '.parquet':
        import pyarrow.parquet as pq
        import pyarrow.compute as pc
        table = pq.read_table(path, columns=['canonical_security_id','trade_date','amount','trading_status','adjustment_source_revision'])
        if target is not None:
            date = int(target.replace('-', ''))
            maximum=pc.max(table['trade_date']).as_py()
            if maximum is not None and maximum > date:
                raise ValueError('FUTURE_CANONICAL_DAILY_DATE')
            table = table.filter(pc.equal(table['trade_date'], date))
        return table.to_pylist()
    with gzip.open(path, 'rt', encoding='utf8') as stream:
        return [json.loads(line) for line in stream]


def finite(value):
    try:
        return None if value is None or isinstance(value, bool) or not math.isfinite(float(value)) else float(value)
    except (ValueError, TypeError):
        return None


def build_current(factors, profiles, daily, prices, *, target, cutoff, binding):
    """All rows originate from the loader's verified accepted artifacts.

    Raw amount and adjusted close use the caller's accepted context pair.
    Close and identity share an accepted coordinate and source revision.
    The source digest and revision are retained separately from amount.
    """
    limit = datetime.fromisoformat(cutoff.replace('Z', '+00:00'))
    for key in ('daily_available_at',):
        timestamp = binding.get(key)
        if timestamp and datetime.fromisoformat(timestamp.replace('Z', '+00:00')) > limit:
            raise ValueError('FUTURE_ACCEPTED_SOURCE_REVISION')
    current = {}
    for row in factors:
        if row['trade_date'] > target:
            raise ValueError('FUTURE_ACCEPTED_CORE')
        if row['trade_date'] != target:
            continue
        fields = {}
        for name, item in row['fields'].items():
            if item.get('source_asof') and day(item['source_asof']) > target:
                raise ValueError('FUTURE_ACCEPTED_FACTOR')
            fields[name] = dict(value=item.get('value'), quality='ACCEPTED' if item.get('quality_state') == 'OBSERVED' else 'UNKNOWN', max_source_date=day(item.get('source_asof') or target))
        # Registry factors cannot impersonate raw amount or canonical close.
        for name in ('amount', 'close'):
            fields.pop(name, None)
        current[row['security_id']] = dict(trade_date=target, fields=fields, price_basis_id=None)
        current[row['security_id']]['legacy_valid_member'] = dict(value=None, quality='UNKNOWN', reason='NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE', producer_contract='NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE', max_source_date=target)
    def fact(value, reason=None, **extra):
        return dict(value=value, quality='ACCEPTED' if value is not None else 'UNKNOWN', reason_code=reason, max_source_date=target, **extra)
    for record in current.values():
        record['fields']['amount'] = fact(None, 'NO_TARGET_ACCEPTED_CANONICAL_DAILY')
        record['fields']['close'] = fact(None, 'NO_TARGET_ACCEPTED_PRICE_COORDINATE')
    seen = set()
    for row in daily:
        date = day(row['trade_date'])
        if date > target:
            raise ValueError('FUTURE_CANONICAL_DAILY_DATE')
        if date != target:
            continue
        sid = row['canonical_security_id']
        if sid in seen:
            raise ValueError('DUPLICATE_CANONICAL_DAILY')
        seen.add(sid)
        if sid not in current:
            continue
        amount = finite(row.get('amount'))
        ready = row.get('trading_status') == 'ACTUAL_TRADED' and amount is not None and amount >= 0
        current[sid]['fields']['amount'] = fact(amount if ready else None, None if ready else 'RAW_AMOUNT_NOT_EVALUABLE', source_revision=row.get('adjustment_source_revision'), available_at=binding['daily_available_at'], artifact_sha256=binding['canonical_daily']['sha256'], source_digest=binding['canonical_daily_source_digest'], trading_status=row.get('trading_status'))
    seen = set()
    for row in prices:
        date = day(row['target_trade_date'])
        if date > target or day(row['max_source_trade_date']) > target:
            raise ValueError('FUTURE_ACCEPTED_PRICE_DATE')
        for name in ('formal_publication_at', 'system_available_at', 'adjustment_source_available_at', 'adjustment_system_available_at'):
            if row.get(name) and datetime.fromisoformat(row[name].replace('Z', '+00:00')) > limit:
                raise ValueError('FUTURE_ACCEPTED_PRICE_REVISION')
        if date != target:
            continue
        sid = row['security_id']
        if sid in seen:
            raise ValueError('DUPLICATE_ACCEPTED_PRICE')
        seen.add(sid)
        if sid not in current:
            continue
        snapshot = row.get('adjustment_snapshot_id')
        ready = row.get('adjusted_quality') == 'ADJUSTED_READY' and row.get('coordinate_basis') == 'T0_CURRENT_COORDINATE' and bool(snapshot) and bool(row.get('adjustment_snapshot_digest'))
        close = finite(row['qfq_ohlc'][3]) if ready and row.get('qfq_ohlc') else None
        basis = f"{row['coordinate_basis']}:{snapshot}" if ready and close is not None else None
        current[sid]['price_basis_id'] = basis
        current[sid]['fields']['close'] = fact(close, None if close is not None else 'PRICE_BASIS_UNAVAILABLE', price_basis_id=basis, adjustment_source_revision=row.get('adjustment_snapshot_digest'), available_at=row.get('formal_publication_at'))
    for row in profiles:
        if row['trade_date'] != target or row['security_id'] not in current:
            continue
        record = current[row['security_id']]
        evidence = row.get('states', {}).get('trend_state', {}).get('evidence', {})
        close, ma20 = finite(evidence.get('close')), finite(evidence.get('ma20'))
        canonical_close = record['fields']['close']['value']
        compatible = canonical_close is not None and close == canonical_close and ma20 is not None
        record['fields']['close_minus_ma20'] = fact(close - ma20 if compatible else None, None if compatible else 'CORE_CANONICAL_COORDINATE_NOT_PROVEN')
    return current


def load_accepted_current(root, core_head, *, target, cutoff, accepted_input_context):
    """Context-driven source loader; no stage-head fallback or fixed session."""
    from sector.accepted_context_r5_2 import validate_context, PERMITTED
    from v4.canonical_governance_hash import canonical_json_sha256
    if core_head.get('external_acceptance') != 'EXTERNALLY_ACCEPTED':
        raise ValueError('UNACCEPTED_INPUT_AUTHORITY')
    context = validate_context(root, accepted_input_context, target=target, cutoff=cutoff)
    available = context['availability'] == 'TARGET_ACCEPTED_DATA_CONTEXT'
    binding = dict(contract_id='V4_08_ACCEPTED_INPUT_ADAPTER_R5_2', accepted_input_context=context,
                   context_digest=canonical_json_sha256(context), target_trade_date=target,
                   authority_scope=context['scope'], daily_production_authority=context['daily_production_authority'],
                   availability=context['availability'], cutoff=cutoff,
                   canonical_daily=context.get('raw_daily',{}), daily_available_at=context.get('raw_daily',{}).get('available_at'),
                   canonical_daily_source_digest=context.get('raw_daily',{}).get('source_digest'))
    daily=[];prices=[]
    raw=context['raw_daily'];price=context['adjusted_price']
    binding['amount_source_capability']='UNAVAILABLE_UNKNOWN'
    binding['price_source_capability']='UNAVAILABLE_UNKNOWN'
    if available and raw['capability'] in PERMITTED:
        try:
            daily=load_rows(root,raw,target)
            if raw.get('source_digest_algorithm','ARTIFACT_SHA256') == 'ARTIFACT_SHA256' and raw['source_digest'] != raw['sha256']:
                raise ValueError('ACCEPTED_RAW_SOURCE_DIGEST_MISMATCH')
            if raw.get('logical_digest') and raw.get('logical_digest_algorithm') == 'JSONL_BYTES_SHA256':
                path=bound_file(root,raw)
                if hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest()!=raw['logical_digest']:
                    raise ValueError('ACCEPTED_RAW_LOGICAL_DIGEST_MISMATCH')
            binding['amount_source_capability']='AVAILABLE_VERIFIED'
        except FileNotFoundError:
            pass
    if available and price['capability'] in PERMITTED:
        try:
            price_path=bound_file(root,price)
            if hashlib.sha256(gzip.decompress(price_path.read_bytes())).hexdigest()!=price['logical_digest']:
                raise ValueError('ACCEPTED_PRICE_LOGICAL_DIGEST_MISMATCH')
            prices=load_rows(root,price)
            binding['price_source_capability']='AVAILABLE_VERIFIED'
        except FileNotFoundError:
            pass
    # Stale or blocked context availability must not poison the independent
    # Core path with old metadata, while its affected amount/price stay UNKNOWN.
    if not available or raw['capability'] not in PERMITTED:
        binding['daily_available_at']=None
    current=build_current(load_rows(root,core_head['accepted_artifacts']['full_scope_factors']),load_rows(root,core_head['accepted_artifact']),
                          daily,prices,target=target,cutoff=cutoff,binding=binding)
    for record in current.values():
        if not available:
            for name in ('amount','close'):
                record['fields'][name]['reason_code']='TARGET_ACCEPTED_DATA_UNAVAILABLE'
        record['accepted_context_digest']=binding['context_digest']
    return current,binding
