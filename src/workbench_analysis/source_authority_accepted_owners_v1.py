"""Exact governance-head -> registry -> owner -> role proof for formal consumers.

The governance head is an independent metadata namespace. Callers cannot supply
an in-memory registry or a business stage head as owner acceptance authority.
"""
from __future__ import annotations
from datetime import date, datetime
import hashlib
import json
from pathlib import Path

REGISTRY_CONTRACT = 'SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_V1'
HEAD_CONTRACT = 'SOURCE_AUTHORITY_GLOBAL_GOVERNANCE_HEAD_V1'
HEAD_PATH = 'data/v4/V4_SOURCE_AUTHORITY_GOVERNANCE_HEAD_R1.json'
REGISTRY_PATH = 'data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY.json'
ERROR = 'AUTHORITY_OWNER_NOT_EXTERNALLY_ACCEPTED'
MODES = {'TARGET_DATE_QUERYABLE_FACT', 'AS_RECORDED_PIT_FACT', 'MUTABLE_CURRENT_SNAPSHOT'}
REQUIRED_OWNER_FIELDS = {'owner_contract_id', 'field_id', 'artifact', 'external_acceptance',
    'formal_consumer_authorization', 'allowed_consumers', 'effective_scope', 'historical_mode',
    'accepted_at', 'supersedes', 'role_binding_id', 'source_role'}

