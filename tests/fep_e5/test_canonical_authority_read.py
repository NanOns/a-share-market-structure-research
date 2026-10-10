"""Actual SQL adapter tests against an explicitly named, G-disk isolated cluster."""
import os
from copy import deepcopy
from pathlib import Path
import pytest
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from workbench_analysis.fep_e5.trusted_authority import read_canonical_candidate,resolve_current_sources

REQUEST=dict(scope_id='S',target_id='T',horizon=1,feature_contract_id='F',model_set_id='M',capability='MODEL_DISPLAY',model_revision=1)
AT='2026-10-09T12:00:00+00:00'

def rows():
    identity={k:v for k,v in REQUEST.items() if k!='model_revision'}
    return dict(deployment_heads=[dict(identity,grant_id='G',activation_id='A',head_version=1)],
        permission_keys=[dict(identity,grant_id='G',model_role='CHAMPION')],
        activations=[dict(activation_id='A',grant_id='G',action='ALLOW',effective_at='2026-10-09T00:00:00+00:00',expected_head_version=0,prior_activation_id=None)],
        deployment_change_receipts=[dict(activation_id='A',grant_id='G',new_head_version=1,expected_head_version=0,expected_prior_activation_id=None,checks={'engineering_only':True})],
        model_set_members=[dict({k:v for k,v in identity.items() if k!='capability'},model_id='MODEL',role='CHAMPION')],
        models=[dict(model_id='MODEL',import_manifest={'model_revision':1},model_digest='SYNTHETIC_DIGEST')],
        model_sets=[dict(model_set_id='M',digest='SYNTHETIC_SET_DIGEST')])

@pytest.fixture
def connection():
    dsn=os.environ.get('FEP_AUTHORITY_TEST_DSN')
    if not dsn:pytest.skip('FEP_AUTHORITY_TEST_DSN not configured; no production DSN fallback')
    pg=psycopg.connect(dsn,autocommit=True)
    meta=pg.execute("select current_database(),current_setting('data_directory'),inet_server_port()").fetchone()
    assert meta[0]=='fep_authority_isolated'
    assert Path(meta[1]).resolve().is_relative_to(Path('G:/codex_tmp/test_temp').resolve())
    assert meta[2]==55547
    pg.execute('drop schema if exists fep cascade');pg.execute('create schema fep')
    yield pg
    pg.close()

def seed(pg,data):
    for name,table_rows in data.items():
        exemplar=table_rows[0]
        definitions=[]
        for key,value in exemplar.items():
            kind='jsonb' if isinstance(value,dict) else 'boolean' if type(value)is bool else 'integer' if type(value)is int else 'text'
            definitions.append(sql.SQL('{} {}').format(sql.Identifier(key),sql.SQL(kind)))
        pg.execute(sql.SQL('create table fep.{} ({})').format(sql.Identifier(name),sql.SQL(',').join(definitions)))
        for row in table_rows:
            pg.execute(sql.SQL('insert into fep.{} ({}) values ({})').format(sql.Identifier(name),sql.SQL(',').join(map(sql.Identifier,row)),sql.SQL(',').join(sql.Placeholder() for _ in row)),[Jsonb(v) if isinstance(v,dict) else v for v in row.values()])

def test_actual_db_positive_candidate_is_never_real_grant(connection):
    seed(connection,rows());r=read_canonical_candidate(connection,REQUEST,at=AT)
    assert r['status']=='CANONICAL_AUTHORITY_CANDIDATE_VERIFIED'
    assert r['registry_verified'] and r['cas_receipt_verified'] and r['deployment_head_verified']
    assert not r['production_authorized'] and r['formal_owner'] is None
    assert r['read_snapshot']['read_only']=='on' and r['read_snapshot']['isolation']=='repeatable read'
    assert 'ENGINEERING_CAS_NOT_PRODUCTION_APPROVAL' in r['errors']
    assert connection.execute('select head_version from fep.deployment_heads').fetchone()==(1,)

