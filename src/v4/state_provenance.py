"""One field provenance gate plus trusted engineering-ledger resolution.

Accepted input data never supplies its own resolver. The PostgreSQL ledger is an
out-of-band trusted owner boundary; ordinary table writers cannot register manifests.
Synthetic namespace is explicit and cannot cross into the accepted interface.
"""
from copy import deepcopy
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
from .state_identity import digest, state_id, CANONICALIZATION, INTERFACE

ROOT=Path(__file__).resolve().parents[2]
CONTRACT='RESEARCH_STATE_V1'
PARAMETERS='V4_10_STATE_REDUCER_PARAMETER_SET_V1'
CONSUMER='V4_10_REDUCER_INTERFACE_V1'
LEDGER='V4_10_ENGINEERING_LEDGER_R1_1'
UNKNOWN='UNKNOWN'
PUBLICATION_ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:\-/]{0,511}$')

def _read(name):
    return json.loads((ROOT/f'config/v4_10_{name}_r1_2.json').read_text(encoding='utf8'))

def publication_ids(ids):
    if type(ids) is not list or not ids or any(type(v) is not str or not PUBLICATION_ID.fullmatch(v) for v in ids) or len(set(ids))!=len(ids):
        raise ValueError('INPUT_PUBLICATION_MANIFEST_SHAPE_INVALID')
    return sorted(ids)

