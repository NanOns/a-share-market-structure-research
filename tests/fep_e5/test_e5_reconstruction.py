"""Real PostgreSQL rejection proofs on both explicit canonical fixtures."""
import os, copy
from datetime import date
import pytest
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from workbench_analysis.fep_e5 import canonical_ledger as c
from workbench_service.canonical_expectancy_service import CanonicalExpectancyReadAPI
from scripts.run_fep_e5_r1r1b import DSNS,pit_seed
from tests.v4_phase0.test_postgres_schema import add_namespace,add_publication

@pytest.fixture(params=['fresh','upgrade'])
def canonical(request):
    if os.environ.get('FEP_E5_CANONICAL_TEST_ENABLE')!='1':pytest.skip('explicit canonical fixtures required')
    pg=psycopg.connect(DSNS[request.param]);assert pg.info.dbname=='fep_e5b_'+request.param
    try:yield pg
    finally:pg.rollback();pg.close()

def row(pg,table,where='true'):
    return pg.execute(sql.SQL('select to_jsonb(t) from fep.{} t where '+where+' order by to_jsonb(t)::text limit 1').format(sql.Identifier(table))).fetchone()[0]
def insert(pg,table,value):
    pg.execute(sql.SQL('insert into fep.{} select * from jsonb_populate_record(null::fep.{},%s)').format(sql.Identifier(table),sql.Identifier(table)),(Jsonb(value),))
def rejected(pg,op,match):
    with pytest.raises(psycopg.Error,match=match):
        with pg.transaction():op()
def revision(pg,**updates):
    r=row(pg,'observation_revisions',"authority_kind='HISTORICAL_RECONSTRUCTION'")
    r.update(revision=2,supersedes_revision=1,dependency_digest=c.digest('UNIT_NEW_REVISION'));r.update(updates);return r

def test_RA_01_reconstruction_is_not_publication(canonical):
    p=canonical;a=row(p,'reconstruction_authorities')
    rejected(p,lambda:add_publication(p,publication_id=a['authority_id'],namespace_id=a['namespace_id'],trade_date=date.fromisoformat(a['trade_date']),lineage_id='UNIT_BAD_RA'),'FEP_RECONSTRUCTION_IS_NOT_PUBLICATION')
def test_RA_02_current_reconstruction_after_T0_without_PIT(canonical):
    p=canonical
    assert p.execute("select count(*) from fep.reconstruction_authorities a join fep.observation_revisions r on r.reconstruction_authority_id=a.authority_id where a.reconstructed_at>r.feature_cutoff and not a.first_observed and not a.real_oos and not a.as_recorded and r.evidence_origin='RECONSTRUCTED_CORRECTED' and r.publication_id is null").fetchone()[0]==205
def test_RA_03_no_historical_accepted_semantics(canonical):
    a=row(canonical,'reconstruction_authorities');a['historical_availability_claim']='HISTORICALLY_ACCEPTED'
    rejected(canonical,lambda:insert(canonical,'reconstruction_authorities',a),'historical_availability_claim')
def test_RA_04_row_digest_is_not_authority(canonical):
    r=revision(canonical,reconstruction_authority_id=c.digest('ROW'))
    rejected(canonical,lambda:insert(canonical,'observation_revisions',r),'query returned no rows')
def test_RA_05_current_publication_cannot_reconstruction(canonical):
    if canonical.info.dbname.endswith('fresh'):pit_seed(canonical)
    r=revision(canonical,publication_id='UNIT_PIT_PUBLICATION')
    rejected(canonical,lambda:insert(canonical,'observation_revisions',r),'observation_authority_union')

@pytest.mark.parametrize('case,field,value',[('RA-06','trade_date','2000-01-01'),('RA-07','namespace_id','UNIT_WRONG_NS'),('RA-08','feature_contract_id','UNIT_WRONG_FEATURE')])
def test_RA_06_08_exact_authority_identity(canonical,case,field,value):
    a=row(canonical,'reconstruction_authorities');a[field]=value
    rejected(canonical,lambda:insert(canonical,'reconstruction_authorities',a),'FEP_RECONSTRUCTION_EXACT_FROZEN_AUTHORITY_REQUIRED')

