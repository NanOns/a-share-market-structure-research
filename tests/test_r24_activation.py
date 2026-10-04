"""Real entry gate and isolated successor activation E2E/negative matrix."""
import copy, json, os, sqlite3
import pytest
from scripts.r24_io import ROOT, read, atomic, ref
from scripts.r24_simulation import prepare, controller, SimulationClock, regrant
from scripts.v4_16_shadow_runtime import ShadowRuntimeController
from scripts.v4_16_real_shadow_runtime import OneSessionLaunchController, RealSourceReadinessAdapter
from scripts.validate_r24_activation import inspect, protected

REASONS={
 'A01':'REAL_SHADOW_NOT_AUTHORIZED_BEFORE_CONSUMPTION',
 'A02':'EXACT_DEPENDENCY_MISMATCH',
 'A03':'AUTHORITY_EFFECTIVE_DATE_MISMATCH',
 'A04':'WRONG_MODEL_CONTRACT_ID',
 'A05':'WRONG_PARAMETER_SET_ID',
 'A06':'WRONG_STATE_LINEAGE_ID',
 'A07':'UNGRANTED_CAPABILITY',
 'A08':'UNACCEPTED_STORAGE',
 'A09':'UNACCEPTED_SOURCE_ADAPTER',
 'A10':'MISSING_MANDATORY_SOURCE',
 'A11':'MISSED_OBSERVATION_SLOT',
 'A12':'CALLER_BACKDATED_READINESS_FORBIDDEN',
 'A13':'PREVIOUS_SHADOW_SESSION_GAP',
 'A14':'ENGINEERING_SEED_FORBIDDEN',
 'A15':'CROSS_NAMESPACE_PRIOR',
 'A16':'INJECTED_TRANSACTION_FAILURE',
 'A17':'SECOND_ORIGINAL_ENROLLMENT_FORBIDDEN',
 'A18':'INVALID_SUPERSEDES_CHAIN',
 'A19':'ACTIVATION_HEAD_CAS_CONFLICT',
 'A20':'REAL_SHADOW_NOT_AUTHORIZED_BEFORE_CONSUMPTION',
}

