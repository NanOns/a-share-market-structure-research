"""Immutable source-bound market payloads, native PG read only consumers."""
import json
from .v4_native import connection, workspace_schema
from .v4_forward_pg_r1 import ForwardFactStore, CONTRACT, digest

def prepare(root, facts, key):
    if facts.get('contract_id')!='CORE_PRODUCT_MARKET_FACT_READ_R1':raise ValueError('MARKET_SOURCE_CONTRACT_REQUIRED')
    store=ForwardFactStore(root,'data/v4/core_market_pg_r1')
    return store.append('market_facts',key,facts)

def read(root,binding,day):
    from workbench_analysis.r43_owner_replay import checked
    path=checked(root,binding);descriptor=json.loads(path.read_bytes())
    schema=workspace_schema(path.parent.parent,'forward')
    if descriptor.get('contract_id')!=CONTRACT or descriptor.get('engine')!='postgresql' or descriptor.get('schema')!=schema or descriptor.get('kind')!='market_facts':raise ValueError('PG_MARKET_DESCRIPTOR_REQUIRED_NO_FALLBACK')
    with connection(schema,read_only=True) as pg:
        if ForwardFactStore._database_identity(pg)!=descriptor.get('database_identity'):raise ValueError('PG_MARKET_DATABASE_IDENTITY_MISMATCH')
        row=pg.execute('SELECT payload,payload_sha256 FROM forward_facts WHERE kind=%s AND fact_key=%s',('market_facts',descriptor['fact_key'])).fetchone()
    if row is None or row[1]!=descriptor['payload_sha256'] or digest(row[0].encode())!=row[1]:raise ValueError('PG_MARKET_PAYLOAD_DIGEST_MISMATCH')
    facts=json.loads(row[0])
    if facts.get('contract_id')!='CORE_PRODUCT_MARKET_FACT_READ_R1' or facts.get('trade_date')!=day:raise ValueError('PG_MARKET_CONTEXT_MISMATCH')
    for source in facts['sources'].values():checked(root,source)
    return facts