def validate_output(row, *, permit_other_model=False, boundary_source=False):
    schema=_read('output_schema')
    if type(row) is not dict or set(schema['required'])-set(row):raise ValueError('PRIOR_FULL_SCHEMA_REQUIRED')
    for name in schema['string_fields']:
        if type(row[name]) is not str or not row[name]:raise ValueError('PRIOR_SCHEMA_TYPE_INVALID:'+name)
    for name in schema['nullable_string_fields']:
        if row[name] is not None and (type(row[name]) is not str or not row[name]):raise ValueError('PRIOR_SCHEMA_TYPE_INVALID:'+name)
    for name in schema['counter_fields']:
        if type(row[name]) is not int or row[name]<0:raise ValueError('PRIOR_SCHEMA_COUNTER_INVALID:'+name)
    for name in ['exit_session_index']:
        if row[name] is not None and (type(row[name]) is not int or row[name]<0 or row[name]>row['session_index']):raise ValueError('PRIOR_SCHEMA_COUNTER_INVALID:'+name)
    for name in ['matched_predicates','unknown_predicates','transition_reasons','preserved_followup_episode_ids']:
        if type(row[name]) is not list or any(type(v) is not str or not v for v in row[name]):raise ValueError('PRIOR_SCHEMA_ARRAY_INVALID:'+name)
    if row['improvement_baseline'] is not None:
        from decimal import Decimal
        if type(row['improvement_baseline']) not in (int,float) or not Decimal(str(row['improvement_baseline'])).is_finite():raise ValueError('PRIOR_BASELINE_INVALID')
    for name in ['raw_qualification','detector_statuses','input_provenance']:
        if type(row[name]) is not dict:raise ValueError('PRIOR_SCHEMA_OBJECT_INVALID:'+name)
    if row['boundary_event'] is not None and type(row['boundary_event']) is not dict:raise ValueError('PRIOR_BOUNDARY_SCHEMA_INVALID')
    if row['prior_state_binding'] is not None and type(row['prior_state_binding']) is not dict:raise ValueError('PRIOR_BINDING_SCHEMA_INVALID')
    if type(row['calendar_binding']) is not dict or {'publication_id','manifest_digest','lineage_id'}-set(row['calendar_binding']):raise ValueError('PRIOR_CALENDAR_SCHEMA_INVALID')
    if row['calendar_binding']['publication_id']!=row['calendar_publication_id']:raise ValueError('PRIOR_CALENDAR_IDENTITY_MISMATCH')
    if any(not re.fullmatch(r'[0-9a-f]{64}',row[n]) for n in ['input_digest','input_publication_manifest_digest']):raise ValueError('PRIOR_DIGEST_SCHEMA_INVALID')
    if set(row['input_provenance'])!=set(_read('input_provenance')['fields']):raise ValueError('PRIOR_FIELD_MANIFEST_INCOMPLETE')
    if any(v not in ('TRUE','FALSE','UNKNOWN') for v in row['raw_qualification'].values()):raise ValueError('PRIOR_RAW_QUALIFICATION_INVALID')
    if row['entity_type'] not in ('STOCK','SECTOR'):raise ValueError('PRIOR_ENTITY_TYPE_INVALID')
    for axis,domain in schema['axes'].items():
        allowed=domain[row['entity_type']] if type(domain) is dict else domain
        if row[axis] not in allowed:raise ValueError('ILLEGAL_PRIOR_AXIS:'+axis)
    if row['entity_type']=='STOCK' and row['maturity']=='WARM':raise ValueError('ILLEGAL_STOCK_WARM_PRIOR')
    if row['mode'] not in ('SYNTHETIC_CONTRACT_VECTOR','ACCEPTED_FACT_INTERFACE') or row['state_freshness'] not in ('FRESH','STALE') or row['final_eligibility'] not in ('TRUE','FALSE','UNKNOWN') or row['scenario_status'] not in ('KNOWN','UNKNOWN'):
        raise ValueError('PRIOR_ENUM_INVALID')
    if (not boundary_source and row['interface_contract_id']!=INTERFACE) or row['canonicalization_contract_id']!=CANONICALIZATION:
        raise ValueError('PRIOR_INTERFACE_IDENTITY_INVALID')
    if not permit_other_model and (row['model_contract_id']!=CONTRACT or row['parameter_set_id']!=PARAMETERS):raise ValueError('MODEL_BOUNDARY_REQUIRED')
    date.fromisoformat(row['trade_date'])
    cutoff=datetime.fromisoformat(row['cutoff'].replace('Z','+00:00'))
    if cutoff.tzinfo is None or cutoff.date()!=date.fromisoformat(row['trade_date']):raise ValueError('PRIOR_CUTOFF_INVALID')
    if row['downgrade_candidate'] is not None and row['downgrade_candidate'] not in schema['axes']['maturity']:raise ValueError('PRIOR_DOWNGRADE_CANDIDATE_INVALID')
    publication_ids(row['input_publication_ids'])
    if row['input_publication_manifest_digest']!=digest(dict(input_publication_ids=row['input_publication_ids'],fields=row['input_provenance'])):
        raise ValueError('PRIOR_INPUT_MANIFEST_DIGEST_MISMATCH')
    expected_id=('OLD_STATE:'+digest({k:v for k,v in row.items() if k!='publication_id'})) if boundary_source else state_id(row)
    if row['publication_id']!=expected_id:raise ValueError('PRIOR_CONTENT_ADDRESS_IDENTITY_MISMATCH')
    if row['state_freshness']=='STALE' and row['final_eligibility']!='UNKNOWN':raise ValueError('PRIOR_STALE_ELIGIBILITY_INVALID')
    if row['mode']=='ACCEPTED_FACT_INTERFACE' and row['state_freshness']=='STALE' and (row['validity']!='UNKNOWN' or row['health']!='UNKNOWN'):
        raise ValueError('PRIOR_STALE_AXES_INVALID')
    if row['parent_episode_id'] and row['parent_episode_id'] not in row['preserved_followup_episode_ids']:raise ValueError('PRIOR_FOLLOWUP_LINEAGE_INVALID')
    return row

