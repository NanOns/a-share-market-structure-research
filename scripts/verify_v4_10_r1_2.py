"""Independent publication/provenance oracle plus real SQL forgery probes."""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.v4.research_state import reduce_state
from src.v4.state_provenance import PostgresEngineeringLedger
from scripts.v4_10_r1_2_fixtures import publish_setup,accepted_bundle,setup_vector,publish,publisher_scope,real_boundary_bundle
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.promote_v4_09_accepted_head import bind

REQUIRED_TAGS=['hard_over_confirmation','required_unknown','PREWATCH_GT_SEED','CONFIRMED_GT_PREWATCH','stock_warm_na','upgrade_immediate',
    'downgrade_day1','downgrade_day2','hysteresis_break','risk_extreme','health_boundaries','tracking','expiry_boundary',
    'expiry_unknown_pause','expiry_baseline_frozen','next_session_reentry','same_day_reentry_forbidden','model_boundary_not_reentry',
    'scenario_unknown','all_maturity_preserved','all_tracking_preserved','health_unknown','no_fake_detector','prior_binding',
    'prior_full_schema_authenticity','prior_content_address_identity','calendar_lineage_binding','model_boundary_authorization',
    'hard_invalidation_provenance','state_input_field_provenance','input_publication_manifest_shape','followup_owner_gate','db_payload_identity_guard','real_model_boundary_transition','noop_model_boundary_rejected','implemented_field_status_authority','trusted_fact_cannot_be_suppressed','controlled_state_publisher_authority','semantic_forge_direct_sql_blocked_by_permission']

def sql_digest(pg,value):
    from psycopg.types.json import Jsonb
    return pg.execute('SELECT v4.state_digest_r1_1(%s)',(Jsonb(value),)).fetchone()[0]

