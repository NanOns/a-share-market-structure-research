"""Producer acceptance and independently verified dated source instances.

R1 governance remains an immutable historical namespace. R3 consumers use the
fixed R2 head; an accepted producer never substitutes for a missing response.
"""
from __future__ import annotations
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
from .source_authority_accepted_owners_v1 import exact_json, OwnerAcceptanceError, reject

HEAD_PATH = 'data/v4/V4_SOURCE_AUTHORITY_GOVERNANCE_HEAD_R2.json'
REGISTRY_PATH = 'data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R2.json'
POLICY = 'SOURCE_AUTHORITY_SOURCE_INSTANCE_POLICY_V1'
MODE = 'TARGET_DATE_QUERYABLE_FACT'

def binding_bytes(root, binding):
    root = Path(root).resolve()
    path = (root / binding['path']).resolve()
    if Path(binding['path']).is_absolute() or not path.is_relative_to(root) or not path.is_file():
        reject('SOURCE_ARTIFACT_PATH_INVALID')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != binding['sha256']:
        reject('SOURCE_ARTIFACT_HASH_MISMATCH')
    return data

def require_accepted_producer(root, rule, *, consumer_contract_id, historical_mode=MODE):
    try:
        from .source_authority_governance_r1 import validate_role_contract
        validate_role_contract(rule)
        head = json.loads((Path(root) / HEAD_PATH).read_text(encoding='utf8'))
        if head.get('contract_id') != 'SOURCE_AUTHORITY_GLOBAL_GOVERNANCE_HEAD_V2':
            reject('GLOBAL_AUTHORITY_HEAD_INVALID')
        if head['registry']['path'] != REGISTRY_PATH:
            reject('REGISTRY_NOT_IN_GLOBAL_AUTHORITY_HEAD')
        registry = exact_json(root, head['registry'])
        if registry.get('contract_id') != 'SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_V2' or registry.get('version') != 2:
            reject('REGISTRY_VERSION_INVALID')
        matches = [e for e in registry['owners'] if e['owner_contract_id'] == rule['owner_contract_id'] and e['field_id'] == rule['field_id']]
        if len(matches) != 1:
            reject('EXACT_PRODUCER_REGISTRATION_MISSING')
        entry = matches[0]
        owner = exact_json(root, entry['producer_contract'])
        for layer in (entry, owner):
            if layer.get('external_acceptance') != 'EXTERNALLY_ACCEPTED' or layer.get('formal_consumer_authorization') is not True:
                reject('PRODUCER_EXTERNAL_OR_FORMAL_AUTHORIZATION_MISSING')
            if consumer_contract_id not in layer['allowed_consumers']:
                reject('CONSUMER_OUT_OF_SCOPE')
            if historical_mode not in layer['historical_modes']:
                reject('HISTORICAL_MODE_OUT_OF_SCOPE')
            if layer['source_instance_policy_id'] != POLICY or layer['role_binding'] != dict(rule):
                reject('UNACCEPTED_PRODUCER_ROLE_OR_POLICY_CHANGE')
        for key in ('field_id', 'allowed_consumers', 'historical_modes', 'source_instance_policy_id',
                    'role_binding', 'accepted_at', 'external_acceptance', 'formal_consumer_authorization'):
            if owner[key] != entry[key]:
                reject('PRODUCER_REGISTRY_DECLARATION_MISMATCH')
        if owner['contract_id'] != entry['owner_contract_id'] or rule.get('enabled_for_formal_consumer') is not True:
            reject('PRODUCER_IDENTITY_OR_ENABLEMENT_INVALID')
        accepted = datetime.fromisoformat(owner['accepted_at'].replace('Z', '+00:00'))
        if accepted.tzinfo is None:
            reject('PRODUCER_ACCEPTANCE_TIME_INVALID')
        return dict(entry=entry, owner=owner, historical_mode=historical_mode, status='PASS_EXACT_ACCEPTED_PRODUCER')
    except OwnerAcceptanceError:
        raise
    except (OSError, KeyError, TypeError, ValueError, AttributeError) as exc:
        raise OwnerAcceptanceError('PRODUCER_PROOF_MISSING_OR_MALFORMED') from exc

