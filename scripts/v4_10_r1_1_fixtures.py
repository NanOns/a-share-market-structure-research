"""Explicit synthetic adapter and disposable trusted-issuer gate fixtures; never live data."""
from copy import deepcopy
from datetime import date,timedelta
import hashlib
import json
from pathlib import Path
from src.v4.state_identity import digest,state_id,INTERFACE,CANONICALIZATION
from src.v4.state_provenance import LEDGER,CONSUMER,CONTRACT,PARAMETERS
ROOT=Path(__file__).resolve().parents[1]

def policy():return json.loads((ROOT/'config/v4_10_input_provenance_r1_1.json').read_text(encoding='utf8'))
def legacy_digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def calendar(synthetic=True):
    sessions=[dict(session_index=i,trade_date=(date(2026,9,8)+timedelta(days=i)).isoformat()) for i in range(32)] if synthetic else [
        dict(session_index=19,trade_date='2026-09-25'),dict(session_index=20,trade_date='2026-09-28'),
        dict(session_index=21,trade_date='2026-09-29'),dict(session_index=22,trade_date='2026-09-30')]
    return dict(mode='SYNTHETIC_CONTRACT_VECTOR' if synthetic else 'ACCEPTED_FACT_INTERFACE',manifest_kind='MARKET_CALENDAR',
        producer_contract_id='MARKET_CALENDAR_V1',lineage_id='SYNTHETIC_MARKET_CALENDAR_V1' if synthetic else 'DISPOSABLE_LEDGER_CALENDAR_GATE_FIXTURE',sessions=sessions)

def envelope(field,value,status,definition,session,dates,entity_type='STOCK'):
    role=definition['time_role'];source_index=session if role=='T' else session-1
    payload=dict(field=field,value=value,session_index=source_index,trade_date=dates.get(source_index))
    unavailable=status in ('NOT_IMPLEMENTED','NOT_APPLICABLE')
    return dict(field=field,value=value,quality='UNKNOWN' if value=='UNKNOWN' else 'KNOWN',status=status,
        producer_contract_id='SYNTHETIC_'+field if status=='SYNTHETIC' else definition['producer_contract_id'],
        producer_parameter_set_id='SYNTHETIC_PARAMETERS_V1' if status=='SYNTHETIC' else definition['producer_parameter_set_id'],
        publication_id=None if unavailable else 'SYNTHETIC_FACTS:FIXTURE_FACTS',source_output_digest=None if unavailable else digest(payload),
        source_field_payload={} if unavailable else payload,time_role=role,required=definition['required'],
        system_available_at=None if unavailable else dates[session]+'T01:00:00+00:00')

def refresh(x):
    x['input_publication_manifest_digest']=digest(dict(input_publication_ids=x['input_publication_ids'],fields=x['input_provenance']))
    return x

def full_prior(old,calendar_binding=None):
    """Fill synthetic schema only. This adapter is never accepted prior authority."""
    row=deepcopy(old)
    if row.get('interface_contract_id')==INTERFACE:return row
    from scripts.freeze_v4_10_contract import fixture
    template=adapt_r1_input(fixture(row['entity_type'],row['maturity']))
    row.update(trade_date=(date(2026,9,8)+timedelta(days=row['session_index'])).isoformat(),calendar_publication_id=template['calendar_publication_id'],
        calendar_binding=template['calendar_binding'],mode='SYNTHETIC_CONTRACT_VECTOR',input_publication_ids=template['input_publication_ids'],
        input_provenance=template['input_provenance'],input_publication_manifest_digest=template['input_publication_manifest_digest'],
        input_digest=digest('EXPLICIT_SYNTHETIC_PRIOR_FIXTURE'),raw_qualification={s:'UNKNOWN' for s in ['CONFIRMED','PREWATCH','SEED']},
        detector_statuses={s:'SYNTHETIC' for s in ['CONFIRMED','WARM','PREWATCH','SEED']},matched_predicates=[],unknown_predicates=[],
        transition_reasons=['SYNTHETIC_PRIOR_FIXTURE'],boundary_event=None,interface_contract_id=INTERFACE,canonicalization_contract_id=CANONICALIZATION)
    row['prior_state_binding']=None
    row['cutoff']=row['trade_date']+'T16:00:00+00:00'
    row['publication_id']=state_id(row)
    return row