@pytest.mark.parametrize('case,token',[('RA-09',None),('RA-10-CURRENT','CURRENT'),('RA-10-LATEST','LATEST'),('RA-10-TODAY','TODAY')])
def test_RA_09_10_manifest_registration_and_dependency_guard(canonical,case,token):
    a=row(canonical,'reconstruction_authorities');a['authority_id']='UNIT_BAD_AUTHORITY:'+case
    if token:a['source_manifest']['calendar']=token
    else:del a['source_manifest']['frozen_source_bindings']
    a['source_manifest_digest']=c.digest(a['source_manifest'])
    # Register a deliberately malformed exact owner contract, exercising the
    # dependency guard beyond equality with the trusted frozen registry.
    name='UNIT_BAD_AUTHORITY_CONTRACT:'+case
    e={k:a[k] for k in ('authority_id','scope_id','namespace_id','trade_date','evidence_origin','feature_contract_id','source_manifest','source_manifest_digest','accepted_head_identity')}
    c.contract(canonical,name,dict(namespace_id=c.NS,exact_authorities=[e]));a['authority_contract_id']=name
    a['reconstructed_at']=c.now()
    rejected(canonical,lambda:insert(canonical,'reconstruction_authorities',a),'FEP_RECONSTRUCTION_MANIFEST_REQUIRED')

@pytest.mark.parametrize('field',['FIRST_OBSERVED','REAL_OOS','production','model_display','priority_use','AS_RECORDED','PROMOTION_EVIDENCE'])
def test_RA_11_13_no_evidence_or_display_upgrade(canonical,field):
    p=row(canonical,'predictions');p['prediction_id']='UNIT_BAD_PRED_'+field;p['outputs'][field]=True
    rejected(canonical,lambda:insert(canonical,'predictions',p),'FEP_RECONSTRUCTION_EVIDENCE_UPGRADE_FORBIDDEN')

@pytest.mark.parametrize('change',[{'authority_kind':'CANONICAL_PUBLICATION'}, {'reconstruction_authority_id':None}, {'authority_kind':'INVALID'}, {'execution_mode':'SHADOW'}, {'evidence_origin':'PIT_OBSERVED'}, {'publication_id':'UNIT_NOT_PUBLICATION'}])
def test_observation_union_fail_closed(canonical,change):
    rejected(canonical,lambda:insert(canonical,'observation_revisions',revision(canonical,**change)), 'FEP_|observation_authority_union|query returned no rows')

@pytest.mark.parametrize('change',[{'authority_kind':'CANONICAL_PUBLICATION'}, {'reconstruction_authority_id':None}, {'authority_kind':'INVALID'}, {'publication_id':'UNIT_NOT_PUBLICATION'}, {'started_at':'2000-01-01T00:00:00Z'}])
def test_prediction_run_union_fail_closed(canonical,change):
    r=row(canonical,'prediction_runs');r['run_id']='UNIT_BAD_RUN';r.update(change)
    rejected(canonical,lambda:insert(canonical,'prediction_runs',r),'prediction_run_authority_union|query returned no rows|FEP_RECONSTRUCTION_RUN_BINDING_REQUIRED')

@pytest.mark.parametrize('field',['snapshot_id','feature_digest','quality_digest','feature_contract_id'])
def test_snapshot_exact_binding(canonical,field):
    s=row(canonical,'snapshots',"feature_contract_id='"+c.FEATURE+"'");s[field]='UNIT_WRONG' if field.endswith('_id') else c.digest('WRONG')
    rejected(canonical,lambda:insert(canonical,'snapshots',s),'FEP_RECONSTRUCTION_SNAPSHOT_EXACT_REQUIRED|FEP_SNAPSHOT_FEATURE_CONTRACT_MISMATCH')

