"""Forward-authority, persisted cohort identity and independent admission negatives."""
import ast, copy, json, shutil, sqlite3
import pytest
from scripts.r24r1_io import ROOT, read, atomic, ref
from scripts.r24r1_simulation import prepare, controller, SimulationClock, regrant, TARGET
from scripts.v4_16_go_forward_shadow_runtime import OneSessionLaunchController, canonical, digest
from scripts.validate_r24r1_activation import inspect, protected

F_CASES=['F%02d'%i for i in range(1,15)]

def daily_negative(case):
    def mutate(d,g,base):
        if case=='F01':d['calendar']=atomic(base+'/missing_calendar.json',dict(session_dates=['2026-09-30']))
        if case=='F02':d['previous_trade_date']='2026-09-29'
        if case=='F04':d['sources']['OWNER_OUTPUT']['target_trade_date']='2026-09-30'
        if case=='F05':d['sources']['OWNER_OUTPUT']['max_source_trade_date']='2026-10-09'
        if case=='F06':d['sources']['OWNER_OUTPUT']['accepted_at']=TARGET+'T13:00:01Z'
        if case=='F07':d['sources'].pop('TDX_RAW_DAILY')
        if case=='F08':d['day_package']=atomic(base+'/stale_package.json',dict(trade_date='2026-09-30',snapshot_identity=d['snapshot_identity'],sources=d['sources']))
        if case=='F09':d['identity']=atomic(base+'/unaccepted_identity.json',dict(accepted=False,target_trade_date=TARGET))
        if case=='F10':d['membership']=None
        if case=='F13':g['minimum_daily_input_revision']=2
        if case=='F14':d['parameter_set_id']='OTHER'
    x=prepare(mutate=mutate)
    if case=='F03':regrant(x,lambda a:a['grant'].update(daily_input_digest='0'*64))
    if case=='F10':regrant(x,lambda a:a['grant'].update(capability_scope=['SECTOR_ENHANCED']))
    if case=='F12':regrant(x,lambda a:a['grant'].update(daily_input_authority=dict(path=x['base']+'/latest.json',bytes=0,sha256='0'*64)))
    if case=='F11':
        c=controller(x); assert c.authority.membership_ref=='NOT_REQUIRED_FOR_SCOPE'
        return dict(case=case,status='PASS_LOCAL',result='PURE_CORE_CONTINUES_WITHOUT_MEMBERSHIP',context=x)
    with pytest.raises((ValueError,FileNotFoundError)) as error:controller(x)
    assert not (ROOT/x['database']).exists()
    return dict(case=case,status='PASS_LOCAL',rejection=str(error.value),database_created=False,context=x)

@pytest.mark.parametrize('case',F_CASES)
def test_daily_negative(case):daily_negative(case)

def positive(name=None):
    before=protected(); x=prepare(name); c=controller(x)
    from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
    assert TARGET not in CurrentStageAuthority(ROOT).sessions
    db=c.database(ROOT/x['database']); launch=OneSessionLaunchController(db)
    try:
        first=launch.run(x['request'],clock=SimulationClock())
        original=copy.deepcopy(db.rows('enrollment'))
        assert launch.run(x['request'],clock=SimulationClock())==first
        revision=dict(x['request'],revision=2,expected_head=first['publication_id'])
        launch.run(revision,clock=SimulationClock())
        assert db.rows('enrollment')==original
        from workbench_analysis.v4_15_settlement import VectorPriceSource
        b=c.sources['future_binding']; source=VectorPriceSource(read(b['path'])['rows'],b)
        with pytest.raises(ValueError,match='PRE_DUE_FUTURE_READ_FORBIDDEN'):launch.settle(original[0]['enrollment_id'],1,source,TARGET)
        launch.settle(original[0]['enrollment_id'],1,source,'2026-10-09')
        launch.stop()
        from scripts.v4_16_go_forward_shadow_runtime import SettlementObligationController
        worker=SettlementObligationController(ROOT,ROOT/x['database'],simulation=True)
        other=worker.database(ROOT/x['database'])
        try:
            OneSessionLaunchController(other).settle(original[0]['enrollment_id'],1,source,'2026-10-09')
            with pytest.raises(ValueError,match='SETTLEMENT_ONLY'):OneSessionLaunchController(other).run(x['request'],clock=SimulationClock())
        finally:other.close()
        with pytest.raises(ValueError,match='SHADOW_STOPPED'):launch.run(revision,clock=SimulationClock())
        for sql in ["DELETE FROM facts WHERE kind='enrollment'","UPDATE facts SET digest='bad' WHERE kind='slot'"]:
            with pytest.raises(sqlite3.IntegrityError):db.conn.execute(sql)
    finally:db.close()
    assert protected()==before
    return dict(context=x,oracle=inspect(ROOT/x['database'],x['manifest']),old_calendar_rejects_target=True,
        correction_preserves_original=True,settlement_continues_after_stop=True)

