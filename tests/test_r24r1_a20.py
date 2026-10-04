"""Real entry gate and isolated successor activation E2E/negative matrix."""
import copy, json, os, sqlite3
import pytest
from scripts.r24r1_io import ROOT, read, atomic, ref
from scripts.r24r1_simulation import prepare, controller, SimulationClock, regrant
from scripts.v4_16_shadow_runtime import ShadowRuntimeController
from scripts.v4_16_go_forward_shadow_runtime import OneSessionLaunchController, RealSourceReadinessAdapter
from scripts.validate_r24r1_activation import inspect, protected

REASONS={
 'A01':'REAL_SHADOW_NOT_AUTHORIZED_BEFORE_CONSUMPTION',
 'A02':'EXACT_DEPENDENCY_MISMATCH',
 'A03':'EXACT_TARGET_DAILY_INPUT_REQUIRED',
 'A04':'WRONG_MODEL_CONTRACT_ID',
 'A05':'WRONG_PARAMETER_SET_ID',
 'A06':'WRONG_STATE_LINEAGE_ID',
 'A07':'UNGRANTED_CAPABILITY',
 'A08':'UNACCEPTED_STORAGE',
 'A09':'UNACCEPTED_SOURCE_ADAPTER',
 'A10':'MISSING_MANDATORY_SOURCE',
 'A11':'MISSED_OBSERVATION_SLOT',
 'A12':'CALLER_BACKDATED_READINESS_FORBIDDEN',
 'A13':'EXACT_TARGET_DAILY_INPUT_REQUIRED',
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
    if case in ('A02','A08','A09','A10'):
        with pytest.raises(ValueError,match=REASONS[case]):controller(x)
        assert not (ROOT/x['database']).exists()
        return dict(case=case,status='PASS_LOCAL',rejection=REASONS[case],before_consumption=True,context=x,
            manifest_binding=ref(x['manifest']),database_created=False)
    c=controller(x);db=c.database(ROOT/x['database']);launch=OneSessionLaunchController(db)
    try:
        if case=='A03':r['trade_date']='2026-09-30'
        if case=='A04':r['model_contract_id']='OTHER'
        if case=='A05':r['parameter_set_id']='OTHER'
        if case=='A06':r['state_lineage_id']='OTHER'
        if case=='A07':r['capabilities']=['A04_H21_CONSUMER']
        if case=='A13':r['trade_date']='2026-10-09'
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