@pytest.mark.parametrize('field,value',[('value',9000),('quality','UNKNOWN'),('source_digest',c.digest('WRONG'))])
def test_feature_values_exact_binding(canonical,field,value):
    f=row(canonical,'feature_values',"quality='OBSERVED'");f[field]=value
    rejected(canonical,lambda:insert(canonical,'feature_values',f),'FEP_RECONSTRUCTION_FEATURE_EXACT_REQUIRED')

@pytest.mark.parametrize('capability',['MODEL_DISPLAY','DESCRIPTIVE_DISPLAY','PRIORITY_USE'])
def test_permission_nonchampion_display_priority_forbidden(canonical,capability):
    k=row(canonical,'permission_keys');k['grant_id']='UNIT_FORBIDDEN_'+capability;k['capability']=capability
    rejected(canonical,lambda:insert(canonical,'permission_keys',k),'permission_role_capability')
def test_permission_wrong_role_exact_FK(canonical):
    k=row(canonical,'permission_keys');k['grant_id']='UNIT_WRONG_ROLE';k['model_role']='CHAMPION';k['capability']='MODEL_DISPLAY'
    rejected(canonical,lambda:insert(canonical,'permission_keys',k),'foreign key')
def test_imported_model_cannot_fake_champion(canonical):
    m=row(canonical,'model_set_members');m['role']='CHAMPION'
    rejected(canonical,lambda:insert(canonical,'model_set_members',m),'FEP_IMPORTED_DIAGNOSTIC_CHAMPION_FORBIDDEN')

@pytest.mark.parametrize('table',['reconstruction_authorities','observation_revisions','snapshots','feature_values','models','model_sets','model_set_members','permission_keys','prediction_slots','slot_model_bindings','prediction_runs','predictions','acceptance_receipts','slot_receipts','activations','deployment_change_receipts'])
@pytest.mark.parametrize('verb',['UPDATE','DELETE'])
def test_append_only_guards(canonical,table,verb):
    operation=sql.SQL('delete from fep.{}').format(sql.Identifier(table)) if verb=='DELETE' else sql.SQL('update fep.{} set {}={}').format(sql.Identifier(table),sql.Identifier(next(iter(row(canonical,table)))),sql.Identifier(next(iter(row(canonical,table)))))
    rejected(canonical,lambda:canonical.execute(operation),'FEP_APPEND_ONLY')

@pytest.mark.parametrize('field,value',[('scope_id','UNIT_WRONG'),('target_id','UNIT_WRONG'),('horizon',20),('model_set_id','UNIT_WRONG'),('snapshot_id','UNIT_WRONG')])
def test_prediction_typed_identity(canonical,field,value):
    p=row(canonical,'predictions');p.update(supersedes_id=p['prediction_id'],prediction_id='UNIT_BAD_IDENTITY',revision=2);p[field]=value
    rejected(canonical,lambda:insert(canonical,'predictions',p),'foreign key|query returned no rows|FEP_RECONSTRUCTION_EVIDENCE_UPGRADE_FORBIDDEN')

def test_canonical_ledger_denominator_and_roles(canonical):
    counts=c.inventory(canonical)
    assert counts['predictions']==615 and counts['prediction_slots']==616 and counts['feature_values']==4100
    assert counts['training_runs']==0 and counts['label_revisions']==0 and counts['reconstruction_authorities']==205
    assert canonical.execute("select role,count(*) from fep.model_set_members group by role order by role").fetchall()==[('BASELINE',1),('CHALLENGER',2)]
    assert canonical.execute("select count(*) from fep.permission_keys where capability<>'SHADOW_INFERENCE'").fetchone()[0]==0

def test_PIT_path_positive_and_preserved(canonical):
    if canonical.info.dbname.endswith('fresh'):pit_seed(canonical)
    r=row(canonical,'observation_revisions',"observation_id='UNIT_PIT_OBSERVATION'")
    assert r['authority_kind']=='CANONICAL_PUBLICATION' and r['publication_id']=='UNIT_PIT_PUBLICATION' and r['reconstruction_authority_id'] is None
    assert r['evidence_origin']=='PIT_OBSERVED'

