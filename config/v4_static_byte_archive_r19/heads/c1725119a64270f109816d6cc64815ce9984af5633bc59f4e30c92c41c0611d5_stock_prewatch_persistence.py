"""Transactional append-only Stock PREWATCH publications and exact payload readback."""
from .stock_prewatch import digest

def persist(pg, records):
    from psycopg.types.json import Jsonb
    if not records: raise ValueError('EMPTY_STOCK_PREWATCH_PUBLICATION')
    records=sorted(records,key=lambda r:r['security_id'])
    first=records[0]; publication=first['publication_id']; checksum=digest(records)
    if len({r['security_id'] for r in records})!=len(records) or any(r['publication_id']!=publication for r in records):
        raise ValueError('DUPLICATE_OR_MIXED_STOCK_PREWATCH_PUBLICATION')
    with pg.transaction():
        pg.execute('''INSERT INTO v4.stock_prewatch_publications
            (publication_id,trade_date,model_contract_id,parameter_set_id,source_publication_id,source_core_logical_digest,publication_digest,row_count,acceptance_scope)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'ENGINEERING_CANDIDATE') ON CONFLICT DO NOTHING''',
            (publication,first['trade_date'],first['model_contract_id'],first['parameter_set_id'],first['source_publication_id'],first['source_core_logical_digest'],checksum,len(records)))
        actual=pg.execute('SELECT publication_digest,row_count FROM v4.stock_prewatch_publications WHERE publication_id=%s',(publication,)).fetchone()
        if actual!=(checksum,len(records)): raise ValueError('APPEND_ONLY_PUBLICATION_CONFLICT')
        for row in records:
            pg.execute('''INSERT INTO v4.stock_prewatch_results
                (publication_id,security_id,trade_date,model_contract_id,parameter_set_id,raw_qualification,emergence_axis,structure_quality_axis,risk_axis,priority_bucket,quality,reasons,input_digest,payload,payload_digest)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
                tuple(row[k] for k in ['publication_id','security_id','trade_date','model_contract_id','parameter_set_id','raw_qualification',
                    'emergence_axis','structure_quality_axis','risk_axis','priority_bucket','quality'])+
                    (Jsonb(row['waiting_for']),row['input_digest'],Jsonb(row),digest(row)))
        loaded=pg.execute('SELECT payload,payload_digest FROM v4.stock_prewatch_results WHERE publication_id=%s ORDER BY security_id',(publication,)).fetchall()
        if [r[0] for r in loaded]!=records or any(digest(r[0])!=r[1] for r in loaded): raise ValueError('EXACT_READBACK_MISMATCH')
    return dict(status='PASS_EXACT_DATABASE_READBACK',row_count=len(records),publication_id=publication,publication_digest=checksum)
