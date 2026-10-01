"""Transactional append-only Stock PREWATCH publications and exact payload readback."""
from .stock_prewatch import digest, CONSUMER_CONTRACT

def persist(pg, records, *, consumer_contract_id=CONSUMER_CONTRACT):
    from psycopg.types.json import Jsonb
    if not records: raise ValueError('EMPTY_STOCK_PREWATCH_PUBLICATION')
    records=sorted(records,key=lambda r:r['security_id'])
    first=records[0]; publication=first['publication_id']; checksum=digest(records)
    if not isinstance(consumer_contract_id,str) or not consumer_contract_id.strip() or len(consumer_contract_id)>256:
        raise ValueError('INVALID_STOCK_PREWATCH_CONSUMER_IDENTITY')
    if len({r['security_id'] for r in records})!=len(records) or any(r['publication_id']!=publication for r in records):
        raise ValueError('DUPLICATE_OR_MIXED_STOCK_PREWATCH_PUBLICATION')
    shared=['trade_date','model_contract_id','parameter_set_id','source_publication_id','source_core_logical_digest']
    if any(any(row.get(k)!=first.get(k) for k in shared) or row.get('consumer_contract_id',consumer_contract_id)!=consumer_contract_id for row in records):
        raise ValueError('MIXED_STOCK_PREWATCH_PUBLICATION_LINEAGE_OR_CONSUMER')
    with pg.transaction():
        pg.execute('''INSERT INTO v4.stock_prewatch_publications
            (publication_id,trade_date,model_contract_id,parameter_set_id,source_publication_id,source_core_logical_digest,publication_digest,row_count,acceptance_scope,consumer_contract_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'ENGINEERING_CANDIDATE',%s) ON CONFLICT DO NOTHING''',
            (publication,first['trade_date'],first['model_contract_id'],first['parameter_set_id'],first['source_publication_id'],first['source_core_logical_digest'],checksum,len(records),consumer_contract_id))
        actual=pg.execute('SELECT publication_digest,row_count,consumer_contract_id FROM v4.stock_prewatch_publications WHERE publication_id=%s',(publication,)).fetchone()
        if actual!=(checksum,len(records),consumer_contract_id): raise ValueError('APPEND_ONLY_PUBLICATION_CONFLICT')
        for row in records:
            pg.execute('''INSERT INTO v4.stock_prewatch_results
                (publication_id,security_id,trade_date,model_contract_id,parameter_set_id,raw_qualification,emergence_axis,structure_quality_axis,risk_axis,priority_bucket,quality,reasons,input_digest,payload,payload_digest,consumer_contract_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
                tuple(row[k] for k in ['publication_id','security_id','trade_date','model_contract_id','parameter_set_id','raw_qualification',
                    'emergence_axis','structure_quality_axis','risk_axis','priority_bucket','quality'])+
                    (Jsonb(row['waiting_for']),row['input_digest'],Jsonb(row),digest(row),consumer_contract_id))
        loaded=pg.execute('SELECT payload,payload_digest,consumer_contract_id FROM v4.stock_prewatch_results WHERE publication_id=%s ORDER BY security_id',(publication,)).fetchall()
        if [r[0] for r in loaded]!=records or any(digest(r[0])!=r[1] or r[2]!=consumer_contract_id for r in loaded): raise ValueError('EXACT_READBACK_MISMATCH')
    return dict(status='PASS_EXACT_DATABASE_READBACK',row_count=len(records),publication_id=publication,publication_digest=checksum,consumer_contract_id=consumer_contract_id)