@pytest.mark.parametrize('case',['wrong_date','wrong_namespace','unaccepted','after_cutoff','missing_dependency','wrong_manifest_publication','replay'])
def test_PIT_original_validator_negatives(canonical,case):
    p=canonical
    if p.info.dbname.endswith('fresh'):pit_seed(p)
    r=row(p,'observation_revisions',"observation_id='UNIT_PIT_OBSERVATION'");r.update(revision=2,supersedes_revision=1,dependency_digest=c.digest(case))
    if case=='after_cutoff':r['feature_cutoff']='2000-01-01T00:00:00Z'
    elif case=='missing_dependency':del r['dependency_manifest']['calendar']
    elif case=='wrong_manifest_publication':r['dependency_manifest']['publication']='WRONG'
    elif case=='replay':r['execution_mode']='REPLAY'
    else:
        ns='UNIT_OTHER_NAMESPACE' if case=='wrong_namespace' else 'UNIT_PIT_NAMESPACE'
        if case=='wrong_namespace':add_namespace(p,ns)
        add_publication(p,publication_id='UNIT_BAD_PUBLICATION',namespace_id=ns,calendar_id='UNIT_BAD_CALENDAR',core_revision=2,trade_date=date(2000,1,1) if case=='wrong_date' else date.today(),lineage_id='UNIT_BAD_LINE',status='CANDIDATE' if case=='unaccepted' else 'ACCEPTED')
        r['publication_id']='UNIT_BAD_PUBLICATION';r['dependency_manifest']['publication']='UNIT_BAD_PUBLICATION'
    rejected(p,lambda:insert(p,'observation_revisions',r),'FEP_PUBLICATION_OBSERVATION_MISMATCH|FEP_MANIFEST_|FEP_RECONSTRUCTION_NOT_PIT')

def test_API_exact_context_and_revoked_boundary(canonical):
    p=row(canonical,'predictions');api=CanonicalExpectancyReadAPI(canonical);token=api.bootstrap(p['slot_id'])['context']
    assert token['publication_id'] is None and token['authority_kind']=='HISTORICAL_RECONSTRUCTION'
    assert api.projection(p['slot_id'],token,diagnostic=True)['axes'] is None
    bad=dict(token,model_id='WRONG');assert api.projection(p['slot_id'],bad)['status']=='CONTEXT_MISMATCH'
    assert api.projection(p['slot_id'],token,mode='TODAY')['status']=='NOT_APPLICABLE_ENTRY_IS_NOT_TODAY_DAILY'
    assert api.priority()['v2_active'] is False

@pytest.mark.parametrize('case',['wrong_version','wrong_prior','wrong_request_payload','negative_version','invalid_action'])
def test_CAS_rejection_atomicity(canonical,case):
    p=canonical;h=c.head(p);k=row(p,'permission_keys');before=c.inventory(p)
    if case=='wrong_version':args=(k['grant_id'],'UNIT_BAD_CAS','ALLOW',h[0]+1,h[1],'UNIT_BAD_REQ',c.digest('req'),Jsonb({}))
    elif case=='wrong_prior':args=(k['grant_id'],'UNIT_BAD_CAS','ALLOW',h[0],None,'UNIT_BAD_REQ',c.digest('req'),Jsonb({}))
    elif case=='wrong_request_payload':
        r=row(p,'deployment_change_receipts');args=(r['grant_id'],r['activation_id'],'ALLOW',r['expected_head_version'],r['expected_prior_activation_id'],r['request_id'],c.digest('different'),Jsonb(r['checks']))
    else:args=(k['grant_id'],'UNIT_BAD_CAS','BROKEN' if case=='invalid_action' else 'ALLOW',-1 if case=='negative_version' else h[0],h[1],'UNIT_BAD_REQ',c.digest('req'),Jsonb({}))
    rejected(p,lambda:p.execute('select fep.cas_deploy(%s,%s,%s,%s,%s,%s,%s,%s)',args),'FEP_CAS_CONFLICT|FEP_IDEMPOTENCY_CONFLICT|FEP_INVALID_CAS_INPUT')
    assert before==c.inventory(p) and c.head(p)==h