def independent_input_audit(x,pg):
    """Read persisted authority directly; uses no runtime gate/helper to establish truth."""
    contract=json.loads((ROOT/'config/v4_10_input_provenance_r1_2.json').read_text(encoding='utf8'))
    schema=json.loads((ROOT/'config/v4_10_output_schema_r1_2.json').read_text(encoding='utf8'))
    checks={};details={};ids=x['input_publication_ids'];fields=x['input_provenance'];mode=x['mode']
    checks['manifest_shape']=type(ids) is list and bool(ids) and all(type(v) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/-]{0,511}',v) for v in ids) and len(set(ids))==len(ids)
    checks['manifest_digest']=checks['manifest_shape'] and x['input_publication_manifest_digest']==sql_digest(pg,dict(input_publication_ids=sorted(ids),fields=fields))
    def published(pub,kind):
        row=pg.execute('SELECT manifest,payload_digest,manifest_kind FROM v4.research_state_input_manifests WHERE publication_id=%s',(pub,)).fetchone()
        return row[0] if row and row[2]==kind and row[1]==sql_digest(pg,row[0]) and pub=='V4_10_INPUT:'+row[1] else None
    if mode=='ACCEPTED_FACT_INTERFACE':
        checks['all_input_publications_exist']=checks['manifest_shape'] and all(published(pub,'FACT_PUBLICATION') for pub in ids)
    boundary=x['model_boundary'];prior=x['prior_state']
    valid_boundary=type(boundary) is dict and boundary.get('status')=='NONE' and set(boundary)=={'status'}
    if type(boundary) is dict and boundary.get('status') in ('AUTHORIZED','SYNTHETIC_MODEL_BOUNDARY_FIXTURE'):
        m=published(boundary.get('publication_id'),'MODEL_BOUNDARY') if mode=='ACCEPTED_FACT_INTERFACE' else x.get('synthetic_boundary_manifest')
        expected=['boundary_contract_id','migration_manifest_id','from_model_contract_id','from_parameter_set_id','to_model_contract_id','to_parameter_set_id','effective_trade_date']
        valid_boundary=bool(prior and m and all(k in boundary and m.get(k)==boundary[k] for k in expected) and
            sql_digest(pg,m)==boundary.get('migration_manifest_sha256') and m.get('authorization')=='AUTHORIZED_ENGINEERING_INTERFACE' and
            boundary.get('from_model_contract_id')==prior.get('model_contract_id') and boundary.get('from_parameter_set_id')==prior.get('parameter_set_id') and
            boundary.get('to_model_contract_id')=='RESEARCH_STATE_V1' and boundary.get('to_parameter_set_id')=='V4_10_STATE_REDUCER_PARAMETER_SET_V1' and
            boundary.get('effective_trade_date')==x['trade_date'] and (boundary.get('from_model_contract_id'),boundary.get('from_parameter_set_id'))!=(boundary.get('to_model_contract_id'),boundary.get('to_parameter_set_id')))
    checks['boundary_manifest']=valid_boundary
    if prior:
        full=not (set(schema['required'])-set(prior))
        types=full and all(type(prior[n]) is str and bool(prior[n]) for n in schema['string_fields']) and all(type(prior[n]) is int and prior[n]>=0 for n in schema['counter_fields'])
        axes=full and all(prior[a] in (d[prior['entity_type']] if type(d) is dict else d) for a,d in schema['axes'].items())
        checks['prior_full_schema']=full and types and axes and not (prior['entity_type']=='STOCK' and prior['maturity']=='WARM')
        checks['prior_identity']=prior.get('publication_id')==('OLD_STATE:' if (x.get('prior_state_binding') or {}).get('ledger_id')=='V4_10_BOUNDARY_PRIOR_LEDGER_R1_2' else 'V4_10:')+sql_digest(pg,{k:v for k,v in prior.items() if k!='publication_id'})
        b=x['prior_state_binding'] or {}
        checks['prior_binding']=b.get('publication_id')==prior.get('publication_id') and b.get('payload_digest')==sql_digest(pg,prior)
        checks['prior_model']=((prior.get('model_contract_id'),prior.get('parameter_set_id'))==('RESEARCH_STATE_V1','V4_10_STATE_REDUCER_PARAMETER_SET_V1') or
            (valid_boundary and boundary.get('status')!='NONE'))
        if mode=='ACCEPTED_FACT_INTERFACE':
            if b.get('ledger_id')=='V4_10_BOUNDARY_PRIOR_LEDGER_R1_2':
                actual=pg.execute('SELECT source_payload,source_payload_digest,source_authority_digest FROM v4.research_state_boundary_prior_publications WHERE source_publication_id=%s',(b.get('source_publication_id'),)).fetchone()
                checks['prior_publication_exists']=bool(actual and actual[0]==prior and actual[1]==b.get('payload_digest')==b.get('source_payload_digest') and actual[2]==b.get('source_authority_digest'))
                checks['boundary_source_binding']=bool(valid_boundary and all(boundary.get(k)==b.get(k)==m.get(k) for k in ['source_publication_id','source_payload_digest','source_authority_digest']))
            else:
                actual=pg.execute('SELECT r.payload,r.payload_digest,p.consumer_contract_id,p.model_contract_id,p.parameter_set_id,p.producer_attestation FROM v4.research_state_engineering_results r JOIN v4.research_state_engineering_publications p USING(publication_id) WHERE r.publication_id=%s AND r.state_publication_id=%s',(b.get('engineering_publication_id'),b.get('publication_id'))).fetchone()
                checks['prior_publication_exists']=bool(prior.get('mode')=='ACCEPTED_FACT_INTERFACE' and b.get('ledger_id')=='V4_10_ENGINEERING_LEDGER_R1_1' and actual and actual[0]==prior and actual[1]==b.get('payload_digest') and actual[2:5]==tuple(b.get(k) for k in ['consumer_contract_id','model_contract_id','parameter_set_id']) and actual[5] and actual[5].get('producer_contract_id')=='V4_10_CONTROLLED_STATE_PUBLISHER_R1_2')
    cb=x['calendar_binding']
    cal=published(cb['publication_id'],'MARKET_CALENDAR') if mode=='ACCEPTED_FACT_INTERFACE' else x.get('synthetic_calendar_manifest')
    checks['calendar_identity']=bool(cal and cal.get('producer_contract_id')=='MARKET_CALENDAR_V1' and cal.get('lineage_id')==cb['lineage_id'] and sql_digest(pg,cal)==cb['manifest_digest'] and x['calendar_publication_id']==cb['publication_id'])
    sessions={s['session_index']:s['trade_date'] for s in cal['sessions']} if cal else {}
    checks['current_session_mapping']=sessions.get(x['session_index'])==x['trade_date']
    if prior:
        checks['prior_calendar']=prior.get('calendar_binding')==cb and prior.get('calendar_publication_id')==cb['publication_id'] and sessions.get(prior.get('session_index'))==prior.get('trade_date') and prior.get('session_index',-1)<=x['session_index']
    for field,definition in contract['fields'].items():
        f=fields.get(field,{});status=f.get('status');value=f.get('value');ok=not(set(contract['envelope_required'])-set(f))
        ok=ok and f.get('field')==field and f.get('time_role')==definition['time_role'] and f.get('required') is definition['required']
        if mode=='ACCEPTED_FACT_INTERFACE' and definition['implemented'] and status=='NOT_IMPLEMENTED':ok=False
        if status=='NOT_APPLICABLE':ok=ok and (x['entity_type'] in definition['not_applicable_entity_types'] or (field in ('frozen_invalidation','episode_invalidation_contract_id') and prior is None))
        if status in ('NOT_IMPLEMENTED','NOT_APPLICABLE'):
            ok=ok and value=='UNKNOWN' and f.get('quality')=='UNKNOWN' and f.get('publication_id') is None and f.get('source_output_digest') is None
            ok=ok and (f.get('producer_contract_id'),f.get('producer_parameter_set_id'))==(definition['producer_contract_id'],definition['producer_parameter_set_id'])
        elif status in ('IMPLEMENTED','SYNTHETIC'):
            payload=f.get('source_field_payload',{})
            ok=ok and payload.get('field')==field and payload.get('value')==value and f.get('source_output_digest')==sql_digest(pg,payload)
            if status=='SYNTHETIC':
                ok=ok and mode=='SYNTHETIC_CONTRACT_VECTOR' and str(f.get('publication_id')).startswith('SYNTHETIC_FACTS:') and str(f.get('producer_contract_id')).startswith('SYNTHETIC_')
            else:
                owner=(definition['implemented'] and x['entity_type'] in definition['accepted_entity_types'] and f.get('producer_contract_id')==definition['producer_contract_id'] and f.get('producer_parameter_set_id')==definition['producer_parameter_set_id'] and checks['manifest_shape'] and f.get('publication_id') in ids)
                if not owner and field in ('SEED','PREWATCH') and mode=='SYNTHETIC_CONTRACT_VECTOR' and x['entity_type'] in definition['accepted_entity_types']:
                    details[field]='EXPECTED_FAIL_CLOSED_UNKNOWN';continue
                pub=published(f.get('publication_id'),'FACT_PUBLICATION')
                ok=ok and owner and bool(pub and pub.get('fields',{}).get(field)=={k:v for k,v in f.items() if k!='publication_id'} and pub.get('entity_id')==x['entity_id'] and pub.get('entity_type')==x['entity_type'])
            index=x['session_index'] if definition['time_role']=='T' else x['session_index']-1
            ok=ok and checks['manifest_shape'] and f.get('publication_id') in ids and payload.get('session_index')==index and payload.get('trade_date')==sessions.get(index)
            if mode=='ACCEPTED_FACT_INTERFACE':
                try:
                    available=datetime.fromisoformat(f['system_available_at'].replace('Z','+00:00'))
                    cutoff=datetime.fromisoformat(x['cutoff'].replace('Z','+00:00'))
                    ok=ok and available.tzinfo is not None and cutoff.tzinfo is not None and available<=cutoff and cutoff.date().isoformat()==x['trade_date']
                except (ValueError,TypeError,AttributeError):ok=False
        else:ok=False
        if definition['domain']=='TRI':ok=ok and value in ('TRUE','FALSE','UNKNOWN')
        if field=='WARM' and x['entity_type']=='STOCK':ok=ok and status=='NOT_APPLICABLE'
        checks['field:'+field]=bool(ok)
        details[field]=dict(producer=f.get('producer_contract_id'),parameters=f.get('producer_parameter_set_id'),publication=f.get('publication_id'),time_role=f.get('time_role'),status=status)
    return dict(valid=all(checks.values()),checks=checks,fields=details)

