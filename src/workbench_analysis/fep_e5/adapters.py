"""Exact serialized upstream consumption; no fit, label resolution or current lookup."""
import math
from workbench_analysis.fep_e3 import models as m
from workbench_analysis.fep_e4 import challenger
from . import contracts as c

def snapshot(row,parent_digest):
    content=dict(observation_id=row['observation_id'],trade_date=row['trade_date'],entity_id=row['entity_id'],
        publication_identity=row['original_e2_row_digest'],parent_artifact_sha256=parent_digest,
        max_feature_source_trade_date=row['feature_snapshot']['max_feature_source_trade_date'],
        model_features=row['model_features'],core_envelopes=row['feature_snapshot']['core_envelopes'])
    sha=c.logical(content)
    return dict(observation_id=row['observation_id'],entity_id=row['entity_id'],trade_date=row['trade_date'],
        input_mode='EXACT_IMMUTABLE_SNAPSHOT',snapshot_id='FEP_E5_EMBEDDED_SNAPSHOT:'+sha,snapshot_digest=sha,
        source_available_at=row['source_fact_available_at'],snapshot=content)

def inference(model,input_row,baseline,prep,ood,serialized=None):
    c.snapshot_input(input_row);snap=input_row['snapshot'];features=snap['model_features']
    is_baseline=model['model_family']=='CONDITIONAL_STATISTICS_BASELINE'
    check=dict(status='NOT_APPLICABLE_DESCRIPTIVE_BASELINE',hard_reasons=[],diagnostic_reasons=[],JOINT_OOD='NOT_APPLICABLE_DESCRIPTIVE',global_OOD_OK=False) if is_baseline else m.ood_check(features,{k:v['quality_state'] for k,v in snap['core_envelopes'].items()},ood)
    quality='OBSERVED' if all(v is not None and snap['core_envelopes'][k]['quality_state']=='OBSERVED' for k,v in features.items()) else 'UNAVAILABLE'
    support=baseline['support_state'];projection_state=c.status(quality,support,check)
    axes=dict(return_expectancy=None,relative_expectancy=None,risk_expectancy=None,structure_expectancy=None,
        confidence_support=baseline['counts'],OOD=check)
    quantiles=None
    if projection_state=='READY':
        if model['model_family']=='CONDITIONAL_STATISTICS_BASELINE':
            c.require(baseline['selected_level']=='L1','BASELINE_BACKOFF_NOT_PORTABLE')
            axes['return_expectancy']=baseline['statistics']['weighted_mean']
            quantiles=[baseline['statistics'][q] for q in ('p25','p50','p75')]
        else:
            rows=[dict(model_features=features)]
            predict=m.predict if model['model_family']=='INTERPRETABLE_MODEL' else challenger.predict
            axes['return_expectancy']=float(predict(serialized['point'],rows,prep)[0])
            quantiles=[float(predict(serialized[k],rows,prep)[0]) for k in ('q25','q50','q75')]
    calibration='NOT_APPLICABLE_DESCRIPTIVE' if model['model_family']=='CONDITIONAL_STATISTICS_BASELINE' else 'WEAK_DIAGNOSTIC_ONLY'
    raw_quantiles=quantiles;coherent=sorted(quantiles) if quantiles is not None else None
    return dict(inference_model_id=model['model_id'],inference_model_set_id=model['model_set_id'],
        inference_snapshot_digest=input_row['snapshot_digest'],inference_source_digest=model['artifact_digest'],
        projection_state=projection_state,axes=axes,raw_quantiles=raw_quantiles,coherent_quantiles=coherent,
        quality_state=quality,support_state=support,OOD_state=check,coherence_state='PASS_FROZEN_REARRANGEMENT' if quantiles is not None else 'UNKNOWN',
        calibration_state=calibration,threshold_state='NOT_FROZEN' if projection_state=='READY' else 'UNKNOWN',
        state=c.classify(axes,dict(quality=quality=='OBSERVED',support=support=='SUPPORTED',calibration=is_baseline,OOD=is_baseline,coherence=quantiles is not None),None),
        evidence_origin='RECONSTRUCTED_CORRECTED',prediction_evidence='HISTORICAL_SIMULATION',FIRST_OBSERVED=False,REAL_OOS=False,
        PROMOTION_EVIDENCE=False,synthetic_only=False,backoff_level=baseline['selected_level'],backoff_trace=baseline['backoff_trace'],
        baseline_estimand='COMPLETE_CASE_DESCRIPTIVE',historical_model_applied_after_observation=True,global_OOD_OK=False)