def test_CAS_replay_idempotent(canonical):
    p=canonical;r=row(p,'deployment_change_receipts');a=p.execute('select action,receipt_digest from fep.activations where activation_id=%s',(r['activation_id'],)).fetchone();before=c.inventory(p)
    value=p.execute('select fep.cas_deploy(%s,%s,%s,%s,%s,%s,%s,%s)',(r['grant_id'],r['activation_id'],a[0],r['expected_head_version'],r['expected_prior_activation_id'],r['request_id'],a[1],Jsonb(r['checks']))).fetchone()[0]
    assert value==r['new_head_version'] and before==c.inventory(p)

def test_CAS_outer_failure_restores_head_and_receipts(canonical):
    p=canonical;h=c.head(p);before=c.inventory(p);k=row(p,'permission_keys')
    with pytest.raises(ValueError,match='INJECT'):
        with p.transaction():
            c.cas(p,k['grant_id'],'ALLOW','UNIT_INJECT_ROLLBACK');raise ValueError('INJECT')
    assert c.head(p)==h and before==c.inventory(p)

def test_application_cannot_admit_authority_or_mutate_head(canonical):
    p=canonical
    for role in ('fep_application','fep_deployer','fep_auditor'):
        assert p.execute("select has_table_privilege(%s,'fep.reconstruction_authorities','INSERT'),has_table_privilege(%s,'fep.deployment_heads','UPDATE')",(role,role)).fetchone()==(False,False)

def unit_reconstruction(pg):
    """Rolled-back synthetic authority, separately registered, no publication."""
    a=row(pg,'reconstruction_authorities');obs=row(pg,'observations',"observation_id='"+a['source_manifest']['source_observation_id']+"'")
    old_obs=obs['observation_id'];obs.update(observation_id='UNIT_RECONSTRUCTION',signal_key='FIRST_PREWATCH:UNIT_RECONSTRUCTION')
    insert(pg,'observations',obs)
    a.update(authority_id='UNIT_RECONSTRUCTION_AUTHORITY',authority_contract_id='UNIT_RECONSTRUCTION_CONTRACT',reconstructed_at=c.now())
    a['source_manifest'].update(source_observation_id=obs['observation_id'],snapshot_id='UNIT_RECONSTRUCTION_SNAPSHOT')
    a['source_manifest']['prediction_input_digest']=c.digest([a['source_manifest']['snapshot_id'],a['source_manifest']['feature_digest'],a['source_manifest']['quality_digest']])
    a['source_manifest_digest']=c.digest(a['source_manifest'])
    e={k:a[k] for k in ('authority_id','scope_id','namespace_id','trade_date','evidence_origin','feature_contract_id','source_manifest','source_manifest_digest','accepted_head_identity')}
    c.contract(pg,a['authority_contract_id'],dict(namespace_id=c.NS,exact_authorities=[e]));a['reconstructed_at']=c.now();insert(pg,'reconstruction_authorities',a)
    r=row(pg,'observation_revisions',"observation_id='"+old_obs+"'")
    manifest=dict(a['source_manifest'],reconstruction_authority=a['authority_id'])
    r.update(observation_id=obs['observation_id'],reconstruction_authority_id=a['authority_id'],dependency_manifest=manifest,dependency_digest=c.digest(manifest),created_at=c.now())
    insert(pg,'observation_revisions',r)
    s=row(pg,'snapshots',"observation_id='"+old_obs+"'");old_snap=s['snapshot_id'];s.update(snapshot_id='UNIT_RECONSTRUCTION_SNAPSHOT',observation_id=obs['observation_id'],created_at=c.now());insert(pg,'snapshots',s)
    for (v,) in pg.execute('select to_jsonb(t) from fep.feature_values t where snapshot_id=%s',(old_snap,)).fetchall():
        v['snapshot_id']=s['snapshot_id'];insert(pg,'feature_values',v)
    return dict(observation_id=obs['observation_id'],reconstruction_authority_id=a['authority_id'],snapshot_id=s['snapshot_id'],feature_digest=s['feature_digest'],quality_digest=s['quality_digest'])

