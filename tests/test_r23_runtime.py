"""Persisted SQLite E2E, activation boundary and required N01..N24 families."""
import ast,copy,sqlite3,uuid,json
import pytest
from scripts.r23_io import ROOT,AUTH,DEPS,read,atomic,ref
from scripts.run_r23_engineering import prepare,request,receipt,positive
from scripts import validate_r23_runtime as oracle
from workbench_analysis.v4_16_shadow_runtime import *

REJECTIONS=[]
@pytest.fixture
def engineering(request):
    REJECTIONS.clear();c,db=prepare();before=counts(db);yield c,db
    after=counts(db);db.close()
    if hasattr(request.node,'callspec') and 'number' in request.node.callspec.params:
        number=request.node.callspec.params['number']
        atomic('reports/r23/isolated_db/test_receipts/N%02d.json'%number,dict(case='N%02d'%number,database=str(db.path),database_binding=ref(str(db.path.relative_to(ROOT))),rejections=list(REJECTIONS),before=before,after=after,evidence_origin='ENGINEERING_FIXTURE',expected='PURE_CORE_CONTINUES' if number==18 else 'FAIL_CLOSED'))
def counts(db):return {t:db.conn.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in db.TABLES}
def reject(fn):
    with pytest.raises((ValueError,sqlite3.IntegrityError)) as caught:fn()
    REJECTIONS.append(str(caught.value))
@pytest.mark.parametrize('number',range(1,25),ids=lambda n:'N%02d'%n)
def test_negative_e2e_families(engineering,number):
    c,db=engineering;r=request(c);tx=ShadowPublicationAcceptanceTransaction(db)
    if number==1:
        reject(lambda:ShadowRuntimeController(ROOT,'REAL_SHADOW'));return
    if number in (13,14,22,24,9,11):tx.accept(r)
    if number==2:r['scheduled_cutoff_at']='2026-09-28T13:00:01Z'
    elif number==3:
        late=receipt(c,'owner','R23_OWNER_LATE','OWNER_OUTPUT','LATE');late['system_available_at']='2026-09-28T13:00:01Z'
        SourceReadinessReceiptRegistry(db).register(late,c.registry['bindings']['owner']);r['receipt_ids'][0]='R23_OWNER_LATE'
    elif number==4:r['receipt_ids'][0]='MISSING'
    elif number in (5,6):
        bad=receipt(c,'owner','R23_OWNER_1','OWNER_OUTPUT')
        if number==5:bad['source_digest']='0'*64
        else:bad['first_observed_at']='2026-09-28T12:58:00Z'
        reject(lambda:SourceReadinessReceiptRegistry(db).register(bad,c.registry['bindings']['owner']));return
    elif number==7:r['prior_namespace']='PRODUCTION_LEGACY'
    elif number==8:r['state_lineage_id']='MISSING_PREVIOUS_LINEAGE'
    elif number==9:r=request(c,2);r['force_new_original']=True
    elif number==10:
        before=counts(db);reject(lambda:tx.accept(r,fail_at='head'));assert counts(db)==before;assert not db.conn.execute('SELECT * FROM shadow_publication_heads').fetchall();return
    elif number==11:
        e=db.rows('shadow_first_enrollments')[0];reject(lambda:db.append('shadow_first_enrollments','NEW_KEY_SAME_EVENT',e));return
    elif number==12:r['raw_provider_fallback']=True
    elif number in (13,14,22):
        en=db.rows('shadow_first_enrollments')[0];binding=c.registry['bindings']['future'];source=VectorPriceSource(c.fixture('future')['rows'],binding)
        if number==14:source.binding={'path':'unaccepted','sha256':'0'*64,'bytes':0}
        reject(lambda:SettlementWorkerOrchestrator(db).run(en['enrollment_id'],1,source,'2026-09-28' if number==13 else '2026-09-29',redraw=number==22));assert source.read_log==[];return
    elif number==15:
        reject(lambda:DailyMembershipSnapshotWriter(db).write(dict(r,membership=[{'membership_basis':'CURRENT_REPLAY','evidence_origin':'PIT_OBSERVED'}])));return
    elif number in (16,17):r['capabilities']=['A04_H21_CONSUMER' if number==16 else 'A08_CURRENT_RUNTIME']
    elif number==18:
        r['optional_baostock_available']=False;tx.accept(r);assert len(db.rows('shadow_first_enrollments'))==1;return
    elif number==19:r['parameter_set_id']='UNVERSIONED_PARAMETERS'
    elif number==20:r['clock_binding']=dict(c.deps['clock'],sha256='0'*64)
    elif number==21:r['ui_exclusion']=True
    elif number==23:r['increment_real_counter']=True
    elif number==24:
        before=counts(db);reject(lambda:RollbackController(db).stop(delete_observations=True));assert counts(db)==before;return
    before=counts(db);reject(lambda:tx.accept(r));assert counts(db)==before