class PostgresEngineeringLedger:
    """Read immutable publications from a DB authority, not from a caller-provided dict."""
    __slots__=('pg','ledger_id')
    def __init__(self,pg):
        identity=pg.execute('SELECT ledger_id,consumer_contract_id,model_contract_id,parameter_set_id FROM v4.research_state_lineage_ledger').fetchall()
        if identity!=[(LEDGER,CONSUMER,CONTRACT,PARAMETERS)]:raise ValueError('ENGINEERING_LEDGER_IDENTITY_MISMATCH')
        self.pg=pg;self.ledger_id=LEDGER

    def manifest(self,publication_id,kind):
        row=self.pg.execute('SELECT manifest,payload_digest,manifest_kind FROM v4.research_state_input_manifests WHERE publication_id=%s',(publication_id,)).fetchone()
        if row is None or row[2]!=kind or row[1]!=digest(row[0]) or publication_id!='V4_10_INPUT:'+digest(row[0]):
            raise ValueError('INPUT_PUBLICATION_NOT_IN_TRUSTED_LEDGER')
        if row[0]['mode']!='ACCEPTED_FACT_INTERFACE':raise ValueError('SYNTHETIC_PUBLICATION_IN_ACCEPTED_MODE')
        return row[0],row[1]

    def prior(self,binding,row):
        needed={'publication_id','payload_digest','engineering_publication_id','ledger_id','consumer_contract_id','model_contract_id','parameter_set_id'}
        if type(binding) is not dict or needed-set(binding):raise ValueError('PRIOR_PUBLICATION_MANIFEST_BINDING_REQUIRED')
        actual=self.pg.execute('''SELECT r.payload,r.payload_digest,p.consumer_contract_id,p.model_contract_id,p.parameter_set_id
            FROM v4.research_state_engineering_results r JOIN v4.research_state_engineering_publications p USING(publication_id)
            WHERE r.publication_id=%s AND r.state_publication_id=%s''',(binding['engineering_publication_id'],binding['publication_id'])).fetchone()
        if (actual is None or binding['ledger_id']!=self.ledger_id or actual[0]!=row or actual[1]!=digest(row) or binding['payload_digest']!=actual[1] or
                tuple(binding[k] for k in ['consumer_contract_id','model_contract_id','parameter_set_id'])!=actual[2:]):
            raise ValueError('PRIOR_NOT_IN_TRUSTED_ENGINEERING_PUBLICATION')
        if row['mode']!='ACCEPTED_FACT_INTERFACE':raise ValueError('SYNTHETIC_PRIOR_IN_ACCEPTED_MODE')
        attestation=self.pg.execute('SELECT producer_attestation FROM v4.research_state_engineering_publications WHERE publication_id=%s',(binding['engineering_publication_id'],)).fetchone()[0]
        if not attestation or attestation.get('producer_contract_id')!='V4_10_CONTROLLED_STATE_PUBLISHER_R1_2':raise ValueError('PRIOR_CONTROLLED_PUBLISHER_ATTESTATION_REQUIRED')

    def boundary_prior(self,binding,row):
        if type(binding) is not dict or binding.get('ledger_id')!='V4_10_BOUNDARY_PRIOR_LEDGER_R1_2':raise ValueError('BOUNDARY_PRIOR_AUTHORITY_REQUIRED')
        actual=self.pg.execute('SELECT source_payload,source_payload_digest,source_authority_digest,source_interface_contract_id FROM v4.research_state_boundary_prior_publications WHERE source_publication_id=%s',(binding.get('source_publication_id'),)).fetchone()
        if not actual or actual[0]!=row or actual[1]!=digest(row) or binding.get('source_payload_digest')!=actual[1] or binding.get('payload_digest')!=actual[1] or binding.get('source_authority_digest')!=actual[2] or binding.get('publication_id')!=row['publication_id']:
            raise ValueError('BOUNDARY_PRIOR_NOT_IN_IMMUTABLE_AUTHORITY')
        validate_output(row,permit_other_model=True,boundary_source=True)
        if (row['model_contract_id'],row['parameter_set_id'])==(CONTRACT,PARAMETERS):raise ValueError('BOUNDARY_PRIOR_OLD_IDENTITY_REQUIRED')

def _ledger(ledger):
    if type(ledger) is not PostgresEngineeringLedger:raise ValueError('TRUSTED_ENGINEERING_LEDGER_REQUIRED')
    return ledger

