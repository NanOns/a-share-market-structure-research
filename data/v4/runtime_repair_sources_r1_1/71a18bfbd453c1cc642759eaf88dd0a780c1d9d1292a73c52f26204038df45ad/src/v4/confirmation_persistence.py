"""Append-only controlled candidate publisher; never writes final state or a head."""
from .confirmation import detect_confirmation,digest,ConfirmationError
from .confirmation_events import state_events
CONSUMER='V4_11_CANDIDATE_ENGINEERING_CONSUMER_V1'

def _insert(pg,table,pid,payload,columns,values):
    from psycopg.types.json import Jsonb
    old=pg.execute('SELECT payload,payload_digest FROM '+table+' WHERE publication_id=%s',(pid,)).fetchone()
    checksum=digest(payload)
    if old:
        if old!=(payload,checksum):raise ConfirmationError('RETRY_PUBLICATION_PAYLOAD_CONFLICT')
        return False
    fields=['publication_id','payload','payload_digest',*columns]
    pg.execute('INSERT INTO '+table+'('+','.join(fields)+') VALUES ('+','.join(['%s']*len(fields))+')',(pid,Jsonb(payload),checksum,*values))
    return True

def publish(pg,inputs,*,consumer_contract_id=CONSUMER,d2_publication=None,prior_session_head=None,revision_of=None):
    from psycopg.types.json import Jsonb
    if consumer_contract_id!=CONSUMER:raise ConfirmationError('CONSUMER_IDENTITY_MISMATCH')
    facts=detect_confirmation(inputs)
    events=None
    if (d2_publication is None)!=(prior_session_head is None):raise ConfirmationError('D2_AND_FROZEN_PRIOR_REQUIRED_TOGETHER')
    if d2_publication is not None:
        if inputs['mode']!='SYNTHETIC_ENGINEERING_VECTOR':raise ConfirmationError('REAL_D2_EVENT_PUBLICATION_NOT_AUTHORIZED')
        from .confirmation_d2_bridge import verify_d2_publication
        states=verify_d2_publication(d2_publication)
        if {r['entity_id'] for r in states}!={r['security_id'] for r in facts['rows']}:raise ConfirmationError('D0_D2_ENTITY_MISMATCH')
        # Each CONFIRMED envelope must contain this exact D0 row, not a supplied final axis.
        byid={r['security_id']:r for r in facts['rows']}
        for x in d2_publication['inputs']:
            f=x['input_provenance']['CONFIRMED'];r=byid[x['entity_id']]
            if f['publication_id']!='SYNTHETIC_FACTS:'+r['publication_id'] or f['value']!=r['confirmation_status']:raise ConfirmationError('D0_D2_FACT_PUBLICATION_MISMATCH')
            if f['source_field_payload'].get('confirmation_row_digest')!=digest(r) or x['input_provenance']['scenario']['value']!=(r['primary_scenario'] or 'NONE'):raise ConfirmationError('D0_D2_WHOLE_FACT_BINDING_MISMATCH')
        events=state_events(d2_publication,prior_session_head,revision_of=revision_of)
    with pg.transaction():
        from psycopg import sql
        previous_role=pg.execute('SELECT current_user').fetchone()[0]
        pg.execute('SET LOCAL ROLE v4_11_candidate_publisher_r1')
        if _insert(pg,'v4.confirmation_candidate_publications_r1',facts['publication_id'],facts,['consumer_contract_id','producer_contract_id','parameter_set_id'],[CONSUMER,'CONFIRMATION_DETECTOR_V1','V4_11_CONFIRMATION_PARAMETER_SET_V1']):
            for r in facts['rows']:pg.execute('INSERT INTO v4.confirmation_candidate_facts_r1 VALUES (%s,%s,%s,%s)',(facts['publication_id'],r['security_id'],CONSUMER,Jsonb(r)))
        actual=pg.execute('SELECT payload FROM v4.confirmation_candidate_facts_r1 WHERE publication_id=%s ORDER BY security_id',(facts['publication_id'],)).fetchall()
        if [r[0] for r in actual]!=facts['rows']:raise ConfirmationError('CONFIRMATION_FACT_READBACK_MISMATCH')
        if events is not None:
            e=dict(contract_id='STATE_EVENT_V1',d2_publication=d2_publication,frozen_prior_session_head=prior_session_head,rows=events,accepted=False,consumer_contract_id=CONSUMER)
            ep='V4_11_EVENTS:'+digest(e)
            if _insert(pg,'v4.confirmation_candidate_event_publications_r1',ep,e,['confirmation_publication_id','consumer_contract_id'],[facts['publication_id'],CONSUMER]):
                for r in events:pg.execute('INSERT INTO v4.confirmation_candidate_events_r1 VALUES (%s,%s,%s,%s)',(ep,r['entity_id'],CONSUMER,Jsonb(r)))
            actual=pg.execute('SELECT payload FROM v4.confirmation_candidate_events_r1 WHERE publication_id=%s ORDER BY entity_id',(ep,)).fetchall()
            if [r[0] for r in actual]!=sorted(events,key=lambda r:r['entity_id']):raise ConfirmationError('STATE_EVENT_READBACK_MISMATCH')
        pg.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(previous_role)))
    return dict(confirmation_publication_id=facts['publication_id'],event_publication_id=ep if events is not None else None)