def test_complete_independent_persisted_positive_e2e():
    result=positive('test_positive_'+uuid.uuid4().hex)
    assert oracle.inspect_database(Path(result['database']))['status']=='PASS_LOCAL'
def test_real_rejected_before_database_creation(monkeypatch):
    called=[];monkeypatch.setattr(sqlite3,'connect',lambda *a,**k:called.append(a))
    reject(lambda:ShadowRuntimeController(ROOT,'REAL_SHADOW'));assert called==[]
def test_dry_run_contract_resolution_no_accept():
    c=ShadowRuntimeController(ROOT,'DRY_RUN_NO_ACCEPT');assert c.clock.resolve('2026-09-28',c.authority.sessions)['scheduled_cutoff_at']=='2026-09-28T13:00:00Z'
    reject(lambda:c.database(ROOT/'reports/r23/isolated_db/forbidden_dry.sqlite'))
def test_db_cannot_be_production_path(engineering):
    c,_=engineering;reject(lambda:c.database(ROOT/'production.sqlite'))
@pytest.mark.parametrize('table',sorted(ShadowDatabase.TABLES))
def test_immutable_storage_sql_triggers(engineering,table):
    _,db=engineering;db.append(table,'TRIGGER_TEST',{'probe':'immutable'})
    with pytest.raises(sqlite3.IntegrityError):db.conn.execute('UPDATE '+table+' SET payload=? WHERE id=?',('{}','TRIGGER_TEST'))
    with pytest.raises(sqlite3.IntegrityError):db.conn.execute('DELETE FROM '+table+' WHERE id=?',('TRIGGER_TEST',))
def test_database_namespace_and_origin_constraints(engineering):
    _,db=engineering
    for ns,origin in [('PRODUCTION_LEGACY','ENGINEERING_FIXTURE'),('SHADOW_V4','PIT_OBSERVED')]:
        with pytest.raises(sqlite3.IntegrityError):db.conn.execute('INSERT INTO shadow_observations VALUES(?,?,?,?,?)',('bad',ns,origin,'{}','0'*64))
def test_receipt_idempotency_and_append_only(engineering):
    c,db=engineering;registry=SourceReadinessReceiptRegistry(db);r=receipt(c,'owner','R23_OWNER_1','OWNER_OUTPUT')
    assert registry.register(r,c.registry['bindings']['owner'])=='R23_OWNER_1'
    r['source_revision']='R99';reject(lambda:registry.register(r,c.registry['bindings']['owner']))
def test_first_manifest_freeze_and_head_cas(engineering):
    c,db=engineering;tx=ShadowPublicationAcceptanceTransaction(db);p=tx.accept(request(c));r=request(c,2);r['expected_head']='STALE_HEAD';before=counts(db)
    reject(lambda:tx.accept(r));assert counts(db)==before
    with pytest.raises(sqlite3.IntegrityError):db.conn.execute('UPDATE shadow_publication_heads SET revision=99')
def test_prior_uses_explicit_accepted_head_not_latest_state(engineering):
    c,db=engineering;seed=c.fixture('seed');fake=dict(seed,publication_id='ROGUE_UNACCEPTED_STATE',revision=999)
    db.append('shadow_state_heads','ROGUE',fake)
    slot=ObservationSlotPlanner(db).plan(request(c));assert ShadowPriorStateReader(db).read(slot)==seed
