"""Interpretable TRAIN-only preprocessing, bounded linear fits and diagnostics."""
from collections import Counter
import math
import numpy as np
from workbench_analysis.fep_e1.contracts import digest
from workbench_analysis.fep_e2.conditional import weights
from .protocol import fit_authority,rearrange,same_population,calibration_role

def date_weights(rows):return np.asarray([float(w) for w in weights(rows)])

def preprocessing(rows,manifest,allowed_ids,partition='TRAIN'):
    ids=[r['observation_id'] for r in rows];fit_authority(partition,ids,allowed_ids,'scaler')
    w=date_weights(rows);numeric={};categories={};terms=[]
    for f in manifest['fields']:
        name=f['field_name'];values=[r['model_features'][name] for r in rows]
        if any(v is None for v in values):raise ValueError('E3_REQUIRED_MISSING_NO_IMPUTER')
        if f['type']=='float64':
            x=np.asarray(values,dtype=float);mean=float(w@x);scale=float(np.sqrt(w@((x-mean)**2)))
            numeric[name]=dict(mean=mean,scale=scale if scale>0 else 1.0,constant=scale==0)
            terms.append(name)
        else:
            categories[name]=sorted(set(values));terms.extend(name+'='+str(v) for v in categories[name][1:])
    result=dict(contract_id='FEP_E3_TRAIN_PREPROCESSING_V1',numeric=numeric,categories=categories,terms=terms,
        train_observation_ids=ids,train_ids_digest=digest(ids),feature_manifest_digest=digest(manifest),
        fit_partition='TRAIN',imputer='NOT_USED_COMPLETE_CASE',winsor='NOT_USED',selector='NOT_USED')
    result['logical_digest']=digest(result);return result

def ood_reference(rows,manifest,allowed_ids,partition='TRAIN'):
    ids=[r['observation_id'] for r in rows];fit_authority(partition,ids,allowed_ids,'ood')
    fields={}
    for f in manifest['fields']:
        name=f['field_name'];values=[r['model_features'][name] for r in rows]
        fields[name]=dict(type=f['type'],quality_states=sorted({r['feature_snapshot']['core_envelopes'][name]['quality_state'] for r in rows}),required=True)
        if f['type']=='float64':fields[name].update(minimum=min(values),maximum=max(values))
        else:fields[name]['categories']=sorted(set(values))
    result=dict(contract_id='FEP_E3_OOD_MARGINAL_REFERENCE_V1',fields=fields,train_ids_digest=digest(ids),fit_partition='TRAIN',
        JOINT_OOD='UNSET',global_OOD_OK=False,semantics='Engineering marginal/schema diagnostics only')
    result['logical_digest']=digest(result);return result

def ood_check(values,qualities,reference):
    hard=[];diagnostic=[]
    if set(values)!=set(reference['fields']):hard.append('SCHEMA_FIELDS_MISMATCH')
    for name,f in reference['fields'].items():
        value=values.get(name)
        if value is None:hard.append(name+':REQUIRED_FEATURE_MISSING');continue
        if qualities.get(name) not in f['quality_states']:hard.append(name+':NEW_QUALITY_OR_UNAVAILABLE_STATE')
        if f['type']=='float64':
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):hard.append(name+':NONFINITE_OR_SCHEMA_MISMATCH')
            elif not f['minimum']<=value<=f['maximum']:diagnostic.append(name+':OUTSIDE_TRAIN_SUPPORT')
        elif type(value) is not bool or value not in f['categories']:hard.append(name+':UNKNOWN_CATEGORY')
    return dict(status='NOT_EVALUABLE_HARD_OOD' if hard else 'MARGINAL_RANGE_FLAGS_JOINT_UNSET' if diagnostic else 'MARGINAL_CHECKS_PASS_JOINT_UNSET',
        hard_reasons=hard,diagnostic_reasons=diagnostic,JOINT_OOD='UNSET',global_OOD_OK=False)

def matrix(rows,preprocessing):
    result=[]
    for r in rows:
        values=r['model_features'];terms=[]
        for term in preprocessing['terms']:
            if term in preprocessing['numeric']:
                p=preprocessing['numeric'][term];terms.append((values[term]-p['mean'])/p['scale'])
            else:
                name,category=term.split('=',1)
                if values[name] not in preprocessing['categories'][name]:raise ValueError('E3_UNKNOWN_CATEGORY')
                terms.append(float(str(values[name])==category))
        result.append(terms)
    return np.asarray(result,dtype=float)