def test_acceptance_transaction_rolls_back_after_prediction(canonical):
    from scripts.run_fep_e5_r1r1b import load,old,REPORT
    pg=canonical;mapping=unit_reconstruction(pg)
    model=load(REPORT/'CANONICAL_PREDICTION_BINDING_READBACK.json')['fixtures']['fresh']['models'][0]
    prior=next(r for r in load(old.REPORT/'POSTGRES_LEDGER_EXPORT.json')['tables']['predictions'] if r['model_id']==model['model_id'])
    prior=dict(prior,slot_id='UNIT_TRANSACTION_SLOT')
    activation=c.cas(pg,model['grant_id'],'ALLOW','UNIT_ACCEPTANCE_ACTIVATION');cutoff=c.now()
    slot=c.plan(pg,prior,mapping,model,cutoff,activation);before=c.inventory(pg)
    with pytest.raises(ValueError,match='FEP_INJECTED_ACCEPTANCE_FAILURE'):
        c.accept(pg,prior,mapping,model,cutoff,activation,fail_before_receipt=True)
    assert before==c.inventory(pg)
    assert pg.execute('select count(*) from fep.prediction_slots where slot_id=%s',(slot,)).fetchone()[0]==1
    # Retry the same frozen slot after rollback, with no replacement model/slot.
    result=c.accept(pg,prior,mapping,model,cutoff,activation)
    assert pg.execute('select count(*) from fep.acceptance_receipts where run_id=%s',(result['run_id'],)).fetchone()[0]==1

def test_prediction_first_observed_literal_forbidden(canonical):
    p=row(canonical,'predictions');p.update(prediction_id='UNIT_BAD_FIRST',prediction_evidence='FIRST_OBSERVED')
    rejected(canonical,lambda:insert(canonical,'predictions',p),'FEP_RECONSTRUCTION_EVIDENCE_UPGRADE_FORBIDDEN')

def test_historical_revision_preserves_first_identity(canonical):
    pg=canonical;p=row(pg,'predictions');original=dict(p)
    p.update(supersedes_id=p['prediction_id'],prediction_id='UNIT_CORRECTED_REVISION',revision=2,prediction_evidence='CORRECTED_RECONSTRUCTION')
    insert(pg,'predictions',p)
    assert row(pg,'predictions',"prediction_id='"+original['prediction_id']+"'")==original
    assert CanonicalExpectancyReadAPI(pg).bootstrap(original['slot_id'])['context']['prediction_id']==original['prediction_id']

def test_run_cross_observation_authority_rejected(canonical):
    pg=canonical;p=row(pg,'predictions');r=row(pg,'prediction_runs',"run_id='"+p['run_id']+"'")
    other=pg.execute('select authority_id from fep.reconstruction_authorities where authority_id<>%s limit 1',(r['reconstruction_authority_id'],)).fetchone()[0]
    other_input=pg.execute("select source_manifest->>'prediction_input_digest' from fep.reconstruction_authorities where authority_id=%s",(other,)).fetchone()[0]
    r.update(run_id='UNIT_CROSS_RUN',reconstruction_authority_id=other,input_digest=other_input);insert(pg,'prediction_runs',r)
    p.update(prediction_id='UNIT_CROSS_PRED',run_id=r['run_id'])
    rejected(pg,lambda:insert(pg,'predictions',p),'FEP_PREDICTION_EXACT_AUTHORITY_CLOCK_REQUIRED')

