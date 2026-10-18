"""Immutable source-bound market payloads, native PG read only consumers."""
import json
from .v4_native import connection, workspace_schema
from .v4_forward_pg_r1 import ForwardFactStore, CONTRACT, digest, resolve_migrated_legacy_fact

def prepare(root, facts, key):
    if facts.get('contract_id')!='CORE_PRODUCT_MARKET_FACT_READ_R1':raise ValueError('MARKET_SOURCE_CONTRACT_REQUIRED')
    store=ForwardFactStore(root,'data/v4/core_market_pg_r1')
    return store.append('market_facts',key,facts)

def read(root,binding,day):
    from workbench_analysis.r43_owner_replay import checked
    path=checked(root,binding);descriptor=json.loads(path.read_bytes())
    schema=workspace_schema(path.parent.parent,'forward')
    source_schema=descriptor.get('schema')
    if (descriptor.get('contract_id')!=CONTRACT or descriptor.get('engine')!='postgresql'
            or source_schema not in ('v4',) and not (isinstance(source_schema,str) and source_schema.startswith('v4_forward_'))
            or descriptor.get('kind')!='market_facts'):raise ValueError('PG_MARKET_DESCRIPTOR_REQUIRED_NO_FALLBACK')
    namespace=descriptor.get('workspace_namespace')
    if source_schema!='v4':namespace=resolve_migrated_legacy_fact(source_schema,descriptor['kind'],descriptor['fact_key'],descriptor['payload_sha256'])
    elif namespace!=ForwardFactStore.namespace_for(path.parent.parent):raise ValueError('PG_MARKET_WORKSPACE_NAMESPACE_MISMATCH')
    with connection(schema,read_only=True) as pg:
        if ForwardFactStore._database_identity(pg)!=descriptor.get('database_identity'):raise ValueError('PG_MARKET_DATABASE_IDENTITY_MISMATCH')
        row=pg.execute('SELECT payload,payload_sha256 FROM forward_facts WHERE workspace_namespace=%s AND kind=%s AND fact_key=%s',(namespace,'market_facts',descriptor['fact_key'])).fetchone()
    if row is None or row[1]!=descriptor['payload_sha256'] or digest(row[0].encode())!=row[1]:raise ValueError('PG_MARKET_PAYLOAD_DIGEST_MISMATCH')
    facts=json.loads(row[0])
    if facts.get('contract_id')!='CORE_PRODUCT_MARKET_FACT_READ_R1' or facts.get('trade_date')!=day:raise ValueError('PG_MARKET_CONTEXT_MISMATCH')
    for source in facts['sources'].values():checked(root,source)
    return facts