def _calendar(x,ledger):
    binding=x['calendar_binding']
    if type(binding) is not dict or {'publication_id','manifest_digest','lineage_id'}-set(binding) or binding['publication_id']!=x['calendar_publication_id']:
        raise ValueError('CALENDAR_BINDING_REQUIRED')
    if x['mode']=='ACCEPTED_FACT_INTERFACE':manifest,checksum=_ledger(ledger).manifest(binding['publication_id'],'MARKET_CALENDAR')
    else:
        manifest=x['synthetic_calendar_manifest'];checksum=digest(manifest)
        if manifest['mode']!='SYNTHETIC_CONTRACT_VECTOR' or not binding['publication_id'].startswith('SYNTHETIC_CALENDAR:'):
            raise ValueError('SYNTHETIC_CALENDAR_NAMESPACE_REQUIRED')
    if checksum!=binding['manifest_digest'] or manifest['lineage_id']!=binding['lineage_id'] or manifest['producer_contract_id']!='MARKET_CALENDAR_V1':
        raise ValueError('CALENDAR_IDENTITY_MISMATCH')
    sessions=manifest['sessions']
    if type(sessions) is not list or not sessions or any(type(s) is not dict or set(s)!={'trade_date','session_index'} for s in sessions):
        raise ValueError('CALENDAR_SESSION_MAPPING_INVALID')
    for s in sessions:
        date.fromisoformat(s['trade_date'])
        if type(s['session_index']) is not int or s['session_index']<0:raise ValueError('CALENDAR_SESSION_MAPPING_INVALID')
    indices=[s['session_index'] for s in sessions];dates=[s['trade_date'] for s in sessions]
    if indices!=sorted(set(indices)) or dates!=sorted(set(dates)):raise ValueError('CALENDAR_SESSION_MAPPING_INVALID')
    mapping={s['session_index']:s['trade_date'] for s in sessions}
    if mapping.get(x['session_index'])!=x['trade_date']:raise ValueError('TRADE_DATE_SESSION_INDEX_INCONSISTENT')
    if x['prior_state']:
        prior=x['prior_state']
        if prior['calendar_publication_id']!=binding['publication_id'] or prior['calendar_binding']!=binding:
            raise ValueError('PRIOR_CALENDAR_IDENTITY_MISMATCH')
        if mapping.get(prior['session_index'])!=prior['trade_date'] or prior['session_index']>x['session_index']:
            raise ValueError('PRIOR_TRADE_DATE_SESSION_INDEX_INCONSISTENT')
        if prior['session_index']==x['session_index'] and prior['trade_date']!=x['trade_date']:
            raise ValueError('SAME_SESSION_DATE_MISMATCH')
    return mapping

def _boundary(x,ledger):
    b=x['model_boundary']
    if type(b) is not dict or b.get('status') not in ('NONE','AUTHORIZED','SYNTHETIC_MODEL_BOUNDARY_FIXTURE'):
        raise ValueError('MODEL_BOUNDARY_UNAUTHORIZED')
    if b['status']=='NONE':
        if set(b)!={'status'}:raise ValueError('MODEL_BOUNDARY_NONE_SHAPE_INVALID')
        return False
    fields={'boundary_contract_id','migration_manifest_id','migration_manifest_sha256','from_model_contract_id','from_parameter_set_id',
            'to_model_contract_id','to_parameter_set_id','effective_trade_date','publication_id'}
    if fields-set(b) or not x['prior_state']:raise ValueError('MODEL_BOUNDARY_MANIFEST_REQUIRED')
    if x['mode']=='ACCEPTED_FACT_INTERFACE':
        if b['status']!='AUTHORIZED':raise ValueError('MODEL_BOUNDARY_UNAUTHORIZED')
        manifest,checksum=_ledger(ledger).manifest(b['publication_id'],'MODEL_BOUNDARY')
    else:
        if b['status']!='SYNTHETIC_MODEL_BOUNDARY_FIXTURE':raise ValueError('MODEL_BOUNDARY_UNAUTHORIZED')
        manifest=x['synthetic_boundary_manifest'];checksum=digest(manifest)
        if not b['publication_id'].startswith('SYNTHETIC_BOUNDARY:'):raise ValueError('MODEL_BOUNDARY_UNAUTHORIZED')
    if checksum!=b['migration_manifest_sha256']:raise ValueError('BOUNDARY_MANIFEST_DIGEST_MISMATCH')
    if manifest['authorization']!='AUTHORIZED_ENGINEERING_INTERFACE' or b['boundary_contract_id']!='V4_10_MODEL_BOUNDARY_V1' or any(manifest.get(k)!=b[k] for k in fields-{'publication_id','migration_manifest_sha256'}):
        raise ValueError('MODEL_BOUNDARY_UNAUTHORIZED')
    prior=x['prior_state']
    if (b['from_model_contract_id'],b['from_parameter_set_id'])!=(prior['model_contract_id'],prior['parameter_set_id']):raise ValueError('BOUNDARY_FROM_MODEL_MISMATCH')
    if (b['to_model_contract_id'],b['to_parameter_set_id'])!=(CONTRACT,PARAMETERS):raise ValueError('BOUNDARY_TO_MODEL_MISMATCH')
    if b['effective_trade_date']!=x['trade_date']:raise ValueError('BOUNDARY_EFFECTIVE_DATE_MISMATCH')
    if (b['from_model_contract_id'],b['from_parameter_set_id'])==(b['to_model_contract_id'],b['to_parameter_set_id']):raise ValueError('MODEL_BOUNDARY_NOOP_FORBIDDEN')
    if x['mode']=='ACCEPTED_FACT_INTERFACE':
        binding=x['prior_state_binding'] or {}
        for key in ['source_publication_id','source_payload_digest','source_authority_digest']:
            if b.get(key)!=binding.get(key) or manifest.get(key)!=binding.get(key) or binding.get(key) is None:raise ValueError('BOUNDARY_SOURCE_BINDING_MISMATCH')
    return True