class OwnerAcceptanceError(ValueError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(ERROR + ':' + reason)

def reject(reason):
    raise OwnerAcceptanceError(reason)

def exact_json(root, binding):
    root = Path(root).resolve()
    if not isinstance(binding, dict) or not isinstance(binding.get('path'), str):
        reject('BINDING_MISSING')
    path = (root / binding['path']).resolve()
    if Path(binding['path']).is_absolute() or not path.is_relative_to(root) or not path.is_file():
        reject('ARTIFACT_PATH_INVALID')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != binding.get('sha256'):
        reject('ARTIFACT_HASH_MISMATCH')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                reject('DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    value = json.loads(data.decode('utf-8'), object_pairs_hook=unique)
    if not isinstance(value, dict):
        reject('ARTIFACT_SCHEMA_INVALID')
    return value

def validate_registry_schema(registry):
    if registry.get('contract_id') != REGISTRY_CONTRACT or type(registry.get('version')) is not int or registry['version'] != 1:
        reject('REGISTRY_VERSION_INVALID')
    entries = registry.get('owners')
    if not isinstance(entries, list):
        reject('REGISTRY_OWNERS_MISSING')
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict) or not REQUIRED_OWNER_FIELDS <= entry.keys():
            reject('OWNER_SCHEMA_INCOMPLETE')
        for key in ('owner_contract_id', 'field_id', 'role_binding_id'):
            if not isinstance(entry[key], str) or not entry[key]:
                reject('OWNER_IDENTITY_INVALID')
        identity = (entry['owner_contract_id'], entry['field_id'])
        if identity in seen:
            reject('OWNER_REGISTRATION_AMBIGUOUS')
        seen.add(identity)
        if entry['source_role'] not in ('CORE_AUTHORITY', 'FIELD_AUTHORITY'):
            reject('OWNER_ROLE_INVALID')
        if entry['historical_mode'] not in MODES:
            reject('OWNER_HISTORICAL_MODE_INVALID')
        if (not isinstance(entry['allowed_consumers'], list) or not entry['allowed_consumers']
            or any(not isinstance(x, str) or not x for x in entry['allowed_consumers'])
            or len(entry['allowed_consumers']) != len(set(entry['allowed_consumers']))):
            reject('OWNER_CONSUMERS_INVALID')
        scope = entry['effective_scope']
        if not isinstance(scope, dict):
            reject('OWNER_SCOPE_INVALID')
        if date.fromisoformat(scope['start_date']) > date.fromisoformat(scope['end_date']):
            reject('OWNER_SCOPE_INVALID')
        accepted = datetime.fromisoformat(str(entry['accepted_at']).replace('Z', '+00:00'))
        if accepted.tzinfo is None:
            reject('OWNER_ACCEPTANCE_TIME_INVALID')
        if entry['supersedes'] is not None and not isinstance(entry['supersedes'], dict):
            reject('OWNER_SUPERSEDES_INVALID')
    return True

def load_registered_owners(root):
    root = Path(root)
    # This fixed repository path, rather than a consumer-provided object, is the trust root.
    head_path = root / HEAD_PATH
    head = exact_json(root, dict(path=HEAD_PATH, sha256=hashlib.sha256(head_path.read_bytes()).hexdigest()))
    if head.get('contract_id') != HEAD_CONTRACT:
        reject('GLOBAL_AUTHORITY_HEAD_INVALID')
    binding = head.get('registry')
    if (not isinstance(binding, dict) or binding.get('path') != REGISTRY_PATH
        or type(binding.get('version')) is not int or binding['version'] != 1):
        reject('REGISTRY_NOT_IN_GLOBAL_AUTHORITY_HEAD')
    registry = exact_json(root, binding)
    validate_registry_schema(registry)
    return registry

def require_accepted_owner(root, rule, *, consumer_contract_id, target_trade_date,
                           historical_mode, expected_owner_binding=None):
    """Return an exact accepted owner, or one uniform fail-closed error code."""
    try:
        from .source_authority_governance_r1 import validate_role_contract
        validate_role_contract(rule)
        if root is None:
            reject('PROJECT_ROOT_REQUIRED')
        if (rule.get('enabled') is False or rule.get('enabled_for_formal_consumer') is False
            or rule.get('authority_status') == 'PENDING_EXTERNAL_ACCEPTANCE'):
            reject('PENDING_OWNER')
        registry = load_registered_owners(root)
        matches = [e for e in registry['owners'] if e['owner_contract_id'] == rule['owner_contract_id']
                   and e['field_id'] == rule['field_id']]
        if len(matches) != 1:
            reject('EXACT_OWNER_REGISTRATION_MISSING')
        entry = matches[0]
        if entry['external_acceptance'] != 'EXTERNALLY_ACCEPTED':
            reject('EXTERNAL_ACCEPTANCE_MISSING')
        if entry['formal_consumer_authorization'] is not True:
            reject('FORMAL_AUTHORIZATION_MISSING')
        if consumer_contract_id not in entry['allowed_consumers'] or consumer_contract_id not in rule['allowed_consumers']:
            reject('CONSUMER_OUT_OF_SCOPE')
        if historical_mode != entry['historical_mode'] or historical_mode != rule['historical_retrieval_mode']:
            reject('HISTORICAL_MODE_OUT_OF_SCOPE')
        target = date.fromisoformat(target_trade_date)
        if not date.fromisoformat(entry['effective_scope']['start_date']) <= target <= date.fromisoformat(entry['effective_scope']['end_date']):
            reject('TARGET_OUT_OF_SCOPE')
        if entry['source_role'] != rule['role'] or entry['role_binding_id'] != rule.get('role_binding_id'):
            reject('ACCEPTED_ROLE_BINDING_MISSING')
        if expected_owner_binding is not None:
            if any(expected_owner_binding.get(k) != entry['artifact'].get(k) for k in ('path', 'sha256')):
                reject('EXPECTED_OWNER_BINDING_MISMATCH')
        owner = exact_json(root, entry['artifact'])
        if owner.get('external_acceptance') != 'EXTERNALLY_ACCEPTED' or owner.get('formal_consumer_authorization') is not True:
            reject('OWNER_EXTERNAL_OR_FORMAL_AUTHORIZATION_MISSING')
        if owner.get('contract_id') != entry['owner_contract_id'] or owner.get('field_id') != entry['field_id']:
            reject('OWNER_CONTRACT_IDENTITY_MISMATCH')
        # Acceptance must agree in both independently bound layers, never just a caller flag.
        for key in ('external_acceptance', 'formal_consumer_authorization', 'allowed_consumers',
                    'effective_scope', 'historical_mode', 'accepted_at', 'supersedes'):
            if owner.get(key) != entry[key]:
                reject('OWNER_REGISTRY_DECLARATION_MISMATCH')
        if owner.get('role_binding') != dict(rule):
            reject('UNACCEPTED_ROLE_CHANGE_OR_SUPPLEMENTAL_PROMOTION')
        prior = entry['supersedes']
        if prior is not None:
            old = exact_json(root, prior)
            if old.get('contract_id') == owner['contract_id']:
                reject('PROMOTION_REQUIRES_NEW_VERSIONED_OWNER')
        return dict(entry=entry, owner=owner, status='PASS_EXACT_ACCEPTED_OWNER')
    except OwnerAcceptanceError:
        raise
    except (OSError, KeyError, TypeError, ValueError, AttributeError) as exc:
        raise OwnerAcceptanceError('OWNER_PROOF_MISSING_OR_MALFORMED') from exc
