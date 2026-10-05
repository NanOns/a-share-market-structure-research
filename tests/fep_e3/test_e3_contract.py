"""Explicit synthetic negatives only; never historical model inputs."""
from copy import deepcopy
from datetime import date,timedelta
import json
from pathlib import Path
import pytest
from workbench_analysis.fep_e1.contracts import digest
from workbench_analysis.fep_e3 import protocol as p,models as m

ROOT=Path(__file__).resolve().parents[2]
EARLY='2026-10-05T10:00:00Z';CUTOFF='2026-10-05T11:00:00Z'

def feature_manifest():
    return p.manifest(json.loads((ROOT/'config/v4_03_field_registry_v1.json').read_bytes()),
        json.loads((ROOT/'config/fep_feature_registry_v1.json').read_bytes()))

def sample(n=16):
    fm=feature_manifest();rows=[]
    for i in range(n):
        trade=(date(2024,1,1)+timedelta(days=i)).isoformat();values={f['field_name']:(False if f['type']=='boolean' else float(i+1)/10) for f in fm['fields']}
        envelopes={k:dict(value=v,quality_state='OBSERVED',contract_id='CORE_FACTOR_V1',window_end_trade_date=trade) for k,v in values.items()}
        rows.append(dict(p.SCOPE,observation_id='test'+str(i),entity_id='test_entity'+str(i),episode_id='ep'+str(i),
            trade_date=trade,date_ordinal=i*2,label_end_ordinal=i*2+1,episode_start=i*2,episode_end=i*2+2,
            source_fact_available_at=EARLY,label_revision_available_at=EARLY,label_training_mature_at=EARLY,
            status='ELIGIBLE',feature_issues=[],model_features=values,feature_snapshot=dict(core_envelopes=envelopes,max_feature_source_trade_date=trade),
            outcome=(i%5-2)*.001,FIRST_OBSERVED=False,REAL_OOS=False,AS_RECORDED=False,production=False,shadow=False))
    return rows,fm

def groups():return dict(TRAIN=['2024-01-01'],INTERNAL_TUNE=['2024-02-01'],CALIBRATION=['2024-03-01'],OUTER_TEST=['2024-04-01'])

def test_e3_01_random_date_split_rejected():
    with pytest.raises(ValueError,match='RANDOM_SPLIT'):p.validate_dates(groups(),'RANDOM_CV')

def test_e3_02_same_date_split_rejected():
    g=groups();g['OUTER_TEST']=g['TRAIN']
    with pytest.raises(ValueError,match='DATE_SPLIT_LEAKAGE'):p.validate_dates(g,'RIGHT_TO_LEFT_MINIMUM_SUPPORT_CHRONOLOGICAL_V1')

def test_e3_03_actual_label_end_crosses_boundary():
    rows,_=sample();rows[0]['label_end_ordinal']=4
    assert 'LABEL_EVENT_END_CROSSES_BOUNDARY' in p.leakage(rows[0],4,CUTOFF)

def test_e3_04_late_revision_leakage():
    rows,_=sample();rows[0]['label_revision_available_at']='2026-10-05T12:00:00Z'
    assert any('LABEL_REVISION' in v for v in p.leakage(rows[0],10,CUTOFF))

@pytest.mark.parametrize('kind',['source_clock','feature_window'])
def test_e3_05_future_source_rejected(kind):
    rows,_=sample();r=rows[0]
    if kind=='source_clock':r['source_fact_available_at']='2026-10-05T12:00:00Z'
    else:r['feature_snapshot']['max_feature_source_trade_date']='2030-01-01'
    assert p.leakage(r,10,CUTOFF)

def test_e3_06_scaler_full_dataset_rejected():
    rows,fm=sample();ids=[r['observation_id'] for r in rows[:5]]
    with pytest.raises(ValueError,match='NON_TRAIN_SCALER'):m.preprocessing(rows,fm,ids)

@pytest.mark.parametrize('part',['CALIBRATION','OUTER_TEST'])
def test_e3_07_imputer_nontrain_rejected(part):
    with pytest.raises(ValueError,match='NON_TRAIN_IMPUTER'):p.fit_authority(part,['a'],['a'],'imputer')

def test_e3_08_ood_reference_nontrain_rejected():
    rows,fm=sample()
    with pytest.raises(ValueError,match='NON_TRAIN_OOD'):m.ood_reference(rows,fm,[r['observation_id'] for r in rows],partition='OUTER_TEST')

def test_e3_09_outer_tuning_rejected():
    with pytest.raises(ValueError,match='TUNING_REJECTED'):p.tuning_authority('OUTER_TEST')

def test_e3_10_outer_reopen_changed_model_new_lineage(tmp_path):
    path=tmp_path/'outer.json';p.open_outer(path,dict(model='original'))
    with pytest.raises(ValueError,match='NEW_LINEAGE_REQUIRED'):p.open_outer(path,dict(model='changed'))
    assert json.loads(path.read_bytes())==dict(model='original')

def test_e3_11_pooled_entry_rejected():
    rows,_=sample();rows[0]['signal_type']='ENTRY'
    with pytest.raises(ValueError,match='SCOPE_NOT_ADMITTED'):p.scope(rows)