def require_source_instance_for_target(root, producer_proof, instance_binding, *, target_trade_date):
    if instance_binding is None:
        reject('SOURCE_INSTANCE_MISSING_FOR_TARGET_DATE')
    try:
        owner = producer_proof['owner']
        if owner.get('source_instance_representation') == 'HISTORICAL_NORMALIZED_ARCHIVE':
            return require_historical_instance(root, producer_proof, instance_binding, target_trade_date=target_trade_date)
        instance = exact_json(root, instance_binding)
        target = date.fromisoformat(target_trade_date)
        if instance['contract_id'] != POLICY or instance['field_id'] != owner['field_id'] or instance['source_family'] != owner['role_binding']['source_family']:
            reject('SOURCE_INSTANCE_IDENTITY_INVALID')
        if instance['target_trade_date'] != target.isoformat() or instance['provider_date'] != target.isoformat():
            reject('SOURCE_INSTANCE_TARGET_DATE_MISMATCH')
        if producer_proof['historical_mode'] != MODE or instance['knowledge_lineage'] != 'RECONSTRUCTED_CORRECTED' or instance['AS_RECORDED'] is not False or instance['first_available_at_target_proven'] is not False:
            reject('SOURCE_INSTANCE_CANNOT_MINT_AS_RECORDED')
        observed = datetime.fromisoformat(instance['observed_at'].replace('Z', '+00:00'))
        received = datetime.fromisoformat(instance['received_at'].replace('Z', '+00:00'))
        if observed.tzinfo is None or received.tzinfo is None or received < observed or observed.date() < target:
            reject('SOURCE_INSTANCE_TIME_INVALID')
        if instance['query_status'] != 'PASS_NONEMPTY_BOUNDED_EXACT_DATE':
            reject('SOURCE_INSTANCE_QUERY_NOT_USABLE')
        schema = exact_json(root, owner['schema_contract'])
        if instance['schema_contract'] != owner['schema_contract']:
            reject('SOURCE_INSTANCE_SCHEMA_MISMATCH')
        raw = exact_json(root, instance['raw_artifact'])
        meta, rows = raw['provider_metadata'], raw['rows']
        if meta['fields'] != schema['fields'] or meta['error_code'] != '0' or meta['page_count'] != 1:
            reject('SOURCE_INSTANCE_SCHEMA_OR_QUERY_INVALID')
        if not rows:
            reject('SOURCE_INSTANCE_EMPTY_UNKNOWN')
        receipt = exact_json(root, instance['capture_receipt'])['responses']['query_daily_history_k_AStock']
        for key in ('observed_at', 'received_at', 'provider_date', 'target_trade_date'):
            if receipt[key] != instance[key]:
                reject('SOURCE_INSTANCE_CAPTURE_RECEIPT_MISMATCH')
        if receipt['raw_response_binding'] != instance['raw_artifact'] or receipt['fields'] != schema['fields']:
            reject('SOURCE_INSTANCE_CAPTURE_RECEIPT_MISMATCH')
        if receipt['request_count'] != 1 or receipt['page_count'] != 1 or receipt['max_pages'] != 1 or not 0 < len(rows) == receipt['row_count'] <= receipt['max_rows'] <= schema['max_rows']:
            reject('SOURCE_INSTANCE_UNBOUNDED_OR_AMBIGUOUS')
        if instance['source_revision'] != 'sha256:' + instance['raw_artifact']['sha256']:
            reject('SOURCE_INSTANCE_REVISION_MISMATCH')
        column = {'TRADING_STATUS': 'tradestatus', 'ISST': 'isST'}.get(instance['field_id'])
        if column is None:
            reject('SOURCE_INSTANCE_FIELD_OUT_OF_SCOPE')
        keys = []
        for row in rows:
            if set(row) != set(schema['fields']) or row['date'] != target.isoformat() or row[column] not in ('0', '1') or row['adjustflag'] != '3':
                reject('SOURCE_INSTANCE_ROW_SCHEMA_OR_DATE_INVALID')
            keys.append(row['code'].upper())
        if len(set(keys)) != len(keys):
            reject('SOURCE_INSTANCE_UNBOUNDED_OR_AMBIGUOUS')
        identity = exact_json(root, instance['identity_binding'])
        calendar = exact_json(root, instance['calendar_binding'])
        if identity['target_trade_date'] != target.isoformat() or calendar['target_trade_date'] != target.isoformat():
            reject('SOURCE_INSTANCE_UNIVERSE_CALENDAR_TARGET_MISMATCH')
        # Anchors belong to the producer policy, not caller-selected evidence.
        if identity['accepted_head']['path'] != owner['identity_head_path'] or calendar['accepted_head']['path'] != owner['calendar_head_path']:
            reject('SOURCE_INSTANCE_ACCEPTED_ANCHOR_MISMATCH')
        identity_head = exact_json(root, identity['accepted_head'])
        if identity_head.get('status') != 'ACCEPTED':
            reject('SOURCE_INSTANCE_ACCEPTED_ANCHOR_MISMATCH')
        accepted_identity = exact_json(root, identity_head['identity_revision'])
        eligible = {r['source_security_key']: r['security_id'] for r in accepted_identity['records']
                    if r['source_security_key'].split('.')[0] in owner['universe_exchanges']
                    and r['list_date'] <= target.isoformat() and (not r.get('delist_date') or r['delist_date'] >= target.isoformat())
                    and r.get('symbol_effective_from', r['list_date']) <= target.isoformat()
                    and (not r.get('symbol_effective_to') or r['symbol_effective_to'] >= target.isoformat())}
        universe = {r['source_security_key']: r['security_id'] for r in identity['members']}
        if len(universe) != len(identity['members']) or set(universe) != set(keys) or universe != eligible:
            reject('SOURCE_INSTANCE_IDENTITY_UNIVERSE_MISMATCH')
        calendar_head = exact_json(root, calendar['accepted_head'])
        if calendar_head.get('status') != 'ACCEPTED':
            reject('SOURCE_INSTANCE_ACCEPTED_ANCHOR_MISMATCH')
        extension = exact_json(root, calendar_head['accepted_extension'])
        sessions = [r for r in extension['sessions'] if r['trade_date'] == target.isoformat()]
        if calendar['sessions'] != sessions or {r['market'] for r in sessions} != {'SSE', 'SZSE'}:
            reject('SOURCE_INSTANCE_CALENDAR_INVALID')
        return dict(status='PASS_EXACT_SOURCE_INSTANCE', source_instance=instance_binding,
                    target_trade_date=target.isoformat(), row_count=len(rows), field_id=instance['field_id'],
                    knowledge_lineage='RECONSTRUCTED_CORRECTED', AS_RECORDED=False,
                    first_available_at_target_proven=False)
    except OwnerAcceptanceError:
        raise
    except (OSError, KeyError, TypeError, ValueError, AttributeError) as exc:
        raise OwnerAcceptanceError('SOURCE_INSTANCE_PROOF_MISSING_OR_MALFORMED') from exc