@pytest.mark.parametrize('table,key,value,error',[
    ('permission_keys','model_set_id','OTHER','EXACT_GRANT_HEAD_BINDING_MISMATCH'),
    ('permission_keys','grant_id','FORGED','CANONICAL_OWNER_NOT_UNIQUE'),
    ('activations','action','REVOKE','CURRENT_HEAD_REVOKED_OR_FUTURE'),
    ('activations','effective_at','2026-10-12T00:00:00+00:00','CURRENT_HEAD_REVOKED_OR_FUTURE'),
    ('deployment_change_receipts','new_head_version',2,'CURRENT_HEAD_CAS_RECEIPT_MISMATCH'),
    ('deployment_change_receipts','grant_id','FORGED','CURRENT_HEAD_CAS_RECEIPT_MISMATCH'),
    ('deployment_change_receipts','expected_prior_activation_id','OTHER','CURRENT_HEAD_CAS_RECEIPT_MISMATCH'),
    ('model_set_members','role','BASELINE','CANONICAL_OWNER_NOT_UNIQUE'),
])
def test_actual_db_negative_binding_matrix(connection,table,key,value,error):
    data=rows();data[table][0][key]=value;seed(connection,data)
    r=read_canonical_candidate(connection,REQUEST,at=AT)
    assert not r['production_authorized'] and any(error in e for e in r['errors'])

def test_model_revision_is_not_prediction_revision(connection):
    data=rows();data['models'][0]['import_manifest']={};seed(connection,data)
    r=read_canonical_candidate(connection,REQUEST,at=AT)
    assert 'MODEL_REVISION_PRODUCTION_REGISTRY_MISSING' in r['errors'] and not r['production_authorized']

def test_model_revision_mismatch(connection):
    seed(connection,rows());request=dict(REQUEST,model_revision=2)
    assert 'MODEL_REVISION_PRODUCTION_REGISTRY_MISSING' in read_canonical_candidate(connection,request,at=AT)['errors']

def test_missing_registry_and_shadow_fail_closed(connection):
    r=read_canonical_candidate(connection,REQUEST,at=AT)
    assert not r['production_authorized'] and any(e.startswith('CANONICAL_DB_READ_FAILED') for e in r['errors'])
    r=read_canonical_candidate(connection,dict(REQUEST,capability='SHADOW_INFERENCE'),at=AT)
    assert r['errors']==['SHADOW_CAPABILITY_CANNOT_AUTHORIZE_PRODUCTION']

def test_existing_write_transaction_is_rejected(connection):
    seed(connection,rows())
    with connection.transaction():
        r=read_canonical_candidate(connection,REQUEST,at=AT)
        assert r['errors']==['FRESH_READ_ONLY_CONNECTION_REQUIRED'] and not r['production_authorized']

def test_current_source_discovery_no_default_dsn():
    root=Path(__file__).resolve().parents[2]
    r=resolve_current_sources(root)
    assert not r['production_authorized'] and r['formal_owner'] is None
    assert 'FORMAL_PRODUCTION_DB_OWNER_NOT_ADMITTED' in r['errors']

def complete_rows():
    from workbench_analysis.fep_e1.contracts import digest
    data=rows();data['models'][0]['training_run_id']='TRAIN'
    data['deployment_change_receipts'][0]['checks']={}
    manifest={'sources':[dict(source_owner='SYNTHETIC_SOURCE',sha256='SYNTHETIC_SHA',first_available_at='2026-10-09T00:00:00+00:00')]}
    fields={k:dict(status='READY',value=v) for k,v in dict(return_expectancy=1.0,downside_risk=2.0,return_quantiles=[-1,0,1],prediction_revision=1,model_display=True,priority_use=False).items()}
    output={'fields':fields};od=digest(output)
    data.update(predictions=[dict({k:v for k,v in REQUEST.items() if k not in ('model_revision','capability')},prediction_id='P',model_id='MODEL',observation_id='O',run_id='R',snapshot_id='SNAP',prediction_evidence='FIRST_OBSERVED',revision=1,accepted_at=AT,outputs=output,output_digest=od)],
        prediction_runs=[dict(run_id='R',model_set_id='M',publication_id='PUB',output_digest=od,finished_at=AT)],
        acceptance_receipts=[dict(run_id='R',grant_id='G',activation_id='A',accepted_at=AT,checks={})],
        snapshots=[dict(snapshot_id='SNAP',observation_id='O',observation_revision=1,feature_contract_id='F')],
        observation_revisions=[dict(observation_id='O',revision=1,publication_id='PUB',feature_cutoff=AT,dependency_manifest=manifest,dependency_digest=digest(manifest),evidence_origin='PIT_OBSERVED',execution_mode='PRODUCTION')],
        training_runs=[dict(training_run_id='TRAIN',dataset_id='DATA',fold_id='FOLD',fit_started_at=AT)],
        dataset_rows=[dict(dataset_id='DATA',scope_id='S',feature_contract_id='F',observation_id='L',target_id='T',label_revision=1,fold_id='FOLD',partition_name='FIT')],
        label_revisions=[dict(observation_id='L',target_id='T',revision=1,binding_id='B',horizon=1,training_allowed=True)],
        label_source_bindings=[dict(binding_id='B',label_training_mature_at=AT,label_revision_available_at=AT)])
    return data