def fit(rows,prep,family,parameters,dependencies,allowed_ids):
    fit_authority('TRAIN',[r['observation_id'] for r in rows],allowed_ids,'model')
    from sklearn.linear_model import HuberRegressor,QuantileRegressor
    from sklearn.exceptions import ConvergenceWarning
    from threadpoolctl import threadpool_limits
    import warnings
    x=matrix(rows,prep);y=np.asarray([r['outcome'] for r in rows]);w=date_weights(rows)*len(rows)
    with threadpool_limits(limits=2),warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always')
        if family=='HUBER_LINEAR':model=HuberRegressor(**parameters,fit_intercept=True,max_iter=2000,tol=1e-8)
        elif family=='QUANTILE_LINEAR':model=QuantileRegressor(**parameters,fit_intercept=True,solver='highs',solver_options={'threads':2})
        else:raise ValueError('E3_MODEL_FAMILY_NOT_REGISTERED')
        model.fit(x,y,sample_weight=w)
    if any(issubclass(v.category,ConvergenceWarning) for v in captured):raise ValueError('E3_FIT_CONVERGENCE_FAILED')
    coefficients=[float(v) for v in model.coef_];intercept=float(model.intercept_)
    if not all(math.isfinite(v) for v in coefficients+[intercept]):raise ValueError('E3_NONFINITE_MODEL')
    return dict(family=family,parameters=parameters,coefficients=coefficients,intercept=intercept,
        feature_terms=prep['terms'],dependencies=dependencies,n_iter=int(model.n_iter_),
        warnings=[str(v.message) for v in captured],state='ENGINEERING_ONLY',CHAMPION=False,
        MODEL_DISPLAY='UNGRANTED',PRIORITY_USE='UNGRANTED',production=False,shadow=False)

def predict(model,rows,prep):
    if model['feature_terms']!=prep['terms']:raise ValueError('E3_MODEL_PREPROCESSING_SCHEMA')
    return matrix(rows,prep)@np.asarray(model['coefficients'])+model['intercept']

def point_metrics(rows,prediction):
    if not rows:return dict(status='OUTER_TEST_FAILED_EMPTY_POPULATION')
    y=np.asarray([r['outcome'] for r in rows]);p=np.asarray(prediction);w=date_weights(rows);e=y-p
    huber=np.where(np.abs(e)<=.01,.5*e**2,.01*(np.abs(e)-.005))
    result=dict(DATE_BALANCED_MAE=float(w@np.abs(e)),DATE_BALANCED_HUBER_LOSS=float(w@huber),
        DATE_BALANCED_RMSE=float(np.sqrt(w@(e**2))),weighted_sign_hit_rate=float(w@(np.sign(y)==np.sign(p))))
    from scipy.stats import spearmanr
    by_date=[]
    for date in sorted({r['trade_date'] for r in rows}):
        indexes=[i for i,r in enumerate(rows) if r['trade_date']==date]
        if len(indexes)>=2 and len(set(y[indexes]))>1 and len(set(p[indexes]))>1:
            by_date.append(dict(trade_date=date,rho=float(spearmanr(y[indexes],p[indexes]).statistic),rows=len(indexes)))
    result['spearman_by_date']=by_date
    result['mean_date_spearman']=sum(r['rho'] for r in by_date)/len(by_date) if by_date else None
    result['aggregate_spearman']=float(spearmanr(y,p).statistic) if len(set(y))>1 and len(set(p))>1 else None
    return result

def pinball(rows,prediction,q):
    residual=np.asarray([r['outcome'] for r in rows])-np.asarray(prediction)
    return float(date_weights(rows)@np.maximum(q*residual,(q-1)*residual))

def distribution_diagnostics(rows,raw,rule):
    calibration_role('NOT_APPLICABLE_REGRESSION')
    raw=np.asarray(raw);coherent=np.asarray([rearrange(list(v),rule) for v in raw])
    w=date_weights(rows);y=np.asarray([r['outcome'] for r in rows]);cross=(raw[:,0]>raw[:,1])|(raw[:,1]>raw[:,2])
    result=dict(probability_calibration='NOT_APPLICABLE_REGRESSION',role='CALIBRATION_DIAGNOSTIC_ONLY',
        raw_crossing_rows=int(cross.sum()),weighted_raw_crossing_frequency=float(w@cross),
        coherent_crossing_rows=int(((coherent[:,0]>coherent[:,1])|(coherent[:,1]>coherent[:,2])).sum()),
        rearrangement=rule,mean_interval_width=float(w@(coherent[:,2]-coherent[:,0])),
        empirical_middle_interval_coverage=float(w@((y>=coherent[:,0])&(y<=coherent[:,2]))),
        quantiles={str(q):dict(raw_pinball=pinball(rows,raw[:,j],q),coherent_pinball=pinball(rows,coherent[:,j],q),
            empirical_coverage=float(w@(y<=coherent[:,j]))) for j,q in enumerate((.25,.5,.75))},
        coverage_is_predictive_probability=False)
    return result,coherent

def comparison(rows,model_predictions,baseline_predictions,model_ids,baseline_ids):
    same_population(model_ids,baseline_ids);a=point_metrics(rows,model_predictions);b=point_metrics(rows,baseline_predictions)
    delta=b['DATE_BALANCED_MAE']-a['DATE_BALANCED_MAE']
    from .protocol import blocks
    return dict(primary_metric='DATE_BALANCED_MAE',model=a,baseline=b,absolute_improvement_delta=delta,
        relative_improvement_delta=delta/b['DATE_BALANCED_MAE'] if b['DATE_BALANCED_MAE'] else None,
        MODEL_EFFECTIVENESS='INCREMENT' if delta>0 else 'NO_INCREMENT',
        rows=len(rows),dates=len({r['trade_date'] for r in rows}),blocks=blocks(rows),
        entities=len({r['entity_id'] for r in rows}),episodes=len({(r['entity_id'],r['episode_id']) for r in rows}),
        exact_outer_observation_ids=model_ids,same_date_balanced_weight_digest=digest([float(v) for v in date_weights(rows)]),
        real_OOS=False,model_display='UNGRANTED',priority_use='UNGRANTED')