def validate_inputs(inputs,ledger=None):
    policy=_read('input_provenance')
    x=deepcopy(inputs)
    if type(x) is not dict or set(_read('input_schema')['required'])-set(x):raise ValueError('MISSING_STATE_INPUT_FIELDS')
    if x['interface_contract_id']!=INTERFACE or x['mode'] not in ('SYNTHETIC_CONTRACT_VECTOR','ACCEPTED_FACT_INTERFACE'):
        raise ValueError('STATE_INPUT_SCOPE_INVALID')
    if type(x['entity_id']) is not str or not x['entity_id'] or x['entity_type'] not in ('STOCK','SECTOR') or type(x['session_index']) is not int or x['session_index']<0:
        raise ValueError('STATE_ENTITY_SESSION_INVALID')
    x['input_publication_ids']=publication_ids(x['input_publication_ids'])
    provenance=x['input_provenance']
    if type(provenance) is not dict or set(provenance)!=set(policy['fields']):raise ValueError('STATE_INPUT_FIELD_MANIFEST_INCOMPLETE')
    if x['input_publication_manifest_digest']!=digest(dict(input_publication_ids=x['input_publication_ids'],fields=provenance)):
        raise ValueError('INPUT_PUBLICATION_MANIFEST_DIGEST_MISMATCH')
    # Reject synthetic field values before using any accepted-mode authority.
    if x['mode']=='ACCEPTED_FACT_INTERFACE' and any(f.get('status')=='SYNTHETIC' for f in provenance.values()):
        raise ValueError('SYNTHETIC_DETECTOR_IN_ACCEPTED_INPUT')
    if x['mode']=='ACCEPTED_FACT_INTERFACE':
        for publication in x['input_publication_ids']:_ledger(ledger).manifest(publication,'FACT_PUBLICATION')
    boundary=_boundary(x,ledger)
    prior=x['prior_state']
    if prior is not None:
        if x['mode']=='ACCEPTED_FACT_INTERFACE' and not boundary and (prior['model_contract_id'],prior['parameter_set_id'])!=(CONTRACT,PARAMETERS):raise ValueError('MODEL_BOUNDARY_REQUIRED')
        is_old=x['mode']=='ACCEPTED_FACT_INTERFACE' and boundary and (prior['model_contract_id'],prior['parameter_set_id'])!=(CONTRACT,PARAMETERS)
        if is_old:_ledger(ledger).boundary_prior(x['prior_state_binding'],prior)
        else:validate_output(prior,permit_other_model=boundary)
        if x['mode']=='ACCEPTED_FACT_INTERFACE' and prior['mode']!='ACCEPTED_FACT_INTERFACE':
            raise ValueError('SYNTHETIC_PRIOR_IN_ACCEPTED_MODE')
        if prior['entity_id']!=x['entity_id'] or prior['entity_type']!=x['entity_type']:raise ValueError('ILLEGAL_PRIOR_STATE_LINEAGE')
        binding=x['prior_state_binding']
        if type(binding) is not dict or binding.get('publication_id')!=prior['publication_id'] or binding.get('payload_digest')!=digest(prior):raise ValueError('PRIOR_STATE_BINDING_MISMATCH')
        if x['mode']=='ACCEPTED_FACT_INTERFACE' and not is_old:_ledger(ledger).prior(binding,prior)
        elif x['mode']=='SYNTHETIC_CONTRACT_VECTOR' and (prior['mode']!='SYNTHETIC_CONTRACT_VECTOR' or binding.get('ledger_id')!='SYNTHETIC_ENGINEERING_LEDGER'):raise ValueError('SYNTHETIC_PRIOR_NAMESPACE_REQUIRED')
    elif x['prior_state_binding'] is not None:raise ValueError('ORPHAN_PRIOR_STATE_BINDING')
    mapping=_calendar(x,ledger)
    values={}; normalized=deepcopy(x); lineage_unknown=[]
    for field,definition in policy['fields'].items():
        f=provenance[field]
        if type(f) is not dict or set(policy['envelope_required'])-set(f):raise ValueError('FIELD_PROVENANCE_SHAPE_INVALID:'+field)
        if f['field']!=field or type(f['required']) is not bool or f['required']!=definition['required'] or f['time_role']!=definition['time_role']:
            raise ValueError('FIELD_PROVENANCE_POLICY_MISMATCH:'+field)
        status=f['status'];value=f['value']
        if status not in ('IMPLEMENTED','SYNTHETIC','NOT_IMPLEMENTED','NOT_APPLICABLE'):raise ValueError('FIELD_STATUS_INVALID:'+field)
        if x['mode']=='ACCEPTED_FACT_INTERFACE' and definition['implemented'] and status=='NOT_IMPLEMENTED':
            raise ValueError('STATE_IMPLEMENTED_FIELD_CANNOT_BE_NOT_IMPLEMENTED:'+field)
        if status in ('NOT_IMPLEMENTED','NOT_APPLICABLE'):
            if (f['producer_contract_id'],f['producer_parameter_set_id'])!=(definition['producer_contract_id'],definition['producer_parameter_set_id']):
                raise ValueError('FIELD_PRODUCER_LINEAGE_MISMATCH:'+field)
            if value!='UNKNOWN' or f['quality']!='UNKNOWN' or f['publication_id'] is not None or f['source_output_digest'] is not None:
                raise ValueError('NOT_IMPLEMENTED_FACT_MUST_REMAIN_UNKNOWN:'+field)
            if status=='NOT_APPLICABLE' and not ((x['entity_type'] in definition.get('not_applicable_entity_types',[])) or
                (field in ('frozen_invalidation','episode_invalidation_contract_id') and prior is None)):
                raise ValueError('FIELD_NOT_APPLICABLE_UNAUTHORIZED:'+field)
        else:
            if value=='UNKNOWN' and f['quality']!='UNKNOWN':raise ValueError('FIELD_QUALITY_VALUE_MISMATCH:'+field)
            if f['quality'] not in ('KNOWN','UNKNOWN'):raise ValueError('FIELD_QUALITY_INVALID:'+field)
            payload=f['source_field_payload']
            if type(payload) is not dict or payload.get('field')!=field or payload.get('value')!=value or f['source_output_digest']!=digest(payload):
                raise ValueError('FIELD_SOURCE_DIGEST_MISMATCH:'+field)
            if status=='SYNTHETIC':
                if x['mode']!='SYNTHETIC_CONTRACT_VECTOR' or not f['publication_id'].startswith('SYNTHETIC_FACTS:') or not f['producer_contract_id'].startswith('SYNTHETIC_'):
                    raise ValueError('SYNTHETIC_FIELD_NAMESPACE_REQUIRED:'+field)
            else:
                if not definition['implemented']:raise ValueError('OWNER_PRODUCER_NOT_IMPLEMENTED:'+field)
                if x['entity_type'] not in definition['accepted_entity_types']:raise ValueError('FIELD_PRODUCER_ENTITY_SCOPE_MISMATCH:'+field)
                mismatch=(f['producer_contract_id']!=definition['producer_contract_id'] or f['producer_parameter_set_id']!=definition['producer_parameter_set_id'] or f['publication_id'] not in x['input_publication_ids'])
                if mismatch and field in ('SEED','PREWATCH') and x['mode']=='SYNTHETIC_CONTRACT_VECTOR':
                    values[field]='UNKNOWN';lineage_unknown.append(field+':PRODUCER_LINEAGE_MISMATCH');continue
                if mismatch:raise ValueError('FIELD_PRODUCER_LINEAGE_MISMATCH:'+field)
                manifest,_=_ledger(ledger).manifest(f['publication_id'],'FACT_PUBLICATION')
                if manifest['fields'].get(field)!={k:v for k,v in f.items() if k!='publication_id'} or manifest['entity_id']!=x['entity_id'] or manifest['entity_type']!=x['entity_type'] or manifest['calendar_publication_id']!=x['calendar_publication_id']:
                    raise ValueError('FIELD_NOT_IN_TRUSTED_PUBLICATION:'+field)
            if f['publication_id'] not in x['input_publication_ids']:
                raise ValueError('FIELD_PUBLICATION_EXACT_MEMBERSHIP_REQUIRED:'+field)
            expected_index=x['session_index'] if f['time_role']=='T' else x['session_index']-1
            if payload.get('session_index')!=expected_index or payload.get('trade_date')!=mapping.get(expected_index):
                raise ValueError('FIELD_TIME_ROLE_MISMATCH:'+field)
            if x['mode']=='ACCEPTED_FACT_INTERFACE':
                try:
                    cutoff=datetime.fromisoformat(x['cutoff'].replace('Z','+00:00'))
                    available=datetime.fromisoformat(f['system_available_at'].replace('Z','+00:00'))
                except (ValueError,TypeError,AttributeError):raise ValueError('FIELD_TIME_AVAILABILITY_MISMATCH:'+field)
                if cutoff.tzinfo is None or available.tzinfo is None or available>cutoff or cutoff.date()!=date.fromisoformat(x['trade_date']):
                    raise ValueError('FIELD_TIME_AVAILABILITY_MISMATCH:'+field)
        if definition['domain']=='TRI' and value not in ('TRUE','FALSE','UNKNOWN'):raise ValueError('INVALID_TRI_STATE:'+field)
        if definition['domain']=='NUMBER' and value!='UNKNOWN':
            from decimal import Decimal
            if type(value) not in (float,int) or not Decimal(str(value)).is_finite():raise ValueError('FINITE_HEALTH_METRIC_REQUIRED')
        if definition['domain']=='RISK' and value not in ('LOW','MEDIUM','HIGH','EXTREME','UNKNOWN'):raise ValueError('INVALID_RISK')
        if definition['domain']=='SCENARIO' and value!='UNKNOWN' and value not in _read('output_schema')['axes']['scenario'][x['entity_type']]:raise ValueError('INVALID_SCENARIO_AXIS')
        if definition['domain']=='CONTRACT_ID' and value!='UNKNOWN' and (type(value) is not str or not value):raise ValueError('EPISODE_CONTRACT_ID_INVALID')
        values[field]=value
    if provenance['WARM']['status']!='NOT_APPLICABLE' and x['entity_type']=='STOCK':raise ValueError('STOCK_WARM_NOT_APPLICABLE_REQUIRED')
    normalized['detectors']={s:dict(value=values[s],status=provenance[s]['status'],contract_id=provenance[s]['producer_contract_id'],
        parameter_set_id=provenance[s]['producer_parameter_set_id'],publication_id=provenance[s]['publication_id']) for s in ['CONFIRMED','WARM','PREWATCH','SEED']}
    normalized.update(core_price_damage=values['core_price_damage'],frozen_invalidation=dict(value=values['frozen_invalidation'],
        episode_id=provenance['frozen_invalidation']['source_field_payload'].get('episode_id'),
        contract_id=provenance['frozen_invalidation']['source_field_payload'].get('invalidation_contract_id')),
        episode_invalidation_contract_id=None if values['episode_invalidation_contract_id']=='UNKNOWN' else values['episode_invalidation_contract_id'],
        risk=values['risk'],delta3=None if values['delta3']=='UNKNOWN' else values['delta3'],dq5=None if values['dq5']=='UNKNOWN' else values['dq5'],
        scenario=dict(value=values['scenario'],status='UNKNOWN' if values['scenario']=='UNKNOWN' else 'KNOWN'),
        suspended=values['suspended'],followup_complete=values['followup_complete'],model_boundary=boundary,
        provenance_unknown=lineage_unknown,authorized_boundary=x['model_boundary'] if boundary else None)
    return normalized