def test_actual_db_complete_prediction_candidate_still_not_authorized(connection):
    seed(connection,complete_rows())
    r=read_canonical_candidate(connection,dict(REQUEST,prediction_id='P'),at=AT)
    assert r['candidate_output_status']=='READY_ENGINEERING_EVIDENCE_ONLY'
    assert r['first_asof_verified'] and r['mature_observed_count']==1
    assert r['errors']==['CURRENT_INDEPENDENT_CAPABILITY_APPROVAL_SOURCE_MISSING']
    assert not r['production_authorized']

@pytest.mark.parametrize('table,key,value,error',[
    ('predictions','output_digest','MUTATED','PREDICTION_RUN_SNAPSHOT_ACCEPTANCE_LINEAGE_MISMATCH'),
    ('observation_revisions','evidence_origin','RECONSTRUCTED_CORRECTED','PREDICTION_OR_INPUT_NOT_AS_RECORDED'),
    ('label_source_bindings','label_training_mature_at','2026-10-12T00:00:00+00:00','REAL_MATURE_FIT_SAMPLE_NOT_VERIFIED'),
    ('snapshots','feature_contract_id','OTHER','PREDICTION_RUN_SNAPSHOT_ACCEPTANCE_LINEAGE_MISMATCH'),
])
def test_actual_prediction_negative_matrix(connection,table,key,value,error):
    data=complete_rows();data[table][0][key]=value;seed(connection,data)
    r=read_canonical_candidate(connection,dict(REQUEST,prediction_id='P'),at=AT)
    assert not r['production_authorized'] and 'candidate_output_status' not in r
    assert any(error in e for e in r['errors'])

def test_wrong_model_revision_cannot_display_ready_candidate(connection):
    seed(connection,complete_rows())
    r=read_canonical_candidate(connection,dict(REQUEST,prediction_id='P',model_revision=2),at=AT)
    assert 'candidate_output_status' not in r and not r['production_authorized']

@pytest.mark.parametrize('scenario,error',[
    ('frozen_mutation','FROZEN_PREDICTION_OUTPUT_MUTATION'),
    ('missing_ready_field','PREDICTION_FIELDS_NOT_READY'),
    ('invalid_field_type','PREDICTION_FIELD_VALUE_SCHEMA_INVALID'),
    ('future_first_available','FIRST_AVAILABLE_SOURCE_OWNER_NOT_VERIFIED'),
    ('bool_model_revision','EXACT_REQUEST_AND_MODEL_REVISION_REQUIRED')])
def test_actual_db_output_and_first_availability_matrix(connection,scenario,error):
    from workbench_analysis.fep_e1.contracts import digest
    data=complete_rows();request=dict(REQUEST,prediction_id='P')
    if scenario=='bool_model_revision':request['model_revision']=True
    elif scenario=='future_first_available':
        row=data['observation_revisions'][0]
        row['dependency_manifest']['sources'][0]['first_available_at']='2026-10-12T00:00:00+00:00'
        row['dependency_digest']=digest(row['dependency_manifest'])
    else:
        pred=data['predictions'][0]
        if scenario=='frozen_mutation':pred['outputs']['fields']['return_expectancy']['value']=99
        else:
            pred['outputs']['fields']['return_expectancy']['value']=None if scenario=='missing_ready_field' else 'NOT_A_NUMBER'
            pred['output_digest']=digest(pred['outputs']);data['prediction_runs'][0]['output_digest']=pred['output_digest']
    seed(connection,data);r=read_canonical_candidate(connection,request,at=AT)
    assert not r['production_authorized'] and 'candidate_output_status' not in r
    assert any(error in e for e in r['errors'])
