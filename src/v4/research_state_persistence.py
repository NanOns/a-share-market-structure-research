"""Explicit append-only engineering publications with exact readback and revisions."""
from .research_state import digest,CONTRACT,PARAMETERS,load_package
from .state_provenance import validate_output

def persist(pg, records, publication_id, revision_of=None):
    from psycopg.types.json import Jsonb
    if not records or not publication_id:raise ValueError('EMPTY_RESEARCH_STATE_PUBLICATION')
    schema=load_package()[0]
    records=sorted(records,key=lambda r:(r['entity_id'],r['entity_type'],r['episode_id'] or 'NO_EPISODE'))
    keys=[(r['entity_id'],r['entity_type'],r['episode_id'] or 'NO_EPISODE') for r in records]
    if len(set(keys))!=len(keys) or len({r['publication_id'] for r in records})!=len(records):
        raise ValueError('DUPLICATE_RESEARCH_STATE_ENTITY_EPISODE')
    for row in records:
        validate_output(row)
        if row['model_contract_id']!=CONTRACT or row['parameter_set_id']!=PARAMETERS:
            raise ValueError('RESEARCH_STATE_MODEL_PARAMETER_MISMATCH')
        expected=dict(row);state_id=expected.pop('publication_id')
        if state_id!='V4_10:'+digest(expected):raise ValueError('STATE_PUBLICATION_CONTENT_ID_MISMATCH')
        for axis,domain in schema['axes'].items():
            if row[axis] not in (domain[row['entity_type']] if isinstance(domain,dict) else domain):raise ValueError('STATE_AXIS_DOMAIN_MISMATCH')
    checksum=digest(records)
    with pg.transaction():
        pg.execute('''INSERT INTO v4.research_state_engineering_publications
            (publication_id,revision_of,model_contract_id,consumer_contract_id,parameter_set_id,publication_digest,row_count,acceptance_scope)
            VALUES (%s,%s,%s,'V4_10_REDUCER_INTERFACE_V1',%s,%s,%s,'ENGINEERING_INTERFACE_ONLY') ON CONFLICT DO NOTHING''',
            (publication_id,revision_of,CONTRACT,PARAMETERS,checksum,len(records)))
        actual=pg.execute('''SELECT publication_digest,row_count,revision_of,model_contract_id,parameter_set_id,consumer_contract_id
            FROM v4.research_state_engineering_publications WHERE publication_id=%s''',(publication_id,)).fetchone()
        if actual!=(checksum,len(records),revision_of,CONTRACT,PARAMETERS,'V4_10_REDUCER_INTERFACE_V1'):
            raise ValueError('APPEND_ONLY_STATE_PUBLICATION_CONFLICT')
        for row in records:
            pg.execute('''INSERT INTO v4.research_state_engineering_results
                (publication_id,state_publication_id,entity_id,entity_type,episode_key,episode_id,parent_episode_id,trade_date,session_index,
                 model_contract_id,parameter_set_id,maturity,health,validity,tracking,scenario,state_freshness,final_eligibility,
                 prior_state_binding,input_publication_ids,matched_predicates,unknown_predicates,transition_reasons,payload,payload_digest,
                 interface_contract_id,canonicalization_contract_id,calendar_publication_id,calendar_lineage_id,calendar_manifest_digest,
                 input_publication_manifest_digest,input_provenance,boundary_event,prior_engineering_publication_id,prior_row_payload_digest)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
                (publication_id,row['publication_id'],row['entity_id'],row['entity_type'],row['episode_id'] or 'NO_EPISODE')+
                tuple(row[k] for k in ['episode_id','parent_episode_id','trade_date','session_index','model_contract_id','parameter_set_id',
                    'maturity','health','validity','tracking','scenario','state_freshness','final_eligibility'])+
                tuple(Jsonb(row[k]) for k in ['prior_state_binding','input_publication_ids','matched_predicates','unknown_predicates','transition_reasons'])+
                (Jsonb(row),digest(row),row['interface_contract_id'],row['canonicalization_contract_id'],row['calendar_publication_id'],
                 row['calendar_binding']['lineage_id'],row['calendar_binding']['manifest_digest'],row['input_publication_manifest_digest'],
                 Jsonb(row['input_provenance']),Jsonb(row['boundary_event']),
                 row['prior_state_binding'].get('engineering_publication_id') if row['prior_state_binding'] else None,
                 row['prior_state_binding']['payload_digest'] if row['prior_state_binding'] else None))
        loaded=pg.execute('''SELECT payload,payload_digest FROM v4.research_state_engineering_results
            WHERE publication_id=%s ORDER BY entity_id COLLATE "C",entity_type COLLATE "C",episode_key COLLATE "C"''',(publication_id,)).fetchall()
        if [r[0] for r in loaded]!=records or any(digest(r[0])!=r[1] for r in loaded):raise ValueError('STATE_EXACT_READBACK_MISMATCH')
    return dict(status='PASS_EXACT_DATABASE_READBACK',publication_id=publication_id,publication_digest=checksum,row_count=len(records),revision_of=revision_of)