def negative(case):
    baseline=protected()
    if case in ('A01','A20'):
        old=os.environ.get('REAL_SHADOW_AUTHORIZED')
        if case=='A20':os.environ['REAL_SHADOW_AUTHORIZED']='true'
        try:
            with pytest.raises(ValueError,match=REASONS[case]):ShadowRuntimeController(ROOT,'REAL_SHADOW')
        finally:
            if old is None:os.environ.pop('REAL_SHADOW_AUTHORIZED',None)
            else:os.environ['REAL_SHADOW_AUTHORIZED']=old
        assert protected()==baseline
        return dict(case=case,status='PASS_LOCAL',rejection=REASONS[case],before_consumption=True)
    def changes(a,d,s,seed):
        if case=='A09':s['adapter_id']='UNACCEPTED'
        if case=='A10':s['sources'].pop('T0_SNAPSHOT')
        if case=='A14':seed.update(publication_id='R23_ISOLATED_SEED',evidence_origin='ENGINEERING_FIXTURE')
    x=prepare(changes=changes)
    r=x['request']
    if case=='A02':
        deps=read(x['manifest'])
        p=read(deps['activation']['path']);p['authority_id']='CORRUPTED'
        atomic(deps['activation']['path'],p)
    if case=='A08':regrant(x,lambda a:a['grant'].update(storage=dict(path='UNACCEPTED',sha256='0'*64,bytes=0)))
    if case in ('A02','A08','A09'):
        with pytest.raises(ValueError,match=REASONS[case]):controller(x)
        assert not (ROOT/x['database']).exists()
        return dict(case=case,status='PASS_LOCAL',rejection=REASONS[case],before_consumption=True,context=x,
            manifest_binding=ref(x['manifest']),database_created=False)
    c=controller(x);db=c.database(ROOT/x['database']);launch=OneSessionLaunchController(db)
    try:
        if case=='A03':r['trade_date']='2026-09-24'
        if case=='A04':r['model_contract_id']='OTHER'
        if case=='A05':r['parameter_set_id']='OTHER'
        if case=='A06':r['state_lineage_id']='OTHER'
        if case=='A07':r['capabilities']=['A04_H21_CONSUMER']
        if case=='A13':r['trade_date']='2026-09-29'
        if case=='A15':r['prior_namespace']='LEGACY'
        if case=='A19':db.conn.execute('INSERT INTO activation_head VALUES(1,?)',('OTHER_AUTHORITY',))
        if case in ('A17','A18'):
            first=launch.run(r,clock=SimulationClock())
            r.update(revision=2,expected_head=first['publication_id'])
            if case=='A17':r['force_new_original']=True
            else:r['supersedes_observation']='MISSING'
        before=db.conn.execute("SELECT * FROM facts WHERE kind NOT IN ('receipt','slot_plan')").fetchall()
        if case=='A11':
            result=launch.run(r,clock=SimulationClock(late=True))
            assert result['slot_status']=='MISSED_OBSERVATION_SLOT'
            assert not db.rows('publication') and not db.rows('enrollment')
            with pytest.raises(ValueError,match='MISSED_SLOT_CANNOT_UPGRADE'):launch.run(r,clock=SimulationClock())
        else:
            with pytest.raises(ValueError,match=REASONS[case]):
                if case=='A12':
                    binding=c.sources['sources']['OWNER_OUTPUT']['binding']
                    RealSourceReadinessAdapter(db).acquire('OWNER_OUTPUT',r['trade_date'],binding,
                         clock=SimulationClock(),first_observed_at='2000-01-01T00:00:00Z')
                else:launch.run(r,clock=SimulationClock(),fail_at='head' if case=='A16' else None)
            assert db.conn.execute("SELECT * FROM facts WHERE kind NOT IN ('receipt','slot_plan')").fetchall()==before
            if case=='A16':assert len(db.rows('receipt'))==2
        assert protected()==baseline
        return dict(case=case,status='PASS_LOCAL',rejection=REASONS[case],partial_publication_visible=False,context=x,
            manifest_binding=ref(x['manifest']),database_binding=ref(x['database']))
    finally:db.close()

@pytest.mark.parametrize('case',list(REASONS))
def test_negative_activation(case):negative(case)

def positive(name=None):
    before=protected()
    x=prepare(name)
    c=controller(x);db=c.database(ROOT/x['database']);launch=OneSessionLaunchController(db)
    try:
        first=launch.run(x['request'],clock=SimulationClock())
        original=copy.deepcopy(db.rows('enrollment'))
        assert launch.run(x['request'],clock=SimulationClock())==first
        revision=dict(x['request'],revision=2,expected_head=first['publication_id'])
        launch.run(revision,clock=SimulationClock())
        assert db.rows('enrollment')==original
        assert len(db.rows('observation'))==2
        from workbench_analysis.v4_15_settlement import VectorPriceSource
        binding=c.sources['future_binding'];rows=read(binding['path'])['rows']
        with pytest.raises(ValueError,match='PRE_DUE_FUTURE_READ_FORBIDDEN'):
            launch.settle(original[0]['enrollment_id'],1,VectorPriceSource(rows,binding),'2026-09-28')
        launch.settle(original[0]['enrollment_id'],1,VectorPriceSource(rows,binding),'2026-09-29')
        launch.stop()
        from scripts.v4_16_real_shadow_runtime import SettlementObligationController
        obligation_controller=SettlementObligationController(ROOT,ROOT/x['database'],simulation=True)
        obligation_db=obligation_controller.database(ROOT/x['database'])
        try:
            worker=OneSessionLaunchController(obligation_db)
            worker.settle(original[0]['enrollment_id'],1,VectorPriceSource(rows,binding),'2026-09-29')
            with pytest.raises(ValueError,match='SETTLEMENT_ONLY_CANNOT_ACCEPT_PUBLICATION'):
                worker.run(x['request'],clock=SimulationClock())
        finally:obligation_db.close()
        with pytest.raises(ValueError,match='SHADOW_STOPPED'):launch.run(revision,clock=SimulationClock())
        launch.settle(original[0]['enrollment_id'],1,VectorPriceSource(rows,binding),'2026-09-29')
        assert db.rows('enrollment')==original and len(db.rows('due'))==5
        for sql in ("DELETE FROM facts WHERE kind='observation'","UPDATE facts SET digest='fake' WHERE kind='slot'"):
            with pytest.raises(sqlite3.IntegrityError,match='APPEND_ONLY'):db.conn.execute(sql)
    finally:db.close()
    assert protected()==before
    oracle=inspect(ROOT/x['database'],x['manifest'])
    assert oracle['publications']==2 and oracle['enrollments']==1 and oracle['observations']==2
    return dict(context=x,oracle=oracle,protected_before=before,protected_after=protected(),
      rollback_preserves_enrollments=True,settlement_continues_after_stop=True,idempotency=True)