def test_acceptance_wrong_model_set_or_revoke_rejected(canonical):
    pg=canonical;r=row(pg,'acceptance_receipts');r['receipt_id']='UNIT_BAD_ACCEPT'
    revoke=pg.execute("select activation_id from fep.activations where grant_id=%s and action='REVOKE' limit 1",(r['grant_id'],)).fetchone()[0]
    r['activation_id']=revoke
    rejected(pg,lambda:insert(pg,'acceptance_receipts',r),'FEP_EXACT_SHADOW_ACCEPTANCE_REQUIRED')
    k=row(pg,'permission_keys',"grant_id<>'"+r['grant_id']+"'")
    activation=pg.execute("select activation_id from fep.activations where grant_id=%s and action='ALLOW' limit 1",(k['grant_id'],)).fetchone()[0]
    r.update(grant_id=k['grant_id'],activation_id=activation)
    rejected(pg,lambda:insert(pg,'acceptance_receipts',r),'FEP_ACCEPTANCE_MODELSET_MISMATCH|FEP_EXACT_SHADOW_ACCEPTANCE_REQUIRED')

def test_priority_failure_after_insert_has_no_partial_fact(canonical):
    pg=canonical;p=row(pg,'priority_projection');before=c.inventory(pg)
    with pytest.raises(ValueError,match='INJECTED_PRIORITY_AFTER_INSERT'):
        with pg.transaction():
            c.contract(pg,'UNIT_PRIORITY_ATOMICITY',dict(synthetic_only=True))
            p.update(projection_id='UNIT_PRIORITY_ATOMICITY',priority_contract_id='UNIT_PRIORITY_ATOMICITY')
            insert(pg,'priority_projection',p)
            assert c.inventory(pg)['priority_projection']==before['priority_projection']+1
            raise ValueError('INJECTED_PRIORITY_AFTER_INSERT')
    assert before==c.inventory(pg)

def test_priority_fixture_references_canonical_predictions_only(canonical):
    pg=canonical;p=row(pg,'priority_projection');assert p['axis_state']=='SYNTHETIC_LINKAGE_ONLY'
    assert p['axis_values']['synthetic_only'] is True and len(p['axis_values']['synthetic_fixture']['rows'])==7
    assert len(p['prediction_refs'])==3
    for ref in p['prediction_refs']:
        stored=row(pg,'predictions',"prediction_id='"+ref['prediction_id']+"'")
        assert stored['observation_id']==p['observation_id'] and stored['run_id']==ref['run_id'] and stored['snapshot_id']==ref['snapshot_id']
    assert pg.execute('select count(*) from fep.priority_projection_grants').fetchone()[0]==0

def test_CAS_cross_model_set_revoke_rejected(canonical):
    pg=canonical;h=c.head(pg);k=row(pg,'permission_keys',"grant_id<>'"+h[2]+"'");before=c.inventory(pg)
    rejected(pg,lambda:c.cas(pg,k['grant_id'],'REVOKE','UNIT_CROSS_GRANT_REVOKE'),'FEP_CAS_CONFLICT')
    assert c.head(pg)==h and before==c.inventory(pg)

def test_acceptance_stale_allow_cannot_admit_after_revoke(canonical):
    pg=canonical;r=row(pg,'acceptance_receipts');r['receipt_id']='UNIT_STALE_ALLOW'
    rejected(pg,lambda:insert(pg,'acceptance_receipts',r),'FEP_EXACT_SHADOW_ACCEPTANCE_REQUIRED')

def test_run_input_digest_must_match_exact_snapshot(canonical):
    r=row(canonical,'prediction_runs');r.update(run_id='UNIT_WRONG_INPUT',input_digest=c.digest('BAD_SNAPSHOT_INPUT'))
    rejected(canonical,lambda:insert(canonical,'prediction_runs',r),'FEP_RECONSTRUCTION_RUN_BINDING_REQUIRED')
