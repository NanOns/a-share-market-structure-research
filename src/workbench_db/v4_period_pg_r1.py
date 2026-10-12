"""Explicit reconstructed period Owner, never a replacement operational Head."""
import json
from pathlib import Path
from .v4_native import connection,workspace_schema,configured_dsn
from .v4_forward_pg_r1 import ForwardFactStore,CONTRACT,digest
OWNER='CORE_PRODUCT_PERIOD_PG_OWNER_R1'

def prepare(root,payload,key):
    if payload.get('contract_id')!=OWNER:raise ValueError('PERIOD_OWNER_CONTRACT_REQUIRED')
    store=ForwardFactStore(root,'data/v4/core_period_pg_r1')
    rows=payload['rows']; chunks=[]
    # Bound each immutable PG statement; retain every row and its order.
    for offset in range(0,len(rows),1000):
        part=dict(contract_id=OWNER,domain=payload['domain'],T0=payload['T0'],head_token=payload['head_token'],offset=offset,rows=rows[offset:offset+1000])
        chunks.append(store.append(payload['domain'],key+'_chunk_'+str(offset),part))
    envelope={name:value for name,value in payload.items() if name!='rows'}
    envelope.update(storage_contract='ORDERED_PG_PERIOD_CHUNKS_R1',row_count=len(rows),chunks=chunks)
    return store.append(payload['domain'],key+'_manifest_r1',envelope)

def read(root,binding,day,domain,head_token):
    from workbench_analysis.r43_owner_replay import checked
    path=checked(root,binding);d=json.loads(path.read_bytes());schema=workspace_schema(path.parent.parent,'forward')
    if d.get('contract_id')!=CONTRACT or d.get('schema')!=schema or d.get('kind')!=domain or d.get('engine')!='postgresql':raise ValueError('PG_PERIOD_DESCRIPTOR_REQUIRED_NO_FALLBACK')
    with connection(schema,read_only=True) as pg:
        if ForwardFactStore._database_identity(pg)!=d.get('database_identity'):raise ValueError('PG_PERIOD_DATABASE_IDENTITY_MISMATCH')
        row=pg.execute('SELECT payload,payload_sha256 FROM forward_facts WHERE kind=%s AND fact_key=%s',(domain,d['fact_key'])).fetchone()
    if row is None or row[1]!=d['payload_sha256'] or digest(row[0].encode())!=row[1]:raise ValueError('PG_PERIOD_PAYLOAD_DIGEST_MISMATCH')
    payload=json.loads(row[0])
    if (payload.get('contract_id'),payload.get('T0'),payload.get('domain'),payload.get('head_token'))!=(OWNER,day,domain,head_token):raise ValueError('PG_PERIOD_CONTEXT_MISMATCH')
    for source in payload['source_bindings'].values():checked(root,source)
    if payload.get('storage_contract')=='ORDERED_PG_PERIOD_CHUNKS_R1':
        # Read-only consumers must never create schemas or run migration DDL.
        store=ForwardFactStore.__new__(ForwardFactStore)
        store.root=Path(root).resolve();store.folder=store.root/'data/v4/core_period_pg_r1'
        store.schema=schema;store.database_identity=d['database_identity'];store.dsn=configured_dsn();rows=[]
        for ref in payload['chunks']:
            part=store.read(ref)
            if (part.get('contract_id'),part.get('T0'),part.get('domain'),part.get('head_token'),part.get('offset'))!=(OWNER,day,domain,head_token,len(rows)):
                raise ValueError('PG_PERIOD_CHUNK_CONTEXT_MISMATCH')
            rows.extend(part['rows'])
        if len(rows)!=payload['row_count']:raise ValueError('PG_PERIOD_CHUNK_COUNT_MISMATCH')
        return rows
    return payload['rows']
