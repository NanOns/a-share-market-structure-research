"""Negative event strata vectors; never admitted as historical observations."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from workbench_analysis.fep_e1.contracts import digest
from workbench_analysis.fep_e2.historical_dataset import LINEAGE,scoped_policy,verify_stage_order
from workbench_analysis.fep_e2.event_strata import event_observation,event_dataset,event_policy,event_baseline,owner_gap
from workbench_analysis.fep_e2.support import discover,inventory
from tests.fep_e2.test_conditional import fixture,POLICY,CONTRACT,NOW

ROOT=Path(__file__).resolve().parents[2]

def vector(signal='FIRST_PREWATCH',episode='ep1'):
    row=dict(LINEAGE,source_kind='REAL_ACCEPTED_HISTORICAL_SOURCE',observation_id=signal+episode,
        entity_id='entity',trade_date='2026-09-01',episode_key=episode)
    en=dict(enrollment_id=row['observation_id'],signal_type=signal,entity_id='entity',T0=row['trade_date'],
        episode_id=episode,logical_event_id=signal+episode)
    event=dict(logical_event_id=en['logical_event_id'],episode_id=episode)
    state=dict(publication_id='state1',parent_episode_id=None,transition_reasons=['ENROLLED'],maturity='PREWATCH')
    return row,en,event,state

def first_dataset():
    d=fixture();rows=[]
    for r in d['denominator']:
        rows.append(dict(r,signal_type='FIRST_PREWATCH',predecessor_observation_id=r['observation_id']))
    return event_dataset(d,rows)

def test_01_pooled_entry_policy_rejected():
    d=fixture()
    with pytest.raises(ValueError,match='POOLED_ENTRY'):event_baseline(d,d['denominator'][0],POLICY,CONTRACT,NOW)

def test_02_exact_first_signal():
    d=first_dataset();p=deepcopy(POLICY);p['applicability']['signal_type']='FIRST_PREWATCH'
    assert event_baseline(d,d['denominator'][0],p,CONTRACT,NOW)['base_partition']['signal_type']=='FIRST_PREWATCH'

def test_03_policy_cannot_serve_reentry():
    d=first_dataset();p=deepcopy(POLICY);p['applicability']['signal_type']='REENTRY'
    with pytest.raises(ValueError,match='APPLICABILITY'):event_baseline(d,d['denominator'][0],p,CONTRACT,NOW)

def test_04_same_entity_different_episodes():
    a=event_observation(*vector(episode='ep1'));b=event_observation(*vector(episode='ep2'))
    assert a['observation_id']!=b['observation_id'] and a['entity_id']==b['entity_id']

def test_05_same_episode_different_events_not_independent_episodes():
    a=event_observation(*vector());b=event_observation(*vector('NEW_CONFIRMED'))
    assert a['observation_id']!=b['observation_id'] and a['episode_id']==b['episode_id']
    rows=[dict(r,date_ordinal=1,label_end_ordinal=2,episode_start=1,episode_end=8) for r in (a,b)]
    assert inventory(rows)['episodes']==1

def test_06_missing_invalidation_never_false():
    gap=owner_gap('REENTRY',dict(implemented=False,required=True,producer_contract_id='MISSING'))
    assert gap['value']=='UNKNOWN' and gap['reason']=='OWNER_REQUIRED_INPUT_UNAVAILABLE'

def test_07_reentry_without_owner_not_enabled():
    assert owner_gap('REENTRY',dict(implemented=False,required=True,producer_contract_id='MISSING'))['status']=='NOT_ENABLED_OWNER_INPUT_UNAVAILABLE'

def test_08_gap_ledger_keeps_all_opportunities():
    ledger=json.loads((ROOT/'reports/fep_e2_r1r2/EVENT_DENOMINATOR_LEDGER.json').read_bytes())
    assert ledger['counts']['REENTRY_OWNER_INPUT_UNAVAILABLE']>0
    assert ledger['counts']['NEW_CONFIRMED_OWNER_INPUT_UNAVAILABLE']==ledger['counts']['REENTRY_OWNER_INPUT_UNAVAILABLE']
    assert len(ledger['receipts'])==5337 and ledger['states_scanned']==2860632

def test_09_pooled_superseded_preserved():
    p=json.loads((ROOT/'reports/fep_e2_r1r2/POOLED_BASELINE_SUPERSESSION.json').read_bytes())
    assert p['status']=='SUPERSEDED_DIAGNOSTIC_ONLY' and not p['may_feed_E3']
    assert p['old_artifacts_preserved']

def test_10_freeze_before_statistics():
    with pytest.raises(ValueError,match='STAGE_ORDER'):verify_stage_order(NOW,NOW,NOW,NOW)

def test_11_discovery_no_performance():
    d=first_dataset();a=discover(d['denominator'],d['rows'])
    for r in d['denominator']:r['outcome']=999999
    assert discover(d['denominator'],d['rows'])==a
    app=dict(POLICY['applicability'],signal_type='FIRST_PREWATCH')
    assert event_policy(a,app,NOW)['derivation']['classification']=='ENGINEERING_SUPPORT_HEURISTIC'
    a['mean']=1
    with pytest.raises(ValueError,match='PERFORMANCE'):event_policy(a,app,NOW)

@pytest.mark.parametrize('path',['src/workbench_analysis/fep_e2/historical_labels.py',
    'src/workbench_analysis/v4_15_settlement.py','src/workbench_analysis/fep_e2/historical_dataset.py',
    'src/workbench_analysis/fep_e2/historical_owners.py'])
def test_12_13_pass_keep_owner_bytes(path):
    import subprocess,hashlib
    assert hashlib.sha256((ROOT/path).read_bytes()).digest()==hashlib.sha256(subprocess.check_output(['git','show','f8708c3:'+path],cwd=ROOT)).digest()

def test_14_first_observed_not_granted():
    row,*rest=vector();row['FIRST_OBSERVED']=True
    with pytest.raises(ValueError,match='LINEAGE'):event_observation(row,*rest)

def test_15_priority_unchanged():
    import subprocess
    for path in ('config/research_priority.yaml','src/candidates/research_priority.py',
                 'src/shadow_v2/research_priority.py','config/v4_09_priority_provenance_contract_r1_1.json'):
        assert (ROOT/path).read_bytes()==subprocess.check_output(['git','show','f8708c3:'+path],cwd=ROOT)

def test_16_owner_episode_mismatch():
    row,en,event,state=vector();event['episode_id']='other'
    with pytest.raises(ValueError,match='EPISODE'):event_observation(row,en,event,state)

def test_17_parent_episode_not_first():
    row,en,event,state=vector();state['parent_episode_id']='old'
    with pytest.raises(ValueError,match='PREDICATE'):event_observation(row,en,event,state)

def test_18_pooled_policy_creation_rejected():
    d=fixture()
    with pytest.raises(ValueError,match='POOLED_ENTRY'):event_policy(discover(d['denominator'],d['rows']),POLICY['applicability'],NOW)

def test_19_event_projection_keeps_revision_and_denominator():
    d=fixture();before=deepcopy(d);row=dict(d['denominator'][0],signal_type='FIRST_PREWATCH')
    subset=event_dataset(d,[row])
    assert d==before and subset['selections']==d['selections'][:1]
    assert subset['rows'][0]['selected_label_digest']==d['rows'][0]['selected_label_digest']