def require_historical_instance(root, producer_proof, instance_binding, *, target_trade_date):
    """Accepted archive with explicit per-date revision census, never a range-only grant."""
    owner = producer_proof['owner']
    if instance_binding != owner.get('historical_source_instance_archive'):
        reject('HISTORICAL_SOURCE_INSTANCE_BINDING_MISMATCH')
    archive = exact_json(root, instance_binding)
    target = date.fromisoformat(target_trade_date).isoformat()
    if producer_proof['historical_mode'] != MODE or target not in archive['source_revisions_by_target_date']:
        reject('SOURCE_INSTANCE_MISSING_FOR_TARGET_DATE')
    scope = owner['effective_scope']
    if not scope['start_date'] <= target <= scope['end_date']:
        reject('TARGET_OUT_OF_SCOPE')
    if archive['field_id'] != owner['field_id'] or archive['knowledge_lineage'] != 'RECONSTRUCTED_CORRECTED' or archive['AS_RECORDED'] is not False:
        reject('HISTORICAL_SOURCE_INSTANCE_IDENTITY_INVALID')
    for binding in owner['source_bindings']:
        binding_bytes(root, binding)
    oracle = exact_json(root, archive['independent_oracle'])
    if oracle['status_differences'] != 0 or oracle['st_differences'] != 0 or oracle['rows'] != archive['rows']:
        reject('HISTORICAL_FULL_ROW_ORACLE_INVALID')
    receipts = exact_json(root, archive['primary_query_receipts'])['query_receipts']
    receipts += exact_json(root, archive['bounded_recovery'])['retry_receipts']
    revisions = {r['trade_date']: 'sha256:' + r['normalized_full_market_status_sha256'] for r in receipts if r.get('normalized_full_market_status_sha256')}
    if revisions != archive['source_revisions_by_target_date']:
        reject('HISTORICAL_SOURCE_REVISION_MISMATCH')
    return dict(status='PASS_EXACT_HISTORICAL_SOURCE_INSTANCE', target_trade_date=target,
                field_id=owner['field_id'], source_revision=revisions[target],
                knowledge_lineage='RECONSTRUCTED_CORRECTED', AS_RECORDED=False,
                first_available_at_target_proven=False, scope='ACCEPTED_HISTORICAL_PATH_B_ONLY')

def require_formal_source(root, rule, *, consumer_contract_id, target_trade_date,
                          instance_binding=None, historical_mode=MODE):
    producer = require_accepted_producer(root, rule, consumer_contract_id=consumer_contract_id,
                                         historical_mode=historical_mode)
    instance = require_source_instance_for_target(root, producer, instance_binding, target_trade_date=target_trade_date)
    return dict(producer=producer, instance=instance, status='PASS_PRODUCER_AND_SOURCE_INSTANCE')
