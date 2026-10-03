import copy,json
from pathlib import Path
import pytest
from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
from workbench_analysis.v4_15_persistence import Store
from workbench_analysis.v4_15_radar_cohort import RadarCohortRuntime
ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture
def runtime(tmp_path):
    a=CurrentStageAuthority(ROOT);return RadarCohortRuntime(a,Store(tmp_path))
def fixture(rt,pid='r1',event='FIRST_PREWATCH',**changes):
    row=dict(entity_type='STOCK',entity_id='S1',episode_id='EP1',maturity='PREWATCH',final_eligibility='TRUE',model_contract_id='M1',state_lineage_id='L1',radar_owner_events=[event],comparison_reference=100,adjustment_identity='AFFINE1',matched_predicates=['PREWATCH'],unknown_predicates=['UNKNOWN_FACT'])
    row.update(changes.pop('row',{}))
    f=dict(evidence_class='ENGINEERING_SYNTHETIC',authority=rt.authority.head_ref,publication_id=pid,trade_date='2026-09-01',rows=[row]);f.update(changes)
    return rt.store.append('owner_fixture',pid,f)
def test_first_persistent_revision_and_correction(runtime):
    r=runtime;s=r.store
    first=s.read(r.engineering_fixture(fixture(r)))
    frozen=s.read(first['enrollments'][0]);assert len(first['logical_events'])==1
    second=s.read(r.engineering_fixture(fixture(r,'r2')))
    assert first['logical_events']==second['logical_events'] and first['enrollments']==second['enrollments']
    r.engineering_fixture(fixture(r,'r3',observation_metadata={'observation_state':'CORRECTED','source_correction':True}))
    r.engineering_fixture(fixture(r,'r4',observation_metadata={'observation_state':'RETRACTED'}))
    persistent=s.read(r.engineering_fixture(fixture(r,'r5',row={'radar_owner_events':[]})))
    assert len(persistent['daily_ledger'])==1 and not persistent['logical_events']
    assert len(s.refs('enrollment'))==1 and s.read(first['enrollments'][0])==frozen
    assert len(s.refs('event_observation'))==4
    assert s.read(first['observations'][0])['conflict']['quality']=='HYPOTHESIS_SET_INCOMPLETE'
@pytest.mark.parametrize('event,entity,eligible,enroll',[('FIRST_PREWATCH','STOCK','TRUE',True),('REENTRY_PREWATCH','STOCK','TRUE',True),('NEW_CONFIRMED','STOCK','TRUE',True),('REACCELERATION_EVENT','STOCK','TRUE',True),('UPGRADE_TO_WARM','SECTOR','TRUE',True),('INVALIDATION','STOCK','FALSE',False),('UPGRADE_TO_WARM','STOCK','TRUE',False)])
def test_frozen_event_families(runtime,event,entity,eligible,enroll):
    m=runtime.store.read(runtime.engineering_fixture(fixture(runtime,event=event,row={'entity_type':entity,'final_eligibility':eligible})))
    assert bool(m['enrollments'])==enroll
    if entity=='STOCK' and event=='UPGRADE_TO_WARM':assert m['diagnostics'][0]['status'].startswith('NOT_APPLICABLE')
def test_focus_display_and_multisector_do_not_filter(runtime):
    one=runtime.store.read(runtime.engineering_fixture(fixture(runtime,row={'focus':False,'displayed':False,'supporting_sectors':['A','B','C']})))
    assert len(one['logical_events'])==len(one['enrollments'])==1
    assert len(one['daily_ledger'])==1
@pytest.mark.parametrize('key',['focus_filter','ui_top_k_filter','future_source','fep_prediction','reset_T0','redraw_controls','qualification_source'])
def test_forbidden_metadata(runtime,key):
    with pytest.raises(ValueError,match='FORBIDDEN'):
        runtime.engineering_fixture(fixture(runtime,observation_metadata={key:True}))
def test_changed_byte_overwrite_rejected(runtime):
    fixture(runtime)
    with pytest.raises(ValueError,match='OVERWRITE'):fixture(runtime,row={'comparison_reference':99})
def test_illegal_episode_revision(runtime):
    runtime.engineering_fixture(fixture(runtime))
    with pytest.raises(ValueError,match='EPISODE'):runtime.engineering_fixture(fixture(runtime,'r2',row={'episode_id':'EP2'}))
def test_formal_exit_reentry_preserves_old(runtime):
    runtime.engineering_fixture(fixture(runtime))
    runtime.engineering_fixture(fixture(runtime,'exit',event='INVALIDATION',row={'final_eligibility':'FALSE'}))
    runtime.engineering_fixture(fixture(runtime,'reentry',event='REENTRY_PREWATCH',row={'episode_id':'EP2','parent_episode_id':'EP1','formal_owner_new_episode':True}))
    assert len(runtime.store.refs('enrollment'))==2
def test_no_current_authority_and_namespace_escape(runtime,tmp_path):
    with pytest.raises(ValueError):RadarCohortRuntime(object(),runtime.store)
    with pytest.raises(ValueError):Store(tmp_path,'../outside')
def test_unsealed_publication_rejected(runtime):
    with pytest.raises(ValueError,match='NOT_SEALED'):runtime.project({'path':'fake','sha256':'0'*64,'bytes':0})
def test_future_event_rejected(runtime):
    ref=fixture(runtime,row={'radar_owner_events':[]},events=[{'entity_type':'STOCK','entity_id':'S1','event_type':'FIRST_PREWATCH','event_trade_date':'2026-09-02'}])
    with pytest.raises(ValueError,match='FUTURE'):runtime.engineering_fixture(ref)
def test_duplicate_entity_rejected(runtime):
    f=runtime.store.read(fixture(runtime));f['publication_id']='duplicate';f['rows']*=2
    ref=runtime.store.append('owner_fixture','duplicate',f)
    with pytest.raises(ValueError,match='DUPLICATE'):runtime.engineering_fixture(ref)
@pytest.mark.parametrize('maturity',['SEED','NEAR_MISS'])
def test_diagnostics_never_primary_enrollment(runtime,maturity):
    m=runtime.store.read(runtime.engineering_fixture(fixture(runtime,row={'maturity':maturity})))
    assert not m['enrollments']
