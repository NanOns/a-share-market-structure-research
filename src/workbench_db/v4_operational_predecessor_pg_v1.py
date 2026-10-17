"""Head-bound PG reader for the exact predecessor operational Head."""
import json
from pathlib import Path

from .v4_forward_pg_r1 import canonical, digest
from .v4_operational_owner_pg_closeout import (
    prepare as append_owner_fact,
    read as read_owner_fact,
)
from workbench_analysis.r43_owner_replay import checked

KEY = 'native_predecessor_head'
CONTRACT = 'V4_OPERATIONAL_PREDECESSOR_HEAD_PG_R1'
DOMAIN = 'predecessor_head'
OPERATIONAL_CONTRACT = 'V4_OPERATIONAL_INCREMENTAL_SUCCESSOR_V1'


def _fact_key(day, source_binding):
    return digest(canonical(dict(contract_id=CONTRACT, T0=day, source_binding=source_binding)))


def prepare(root, candidate):
    """Append the exact predecessor Head and bind its PG locator to a successor."""
    root = Path(root).resolve()
    day = candidate['accepted_trade_date']
    source_binding = candidate['predecessor']
    value = json.loads(checked(root, source_binding).read_bytes())
    if value.get('contract_id') != OPERATIONAL_CONTRACT:
        raise ValueError('PREDECESSOR_OPERATIONAL_HEAD_REQUIRED')
    fact_key = _fact_key(day, source_binding)
    descriptor = append_owner_fact(root, fact_key, day, DOMAIN, source_binding, [value])
    if read_owner_fact(root, descriptor, fact_key, day, DOMAIN, source_binding) != [value]:
        raise ValueError('PREDECESSOR_HEAD_PG_PAYLOAD_DIFFERENCE')
    candidate[KEY] = dict(contract_id=CONTRACT, T0=day, source_binding=source_binding,
        descriptor=descriptor, fact_key=fact_key)
    return dict(contract_id=CONTRACT, T0=day, predecessor_source=source_binding,
        publication=False)


def read(root, candidate, *, workspace_root=None):
    """Read predecessor bytes from PG while preserving its source Head identity."""
    authority = candidate.get(KEY)
    if (not isinstance(authority, dict) or authority.get('contract_id') != CONTRACT
            or authority.get('T0') != candidate.get('accepted_trade_date')):
        raise ValueError('PREDECESSOR_HEAD_PG_AUTHORITY_REQUIRED_NO_FALLBACK')
    source_binding = authority.get('source_binding')
    if source_binding != candidate.get('predecessor'):
        raise ValueError('PREDECESSOR_HEAD_SOURCE_BINDING_MISMATCH')
    if authority.get('fact_key') != _fact_key(authority['T0'], source_binding):
        raise ValueError('PREDECESSOR_HEAD_FACT_KEY_MISMATCH')
    content = read_owner_fact(root, authority['descriptor'], authority['fact_key'], authority['T0'],
        DOMAIN, source_binding, workspace_root=workspace_root)
    if not isinstance(content, list) or len(content) != 1 or not isinstance(content[0], dict):
        raise ValueError('PREDECESSOR_HEAD_PG_PAYLOAD_SHAPE_INVALID')
    if content[0].get('contract_id') != OPERATIONAL_CONTRACT:
        raise ValueError('PREDECESSOR_OPERATIONAL_HEAD_REQUIRED')
    return content[0]


def read_predecessor(root, candidate, *, workspace_root=None):
    # Historical bytes may be read only by prepare() at the explicit one-time
    # ingress boundary. Runtime validation must use the exact PG fact written
    # for this candidate; falling back to the predecessor path reintroduced a
    # second mutable Head authority.
    return read(root, candidate, workspace_root=workspace_root)
