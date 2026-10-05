from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import os
import psycopg
import pytest
from .conftest import *


def grants(p):
    dataset(p,'cas-ds',expected=[])
    p.execute("insert into fep.training_runs values ('train','cas-ds','fold','{}','ENGINEERING_FIXTURE','POLICY','fixture-commit','{}','{}',%s,%s,%s,'ENGINEERING_FIXTURE_NO_ARTIFACT',%s)",(T,T,T,digest('fixture')))
    for i in (1,2):
        p.execute("insert into fep.models values (%s,'train',%s,'ABS:T5',5,'FEATURE','ENGINEERING_FIXTURE',%s,%s,%s,%s,%s)",
                  (f'm{i}',SCOPE,digest(['t',i]),digest(['c',i]),digest(['o',i]),digest(['m',i]),T))
        p.execute("insert into fep.model_sets values (%s,'POLICY',%s,%s)",(f'set{i}',digest(['set',i]),T))
        p.execute("insert into fep.model_set_members values (%s,%s,'ABS:T5',5,'FEATURE',%s,'CHAMPION')",(f'set{i}',SCOPE,f'm{i}'))
        p.execute("insert into fep.permission_keys values (%s,%s,'ABS:T5',5,'FEATURE',%s,'CHAMPION','SHADOW_INFERENCE')",(f'g{i}',SCOPE,f'set{i}'))


def cas(p, grant='g1', activation='a1', version=0, prior=None, request='req1', action='ALLOW', receipt=None, checks=None):
    return p.execute('select fep.cas_deploy(%s,%s,%s,%s,%s,%s,%s,%s)',
                     (grant,activation,action,version,prior,request,receipt or digest('receipt'),Jsonb({} if checks is None else checks))).fetchone()[0]


@pytest.fixture
def ready(base):
    grants(base)
    return base


def test_E1_23_initial_and_replacement(ready):
    assert cas(ready)==1
    assert cas(ready,grant='g2',activation='a2',version=1,prior='a1',request='req2')==2
    assert ready.execute('select head_version,model_set_id from fep.deployment_heads').fetchone()==(2,'set2')


def test_E1_25_conflict_rolls_back_all(ready):
    cas(ready)
    before=[ready.execute('select count(*) from fep.'+table).fetchone()[0] for table in ['activations','deployment_change_receipts','deployment_heads']]
    rejected(ready,lambda:cas(ready,activation='loser',request='loser'),match='CAS_CONFLICT')
    after=[ready.execute('select count(*) from fep.'+table).fetchone()[0] for table in ['activations','deployment_change_receipts','deployment_heads']]
    assert before==after==[1,1,1]


def test_E1_26_idempotency(ready):
    assert cas(ready)==cas(ready)==1
    assert ready.execute('select count(*) from fep.deployment_change_receipts').fetchone()[0]==1


@pytest.mark.parametrize('kwargs',[dict(grant='g2'),dict(activation='changed'),dict(action='REVOKE'),dict(version=1),dict(prior='a1'),dict(receipt=digest('changed')),dict(checks={'changed':True})])
def test_E1_27_changed_request_args(ready,kwargs):
    cas(ready)
    rejected(ready,lambda:cas(ready,**kwargs),match='IDEMPOTENCY_CONFLICT')


@pytest.mark.parametrize('position',[0,1,2,3,5,6,7])
def test_E1_28_null_parameters(ready,position):
    values=['g1','a1','ALLOW',0,None,'req1',digest('receipt'),Jsonb({})];values[position]=None
    rejected(ready,lambda:ready.execute('select fep.cas_deploy(%s,%s,%s,%s,%s,%s,%s,%s)',values),match='REQUIRED_CAS_PARAMETER_NULL')


def test_null_prior_changed_replay(ready):
    cas(ready)
    rejected(ready,lambda:cas(ready,prior='a1'),match='IDEMPOTENCY_CONFLICT')
    rejected(ready,lambda:cas(ready,activation='a2',version=1,prior=None,request='req2'),match='CAS_CONFLICT')


def test_E1_29_fake_revoke(ready):
    cas(ready)
    rejected(ready,lambda:cas(ready,grant='g2',activation='revoke',version=1,prior='a1',request='revoke',action='REVOKE'),match='CAS_CONFLICT')
    assert cas(ready,activation='valid-revoke',version=1,prior='a1',request='valid-revoke',action='REVOKE')==2


def test_E1_30_future_head(ready):
    ready.execute("insert into fep.activations values ('future','g1','ALLOW',%s,%s,null,0,%s)",(T,T,digest('future')))
    rejected(ready,lambda:ready.execute("insert into fep.deployment_heads values (%s,'SHADOW_INFERENCE','ABS:T5',5,'FEATURE','set1','g1','future',1,%s)",(SCOPE,T)),match='HEAD_ACTIVATION_INVALID')


def test_E1_31_public_execute(ready):
    signature='fep.cas_deploy(text,text,text,bigint,text,text,fep.sha256,jsonb)'
    assert ready.execute('select has_function_privilege(\'fep_auditor\',%s,\'EXECUTE\')',(signature,)).fetchone()[0] is False
    with ready.transaction():
        ready.execute('set local role fep_auditor')
        rejected(ready,lambda:cas(ready),match='permission denied')


