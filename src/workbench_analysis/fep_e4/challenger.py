"""Explicit E3 reuse, bounded HGB fits and portable immutable tree computation."""
import json
import math
import numpy as np
from workbench_analysis.fep_e1.contracts import digest
from workbench_analysis.fep_e3 import protocol as p,models as m

FLAGS=dict(SEEN_OUTER_DIAGNOSTIC_ONLY=True,TEST_PREVIOUSLY_SEEN=True,REAL_OOS=False,
    PROMOTION_EVIDENCE=False,CHAMPION=False,PROMOTION='UNGRANTED',MODEL_DISPLAY='UNGRANTED',
    PRIORITY_USE='UNGRANTED',production=False,shadow=False,focus=False)
COHERENCE='PRE_REGISTERED_INCREASING_REARRANGEMENT_V1'

def exact(actual,expected,what):
    if digest(actual)!=digest(expected):raise ValueError('E4_EXACT_'+what+'_REUSE_REQUIRED')

def split_rule(rule):
    if rule!='EXACT_E3_FOLDS_NO_NEW_SPLIT':raise ValueError('E4_NEW_SPLIT_REJECTED')

def claims(flags):
    for key,value in FLAGS.items():
        if key not in flags or type(flags[key]) is not type(value) or flags[key]!=value:raise ValueError('E4_FORBIDDEN_CLAIM:'+key)
    if flags.get('evidence_class','SEEN_OUTER_DIAGNOSTIC_ONLY')!='SEEN_OUTER_DIAGNOSTIC_ONLY':raise ValueError('E4_UNSEEN_CLAIM_REJECTED')

def budget(point,quantile):
    if not point or not quantile or len(point)>8 or len(quantile)>12 or len(point)+len(quantile)>20:
        raise ValueError('E4_TRIAL_BUDGET_OVERFLOW')
    allowed={'learning_rate','max_leaf_nodes','max_depth','min_samples_leaf','l2_regularization'}
    for params in point+quantile:
        if set(params)-allowed-{'quantile'}:raise ValueError('E4_PARAMETER_NOT_REGISTERED')
    if any('quantile' in v for v in point) or set(v.get('quantile') for v in quantile)!={.25,.5,.75}:
        raise ValueError('E4_QUANTILE_GRID_INVALID')

def coherence(rule):
    if rule!=COHERENCE:raise ValueError('E4_POST_RESULT_COHERENCE_REJECTED')

def select(trials,partition,family,q=None):
    p.tuning_authority(partition)
    valid=[t for t in trials if t['status']=='SUCCESS' and t['family']==family and (q is None or t['parameters']['quantile']==q)]
    if not valid:raise ValueError('E4_ALL_FAMILY_TRIALS_FAILED')
    return min(valid,key=lambda t:(t['selection_metric'],t['index']))

def predict_matrix(model,x,return_leaves=False):
    x=np.asarray(x,dtype=float)
    if x.ndim!=2 or x.shape[1]!=len(model['feature_terms']) or not np.isfinite(x).all():raise ValueError('E4_BAD_MODEL_INPUT')
    result=np.full(len(x),model['baseline'],dtype=float);leaves=[]
    for tree in model['trees']:
        leaf=[]
        for row in x:
            node=0
            while not tree[node]['is_leaf']:
                n=tree[node];node=n['left'] if row[n['feature_idx']]<=n['threshold'] else n['right']
            leaf.append(node)
        result+=np.asarray([tree[i]['value'] for i in leaf]);leaves.append(leaf)
    return (result,leaves) if return_leaves else result

def predict(model,rows,prep):
    exact(model['feature_terms'],prep['terms'],'FEATURE_TERMS')
    return predict_matrix(model,m.matrix(rows,prep))

