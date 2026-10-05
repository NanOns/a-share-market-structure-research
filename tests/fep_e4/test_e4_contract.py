"""Mandatory E4 negatives and computation parity; synthetic vectors only."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
import numpy as np
from workbench_analysis.fep_e1.contracts import digest
from workbench_analysis.fep_e1.feature_owner import verify_file
from workbench_analysis.fep_e3 import protocol as p,models as m
from workbench_analysis.fep_e4 import challenger as c
from tests.fep_e3.test_e3_contract import sample

def test_e4_01_new_random_split_rejected():
    with pytest.raises(ValueError,match='NEW_SPLIT'):c.split_rule('RANDOM_CV')

def test_e4_02_fold_mutation_rejected():
    with pytest.raises(ValueError,match='FOLD'):c.exact({'TRAIN':['a']},{'TRAIN':['b']},'FOLD')

def test_e4_03_pooled_entry_rejected():
    rows,_=sample();rows[0]['signal_type']='ENTRY'
    with pytest.raises(ValueError,match='SCOPE'):p.scope(rows)

@pytest.mark.parametrize('signal',['REENTRY','NEW_CONFIRMED'])
def test_e4_04_other_events_rejected(signal):
    rows,_=sample();rows[0]['signal_type']=signal
    with pytest.raises(ValueError,match='SCOPE'):p.scope(rows)

def test_e4_05_new_feature_rejected():
    with pytest.raises(ValueError,match='FEATURE_TERMS'):c.exact(['new'],['amount_ratio20'],'FEATURE_TERMS')

def test_e4_06_ood_relaxation_rejected():
    with pytest.raises(ValueError,match='OOD'):c.exact({'required':False},{'required':True},'OOD')

def test_e4_07_seen_outer_tuning_rejected():
    with pytest.raises(ValueError,match='TUNING'):c.select([],'OUTER_TEST','HGB_ABSOLUTE_ERROR')

def bad_claim(key,value):
    flags=dict(c.FLAGS);flags[key]=value
    with pytest.raises(ValueError,match='CLAIM'):c.claims(flags)

def test_e4_08_unseen_claim_rejected():bad_claim('evidence_class','UNSEEN_TEST')
def test_e4_09_real_oos_claim_rejected():bad_claim('REAL_OOS',True)
def test_e4_10_promotion_rejected():bad_claim('PROMOTION_EVIDENCE',True)

def test_e4_11_budget_overflow_rejected():
    with pytest.raises(ValueError,match='BUDGET'):c.budget([{}]*9,[{'quantile':q} for q in (.25,.5,.75)])

def test_e4_12_failed_trial_deletion_rejected():
    with pytest.raises(ValueError,match='DELETE'):p.ledger_integrity([0,1,2],[0,2])

def test_e4_13_calibration_selection_rejected():
    with pytest.raises(ValueError,match='TUNING'):c.select([],'CALIBRATION','HGB_ABSOLUTE_ERROR')

def test_e4_14_post_result_coherence_rejected():
    with pytest.raises(ValueError,match='COHERENCE'):c.coherence('SORT_AFTER_SEEING_TEST')

def mutate_file(tmp_path,name):
    path=tmp_path/name;path.write_bytes(b'accepted');ref=dict(path=name,sha256=__import__('hashlib').sha256(b'accepted').hexdigest(),bytes=8)
    path.write_bytes(b'mutated')
    with pytest.raises(ValueError):verify_file(tmp_path,ref)

def test_e4_15_e3_mutation_rejected(tmp_path):mutate_file(tmp_path,'e3.json')
def test_e4_16_priority_mutation_rejected(tmp_path):mutate_file(tmp_path,'priority.json')
def test_e4_17_model_display_rejected():bad_claim('MODEL_DISPLAY','GRANTED')
def test_e4_18_priority_use_rejected():bad_claim('PRIORITY_USE','GRANTED')

@pytest.mark.parametrize('key',['production','shadow','focus'])
def test_e4_19_production_shadow_rejected(key):bad_claim(key,True)

def test_e4_20_failure_leaves_upstream_unchanged(tmp_path):
    upstream=tmp_path/'upstream.json';upstream.write_bytes(b'accepted E2 E3 Core');before=upstream.read_bytes()
    rows,fm=sample();ids=[r['observation_id'] for r in rows];prep=m.preprocessing(rows,fm,ids)
    with pytest.raises(ValueError,match='FAMILY'):c.fit(rows,prep,'RANDOM_FOREST',{},dict(upstream=str(upstream)),ids)
    assert upstream.read_bytes()==before

@pytest.mark.parametrize('family,q',[('HGB_ABSOLUTE_ERROR',None),('HGB_QUANTILE',.25),('HGB_QUANTILE',.5),('HGB_QUANTILE',.75)])
def test_e4_tree_serialization_actual_parity(family,q):
    rows,fm=sample(80);ids=[r['observation_id'] for r in rows];prep=m.preprocessing(rows,fm,ids)
    params=dict(learning_rate=.05,max_leaf_nodes=7,max_depth=3,min_samples_leaf=10,l2_regularization=1.)
    if q is not None:params['quantile']=q
    model=c.fit(rows,prep,family,params,{},ids);restored=json.loads(json.dumps(model,sort_keys=True))
    assert model['TRAIN_serialization_max_abs_delta']<=1e-12
    assert np.array_equal(c.predict(model,rows,prep),c.predict(restored,rows,prep))
    assert model['n_iter']==100 and model['fixed_parameters']['early_stopping'] is False
    assert all(sum(leaf['routed_rows'] for leaf in tree['leaves'])==len(rows) for tree in model['TRAIN_leaf_support'])

def test_e4_selection_ignores_failed_trial_and_tie_breaks():
    trials=[dict(index=0,status='FAILED',family='HGB_ABSOLUTE_ERROR',parameters={}),
        dict(index=2,status='SUCCESS',family='HGB_ABSOLUTE_ERROR',parameters={},selection_metric=1),
        dict(index=1,status='SUCCESS',family='HGB_ABSOLUTE_ERROR',parameters={},selection_metric=1)]
    assert c.select(trials,'INTERNAL_TUNE','HGB_ABSOLUTE_ERROR')['index']==1

def test_e4_outer_importance_rejected():
    with pytest.raises(ValueError,match='IMPORTANCE'):c.permutation_diagnostic({},[],{},'OUTER_TEST')

def test_e4_nontrain_fit_rejected():
    rows,fm=sample();ids=[r['observation_id'] for r in rows];prep=m.preprocessing(rows,fm,ids)
    with pytest.raises(ValueError,match='NON_TRAIN'):c.fit(rows,prep,'HGB_ABSOLUTE_ERROR',{}, {},ids,partition='CALIBRATION')

def test_e4_immutable_id_excludes_timestamp(tmp_path):
    first,path=p.immutable(tmp_path,'challenger',dict(value=1,created_at='old',run_id='one'))
    second,same=p.immutable(tmp_path,'challenger',dict(value=1,created_at='new',run_id='two'))
    assert first['logical_digest']==second['logical_digest'] and path==same