def test_future_reachability():positive()

def corruption(case,tmp_path):
    x=positive()['context']; target=tmp_path/(case+'.sqlite'); shutil.copyfile(ROOT/x['database'],target)
    conn=sqlite3.connect(target)
    conn.execute('DROP TRIGGER no_fact_update')
    kind='enrollment' if case.startswith('C') else 'realtime_admission'
    key,raw=conn.execute('SELECT id,payload FROM facts WHERE kind=? LIMIT 1',(kind,)).fetchone(); p=json.loads(raw)
    if case=='C01':p['enrollment_id']=digest([p['logical_event_id'],'SHADOW_V4_FIRST_OBSERVED'])
    if case=='C02':p['cohort_namespace']='CORRECTED'
    if case=='C03':p['logical_event_id']='0'*64
    if case=='C04':p['enrollment_id']='1'*64
    if case=='S01':p['owner_event']['logical_event_id']='0'*64
    if case=='S02':p['observation_slot']['revision']=99
    if case=='S03':p['visibility_receipt_ids']=[]
    if case=='S04':p['source_manifest_digest']='0'*64
    physical_key=p['enrollment_id'] if case=='C01' else key
    conn.execute('UPDATE facts SET id=?,payload=?,digest=? WHERE kind=? AND id=?',(physical_key,canonical(p),digest(p),kind,key))
    conn.execute("CREATE TRIGGER no_fact_update BEFORE UPDATE ON facts BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END")
    conn.commit();conn.close()
    with pytest.raises(ValueError) as error:inspect(target,x['manifest'],test_only_storage_copy=True)
    return dict(case=case,status='PASS_LOCAL',rejection=str(error.value))

@pytest.mark.parametrize('case',['C01','C02','C03','C04','S01','S02','S03','S04'])
def test_independent_corruption(case,tmp_path):corruption(case,tmp_path)

def test_oracle_has_no_writer_imports():
    tree=ast.parse((ROOT/'scripts/validate_r24r1_activation.py').read_text())
    imports=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
    assert not any(any(s in name for s in ['shadow_runtime','go_forward_authority','owner_projection','simulation']) for name in imports)

@pytest.mark.parametrize('point',['cohort','head'])
def test_atomic_failure(point):
    x=prepare(); db=controller(x).database(ROOT/x['database'])
    try:
        with pytest.raises(ValueError,match='INJECTED_TRANSACTION_FAILURE'):OneSessionLaunchController(db).run(x['request'],clock=SimulationClock(),fail_at=point)
        assert not db.rows('publication') and not db.rows('enrollment') and not db.rows('realtime_admission') and not db.rows('daily_input')
        assert len(db.rows('receipt'))==2
    finally:db.close()

def test_duplicate_logical_event_is_rejected_by_storage():
    x=prepare(); db=controller(x).database(ROOT/x['database'])
    try:
        OneSessionLaunchController(db).run(x['request'],clock=SimulationClock())
        e=db.rows('enrollment')[0]
        with pytest.raises(sqlite3.IntegrityError):db.append('enrollment','alternate',dict(e,enrollment_id='alternate'))
        assert len(db.rows('enrollment'))==1
    finally:db.close()

def test_nested_future_source_row_cannot_hide_behind_declared_max():
    def mutate(d,g,base):
        d['sources']['ADJUSTED_DAILY']['binding']=atomic(base+'/future_row.json',dict(trade_date=TARGET,max_source_trade_date=TARGET,rows=[dict(trade_date='2026-10-09')]))
    x=prepare(mutate=mutate)
    with pytest.raises(ValueError,match='SOURCE_PAYLOAD_MAX_DATE_MISMATCH'):controller(x)
