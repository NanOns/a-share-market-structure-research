"""Head-bound PG reader for the exact predecessor operational Head."""
import json
from pathlib import Path

from .v4_forward_pg_r1 import canonical, digest, ForwardFactStore

KEY = 'native_predecessor_head'
CONTRACT = 'V4_OPERATIONAL_PREDECESSOR_HEAD_PG_R1'
DOMAIN = 'predecessor_head'
OPERATIONAL_CONTRACT = 'V4_OPERATIONAL_INCREMENTAL_SUCCESSOR_V1'
FOLDER = 'data/v4/operational_predecessor_head_pg_r1'


def _fact_key(day, source_binding):
    return digest(canonical(dict(contract_id=CONTRACT, T0=day, source_binding=source_binding)))


def prepare(root, candidate):
    """Freeze the exact currently accepted PG Head as an immutable predecessor fact."""
    root = Path(root).resolve()
    day=candidate['accepted_trade_date']
    from .v4_operational_live_head_pg_r1 import read_current
    current=read_current(root)
    source_binding=candidate['predecessor']
    if source_binding.get('path')!='pg://v4/operational_research_heads/current':
        raise ValueError('PREDECESSOR_PG_HEAD_BINDING_REQUIRED')
    if (source_binding.get('sha256')!=current['head_sha256']
            or source_binding.get('bytes')!=current['head_bytes']):
        raise ValueError('STALE_OPERATIONAL_HEAD_PG_CAS')
    value=current['candidate']
    if value.get('contract_id') != OPERATIONAL_CONTRACT:
        raise ValueError('PREDECESSOR_OPERATIONAL_HEAD_REQUIRED')
    fact_key=_fact_key(day,source_binding)
    payload=dict(contract_id=CONTRACT,T0=day,source_binding=source_binding,
        head_sha256=current['head_sha256'],generation=current['generation'],head=value,
        database_identity=current['database_identity'])
    store=ForwardFactStore(root,FOLDER)
    descriptor=store.append(DOMAIN,fact_key,payload)
    if store.read(descriptor)!=payload:
        raise ValueError('PREDECESSOR_HEAD_PG_PAYLOAD_DIFFERENCE')
    candidate[KEY] = dict(contract_id=CONTRACT, T0=day, source_binding=source_binding,
        descriptor=descriptor, fact_key=fact_key,head_sha256=current['head_sha256'],
        generation=current['generation'],database_identity=current['database_identity'])
    return dict(contract_id=CONTRACT, T0=day, predecessor_source=source_binding,
        predecessor_head_sha256=current['head_sha256'],generation=current['generation'],publication=False)


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
    store=ForwardFactStore(root,FOLDER)
    payload=store.read(authority['descriptor'])
    if not isinstance(payload,dict) or payload.get('contract_id')!=CONTRACT:
        raise ValueError('PREDECESSOR_HEAD_PG_PAYLOAD_SHAPE_INVALID')
    if (payload.get('T0')!=authority['T0'] or payload.get('source_binding')!=source_binding
            or payload.get('head_sha256')!=authority.get('head_sha256')
            or payload.get('generation')!=authority.get('generation')
            or payload.get('database_identity')!=authority.get('database_identity')):
        raise ValueError('PREDECESSOR_HEAD_PG_IDENTITY_MISMATCH')
    head=payload.get('head')
    if not isinstance(head,dict) or head.get('contract_id') != OPERATIONAL_CONTRACT:
        raise ValueError('PREDECESSOR_OPERATIONAL_HEAD_REQUIRED')
    return head


def read_predecessor(root, candidate, *, workspace_root=None):
    # Historical bytes may be read only by prepare() at the explicit one-time
    # ingress boundary. Runtime validation must use the exact PG fact written
    # for this candidate; falling back to the predecessor path reintroduced a
    # second mutable Head authority.
    return read(root, candidate, workspace_root=workspace_root)