def fit(rows,prep,family,parameters,dependencies,allowed_ids,partition='TRAIN'):
    p.scope(rows);p.fit_authority(partition,[r['observation_id'] for r in rows],allowed_ids,'tree_model')
    if family not in ('HGB_ABSOLUTE_ERROR','HGB_QUANTILE'):raise ValueError('E4_MODEL_FAMILY_REJECTED')
    from sklearn.ensemble import HistGradientBoostingRegressor
    from threadpoolctl import threadpool_limits
    x=m.matrix(rows,prep);y=np.asarray([r['outcome'] for r in rows]);w=m.date_weights(rows)*len(rows)
    if not np.isfinite(x).all():raise ValueError('E4_NO_IMPUTATION')
    params=dict(parameters)
    if family=='HGB_ABSOLUTE_ERROR' and 'quantile' in params:raise ValueError('E4_POINT_QUANTILE_PARAMETER')
    with threadpool_limits(limits=2):
        estimator=HistGradientBoostingRegressor(loss='absolute_error' if family=='HGB_ABSOLUTE_ERROR' else 'quantile',
            **params,max_iter=100,max_bins=255,early_stopping=False,categorical_features=None,random_state=20261005)
        estimator.fit(x,y,sample_weight=w)
    trees=[]
    for iteration in estimator._predictors:
        nodes=[]
        if len(iteration)!=1:raise ValueError('E4_NON_REGRESSION_PREDICTOR')
        for n in iteration[0].nodes:
            if n['is_categorical']:raise ValueError('E4_UNREGISTERED_CATEGORICAL_TREE')
            nodes.append(dict(value=float(n['value']),count=int(n['count']),feature_idx=int(n['feature_idx']),
                threshold=float(n['num_threshold']),left=int(n['left']),right=int(n['right']),
                depth=int(n['depth']),is_leaf=bool(n['is_leaf'])))
        trees.append(nodes)
    model=dict(family=family,parameters=parameters,feature_terms=prep['terms'],dependencies=dependencies,
        baseline=float(estimator._baseline_prediction[0,0]),trees=trees,n_iter=int(estimator.n_iter_),
        computation='Baseline plus numerical tree leaf values; leaf values already include learning_rate',
        fixed_parameters=dict(max_iter=100,max_bins=255,early_stopping=False,categorical_features=None,random_state=20261005),
        state='CHALLENGER_ENGINEERING_ONLY',**FLAGS)
    restored=json.loads(json.dumps(model,sort_keys=True,allow_nan=False))
    delta=float(np.max(np.abs(predict_matrix(restored,x)-estimator.predict(x))))
    if not math.isfinite(delta) or delta>1e-12:raise ValueError('E4_MODEL_SERIALIZATION_PARITY_FAILED')
    model['TRAIN_serialization_max_abs_delta']=delta
    model['complexity']=dict(trees=len(trees),nodes=sum(map(len,trees)),leaves=sum(n['is_leaf'] for t in trees for n in t),
        maximum_depth=max(n['depth'] for t in trees for n in t))
    _,leaves=predict_matrix(model,x,True);weights=m.date_weights(rows)
    model['TRAIN_leaf_support']=[dict(tree_index=j,leaves=[dict(node=i,node_count=n['count'],
        routed_rows=sum(v==i for v in leaves[j]),date_balanced_weight=float(sum(weights[k] for k,v in enumerate(leaves[j]) if v==i)))
        for i,n in enumerate(t) if n['is_leaf']]) for j,t in enumerate(trees)]
    return model

def permutation_diagnostic(model,rows,prep,partition='TRAIN'):
    if partition not in ('TRAIN','CALIBRATION'):raise ValueError('E4_OUTER_FEATURE_IMPORTANCE_REJECTED')
    x=m.matrix(rows,prep);base=m.point_metrics(rows,predict_matrix(model,x))['DATE_BALANCED_MAE'];rng=np.random.default_rng(20261005)
    result=[]
    for index,term in enumerate(prep['terms']):
        deltas=[]
        for _ in range(3):
            changed=x.copy();changed[:,index]=x[rng.permutation(len(x)),index]
            deltas.append(m.point_metrics(rows,predict_matrix(model,changed))['DATE_BALANCED_MAE']-base)
        result.append(dict(feature_term=term,MAE_increases=deltas,mean_MAE_increase=float(np.mean(deltas))))
    return dict(partition=partition,seed=20261005,repeats=3,baseline_DATE_BALANCED_MAE=base,features=result,
        feature_selection=False,causal_claim=False,funding_intent_claim=False,correlated_features_limit='Unconditional permutation diagnostic only')