def direct_sql_probes(pg):
    """Bypass persistence validation; recompute otherwise consistent attacks in SQL."""
    from psycopg.types.json import Jsonb
    import psycopg
    x,manifests=accepted_bundle();publish_setup(pg,manifests)
    row=reduce_state(x,ledger=PostgresEngineeringLedger(pg));publish(pg,x,'R1_1_SQL_PROBE_BASE')
    bx,bsetup=real_boundary_bundle();setup_vector(pg,bsetup)
    boundary_row=reduce_state(bx,ledger=PostgresEngineeringLedger(pg));publish(pg,bx,'R1_1_SQL_BOUNDARY_BASE')
    columns=[r[0] for r in pg.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='v4' AND table_name='research_state_engineering_results' ORDER BY ordinal_position").fetchall()]
    errors={};checks={}
    for name in ['direct_sql_forged_payload_digest','direct_sql_forged_state_publication_id','direct_sql_producer_lineage_mismatch','direct_sql_calendar_binding_mismatch',
        'direct_sql_boundary_manifest_field_mismatch','direct_sql_unpublished_extra_input','direct_sql_null_cutoff']:
        is_boundary=name=='direct_sql_boundary_manifest_field_mismatch'
        attacked=deepcopy(boundary_row if is_boundary else row)
        if name=='direct_sql_producer_lineage_mismatch':
            attacked['input_provenance']['risk']['producer_contract_id']='CALLER_FORGED_PRODUCER'
            attacked['input_publication_manifest_digest']=sql_digest(pg,dict(input_publication_ids=attacked['input_publication_ids'],fields=attacked['input_provenance']))
        if name=='direct_sql_calendar_binding_mismatch':attacked['calendar_binding']['lineage_id']='CALLER_FORGED_CALENDAR'
        if is_boundary:attacked['boundary_event']['authorized_manifest']['migration_manifest_id']='CALLER_FORGED_MIGRATION'
        if name=='direct_sql_unpublished_extra_input':
            attacked['input_publication_ids']=sorted(attacked['input_publication_ids']+['UNPUBLISHED_EXTRA_INPUT'])
            attacked['input_publication_manifest_digest']=sql_digest(pg,dict(input_publication_ids=attacked['input_publication_ids'],fields=attacked['input_provenance']))
        if name=='direct_sql_null_cutoff':attacked['cutoff']=None
        attacked['publication_id']='V4_10:'+sql_digest(pg,{k:v for k,v in attacked.items() if k!='publication_id'})
        if name=='direct_sql_forged_state_publication_id':attacked['publication_id']='V4_10:'+'f'*64
        checksum=sql_digest(pg,attacked)
        if name=='direct_sql_forged_payload_digest':checksum='f'*64
        overrides=dict(publication_id='R1_1_ATTACK:'+name,state_publication_id=attacked['publication_id'],payload=Jsonb(attacked),payload_digest=checksum,
            input_provenance=Jsonb(attacked['input_provenance']),input_publication_manifest_digest=attacked['input_publication_manifest_digest'],
            calendar_lineage_id=attacked['calendar_binding']['lineage_id'],boundary_event=Jsonb(attacked['boundary_event']),input_publication_ids=Jsonb(attacked['input_publication_ids']))
        select=[];params=[]
        for column in columns:
            if column in overrides:select.append('%s');params.append(overrides[column])
            else:select.append('r."'+column+'"')
        expected={'direct_sql_forged_payload_digest':'STATE_PAYLOAD_DIGEST_MISMATCH','direct_sql_forged_state_publication_id':'STATE_CONTENT_ADDRESS_IDENTITY_MISMATCH',
            'direct_sql_producer_lineage_mismatch':'STATE_FIELD_PRODUCER_LINEAGE_MISMATCH','direct_sql_calendar_binding_mismatch':'STATE_CALENDAR_LINEAGE_MISMATCH',
            'direct_sql_boundary_manifest_field_mismatch':'STATE_BOUNDARY_AUTHORIZATION_MISMATCH','direct_sql_unpublished_extra_input':'STATE_INPUT_PUBLICATION_NOT_IN_TRUSTED_LEDGER',
            'direct_sql_null_cutoff':'STATE_CUTOFF_REQUIRED'}[name]
        try:
            with pg.transaction():
                pg.execute('SET LOCAL ROLE v4_10_reducer_publisher_r1_2')
                pg.execute('''INSERT INTO v4.research_state_engineering_publications(publication_id,model_contract_id,consumer_contract_id,parameter_set_id,publication_digest,row_count,acceptance_scope,producer_attestation)
                    VALUES (%s,'RESEARCH_STATE_V1','V4_10_REDUCER_INTERFACE_V1','V4_10_STATE_REDUCER_PARAMETER_SET_V1',%s,1,'ENGINEERING_INTERFACE_ONLY',%s)''',
                    (overrides['publication_id'],sql_digest(pg,[attacked]),Jsonb(dict(producer_contract_id='V4_10_CONTROLLED_STATE_PUBLISHER_R1_2',input_request_digest='a'*64,publication_digest=sql_digest(pg,[attacked])))))
                pg.execute('INSERT INTO v4.research_state_engineering_results('+','.join('"'+c+'"' for c in columns)+') SELECT '+','.join(select)+
                    " FROM v4.research_state_engineering_results r WHERE r.publication_id=%s",params+['R1_1_SQL_BOUNDARY_BASE' if is_boundary else 'R1_1_SQL_PROBE_BASE'])
        except psycopg.Error as e:checks[name]=expected in str(e);errors[name]=str(e).split('\n')[0]
        else:checks[name]=False
    more,more_errors=authority_sql_probes(pg,row,boundary_row)
    checks.update(more);errors.update(more_errors)
    return checks,errors

def authority_sql_probes(pg,row,boundary_row):
    import psycopg
    from psycopg.types.json import Jsonb
    from src.v4.research_state_persistence import publish_state,persist
    checks={};errors={}
    from scripts.build_v4_10_r1_2_vectors import sector_unknown_bundle
    sx,sms=sector_unknown_bundle();publish_setup(pg,sms);sector_row=reduce_state(sx,ledger=PostgresEngineeringLedger(pg));publish(pg,sx,'R1_2_SQL_DQ5_BASE')
    tx,tms=accepted_bundle();f=tx['input_provenance']['core_price_damage'];f.update(value='TRUE',quality='KNOWN');f['source_field_payload']['value']='TRUE';f['source_output_digest']=sql_digest(pg,f['source_field_payload']);tms[1]['fields']['core_price_damage']={k:v for k,v in f.items() if k!='publication_id'}
    pub='V4_10_INPUT:'+sql_digest(pg,tms[1]);tx['input_publication_ids']=[pub]
    for ff in tx['input_provenance'].values():
        if ff['status']=='IMPLEMENTED':ff['publication_id']=pub
    tx['input_publication_manifest_digest']=sql_digest(pg,dict(input_publication_ids=tx['input_publication_ids'],fields=tx['input_provenance']))
    publish_setup(pg,tms);truth_row=reduce_state(tx,ledger=PostgresEngineeringLedger(pg));publish(pg,tx,'R1_2_SQL_TRUE_BASE')
    def rejected(name,operation,phrase):
        try:
            with pg.transaction():operation()
        except psycopg.Error as e:checks[name]=phrase in str(e);errors[name]=str(e).split('\n')[0]
        else:checks[name]=False
    with pg.transaction():
        pg.execute('SAVEPOINT ordinary_role_scope');pg.execute('CREATE ROLE v410_r1_2_ordinary_writer NOLOGIN')
        pg.execute('GRANT v4_10_state_reader_r1_2 TO v410_r1_2_ordinary_writer')
        forged=deepcopy(row);forged.update(maturity='CONFIRMED',validity='VALID',state_freshness='FRESH',final_eligibility='TRUE',transition_reasons=['CALLER_SEMANTIC_FORGE'])
        forged['publication_id']='V4_10:'+sql_digest(pg,{k:v for k,v in forged.items() if k!='publication_id'})
        forged_digest=sql_digest(pg,forged)
        def ordinary_insert(table):
            pg.execute('SET LOCAL ROLE v410_r1_2_ordinary_writer')
            if table=='research_state_engineering_results':
                # All identities/source manifests valid; this is a semantic forgery.
                columns=[r[0] for r in pg.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='v4' AND table_name='research_state_engineering_results' ORDER BY ordinal_position").fetchall()]
                changes=dict(state_publication_id=forged['publication_id'],payload=Jsonb(forged),payload_digest=forged_digest,maturity='CONFIRMED',validity='VALID',state_freshness='FRESH',final_eligibility='TRUE',transition_reasons=Jsonb(forged['transition_reasons']))
                values=[];params=[]
                for column in columns:
                    if column in changes:values.append('%s');params.append(changes[column])
                    else:values.append('r."'+column+'"')
                pg.execute('INSERT INTO v4.research_state_engineering_results('+','.join('"'+c+'"' for c in columns)+') SELECT '+','.join(values)+" FROM v4.research_state_engineering_results r WHERE publication_id='R1_1_SQL_PROBE_BASE'",params)
            else:pg.execute('INSERT INTO v4.research_state_engineering_publications SELECT * FROM v4.research_state_engineering_publications LIMIT 1')
        rejected('ordinary_semantic_forge_insert_blocked',lambda:ordinary_insert('research_state_engineering_results'),'permission denied for table research_state_engineering_results')
        rejected('ordinary_publication_insert_blocked',lambda:ordinary_insert('research_state_engineering_publications'),'permission denied for table research_state_engineering_publications')
        with publisher_scope(pg):checks['controlled_publisher_positive_path']=publish_state(pg,[accepted_bundle()[0]],'R1_2_CONTROLLED_POSITIVE')['status']=='PASS_EXACT_DATABASE_READBACK'
        pg.execute('SET LOCAL ROLE v410_r1_2_ordinary_writer')
        checks['ordinary_select_allowed']=pg.execute('SELECT count(*) FROM v4.research_state_engineering_results').fetchone()[0]>0
        try:publish_state(pg,[accepted_bundle()[0]],'ORDINARY_API_FORGE')
        except ValueError as e:checks['ordinary_select_allowed']&='AUTHORIZED_REDUCER_PUBLISHER_ROLE_REQUIRED' in str(e)
        pg.execute('ROLLBACK TO SAVEPOINT ordinary_role_scope')
    columns=[r[0] for r in pg.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='v4' AND table_name='research_state_engineering_results' ORDER BY ordinal_position").fetchall()]
    def insert_attack(attacked,name,base):
        attacked['publication_id']='V4_10:'+sql_digest(pg,{k:v for k,v in attacked.items() if k!='publication_id'})
        checksum=sql_digest(pg,attacked);pub='R1_2_SQL_ATTACK:'+name
        overrides=dict(publication_id=pub,state_publication_id=attacked['publication_id'],payload=Jsonb(attacked),payload_digest=checksum,
            input_provenance=Jsonb(attacked['input_provenance']),input_publication_manifest_digest=attacked['input_publication_manifest_digest'],boundary_event=Jsonb(attacked['boundary_event']))
        selects=[];params=[]
        for column in columns:
            if column in overrides:selects.append('%s');params.append(overrides[column])
            else:selects.append('r."'+column+'"')
        pg.execute('SET LOCAL ROLE v4_10_reducer_publisher_r1_2')
        pg.execute("INSERT INTO v4.research_state_engineering_publications(publication_id,model_contract_id,consumer_contract_id,parameter_set_id,publication_digest,row_count,acceptance_scope,producer_attestation) VALUES (%s,'RESEARCH_STATE_V1','V4_10_REDUCER_INTERFACE_V1','V4_10_STATE_REDUCER_PARAMETER_SET_V1',%s,1,'ENGINEERING_INTERFACE_ONLY',%s)",
            (pub,sql_digest(pg,[attacked]),Jsonb(dict(producer_contract_id='V4_10_CONTROLLED_STATE_PUBLISHER_R1_2',input_request_digest='a'*64,publication_digest=sql_digest(pg,[attacked])))))
        pg.execute('INSERT INTO v4.research_state_engineering_results('+','.join('"'+c+'"' for c in columns)+') SELECT '+','.join(selects)+' FROM v4.research_state_engineering_results r WHERE publication_id=%s',params+[base])
    statuses=[]
    for field in ['SEED','PREWATCH','core_price_damage','risk','delta3','suspended','dq5']:
        attacked=deepcopy(sector_row if field=='dq5' else truth_row if field=='core_price_damage' else row);f=attacked['input_provenance'][field]
        f.update(status='NOT_IMPLEMENTED',value='UNKNOWN',quality='UNKNOWN',publication_id=None,source_output_digest=None,source_field_payload={},system_available_at=None)
        attacked['input_publication_manifest_digest']=sql_digest(pg,dict(input_publication_ids=attacked['input_publication_ids'],fields=attacked['input_provenance']))
        name='status_suppress_'+field
        base='R1_2_SQL_DQ5_BASE' if field=='dq5' else 'R1_2_SQL_TRUE_BASE' if field=='core_price_damage' else 'R1_1_SQL_PROBE_BASE'
        rejected(name,lambda a=attacked,n=name,b=base:insert_attack(a,n,b),'STATE_IMPLEMENTED_FIELD_CANNOT_BE_NOT_IMPLEMENTED');statuses.append(checks.pop(name))
    checks['direct_sql_implemented_status_suppression']=all(statuses)
    attacked=deepcopy(boundary_row);b=attacked['boundary_event']['authorized_manifest'];b.update(from_model_contract_id=b['to_model_contract_id'],from_parameter_set_id=b['to_parameter_set_id'])
    rejected('direct_sql_noop_boundary',lambda:insert_attack(attacked,'noop','R1_1_SQL_BOUNDARY_BASE'),'MODEL_BOUNDARY_NOOP_FORBIDDEN')
    attacked=deepcopy(row);f=attacked['input_provenance']['core_price_damage'];f.update(status='NOT_APPLICABLE',value='UNKNOWN',quality='UNKNOWN',publication_id=None,source_output_digest=None,source_field_payload={},system_available_at=None)
    attacked['input_publication_manifest_digest']=sql_digest(pg,dict(input_publication_ids=attacked['input_publication_ids'],fields=attacked['input_provenance']))
    rejected('direct_sql_not_applicable_scope',lambda:insert_attack(attacked,'wrong_na','R1_1_SQL_PROBE_BASE'),'STATE_NOT_APPLICABLE_SCOPE_MISMATCH')
    return checks,errors

def check_vectors(pg):
    vectors=json.loads((ROOT/'config/v4_10_machine_vectors_r1_2.json').read_text(encoding='utf8'))['vectors']
    schema=json.loads((ROOT/'config/v4_10_output_schema_r1_2.json').read_text(encoding='utf8'))
    checks=[];coverage={};outputs=[];audits=[]
    for v in vectors:
        if v['kind']=='SQL':continue
        setup=v.get('ledger_setup')
        setup_vector(pg,setup)
        audit=independent_input_audit(v['input'],pg);audits.append(dict(id=v['id'],**audit))
        for tag in v['coverage']:coverage.setdefault(tag,[]).append(v['id'])
        try:
            ledger=PostgresEngineeringLedger(pg) if v['input']['mode']=='ACCEPTED_FACT_INTERFACE' else None
            r=reduce_state(v['input'],ledger=ledger);outputs.append(r)
            diff={k:dict(expected=e,actual=r.get(k)) for k,e in v['expected'].items() if e!=r.get(k)}
            errors=[]
            if v['expected_error']:errors.append('EXPECTED_ERROR_NOT_RAISED')
            if not audit['valid']:errors.append('INDEPENDENT_INPUT_AUTHORITY_INVALID')
            if set(schema['required'])-set(r):errors.append('OUTPUT_SCHEMA_MISSING_FIELDS')
            if r['publication_id']!='V4_10:'+sql_digest(pg,{k:e for k,e in r.items() if k!='publication_id'}):errors.append('OUTPUT_CONTENT_ADDRESS_MISMATCH')
            if r['state_freshness']=='STALE' and r['final_eligibility']!='UNKNOWN':errors.append('STALE_ELIGIBLE')
            if r['boundary_event'] and 'REENTERED' in r['transition_reasons']:errors.append('BOUNDARY_FAKE_REENTRY')
            if r['boundary_event'] and v['input']['prior_state']['episode_id'] and v['input']['prior_state']['episode_id'] not in r['preserved_followup_episode_ids']:errors.append('BOUNDARY_LOST_OLD_FOLLOWUP')
            if r['parent_episode_id'] and r['parent_episode_id'] not in r['preserved_followup_episode_ids']:errors.append('REENTRY_LOST_OLD_FOLLOWUP')
            if r['boundary_event'] and r['episode_id'] and r['episode_id']==v['input']['prior_state']['episode_id']:errors.append('BOUNDARY_EPISODE_COLLISION')
            if v['id']=='real_boundary_current_episode_namespace_separate':
                # Confirmation remains unavailable: do not invent an enrolled episode.
                # Independently derive the existing current-model identity namespace.
                fresh='EP:'+sql_digest(pg,[r['entity_id'],r['entity_type'],r['session_index'],r['model_contract_id'],r['parameter_set_id'],r['input_publication_ids']])
                if fresh==v['input']['prior_state']['episode_id'] or r['episode_id'] is not None or r['final_eligibility']!='UNKNOWN':errors.append('BOUNDARY_EPISODE_NAMESPACE_OR_FAKE_ENROLLMENT')
            checks.append(dict(id=v['id'],passed=not diff and not errors,differences=diff,invariant_errors=errors))
        except ValueError as e:
            expected=bool(v['expected_error'] and v['expected_error'] in str(e))
            checks.append(dict(id=v['id'],passed=expected and not audit['valid'],error=str(e),independent_rejection=not audit['valid']))
    sql_checks,sql_errors=direct_sql_probes(pg)
    for v in vectors:
        if v['kind']=='SQL':
            checks.append(dict(id=v['id'],passed=sql_checks[v['id']],error=sql_errors.get(v['id'])))
            for tag in v['coverage']:coverage.setdefault(tag,[]).append(v['id'])
    missing=sorted(set(REQUIRED_TAGS)-set(coverage));mismatch=sum(not r['passed'] for r in checks)
    status='PASS' if not missing and not mismatch else 'FAIL'
    result=dict(contract_id='V4_10_R1_2_INDEPENDENT_POSTCHECK',status=status,vector_count=len(vectors),mismatch_count=mismatch,
        required_tags_hardcoded=REQUIRED_TAGS,missing_coverage=missing,oracle='STATIC_EXPECTATIONS + independent direct SQL authority/schema/content-address/calendar/field checks; no runtime gate as oracle',
        source_vectors=bind('config/v4_10_machine_vectors_r1_2.json'),checks=checks,independent_authority_audits=audits,sql_probes=sql_checks)
    covered=dict(contract_id='V4_10_R1_2_MACHINE_VECTOR_COVERAGE',status=status,vector_count=len(vectors),original_semantic_vector_count=98,original_r1_1_vector_count=149,
        coverage=coverage,required_tags_hardcoded=REQUIRED_TAGS,missing_required_tags=missing,
        axes={axis:sorted({r[axis] for r in outputs}) for axis in schema['axes']},
        unknown_semantics=dict(maturity='last-known enum retained',tracking='last-known enum retained',scenario='value retained + UNKNOWN status',
            health='UNKNOWN',validity='UNKNOWN',eligibility='UNKNOWN',state_freshness='STALE'))
    return result,covered

def write_evidence(result,covered):
    prefix=ROOT/'reports/v4_10'
    atomic_json(prefix/'V4_10_R1_2_INDEPENDENT_POSTCHECK.json',result)
    atomic_json(prefix/'V4_10_R1_2_MACHINE_VECTOR_COVERAGE.json',covered)
    groups=dict(PRIOR_LINEAGE=['prior_full_schema_authenticity','prior_content_address_identity','calendar_lineage_binding'],
        MODEL_BOUNDARY=['model_boundary_authorization','real_model_boundary_transition','noop_model_boundary_rejected'],INPUT_PROVENANCE=['hard_invalidation_provenance','state_input_field_provenance','followup_owner_gate','implemented_field_status_authority','trusted_fact_cannot_be_suppressed'],
        INPUT_MANIFEST_SHAPE=['input_publication_manifest_shape'],CONTROLLED_PUBLISHER=['controlled_state_publisher_authority','semantic_forge_direct_sql_blocked_by_permission'])
    for name,tags in groups.items():
        ids={v for tag in tags for v in covered['coverage'][tag]}
        relevant=[c for c in result['checks'] if c['id'] in ids]
        atomic_json(prefix/f'V4_10_R1_2_{name}_ACCEPTANCE.json',dict(status='PASS' if relevant and all(c['passed'] for c in relevant) else 'FAIL',
            contract_id='V4_10_R1_2_'+name+'_ACCEPTANCE',tags=tags,checks=relevant,
            independent_audits=[a for a in result['independent_authority_audits'] if a['id'] in ids],postcheck=bind('reports/v4_10/V4_10_R1_2_INDEPENDENT_POSTCHECK.json')))

def main():
    from scripts.run_v4_08_r3_isolated_verification import disposable_cluster,apply_migrations
    import psycopg
    with disposable_cluster(Path(r'E:\Postgres\bin')) as (dsn,temp):
        with psycopg.connect(dsn) as pg:
            apply_migrations(pg);result,covered=check_vectors(pg)
    write_evidence(result,covered)
    print(json.dumps(dict(status=result['status'],vector_count=result['vector_count'],mismatch_count=result['mismatch_count'],
        failed=[c for c in result['checks'] if not c['passed']])))
    return result['status']!='PASS'

if __name__=='__main__':sys.exit(main())