def boundary_descriptor(prior,current_date,synthetic=True):
    manifest=dict(mode='SYNTHETIC_CONTRACT_VECTOR' if synthetic else 'ACCEPTED_FACT_INTERFACE',manifest_kind='MODEL_BOUNDARY',
        authorization='AUTHORIZED_ENGINEERING_INTERFACE',boundary_contract_id='V4_10_MODEL_BOUNDARY_V1',migration_manifest_id='ENGINEERING_INTERFACE_GATE_FIXTURE',
        from_model_contract_id=prior['model_contract_id'],from_parameter_set_id=prior['parameter_set_id'],to_model_contract_id=CONTRACT,
        to_parameter_set_id=PARAMETERS,effective_trade_date=current_date,reason='EXPLICIT_OWNER_AUTHORIZED_ENGINEERING_BOUNDARY_FIXTURE')
    publication=('SYNTHETIC_BOUNDARY:' if synthetic else 'V4_10_INPUT:')+digest(manifest)
    b={k:manifest[k] for k in ['boundary_contract_id','migration_manifest_id','from_model_contract_id','from_parameter_set_id',
        'to_model_contract_id','to_parameter_set_id','effective_trade_date']}
    b.update(status='SYNTHETIC_MODEL_BOUNDARY_FIXTURE' if synthetic else 'AUTHORIZED',publication_id=publication,migration_manifest_sha256=digest(manifest))
    return b,manifest

def adapt_r1_input(old):
    """Lossless business-value conversion for the preserved 98-vector R1 oracle.

    This is explicitly a synthetic test adapter. Accepted callers cannot opt into it
    through any serialized input flag, and reduce_state never invokes it implicitly.
    """
    old=deepcopy(old);cal=calendar();cal_id='SYNTHETIC_CALENDAR:'+digest(cal)
    dates={s['session_index']:s['trade_date'] for s in cal['sessions']}
    x={k:old[k] for k in ['entity_id','entity_type','session_index','mode']}
    x.update(interface_contract_id=INTERFACE,trade_date=dates[x['session_index']],calendar_publication_id=cal_id,
        calendar_binding=dict(publication_id=cal_id,manifest_digest=digest(cal),lineage_id=cal['lineage_id']),
        synthetic_calendar_manifest=cal,cutoff=dates[x['session_index']]+'T16:00:00+00:00',
        model_boundary={'status':'NONE'},prior_state=None,prior_state_binding=None)
    f={};definitions=policy()['fields']
    for field,d in definitions.items():
        value=old[field] if field in old else old['detectors'][field]['value']
        if field in old['detectors']:
            status=old['detectors'][field]['status']
        elif field=='frozen_invalidation':value=old[field]['value'];status='SYNTHETIC'
        elif field=='scenario':value=old[field]['value'] if old[field]['status']=='KNOWN' else 'UNKNOWN';status='SYNTHETIC'
        elif field in ('suspended','followup_complete'):
            value='TRUE' if value is True else 'FALSE' if value is False else value;status='SYNTHETIC'
        elif field in ('delta3','dq5'):value='UNKNOWN' if value is None else value;status='SYNTHETIC'
        else:status='SYNTHETIC'
        f[field]=envelope(field,value,status,d,x['session_index'],dates,x['entity_type'])
        if field in old['detectors'] and status=='IMPLEMENTED':
            source=old['detectors'][field]
            f[field].update(producer_contract_id=source['contract_id'],producer_parameter_set_id=source['parameter_set_id'],
                publication_id='SYNTHETIC_FACTS:'+source['publication_id'])
        if field=='frozen_invalidation':
            f[field]['source_field_payload'].update(episode_id=old[field]['episode_id'],invalidation_contract_id=old[field]['contract_id'])
            f[field]['source_output_digest']=digest(f[field]['source_field_payload'])
    x['input_provenance']=f
    x['input_publication_ids']=sorted('SYNTHETIC_FACTS:'+v for v in old['input_publication_ids'])
    if old['prior_state']:
        valid=old['prior_state_binding']['payload_digest']==legacy_digest(old['prior_state'])
        row=full_prior(old['prior_state']);x['prior_state']=row
        x['prior_state_binding']=dict(publication_id=row['publication_id'],payload_digest=digest(row) if valid else 'wrong',
            ledger_id='SYNTHETIC_ENGINEERING_LEDGER')
    if old['model_boundary']:
        x['model_boundary'],x['synthetic_boundary_manifest']=boundary_descriptor(x['prior_state'],x['trade_date'])
    return refresh(x)

def synthetic_input(entity_type='STOCK',stage='PREWATCH'):
    from scripts.freeze_v4_10_contract import fixture
    return adapt_r1_input(fixture(entity_type,stage))

