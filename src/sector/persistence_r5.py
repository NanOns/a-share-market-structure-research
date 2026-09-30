"""Append-only R5 candidate persistence with exact readback and retry checks."""
from sector.machine_ast_r3 import ast_digest


def persist(pg, records):
    from psycopg.types.json import Jsonb
    if not records:raise ValueError('EMPTY_R5_PUBLICATION')
    first=records[0]
    digest=ast_digest(records)
    pg.execute('INSERT INTO v4.sector_algorithm_publications_r5 (publication_id,target_trade_date,membership_snapshot_id,parameter_set_id,input_digests,publication_digest,acceptance_scope) VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
        (first['publication_id'],first['target_trade_date'],first['membership_snapshot_id'],first['parameter_set_id'],Jsonb(first['input_digests']),digest,'ENGINEERING_CANDIDATE'))
    actual=pg.execute('SELECT publication_digest FROM v4.sector_algorithm_publications_r5 WHERE publication_id=%s',(first['publication_id'],)).fetchone()[0].strip()
    if actual!=digest:raise ValueError('APPEND_ONLY_R5_PUBLICATION_CONFLICT')
    for r in records:
        payload_digest=ast_digest(r)
        state=r.get('output_state',r.get('confirmed_raw','PRIMITIVES'))
        pg.execute('INSERT INTO v4.sector_algorithm_results_r5 (publication_id,sector_id,sector_type,model_contract_id,parameter_set_id,membership_snapshot_id,target_trade_date,max_source_date,input_digests,output_state,predicates,quality,reason_codes,payload,payload_digest) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
            (r['publication_id'],r['sector_id'],r['sector_type'],r['model_contract_id'],r['parameter_set_id'],r['membership_snapshot_id'],r['target_trade_date'],r['max_source_date'],Jsonb(r['input_digests']),state,Jsonb(r.get('predicates',{})),r.get('quality','PARTIAL_UNKNOWN'),Jsonb(r.get('reason_codes',[])),Jsonb(r),payload_digest))
        loaded=pg.execute('SELECT payload,payload_digest FROM v4.sector_algorithm_results_r5 WHERE publication_id=%s AND sector_id=%s AND model_contract_id=%s',(r['publication_id'],r['sector_id'],r['model_contract_id'])).fetchone()
        if loaded[0]!=r or loaded[1].strip()!=payload_digest:raise ValueError('R5_EXACT_READBACK_OR_IDEMPOTENCY_MISMATCH')
    return dict(status='PASS_EXACT_DATABASE_READBACK',row_count=len(records),publication_digest=digest,
        publication_id=first['publication_id'],target_trade_date=first['target_trade_date'],accepted_scope='ENGINEERING_CANDIDATE')