def test_early_publication_allowed(engineering):
    c,db=engineering;r=request(c);r.update(computation_started_at='2026-09-28T12:59:00Z',computation_finished_at='2026-09-28T12:59:15Z',accepted_at='2026-09-28T12:59:30Z');ShadowPublicationAcceptanceTransaction(db).accept(r)
def test_planner_blocked_missing_and_nonmarket(engineering):
    c,db=engineering;r=request(c);r['receipt_ids']=[];assert ObservationSlotPlanner(db).record(r)['slot_status']=='BLOCKED_SOURCE_NOT_READY'
    r['trade_date']='2026-10-03';reject(lambda:ObservationSlotPlanner(db).plan(r))
def test_blocked_to_ready_and_missed_terminal(engineering):
    c,db=engineering;r=request(c);p=ObservationSlotPlanner(db)
    assert p.record(dict(r,receipt_ids=[]))['slot_status']=='BLOCKED_SOURCE_NOT_READY'
    assert p.record(r)['slot_status']=='PLANNED'
    late=receipt(c,'owner','R23_OWNER_LATE','OWNER_OUTPUT','LATE');late['system_available_at']='2026-09-28T13:00:01Z';SourceReadinessReceiptRegistry(db).register(late,c.registry['bindings']['owner'])
    assert p.record(dict(r,receipt_ids=['R23_OWNER_LATE','R23_SNAPSHOT_1']))['slot_status']=='MISSED_OBSERVATION_SLOT'
    assert p.record(r)['slot_status']=='MISSED_OBSERVATION_SLOT'
    reject(lambda:ShadowPublicationAcceptanceTransaction(db).accept(r))
def test_stop_preserves_obligations_and_rejects_restart(engineering):
    c,db=engineering;tx=ShadowPublicationAcceptanceTransaction(db);tx.accept(request(c));before=ShadowReadbackReader(db).read();RollbackController(db).stop()
    assert ShadowReadbackReader(db).read()==before;reject(lambda:tx.accept(request(c,2)));reject(lambda:RollbackController(db).restart())
def test_health_never_grants_real_capability(engineering):
    _,db=engineering;r=ShadowHealthReceiptWriter(db).failure('FAILURE_PROBE','MISSING_SOURCE');assert r['REAL_SHADOW_OBSERVATIONS']==0 and r['SHADOW_STABLE']=='NOT_GRANTED'
    reject(lambda:db.append('shadow_health_receipts','real',dict(REAL_SHADOW_OBSERVATIONS=1)))
def test_exact_accepted_producer_callable_wiring(engineering):
    _,db=engineering;adapter=AcceptedBusinessProducerAdapter(db)
    for stage in ['v4_10','v4_11','v4_12','v4_13','v4_14']:assert callable(adapter.accepted_producer(stage))
def test_daily_membership_non_pit_capture(engineering):
    c,db=engineering;r=request(c);r['membership']=[dict(sector_id='I',security_id='S',trade_date=r['trade_date'],observed_at='2026-09-28T12:00:00Z',system_available_at='2026-09-28T12:00:01Z',source_revision='FIXTURE1',source_digest='a'*64,membership_basis='ENGINEERING_FIXTURE',membership_quality='ENGINEERING_ONLY',evidence_origin='ENGINEERING_FIXTURE')]
    assert DailyMembershipSnapshotWriter(db).write(r)=='ENGINEERING_ONLY';assert len(db.rows('shadow_membership_snapshots'))==1
def test_independent_oracle_no_runtime_import():
    import inspect
    source=inspect.getsource(oracle);tree=ast.parse(source)
    assert 'v4_16_shadow_runtime' not in source and 'run_r23_engineering' not in source
    assert all(not isinstance(n,ast.ImportFrom) or 'build_' not in (n.module or '') for n in ast.walk(tree))
def test_protected_authority():assert oracle.protected()['status']=='PASS_LOCAL'
