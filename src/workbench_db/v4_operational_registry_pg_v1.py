"""Head-bound PG reader for the daily operational builder registry."""
import json
from pathlib import Path

from .v4_operational_owner_pg_closeout import (
    prepare as append_owner_fact,
    read as read_owner_fact,
)
from .v4_forward_pg_r1 import canonical, digest
from workbench_analysis.r43_owner_replay import checked

KEY = 'native_operational_registry'
CONTRACT = 'V4_OPERATIONAL_BUILDER_REGISTRY_PG_R1'
DOMAIN = 'builder_registry'


def _fact_token(day, source_binding):
    return digest(canonical(dict(contract_id=CONTRACT, T0=day, source_binding=source_binding)))


def prepare(root, candidate):
    """Import one exactly bound registry as a PG fact and update a successor candidate."""
    root = Path(root).resolve()
    day = candidate['accepted_trade_date']
    source_binding = candidate['registry']
    raw = checked(root, source_binding).read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict) or value.get('owner_bindings') != candidate['owners']:
        raise ValueError('OPERATIONAL_REGISTRY_OWNER_BINDING_MISMATCH')
    descriptor = append_owner_fact(root, _fact_token(day, source_binding), day, DOMAIN, source_binding, [value])
    content = read_owner_fact(root, descriptor, _fact_token(day, source_binding), day, DOMAIN, source_binding)
    if content != [value]:
        raise ValueError('OPERATIONAL_REGISTRY_PG_PAYLOAD_DIFFERENCE')
    candidate[KEY] = dict(contract_id=CONTRACT, T0=day, source_binding=source_binding,
        descriptor=descriptor, fact_token=_fact_token(day, source_binding))
    candidate['registry'] = descriptor
    return dict(contract_id=CONTRACT, rows=1, publication=False, source_binding=source_binding)


def read(root, candidate, *, workspace_root=None):
    """Read the exact Head/T0-bound registry payload without opening source JSON."""
    authority = candidate.get(KEY)
    if not isinstance(authority, dict) or authority.get('contract_id') != CONTRACT:
        raise ValueError('OPERATIONAL_REGISTRY_PG_AUTHORITY_REQUIRED_NO_FALLBACK')
    day = candidate.get('accepted_trade_date')
    source_binding = authority.get('source_binding')
    descriptor = authority.get('descriptor')
    if (authority.get('T0') != day or candidate.get('registry') != descriptor
            or authority.get('fact_token') != _fact_token(day, source_binding)):
        raise ValueError('OPERATIONAL_REGISTRY_PG_AUTHORITY_SCOPE_MISMATCH')
    content = read_owner_fact(root, descriptor, authority['fact_token'], day, DOMAIN,
        source_binding, workspace_root=workspace_root)
    if not isinstance(content, list) or len(content) != 1 or not isinstance(content[0], dict):
        raise ValueError('OPERATIONAL_REGISTRY_PG_PAYLOAD_SHAPE_INVALID')
    value = content[0]
    if value.get('owner_bindings') != candidate.get('owners'):
        raise ValueError('OPERATIONAL_REGISTRY_OWNER_BINDING_MISMATCH')
    return value


def read_registry(root, candidate, *, workspace_root=None):
    """Read only the Head-bound PG registry; legacy JSON is ingress-only."""
    if KEY not in candidate:
        raise ValueError('OPERATIONAL_REGISTRY_PG_AUTHORITY_REQUIRED_NO_FALLBACK')
    return read(root, candidate, workspace_root=workspace_root)