@pytest.mark.parametrize('signal',['REENTRY','NEW_CONFIRMED'])
def test_e3_12_other_events_rejected(signal):
    rows,_=sample();rows[0]['signal_type']=signal
    with pytest.raises(ValueError,match='SCOPE_NOT_ADMITTED'):p.scope(rows)

def test_e3_13_unregistered_feature_rejected():
    rows,fm=sample();fm['fields'][0]['field_name']='label_derived_fake'
    with pytest.raises(ValueError,match='UNREGISTERED_FEATURE'):p.features(rows[0],fm)

def test_e3_14_unknown_category_fail_closed():
    rows,fm=sample();ref=m.ood_reference(rows,fm,[r['observation_id'] for r in rows]);values=deepcopy(rows[0]['model_features'])
    values['hh_progress']=True
    check=m.ood_check(values,{k:'OBSERVED' for k in values},ref)
    assert check['status']=='NOT_EVALUABLE_HARD_OOD' and any('UNKNOWN_CATEGORY' in r for r in check['hard_reasons'])

def test_e3_15_raw_crossing_detected_rearrangement_explicit():
    rows,_=sample(2);diag,coherent=m.distribution_diagnostics(rows,[[.2,0,-.1],[0,.1,.2]],'PRE_REGISTERED_INCREASING_REARRANGEMENT_V1')
    assert diag['raw_crossing_rows']==1 and diag['coherent_crossing_rows']==0
    assert list(coherent[0])==[-.1,0,.2]

def test_e3_16_silent_posttest_sort_rejected():
    with pytest.raises(ValueError,match='SILENT_QUANTILE_SORT'):p.rearrange([3,2,1],'POST_TEST_UNREGISTERED_SORT')

def test_e3_17_failed_trial_cannot_disappear():
    with pytest.raises(ValueError,match='TRIAL_DELETE'):p.ledger_integrity(['failed_0','success_1'],['success_1'])

def test_e3_18_same_outer_population_required():
    with pytest.raises(ValueError,match='POPULATION_MISMATCH'):p.same_population(['a','b'],['a'])

def test_e3_19_probability_calibration_forbidden():
    with pytest.raises(ValueError,match='PROBABILITY_CALIBRATION'):p.calibration_role('PROBABILITY_CALIBRATED')

def test_e3_20_no_display_priority_grant():
    rows,fm=sample();ids=[r['observation_id'] for r in rows];prep=m.preprocessing(rows,fm,ids)
    model=m.fit(rows,prep,'HUBER_LINEAR',dict(alpha=.01,epsilon=1.35),dict(test_only=True),ids)
    assert model['MODEL_DISPLAY']==model['PRIORITY_USE']=='UNGRANTED' and not model['production'] and not model['CHAMPION']

def test_e3_21_shared_episode_crossing_purged_entity_not_banned():
    rows,_=sample();r=rows[0];r['episode_end']=100
    assert not p.leakage(r,10,CUTOFF)
    assert 'SHARED_OVERLAPPING_EPISODE_BOUNDARY' in p.leakage(r,10,CUTOFF,{(r['entity_id'],r['episode_id'])})

def test_e3_22_created_time_identity_stable_semantic_change_new_id(tmp_path):
    a,_=p.immutable(tmp_path,'test_model',dict(coefficients=[1],created_at=EARLY,run_id='one'))
    b,_=p.immutable(tmp_path,'test_model',dict(coefficients=[1],created_at=CUTOFF,run_id='two'))
    c,_=p.immutable(tmp_path,'test_model',dict(coefficients=[2],created_at=CUTOFF))
    assert a['logical_digest']==b['logical_digest'] and c['logical_digest']!=a['logical_digest']

def test_e3_23_discovery_no_performance_consumed():
    rows,_=sample(120);a=p.split_discovery(rows,1,CUTOFF)
    for r in rows:r['outcome']=999999
    assert p.split_discovery(rows,1,CUTOFF)==a
    retained,ledger=p.purge(rows,a)
    assert len(ledger)==120 and all(retained[k] for k in p.PARTITIONS)

@pytest.mark.parametrize('issue',['missing','nonfinite','quality','schema'])
def test_e3_24_ood_minimum_cases(issue):
    rows,fm=sample();ref=m.ood_reference(rows,fm,[r['observation_id'] for r in rows]);v=deepcopy(rows[0]['model_features']);q={k:'OBSERVED' for k in v}
    if issue=='missing':v['ret1']=None
    elif issue=='nonfinite':v['ret1']=float('nan')
    elif issue=='quality':q['ret1']='NOT_IMPLEMENTED'
    else:v['fake']=1
    assert m.ood_check(v,q,ref)['hard_reasons']

def test_e3_25_serialization_keeps_explicit_column_order():
    import numpy as np
    rows,fm=sample();prep=m.preprocessing(rows,fm,[r['observation_id'] for r in rows])
    serialized=json.loads(json.dumps(prep,sort_keys=True))
    assert np.array_equal(m.matrix(rows,prep),m.matrix(rows,serialized))