def test_E1_32_application_direct_dml(ready):
    cas(ready)
    with ready.transaction():
        ready.execute('set local role fep_application')
        for sql in ["update fep.deployment_heads set head_version=2",'delete from fep.deployment_heads',
                    "update fep.contracts set version='x'","alter table fep.deployment_heads disable trigger all"]:
            rejected(ready,lambda sql=sql:ready.execute(sql),match='permission denied|must be owner')
    ready.execute('reset role')
    ready.execute('set session authorization fep_application')
    try:
        rejected(ready,lambda:ready.execute('set role fep_cas_owner'),match='permission denied')
    finally:
        ready.execute('reset session authorization')


def test_E1_33_search_path_hijack(ready):
    ready.execute('create schema evil')
    ready.execute('create table evil.deployment_heads (head_version integer)')
    ready.execute("create function evil.clock_timestamp() returns timestamptz language sql as 'select ''2100-01-01''::timestamptz'")
    ready.execute('grant usage on schema evil to fep_deployer')
    with ready.transaction():
        ready.execute('set local role fep_deployer')
        ready.execute('set local search_path=evil,public,fep')
        assert cas(ready)==1
    ready.execute('reset role')
    assert ready.execute('select count(*) from evil.deployment_heads').fetchone()[0]==0
    owner,settings=ready.execute("select pg_get_userbyid(proowner),proconfig from pg_proc where oid='fep.cas_deploy(text,text,text,bigint,text,text,fep.sha256,jsonb)'::regprocedure").fetchone()
    assert owner=='fep_cas_owner' and 'search_path=pg_catalog, fep' in settings


def test_read_only_no_role_escalation(pg):
    memberships=pg.execute("select count(*) from pg_auth_members m join pg_roles r on r.oid=m.member where r.rolname in ('fep_schema_owner','fep_cas_owner','fep_application','fep_deployer','fep_adapter','fep_auditor')").fetchone()[0]
    assert memberships==0
    for role in ['fep_schema_owner','fep_cas_owner','fep_application','fep_deployer','fep_adapter','fep_auditor']:
        assert pg.execute('select rolsuper,rolcreatedb,rolcreaterole,rolcanlogin,rolbypassrls from pg_roles where rolname=%s',(role,)).fetchone()==(False,False,False,False,False)


def test_E1_24_concurrent_cas_and_same_request(pg):
    from workbench_analysis.fep_e1.db import apply
    dsn=os.environ['FEP_E1_TEST_DSN']; old=pg.execute('select current_database()').fetchone()[0]
    import uuid
    name=old+'_concurrency_'+uuid.uuid4().hex[:8]
    from psycopg.conninfo import conninfo_to_dict,make_conninfo
    params=conninfo_to_dict(dsn);params['dbname']='postgres'
    with psycopg.connect(make_conninfo(**params),autocommit=True) as admin:
        from psycopg import sql
        admin.execute(sql.SQL('create database {} template fep_e1_template').format(sql.Identifier(name)))
    params['dbname']=name; isolated=make_conninfo(**params)
    with psycopg.connect(isolated) as p:
        base.__wrapped__(p);grants(p)
    def compete(args):
        barrier,args=args
        with psycopg.connect(isolated) as p:
            barrier.wait()
            txid,pid=p.execute('select txid_current(),pg_backend_pid()').fetchone()
            try:
                value=cas(p,**args);p.commit()
                return dict(status='PASS',version=value,transaction_id=txid,session_pid=pid)
            except psycopg.Error as e:
                p.rollback();return dict(status='BLOCK',exception=str(e),sqlstate=e.sqlstate,transaction_id=txid,session_pid=pid)
    b=Barrier(2)
    with ThreadPoolExecutor(2) as executor:
        results=list(executor.map(compete,[(b,dict(activation='race1',request='race1')),(b,dict(activation='race2',request='race2'))]))
    assert sum(x['status']=='PASS' for x in results)==1
    assert 'FEP_CAS_CONFLICT' in next(x['exception'] for x in results if x['status']=='BLOCK')
    with psycopg.connect(isolated) as p:
        counts={t:p.execute('select count(*) from fep.'+t).fetchone()[0] for t in ['activations','deployment_change_receipts','deployment_heads']}
        assert counts==dict(activations=1,deployment_change_receipts=1,deployment_heads=1)
        prior=p.execute('select activation_id from fep.deployment_heads').fetchone()[0]
    b=Barrier(2);args=dict(grant='g2',activation='replay',version=1,prior=prior,request='same-request')
    with ThreadPoolExecutor(2) as executor:
        replays=list(executor.map(compete,[(b,args),(b,args)]))
    assert all(x['status']=='PASS' and x['version']==2 for x in replays)
    from workbench_analysis.fep_e1.contracts import atomic_json
    atomic_json(ROOT/'reports/fep_e1'/f'CAS_CONCURRENCY_{old}.json',dict(evidence_class='ENGINEERING_FIXTURE',isolated_database=name,concurrent_cas=results,identical_request_replay=replays,rollback_counts=counts))
