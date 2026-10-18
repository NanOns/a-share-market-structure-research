"""Explicit reconstructed period Owner, never a replacement operational Head."""
import json
from pathlib import Path
from .v4_native import connection,workspace_schema,configured_dsn
from .v4_forward_pg_r1 import ForwardFactStore,CONTRACT,digest,resolve_migrated_legacy_fact
OWNER='CORE_PRODUCT_PERIOD_PG_OWNER_R1'

def prepare(root,payload,key):
    if payload.get('contract_id')!=OWNER:raise ValueError('PERIOD_OWNER_CONTRACT_REQUIRED')
    store=ForwardFactStore(root,'data/v4/core_period_pg_r1')
    rows=payload['rows']; chunks=[];security_index={}
    # Bound each immutable PG statement; retain every row and its order.
    for offset in range(0,len(rows),1000):
        part=dict(contract_id=OWNER,domain=payload['domain'],T0=payload['T0'],head_token=payload['head_token'],offset=offset,rows=rows[offset:offset+1000])
        for row in part['rows']:
            entry=security_index.setdefault(row['security_id'],dict(row_count=0,chunk_indices=[]))
            entry['row_count']+=1
            if not entry['chunk_indices'] or entry['chunk_indices'][-1]!=len(chunks):entry['chunk_indices'].append(len(chunks))
        chunks.append(store.append(payload['domain'],key+'_chunk_'+str(offset),part))
    envelope={name:value for name,value in payload.items() if name!='rows'}
    envelope.update(storage_contract='ORDERED_PG_PERIOD_CHUNKS_R2',row_count=len(rows),chunks=chunks,security_index=security_index)
    return store.append(payload['domain'],key+'_manifest_r2',envelope)

def read(root,binding,day,domain,head_token,*,security_id=None):
    from workbench_analysis.r43_owner_replay import checked
    path=checked(root,binding);d=json.loads(path.read_bytes());schema=workspace_schema(path.parent.parent,'forward')
    source_schema=d.get('schema')
    if (d.get('contract_id')!=CONTRACT or source_schema not in ('v4',) and not (isinstance(source_schema,str) and source_schema.startswith('v4_forward_'))
            or d.get('kind')!=domain or d.get('engine')!='postgresql'):raise ValueError('PG_PERIOD_DESCRIPTOR_REQUIRED_NO_FALLBACK')
    namespace=d.get('workspace_namespace')
    if source_schema!='v4':namespace=resolve_migrated_legacy_fact(source_schema,domain,d['fact_key'],d['payload_sha256'])
    with connection(schema,read_only=True) as pg:
        if ForwardFactStore._database_identity(pg)!=d.get('database_identity'):raise ValueError('PG_PERIOD_DATABASE_IDENTITY_MISMATCH')
        row=pg.execute('SELECT payload,payload_sha256 FROM forward_facts WHERE workspace_namespace=%s AND kind=%s AND fact_key=%s',(namespace,domain,d['fact_key'])).fetchone()
    if row is None or row[1]!=d['payload_sha256'] or digest(row[0].encode())!=row[1]:raise ValueError('PG_PERIOD_PAYLOAD_DIGEST_MISMATCH')
    payload=json.loads(row[0])
    if (payload.get('contract_id'),payload.get('T0'),payload.get('domain'),payload.get('head_token'))!=(OWNER,day,domain,head_token):raise ValueError('PG_PERIOD_CONTEXT_MISMATCH')
    for source in payload['source_bindings'].values():checked(root,source)
    if payload.get('storage_contract') in ('ORDERED_PG_PERIOD_CHUNKS_R1','ORDERED_PG_PERIOD_CHUNKS_R2'):
        # Read-only consumers must never create schemas or run migration DDL.
        store=ForwardFactStore.__new__(ForwardFactStore)
        store.root=Path(root).resolve();store.folder=store.root/'data/v4/core_period_pg_r1'
        store.schema=schema;store.workspace_namespace=namespace;store.database_identity=d['database_identity'];store.dsn=configured_dsn();rows=[]
        selected=list(range(len(payload['chunks'])))
        indexed=security_id is not None and payload['storage_contract']=='ORDERED_PG_PERIOD_CHUNKS_R2'
        if indexed:
            entry=payload['security_index'].get(security_id,dict(row_count=0,chunk_indices=[]))
            selected=entry['chunk_indices']
            if selected!=sorted(set(selected)) or any(type(i) is not int or not 0<=i<len(payload['chunks']) for i in selected):raise ValueError('PG_PERIOD_SECURITY_INDEX_INVALID')
        for index in selected:
            ref=payload['chunks'][index]
            part=store.read(ref)
            if (part.get('contract_id'),part.get('T0'),part.get('domain'),part.get('head_token'),part.get('offset'))!=(OWNER,day,domain,head_token,index*1000):
                raise ValueError('PG_PERIOD_CHUNK_CONTEXT_MISMATCH')
            if len(part['rows'])!=min(1000,payload['row_count']-index*1000):raise ValueError('PG_PERIOD_CHUNK_COUNT_MISMATCH')
            rows.extend(row for row in part['rows'] if not indexed or row['security_id']==security_id)
        if len(rows)!=(entry['row_count'] if indexed else payload['row_count']):raise ValueError('PG_PERIOD_CHUNK_COUNT_MISMATCH')
        return rows if security_id is None or indexed else [row for row in rows if row['security_id']==security_id]
    return payload['rows'] if security_id is None else [row for row in payload['rows'] if row['security_id']==security_id]
