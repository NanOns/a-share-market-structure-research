"""Head-bound PG reader for the exact predecessor operational Head."""
import json
from pathlib import Path

from .v4_forward_pg_r1 import canonical, digest, ForwardFactStore

KEY = 'native_predecessor_head'
CONTRACT = 'V4_OPERATIONAL_PREDECESSOR_HEAD_PG_R1'
DOMAIN = 'predecessor_head'
OPERATIONAL_CONTRACT = 'V4_OPERATIONAL_INCREMENTAL_SUCCESSOR_V1'
LEGACY_OWNER_CONTRACTS = {'V4_HEAD_EMBEDDED_NATIVE_PG_OWNER_AUTHORITY_V2',
                          'V4_DATED_OPERATIONAL_RECONSTRUCTED_OWNER_V1'}
FOLDER = 'data/v4/operational_predecessor_head_pg_r1'


def _fact_key(day, source_binding):
    return digest(canonical(dict(contract_id=CONTRACT, T0=day, source_binding=source_binding)))


def prepare(root, candidate):
    """Freeze the exact candidate-bound predecessor as an immutable PG fact.

    Successors of an existing PG Head use its exact current digest. A one-time
    legacy migration may instead ingress the predecessor bytes explicitly
    bound by the candidate; that fact remains a candidate predecessor and is
    never treated as an accepted PG Head.
    """
    root = Path(root).resolve()
    day=candidate['accepted_trade_date']
    source_binding=candidate['predecessor']
    if source_binding.get('path')=='pg://v4/operational_research_heads/current':
        from .v4_operational_live_head_pg_r1 import read_current
        current=read_current(root)
        if (source_binding.get('sha256')!=current['head_sha256']
                or source_binding.get('bytes')!=current['head_bytes']):
            raise ValueError('STALE_OPERATIONAL_HEAD_PG_CAS')
        value=current['candidate']
        if value.get('contract_id') != OPERATIONAL_CONTRACT:
            raise ValueError('PREDECESSOR_OPERATIONAL_HEAD_REQUIRED')
        head_sha256=current['head_sha256'];generation=current['generation']
        database_identity=current['database_identity']
    else:
        # Explicit legacy candidate binding is a one-time ingress selector.
        # Runtime reads below use only the immutable fact appended to PG.
        if not isinstance(source_binding.get('path'),str) or source_binding['path'].startswith('pg://'):
            raise ValueError('PREDECESSOR_PG_HEAD_BINDING_REQUIRED')
        from .v4_historical_source_ingress_pg_r1 import admit_bound
        imported=admit_bound(root,source_binding)
        try:value=json.loads(imported['raw'])
        except (TypeError,ValueError) as exc:
            raise ValueError('PREDECESSOR_LEGACY_HEAD_JSON_INVALID') from exc
        if (value.get('contract_id') not in LEGACY_OWNER_CONTRACTS
                or not isinstance(value.get('owners'),dict)):
            raise ValueError('PREDECESSOR_LEGACY_OWNER_CONTRACT_REQUIRED')
        if value.get('accepted_trade_date','')>=day:
            raise ValueError('PREDECESSOR_TRADE_DATE_ORDER_INVALID')
        head_sha256=source_binding['sha256'];generation=None
        database_identity=None
    fact_key=_fact_key(day,source_binding)
    store=ForwardFactStore(root,FOLDER)
    database_identity=database_identity or store.database_identity
    payload=dict(contract_id=CONTRACT,T0=day,source_binding=source_binding,
        head_sha256=head_sha256,generation=generation,head=value,
        database_identity=database_identity)
    descriptor=store.append(DOMAIN,fact_key,payload)
    if store.read(descriptor)!=payload:
        raise ValueError('PREDECESSOR_HEAD_PG_PAYLOAD_DIFFERENCE')
    candidate[KEY] = dict(contract_id=CONTRACT, T0=day, source_binding=source_binding,
        descriptor=descriptor, fact_key=fact_key,head_sha256=head_sha256,
        generation=generation,database_identity=database_identity,
        source_mode='ACCEPTED_PG_HEAD' if generation is not None else 'EXACT_LEGACY_CANDIDATE_INGRESS')
    return dict(contract_id=CONTRACT, T0=day, predecessor_source=source_binding,
        predecessor_head_sha256=head_sha256,generation=generation,
        source_mode='ACCEPTED_PG_HEAD' if generation is not None else 'EXACT_LEGACY_CANDIDATE_INGRESS',
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
    if (not isinstance(head,dict) or head.get('contract_id') not in
            (OPERATIONAL_CONTRACT,*LEGACY_OWNER_CONTRACTS)):
        raise ValueError('PREDECESSOR_OPERATIONAL_HEAD_REQUIRED')
    return head


def read_predecessor(root, candidate, *, workspace_root=None):
    # Historical bytes may be read only by prepare() at the explicit one-time
    # ingress boundary. Runtime validation must use the exact PG fact written
    # for this candidate; falling back to the predecessor path reintroduced a
    # second mutable Head authority.
    return read(root, candidate, workspace_root=workspace_root)
