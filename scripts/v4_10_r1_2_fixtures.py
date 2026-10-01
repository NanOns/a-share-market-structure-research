"""Disposable trusted issuer fixtures and explicit historical-input adaptation."""
from copy import deepcopy
from contextlib import contextmanager
from scripts.v4_10_r1_1_fixtures import *
from src.v4.research_state_persistence import publish_state
from src.v4.research_state import reduce_state
from src.v4.state_provenance import PostgresEngineeringLedger
from psycopg.types.json import Jsonb
from psycopg import sql

@contextmanager
def publisher_scope(pg):
    previous=pg.execute('SELECT current_user').fetchone()[0]
    pg.execute('SET LOCAL ROLE v4_10_reducer_publisher_r1_2')
    try:yield
    finally:pg.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(previous)))

def publish(pg,x,pub,revision=None):
    with publisher_scope(pg):return publish_state(pg,[x],pub,revision)

def current_prior_fixture(pg):
    x,ms=accepted_bundle(19)
    publish_setup(pg,ms)
    return reduce_state(x,ledger=PostgresEngineeringLedger(pg)),ms

def request_for_row(row):
    return dict(interface_contract_id=row['interface_contract_id'],entity_id=row['entity_id'],entity_type=row['entity_type'],
        session_index=row['session_index'],trade_date=row['trade_date'],calendar_publication_id=row['calendar_publication_id'],calendar_binding=row['calendar_binding'],
        cutoff=row['cutoff'],mode=row['mode'],model_boundary={'status':'NONE'},prior_state=None,prior_state_binding=None,
        input_provenance=row['input_provenance'],input_publication_ids=row['input_publication_ids'],input_publication_manifest_digest=row['input_publication_manifest_digest'])

def publish_setup(pg,manifests,prior=None):
    for m in manifests:
        checksum=digest(m)
        pg.execute('INSERT INTO v4.research_state_input_manifests(publication_id,manifest_kind,manifest,payload_digest,ledger_id) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
            ('V4_10_INPUT:'+checksum,m['manifest_kind'],Jsonb(m),checksum,LEDGER))
    if prior:
        x=request_for_row(prior)
        if reduce_state(x,ledger=PostgresEngineeringLedger(pg))!=prior:raise ValueError('FIXTURE_PRIOR_MUST_BE_ACTUAL_REDUCER_OUTPUT')
        publish(pg,x,'R1_1_PRIOR_FIXTURE')

def old_prior_fixture(episode=True):
    artifact=json.loads((ROOT/'config/v4_10_boundary_old_source_fixture_r1_2.json').read_text(encoding='utf8'))
    golden=artifact['goldens']['with_episode' if episode else 'without_episode']
    return deepcopy(golden['payload']),deepcopy(golden['authority']),[calendar(False)]

def register_old(pg,row,authority):
    pg.execute('''INSERT INTO v4.research_state_boundary_prior_publications
      (source_publication_id,source_payload,source_payload_digest,source_model_contract_id,source_parameter_set_id,source_interface_contract_id,source_trade_date,source_session_index,source_entity_id,source_entity_type,source_episode_id,source_authority,source_authority_digest)
      VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
      (row['publication_id'],Jsonb(row),digest(row),row['model_contract_id'],row['parameter_set_id'],row['interface_contract_id'],row['trade_date'],row['session_index'],row['entity_id'],row['entity_type'],row['episode_id'],Jsonb(authority),digest(authority)))

def real_boundary_bundle(episode=True):
    row,authority,oldms=old_prior_fixture(episode);x,ms=accepted_bundle(prior=row)
    binding=dict(publication_id=row['publication_id'],payload_digest=digest(row),engineering_publication_id=row['publication_id'],
        ledger_id='V4_10_BOUNDARY_PRIOR_LEDGER_R1_2',consumer_contract_id='OLD_RESEARCH_STATE_INTERFACE_V0',model_contract_id=row['model_contract_id'],parameter_set_id=row['parameter_set_id'],
        source_publication_id=row['publication_id'],source_payload_digest=digest(row),source_authority_digest=digest(authority))
    b,m=boundary_descriptor(row,x['trade_date'],False)
    for k in ['source_publication_id','source_payload_digest','source_authority_digest']:b[k]=m[k]=binding[k]
    b.update(publication_id='V4_10_INPUT:'+digest(m),migration_manifest_sha256=digest(m))
    x.update(prior_state_binding=binding,model_boundary=b)
    return x,dict(manifests=oldms+ms+[m],old_prior=row,old_authority=authority,prior=None)

def setup_vector(pg,setup):
    if setup:
        publish_setup(pg,setup['manifests'],setup.get('prior'))
        if setup.get('old_prior'):register_old(pg,setup['old_prior'],setup['old_authority'])

def adapt_r1_2_input(old):
    x=adapt_r1_input(old)
    if x['model_boundary']['status']=='SYNTHETIC_MODEL_BOUNDARY_FIXTURE' and (x['prior_state']['model_contract_id'],x['prior_state']['parameter_set_id'])==(CONTRACT,PARAMETERS):
        x['prior_state'].update(model_contract_id='OLD_RESEARCH_STATE_V0',parameter_set_id='OLD_PARAMETER_SET_V0')
        x['prior_state']['publication_id']=state_id(x['prior_state'])
        x['prior_state_binding'].update(publication_id=x['prior_state']['publication_id'],payload_digest=digest(x['prior_state']))
        x['model_boundary'],x['synthetic_boundary_manifest']=boundary_descriptor(x['prior_state'],x['trade_date'])
    return x