def test_activation_simulation_e2e():positive()

def test_owner_projection_preserves_accepted_semantics():
    import ast, textwrap
    predecessor=(ROOT/'src/workbench_analysis/v4_15_radar_cohort.py').read_text(encoding='utf-8')
    successor=(ROOT/'scripts/v4_16_real_owner_projection_v1.py').read_text(encoding='utf-8')
    old=next(n for n in ast.walk(ast.parse(predecessor)) if isinstance(n,ast.FunctionDef) and n.name=='_project')
    new=next(n for n in ast.walk(ast.parse(successor)) if isinstance(n,ast.FunctionDef) and n.name=='_project')
    expected='\n'.join(predecessor.splitlines()[old.lineno-1:old.end_lineno]).replace(" or date>'2026-09-30'",'')
    expected_node=ast.parse(textwrap.dedent(expected)).body[0]
    assert ast.dump(expected_node,include_attributes=False)==ast.dump(new,include_attributes=False)

def test_authority_rejects_before_source_or_storage(monkeypatch):
    from scripts.v4_16_real_shadow_runtime import RealShadowDatabase, RealSourceReadinessAdapter
    def forbidden(*a,**k):raise AssertionError('DISABLED_AUTHORITY_CONSUMED_INPUT')
    monkeypatch.setattr(RealShadowDatabase,'__init__',forbidden)
    monkeypatch.setattr(RealSourceReadinessAdapter,'acquire',forbidden)
    with pytest.raises(ValueError,match='REAL_SHADOW_NOT_AUTHORIZED_BEFORE_CONSUMPTION'):
        ShadowRuntimeController(ROOT,'REAL_SHADOW')

@pytest.mark.parametrize('mutation',['aggregate','manifest','supersedes','origin','source','scope'])
def test_independent_oracle_corruption(tmp_path,mutation):
    import shutil
    result=positive()
    target=tmp_path/'corrupt.sqlite';shutil.copyfile(ROOT/result['context']['database'],target)
    conn=sqlite3.connect(target)
    conn.execute('DROP TRIGGER no_fact_update')
    kind='observation' if mutation=='supersedes' else 'slot'
    key,raw=conn.execute('SELECT id,payload FROM facts WHERE kind=? ORDER BY rowid DESC',(kind,)).fetchone()
    p=json.loads(raw)
    if mutation=='aggregate':p['system_available_at']='2026-09-28T12:58:00Z'
    if mutation=='manifest':p['source_manifest_digest']='0'*64
    if mutation=='supersedes':p['supersedes_observation']='MISSING'
    if mutation=='origin':p['evidence_class']='PIT_OBSERVED_REAL'
    if mutation=='source':p['visibility_receipt_ids']=[]
    if mutation=='scope':p['capability_scope']=['A04_H21_CONSUMER']
    from scripts.v4_16_real_shadow_runtime import canonical,digest
    conn.execute('UPDATE facts SET payload=?,digest=? WHERE kind=? AND id=?',(canonical(p),digest(p),kind,key))
    # Restore schema name to force semantic checks past schema presence.
    conn.execute("CREATE TRIGGER no_fact_update BEFORE UPDATE ON facts BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END")
    conn.commit();conn.close()
    with pytest.raises(ValueError):inspect(target,result['context']['manifest'],test_only_storage_copy=True)