def accepted_bundle(session_index=20,prior=None):
    """Disposable owner-issued ledger fixture; test evidence only, never market acceptance."""
    cal=calendar(False);cal_id='V4_10_INPUT:'+digest(cal);dates={s['session_index']:s['trade_date'] for s in cal['sessions']}
    x=dict(interface_contract_id=INTERFACE,entity_id='fixture-entity',entity_type='STOCK',session_index=session_index,trade_date=dates[session_index],
        calendar_publication_id=cal_id,calendar_binding=dict(publication_id=cal_id,manifest_digest=digest(cal),lineage_id=cal['lineage_id']),
        cutoff=dates[session_index]+'T16:00:00+00:00',mode='ACCEPTED_FACT_INTERFACE',model_boundary={'status':'NONE'},
        prior_state=prior,prior_state_binding=None)
    fields={}
    for field,d in policy()['fields'].items():
        value='FALSE' if d['domain']=='TRI' else 0 if d['domain']=='NUMBER' else 'LOW' if d['domain']=='RISK' else 'UNKNOWN'
        status='IMPLEMENTED' if d['implemented'] else 'NOT_IMPLEMENTED'
        if status=='NOT_IMPLEMENTED':value='UNKNOWN'
        if field in ('WARM','dq5'):status='NOT_APPLICABLE';value='UNKNOWN'
        if field in ('frozen_invalidation','episode_invalidation_contract_id') and prior is None:status='NOT_APPLICABLE';value='UNKNOWN'
        fields[field]=envelope(field,value,status,d,session_index,dates)
    stored={k:{n:v for n,v in f.items() if n!='publication_id'} for k,f in fields.items() if f['status']=='IMPLEMENTED'}
    facts=dict(mode='ACCEPTED_FACT_INTERFACE',manifest_kind='FACT_PUBLICATION',entity_id=x['entity_id'],entity_type=x['entity_type'],
        calendar_publication_id=cal_id,fields=stored,scope='DISPOSABLE_OWNER_ISSUER_GATE_FIXTURE_NOT_MARKET_DATA_ACCEPTANCE')
    facts_id='V4_10_INPUT:'+digest(facts)
    for f in fields.values():
        if f['status']=='IMPLEMENTED':f['publication_id']=facts_id
    x.update(input_provenance=fields,input_publication_ids=[facts_id])
    if prior:x['prior_state_binding']=dict(publication_id=prior['publication_id'],payload_digest=digest(prior),
        engineering_publication_id='R1_1_PRIOR_FIXTURE',ledger_id=LEDGER,consumer_contract_id=CONSUMER,
        model_contract_id=prior['model_contract_id'],parameter_set_id=prior['parameter_set_id'])
    return refresh(x),[cal,facts]

def accepted_prior_fixture():
    from scripts.freeze_v4_10_contract import prior
    row=full_prior(prior('NONE',session_index=19,tracking='CLOSED',episode_id=None,invalidation_contract_id=None,expiry_count=0,market_age=0))
    x,manifests=accepted_bundle(19)
    row.update(mode='ACCEPTED_FACT_INTERFACE',trade_date=x['trade_date'],calendar_binding=x['calendar_binding'],calendar_publication_id=x['calendar_publication_id'],
        cutoff=x['cutoff'],
        input_provenance=x['input_provenance'],input_publication_ids=x['input_publication_ids'],input_publication_manifest_digest=x['input_publication_manifest_digest'],
        input_digest=digest(x),health='UNKNOWN',validity='UNKNOWN',scenario='NONE',scenario_status='UNKNOWN',state_freshness='STALE',final_eligibility='UNKNOWN',
        raw_qualification={'CONFIRMED':'UNKNOWN','PREWATCH':'FALSE','SEED':'FALSE'},detector_statuses={s:x['input_provenance'][s]['status'] for s in ['CONFIRMED','WARM','PREWATCH','SEED']},
        transition_reasons=['REQUIRED_FACTS_UNKNOWN_PRESERVE'],unknown_predicates=['CONFIRMED'])
    row['publication_id']=state_id(row)
    return row,manifests

def publish_setup(pg,manifests,prior=None):
    """Called only by the disposable trusted issuer in tests and verification."""
    from psycopg.types.json import Jsonb
    for m in manifests:
        checksum=digest(m)
        pg.execute('''INSERT INTO v4.research_state_input_manifests(publication_id,manifest_kind,manifest,payload_digest,ledger_id)
            VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',('V4_10_INPUT:'+checksum,m['manifest_kind'],Jsonb(m),checksum,LEDGER))
    if prior:
        from src.v4.research_state_persistence import persist
        persist(pg,[prior],'R1_1_PRIOR_FIXTURE')
