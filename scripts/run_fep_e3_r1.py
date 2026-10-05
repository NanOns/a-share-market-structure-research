"""Frozen FIRST_PREWATCH:T1 interpretable historical experiment and local gate."""
from collections import Counter
import importlib.metadata,json,os,sys,subprocess,traceback,xml.etree.ElementTree as ET
from pathlib import Path
from scripts.build_fep_e2_r1r1_history import ROOT,binding,now
from workbench_analysis.fep_e1.contracts import atomic_json,digest
from workbench_analysis.fep_e1.feature_owner import verify_file
from workbench_analysis.fep_e2.historical_dataset import read_gzip,write_gzip,LINEAGE
from workbench_analysis.fep_e3 import protocol as p,models as m

REPORT=ROOT/'reports/fep_e3_r1';E2=ROOT/'reports/fep_e2_r1r2';BASELINE='7a10c0a3b1563532b7f1eda5af9b90f204fd03d6'
PROTOCOL_PATH='config/fep_e3_experiment_protocol_v1_1.json'
REGISTRY=REPORT/'registry'/'serialization_v1_1'
def load(path):return json.loads(Path(path).read_bytes())
def emit(name,value):atomic_json(REPORT/(name+'.json'),value)
def rows():return list(read_gzip(REPORT/'EXACT_MODEL_ROWS.jsonl.gz'))
def contract():
    freeze=load(REPORT/'EXPERIMENT_PROTOCOL_FREEZE.json');verify_file(ROOT,freeze['protocol'])
    return load(ROOT/PROTOCOL_PATH)
def folds():
    cp=contract();verify_file(ROOT,cp['model_rows_binding']);verify_file(ROOT,cp['purge_ledger_binding'])
    allrows={r['observation_id']:r for r in rows()};fold=load(REPORT/'FOLD_MANIFEST.json')
    if fold['groups']!=cp['split']['groups'] or digest(fold['retained_ids'])!=cp['fold_retained_ids_digest'] or digest(fold['all_date_ids'])!=cp['fold_all_date_ids_digest']:
        raise ValueError('E3_FROZEN_FOLD_MEMBERSHIP_MUTATION')
    return {k:[allrows[i] for i in ids] for k,ids in fold['retained_ids'].items()}
def save(kind,payload):
    artifact,path=p.immutable(REGISTRY,kind,dict(payload,created_at=now()))
    return artifact,binding(path)

def prepare():
    if (REPORT/'EXPERIMENT_PROTOCOL_FREEZE.json').exists():raise ValueError('E3_PROTOCOL_ALREADY_FROZEN_NEW_LINEAGE_REQUIRED')
    REPORT.mkdir(parents=True,exist_ok=True);tmp=REPORT/'.gitattributes.tmp';tmp.write_bytes(b'* -text\n');tmp.replace(REPORT/'.gitattributes')
    names=['V4_FEP_EXECUTION_MASTER_V4_15E3_R1_20261005.md',
        'V4_15E3_INTERPRETABLE_MODEL_TIME_SPLIT_IMPLEMENTATION_TASK_R1_20261005.md',
        'V4_15E2_FINAL_CAPABILITY_SCOPED_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md']
    for name in names:
        source=Path('D:/Users/lps/Desktop/阶段任务')/name
        if source.exists():
            tmp=REPORT/(name+'.tmp');tmp.write_bytes(source.read_bytes());tmp.replace(REPORT/name)
        else:
            # The originals can be moved after intake; reuse only our initial
            # byte-bound authority copy, never a newly searched substitute.
            entry=load(REPORT/'ENTRY_BASELINE.json')
            ref=next(r for r in entry['authority'] if Path(r['path']).name==name)
            verify_file(ROOT,ref)
    if subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()!=BASELINE:raise ValueError('E3_BASELINE')
    seal=load(E2/'FEP_E2_R1R2_CANDIDATE_SEAL.json')
    for ref in seal['code_bindings']+seal['evidence_bindings']:verify_file(ROOT,ref)
    refs=[binding(E2/n) for n in ['FIRST_PREWATCH_E2_DATASET.json.gz','CONDITIONAL_BASELINE_FIRST_PREWATCH_T1.json','FEP_E2_R1R2_CANDIDATE_SEAL.json']]
    refs+=[binding('config/fep_e2_support_policy_registry_v1_1.json'),binding('config/fep_feature_registry_v1.json'),binding('config/v4_03_field_registry_v1.json')]
    emit('ENTRY_BASELINE',dict(stage='V4-15E3.R1',baseline=BASELINE,entered_at=now(),authority=[binding(REPORT/n) for n in names],
        admitted_scope=p.SCOPE,next='STOP_WAIT_V4_15E3_INDEPENDENT_EXTERNAL_AUDIT'))
    emit('E2_INPUT_BINDING',dict(status='PASS_EXACT_CAPABILITY_SCOPED',bindings=refs,old_seal_bindings=seal['code_bindings']+seal['evidence_bindings'],
        current_heads_not_used_for_membership=True,newer_labels_not_resolved=True))
    data=next(read_gzip(E2/'FIRST_PREWATCH_E2_DATASET.json.gz'));p.scope(data['denominator'])
    from workbench_analysis.fep_e2.conditional import validate_input
    validate_input(data)
    fm=p.manifest(load(ROOT/'config/v4_03_field_registry_v1.json'),load(ROOT/'config/fep_feature_registry_v1.json'))
    fm.update(source_bindings=refs[-2:],accepted_historical_scope_authority=binding(REPORT/names[-1]))
    emit('FEATURE_MANIFEST',fm)
    calendar=load(ROOT/'config/fep_e2_historical_dataset_contract_v1.json')['source_bindings']['calendar']
    sessions=load(ROOT/calendar['path'])['session_dates'];ordinals={d:i for i,d in enumerate(sessions)};compact=[]
    for r in data['denominator']:
        records={v['record_id']:v for v in read_gzip(ROOT/'reports/fep_e2_r1r1/settlement_records'/(r['entity_id']+'.jsonl.gz'))}
        owner=records[r['outcome_ref']['record_id']]
        if digest(owner['payload'])!=r['outcome_ref']['sha256']:raise ValueError('E3_OWNER_LABEL_REFERENCE')
        out=owner['payload']
        if out['outcome_revision_id']!=r['outcome_revision_id'] or digest(out['R_N'])!=r['selected_label_digest']:raise ValueError('E3_LABEL_RESELECTION')
        scheduled_beyond_coverage=(r['status']!='ELIGIBLE' and out['outcome_status']=='PENDING' and out['due_date'] is not None
            and out['due_date']>sessions[-1] and r['label_end_ordinal']==len(sessions))
        if out['due_date'] is not None and ordinals.get(out['due_date'])!=r['label_end_ordinal'] and not scheduled_beyond_coverage:
            raise ValueError('E3_ACTUAL_LABEL_END')
        values,issues=p.features(r,fm)
        item={k:r[k] for k in [*p.SCOPE,'observation_id','entity_id','episode_id','date_ordinal','trade_date','episode_start','episode_end',
            'label_end_ordinal','source_fact_available_at','label_revision_available_at','label_training_mature_at','selected_label_digest',
            'selected_label_revision','outcome_revision_id','outcome_ref','status','outcome_status','contract_versions','entity_type','label_quality_policy',
            'support_class','regime','trend','position','risk','sector','feature_support','AS_RECORDED','FIRST_OBSERVED','REAL_OOS','production','shadow']}
        item.update(model_features=values,feature_issues=issues,label_event_end_actual=out['due_date'],scheduled_beyond_source_coverage=scheduled_beyond_coverage,
            original_e2_row_digest=digest(r),feature_snapshot=dict(max_feature_source_trade_date=r['feature_snapshot']['max_feature_source_trade_date'],
                core_envelopes={k:r['feature_snapshot']['core_envelopes'][k] for k in p.FEATURES}))
        if 'outcome' in r:item['outcome']=r['outcome']
        compact.append(item)
    write_gzip(REPORT/'EXACT_MODEL_ROWS.jsonl.gz',compact)
    cutoff=now();discovery=p.split_discovery(compact,len(p.FEATURES)+2,cutoff)
    emit('EXPERIMENT_PROTOCOL_DISCOVERY',dict(discovery=discovery,input_rows=len(compact),eligible=sum(r['status']=='ELIGIBLE' for r in compact),
        registered_features=len(p.FEATURES),structural_feature_invalid=sum(bool(r['feature_issues']) for r in compact),
        outcome_performance_consumed=False,heuristic='Engineering fold feasibility, not statistical power'))
    retained,purge_ledger=p.purge(compact,discovery)
    write_gzip(REPORT/'PURGE_ROW_LEDGER.jsonl.gz',purge_ledger)
    feature_invalid=Counter(reason for row in compact for reason in row['feature_issues'])
    cp=dict(contract_id='FEP_E3_INTERPRETABLE_FIRST_PREWATCH_T1_V1_1',lineage_id='FEP_E3_R1_FIRST_PREWATCH_T1_SERIALIZATION_V1_1',scope=p.SCOPE,
        predecessor_protocol=binding('config/fep_e3_experiment_protocol_v1.json'),pre_outer_repair=binding(REPORT/'PRE_OUTER_REPAIR_DISPOSITION.json'),
        primary_metric='DATE_BALANCED_MAE',secondary_metrics=['DATE_BALANCED_HUBER_LOSS','DATE_BALANCED_RMSE','WEIGHTED_SIGN_HIT','SPEARMAN','PINBALL','EMPIRICAL_QUANTILE_COVERAGE'],
        model_families=['HUBER_LINEAR','QUANTILE_LINEAR'],feature_manifest_digest=digest(fm),
        split=discovery,maximum_target_span=1,purge='Strict label_event_end before later boundary; shared entity/episode intervals grouped/purged; real availability <= fixed pre-phase knowledge cutoff',
        temporal_semantics='Dual clocks: ordered historical event dates, fixed actual engineering knowledge snapshot before every phase; NOT historical availability/PIT or REAL_OOS',
        knowledge_cutoff=cutoff,probability_calibration='NOT_APPLICABLE_REGRESSION',
        preprocessing='TRAIN weighted scaler + TRAIN category vocabulary; required complete case; no imputer/winsor/selector',
        point_grid=[dict(alpha=a,epsilon=e) for a in (.0001,.01,1.0) for e in (1.35,1.75)],
        quantile_grid=[dict(quantile=q,alpha=a) for q in (.25,.5,.75) for a in (.0001,.01)],
        tuning=dict(partition='INTERNAL_TUNE',maximum_trials=12,point_selection='DATE_BALANCED_MAE',quantile_selection='DATE_BALANCED_PINBALL_PER_Q',tie_break='EXACT_METRIC_THEN_GRID_ORDINAL'),
        quantiles=[.25,.5,.75],rearrangement='PRE_REGISTERED_INCREASING_REARRANGEMENT_V1',calibration='Independent diagnostics only; no model/hyperparameter/feature adjustment',
        ood='TRAIN observed numeric envelopes/category sets/schema/quality; hard missing/category/schema block; marginal ranges diagnostic; JOINT_OOD UNSET',
        baseline='Exact accepted E2 event baseline mechanics on TRAIN admitted complete-case rows, before test; L1 weighted mean predictor, never full-history mean',
        random_seed=20261005,cpu_threads=2,parallel_trials=1,solver=dict(huber_max_iter=2000,huber_tol=1e-8,quantile='HIGHS',huber_diagnostic_delta=.01),
        runtime={k:importlib.metadata.version(k) for k in ('numpy','scipy','scikit-learn','threadpoolctl','joblib')},
        implementation_bindings=[binding('src/workbench_analysis/fep_e3/protocol.py'),binding('src/workbench_analysis/fep_e3/models.py')],
        model_rows_binding=binding(REPORT/'EXACT_MODEL_ROWS.jsonl.gz'),purge_ledger_binding=binding(REPORT/'PURGE_ROW_LEDGER.jsonl.gz'),
        fold_retained_ids_digest=digest({k:[r['observation_id'] for r in v] for k,v in retained.items()}),
        fold_all_date_ids_digest=digest({k:[r['observation_id'] for r in compact if r['trade_date'] in discovery['groups'][k]] for k in p.PARTITIONS}),
        e2_bindings=refs[:4],evidence_class='HISTORICAL_SIMULATION',evidence_origin='RECONSTRUCTED_CORRECTED',REAL_OOS=False,FIRST_OBSERVED=False,
        MODEL_DISPLAY='UNGRANTED',PRIORITY_USE='UNGRANTED',production=False,shadow=False,focus=False)
    cp['logical_digest']=digest(cp)
    atomic_json(ROOT/PROTOCOL_PATH,cp)
    frozen_at=now();emit('EXPERIMENT_PROTOCOL_FREEZE',dict(status='FROZEN_BEFORE_ANY_FIT_OR_OUTER_METRIC',frozen_at=frozen_at,
        protocol=binding(PROTOCOL_PATH),logical_digest=cp['logical_digest'],knowledge_cutoff=cutoff,outer_opened=False,
        exact_model_rows=binding(REPORT/'EXACT_MODEL_ROWS.jsonl.gz')))
    emit('FOLD_MANIFEST',dict(contract_id='FEP_E3_DATE_FOLDS_V1',groups=discovery['groups'],retained_ids={k:[r['observation_id'] for r in v] for k,v in retained.items()},
        all_date_ids={k:[r['observation_id'] for r in compact if r['trade_date'] in discovery['groups'][k]] for k in p.PARTITIONS},
        fold_stats={k:dict(rows=len(v),dates=len({r['trade_date'] for r in v}),blocks=p.blocks(v),entities=len({r['entity_id'] for r in v}),
            episodes=len({(r['entity_id'],r['episode_id']) for r in v})) for k,v in retained.items()}))
    emit('DATE_SPLIT_GATE',dict(status='PASS_CHRONOLOGICAL_DATE_GROUPED',folds=binding(REPORT/'FOLD_MANIFEST.json'),groups=discovery['groups'],random_CV=False))
    emit('PURGE_GATE',dict(status='PASS_EXPLICIT_DUAL_CLOCK_PURGE',ledger=binding(REPORT/'PURGE_ROW_LEDGER.jsonl.gz'),
        rows=len(purge_ledger),excluded=sum(r['action']=='EXCLUDE' for r in purge_ledger),reason_counts=dict(Counter(v for r in purge_ledger for v in r['reasons'])),
        feature_invalid_counts=dict(feature_invalid),minimum_gap_target_sessions=1,
        episode_crossing_not_shared=sum(r['episode_interval_crosses_boundary'] and not r['shared_episode_in_later_partition'] for r in purge_ledger),
        explanation='Different securities/unique episode identities with long followup are not shared episodes. Shared episode observations crossing partitions are excluded; no entity lifetime ban.',
        availability_semantics=cp['temporal_semantics'],frozen_knowledge_cutoff=cutoff))
    print('protocol frozen',load(REPORT/'FOLD_MANIFEST.json')['fold_stats'],flush=True)

def train():
    if (REPORT/'TRAINING_TRIAL_LEDGER.json').exists() or (REPORT/'OUTER_TEST_OPEN.json').exists() or any(REGISTRY.glob('trial_*.json')):
        raise ValueError('E3_TRAINING_ALREADY_FROZEN_NEW_LINEAGE_REQUIRED')
    cp=contract();verify_file(ROOT,load(REPORT/'EXPERIMENT_PROTOCOL_FREEZE.json')['protocol'])
    for ref in cp['implementation_bindings']+cp['e2_bindings']:verify_file(ROOT,ref)
    if any(importlib.metadata.version(k)!=v for k,v in cp['runtime'].items()):raise ValueError('E3_FROZEN_RUNTIME_MISMATCH')
    partitions=folds();train=partitions['TRAIN'];tune=partitions['INTERNAL_TUNE'];ids=[r['observation_id'] for r in train];fm=load(REPORT/'FEATURE_MANIFEST.json')
    if digest(fm)!=cp['feature_manifest_digest']:raise ValueError('E3_FEATURE_MANIFEST_MUTATION')
    prep=m.preprocessing(train,fm,ids);prep_art,prep_ref=save('preprocessing',prep)
    ood=m.ood_reference(train,fm,ids);ood_art,ood_ref=save('ood',ood)
    emit('PREPROCESSING_GATE',dict(status='PASS_TRAIN_ONLY',artifact=prep_ref,fit_rows=len(train),train_ids_digest=digest(ids),imputer='NOT_USED_COMPLETE_CASE'))
    emit('OOD_REFERENCE_GATE',dict(status='PASS_MARGINAL_REFERENCE_ENGINEERING',artifact=ood_ref,fit_partition='TRAIN',JOINT_OOD='UNSET',global_OOD_OK=False,
        model_state='OOD_REFERENCE_INCOMPLETE_JOINT_UNSET'))
    tune_valid=[];tune_ledger=[]
    for r in tune:
        check=m.ood_check(r['model_features'],{k:v['quality_state'] for k,v in r['feature_snapshot']['core_envelopes'].items()},ood)
        tune_ledger.append(dict(observation_id=r['observation_id'],ood=check))
        if not check['hard_reasons']:tune_valid.append(r)
    if not tune_valid:raise ValueError('E3_INTERNAL_TUNE_EMPTY_OOD')
    p.tuning_authority('INTERNAL_TUNE');trials=[];successful=[]
    deps=dict(protocol_logical_digest=cp['logical_digest'],preprocessing_logical_digest=prep_art['logical_digest'],
        exact_E2_dataset=cp['e2_bindings'][0],train_rows_digest=digest(train),feature_manifest_digest=digest(fm),runtime=cp['runtime'])
    grid=[('HUBER_LINEAR',v) for v in cp['point_grid']]+[('QUANTILE_LINEAR',v) for v in cp['quantile_grid']]
    for index,(family,parameters) in enumerate(grid):
        attempted_at=now()
        try:
            model=m.fit(train,prep,family,parameters,deps,ids);pred=m.predict(model,tune_valid,prep)
            metric=m.point_metrics(tune_valid,pred)['DATE_BALANCED_MAE'] if family=='HUBER_LINEAR' else m.pinball(tune_valid,pred,parameters['quantile'])
            trial=dict(index=index,family=family,parameters=parameters,status='SUCCESS',selection_partition='INTERNAL_TUNE',selection_metric=metric,model=model,dependencies=deps)
        except Exception as exc:
            trial=dict(index=index,family=family,parameters=parameters,status='FAILED',error=type(exc).__name__+':'+str(exc),dependencies=deps)
        artifact,ref=save('trial',trial);trials.append(dict(index=index,artifact=ref,logical_digest=artifact['logical_digest'],status=trial['status'],attempted_at=attempted_at))
        if trial['status']=='SUCCESS':successful.append(trial)
        print('trial',index,family,trial['status'],flush=True)
    p.ledger_integrity(list(range(len(grid))),[r['index'] for r in trials])
    emit('TRAINING_TRIAL_LEDGER',dict(status='PASS_APPEND_ONLY_ALL_ATTEMPTS',maximum=cp['tuning']['maximum_trials'],attempted=len(trials),trials=trials,
        failed=sum(t['status']=='FAILED' for t in trials),deleted_trials=0,tune_population=tune_ledger))
    selected={}
    for family,q,name in [('HUBER_LINEAR',None,'point'),('QUANTILE_LINEAR',.25,'q25'),('QUANTILE_LINEAR',.5,'q50'),('QUANTILE_LINEAR',.75,'q75')]:
        eligible=[t for t in successful if t['family']==family and (q is None or t['parameters']['quantile']==q)]
        if not eligible:raise ValueError('E3_ALL_TRIALS_FAILED:'+name)
        winner=min(eligible,key=lambda t:(t['selection_metric'],t['index']));model,ref=save('model_'+name,winner['model'])
        selected[name]=dict(artifact=ref,logical_digest=model['logical_digest'],trial_index=winner['index'],parameters=winner['parameters'])
    emit('POINT_MODEL_GATE',dict(status='PASS_HUBER_LINEAR_ENGINEERING',selected=selected['point'],train_only_fit=True,selection='INTERNAL_TUNE_DATE_BALANCED_MAE'))
    emit('QUANTILE_MODEL_GATE',dict(status='PASS_LINEAR_QUANTILES_ENGINEERING',selected={k:v for k,v in selected.items() if k!='point'},levels=cp['quantiles']))
    # Reuse E2's exact weighting/backoff mechanics, restricted to frozen TRAIN.
    from workbench_analysis.fep_e2.event_strata import event_dataset,event_baseline
    accepted=next(read_gzip(E2/'FIRST_PREWATCH_E2_DATASET.json.gz'));train_keys=set(ids)
    subset=event_dataset(accepted,[r for r in accepted['denominator'] if r['observation_id'] in train_keys])
    policy=load(ROOT/'config/fep_e2_support_policy_registry_v1_1.json')['policies'][0]
    query={k:subset['denominator'][0][k] for k in ('entity_type','observation_scope','signal_type','target','horizon','feature_variant','evidence_origin','label_quality_policy','contract_versions')}
    query.update(regime='UNAVAILABLE',trend='UNAVAILABLE',position='UNAVAILABLE',risk='UNAVAILABLE')
    baseline=event_baseline(subset,query,policy,load(ROOT/'config/fep_conditional_statistics_contract_v1.json'),now())
    if baseline['support_state']!='SUPPORTED':raise ValueError('E3_PRETEST_E2_BASELINE_UNSUPPORTED')
    b,bref=save('pretest_E2_baseline',dict(accepted_full_history_baseline=cp['e2_bindings'][1],training_ids=ids,training_ids_digest=digest(ids),
        method='Accepted E2 L1 weighted mean on TRAIN only',predictor=baseline['statistics']['weighted_mean'],E2_artifact=baseline,production=False))
    emit('PRETEST_DEPENDENCIES',dict(protocol_digest=cp['logical_digest'],preprocessing=prep_ref,ood=ood_ref,selected=selected,baseline=bref,frozen_at=now()))

def predict_partition(partition,dependencies):
    cp=contract();prep=load(ROOT/dependencies['preprocessing']['path']);ood=load(ROOT/dependencies['ood']['path'])
    folds()  # Verify both row content and frozen phase membership before inference.
    selected={k:load(ROOT/v['artifact']['path']) for k,v in dependencies['selected'].items()};accepted=[];ledger=[]
    allrows={r['observation_id']:r for r in rows()};ids=load(REPORT/'FOLD_MANIFEST.json')['all_date_ids'][partition]
    valid=set(load(REPORT/'FOLD_MANIFEST.json')['retained_ids'][partition])
    for key in ids:
        r=allrows[key];check=m.ood_check(r['model_features'],{k:v['quality_state'] for k,v in r['feature_snapshot']['core_envelopes'].items()},ood)
        record=dict(observation_id=key,trade_date=r['trade_date'],status='PREDICTABLE' if key in valid and not check['hard_reasons'] else 'NOT_EVALUABLE',ood=check,label_status=r['status'])
        if record['status']=='PREDICTABLE':accepted.append(r)
        ledger.append(record)
    if not accepted:raise ValueError('E3_'+partition+'_NO_PREDICTABLE_POPULATION')
    point=m.predict(selected['point'],accepted,prep)
    import numpy as np
    raw=np.column_stack([m.predict(selected[name],accepted,prep) for name in ('q25','q50','q75')])
    diagnostics,coherent=m.distribution_diagnostics(accepted,raw,cp['rearrangement'])
    predictions=[dict(observation_id=r['observation_id'],trade_date=r['trade_date'],point=float(point[i]),
        raw_quantiles=[float(v) for v in raw[i]],coherent_quantiles=[float(v) for v in coherent[i]]) for i,r in enumerate(accepted)]
    return accepted,point,diagnostics,predictions,ledger

def calibrate():
    if (REPORT/'CALIBRATION_DIAGNOSTIC_GATE.json').exists() or (REPORT/'OUTER_TEST_OPEN.json').exists():raise ValueError('E3_CALIBRATION_ALREADY_FROZEN')
    dependencies=load(REPORT/'PRETEST_DEPENDENCIES.json');accepted,point,diag,predictions,ledger=predict_partition('CALIBRATION',dependencies)
    diagnostic,ref=save('calibration',dict(diagnostics=diag,point_residual_diagnostics=m.point_metrics(accepted,point),predictions=predictions,
        population_ledger=ledger,pretest_dependencies=dependencies,model_adjustment='NONE',learned_quantile_adjustment='NONE',probability_calibration='NOT_APPLICABLE_REGRESSION'))
    emit('CALIBRATION_DIAGNOSTIC_GATE',dict(status='PASS_CALIBRATION_DIAGNOSTIC_ONLY',artifact=ref,rows=len(accepted),diagnostics=diag,
        model_or_hyperparameters_changed=False,probability_calibration='NOT_APPLICABLE_REGRESSION'))
    emit('COHERENCE_GATE',dict(status='PASS_FROZEN_REARRANGEMENT' if diag['coherent_crossing_rows']==0 else 'COHERENCE_FAILED',
        raw_crossing_rows=diag['raw_crossing_rows'],coherent_crossing_rows=diag['coherent_crossing_rows'],method=contract()['rearrangement'],
        raw_and_coherent_retained=True,frozen_before_outer=True))

def outer():
    cp=contract();dependencies=load(REPORT/'PRETEST_DEPENDENCIES.json');cal=load(REPORT/'CALIBRATION_DIAGNOSTIC_GATE.json')
    for ref in cp['implementation_bindings']+cp['e2_bindings']+[dependencies['preprocessing'],dependencies['ood'],dependencies['baseline'],cal['artifact']]+[s['artifact'] for s in dependencies['selected'].values()]:verify_file(ROOT,ref)
    if load(REPORT/'COHERENCE_GATE.json')['status']=='COHERENCE_FAILED':raise ValueError('E3_COHERENCE_FAILED')
    if load(REPORT/'SERIALIZATION_ROUNDTRIP_GATE.json')['status']!='PASS_EXACT_TRAIN_TRANSFORM_ROUNDTRIP':
        raise ValueError('E3_SERIALIZATION_INTEGRITY_FAILED')
    marker=dict(outer_test_opened_at=now(),experiment_contract_digest=cp['logical_digest'],pretest_dependencies=dependencies,
        calibration_artifact=cal['artifact'],one_shot=True,real_OOS=False)
    p.open_outer(REPORT/'OUTER_TEST_OPEN.json',marker)
    accepted,point,diag,predictions,ledger=predict_partition('OUTER_TEST',dependencies)
    prediction,pr=save('outer_predictions',dict(predictions=predictions,population_ledger=ledger,experiment_contract_digest=cp['logical_digest']))
    baseline=load(ROOT/dependencies['baseline']['path']);ids=[r['observation_id'] for r in accepted]
    baseline_prediction=[baseline['predictor'] for r in accepted]
    result=m.comparison(accepted,point,baseline_prediction,ids,ids)
    result.update(coverage=len(accepted)/len(ledger),outer_total=len(ledger),quantile_diagnostics=diag,
        pretest_baseline=dependencies['baseline'],baseline_does_not_consume_outer_labels=True)
    evaluation,er=save('outer_evaluation',dict(result=result,prediction_digest=prediction['logical_digest'],
        experiment_contract_digest=cp['logical_digest'],evidence_class='HISTORICAL_SIMULATION',REAL_OOS=False))
    emit('OUTER_TEST_EVALUATION',dict(status='PASS_ONE_SHOT_ENGINEERING',artifact=er,result=result))
    emit('BASELINE_COMPARISON',dict(status='PASS_SAME_OUTER_POPULATION',result=result,baseline_pretest_only=dependencies['baseline']))
    emit('OUTER_TEST_SEAL',dict(status='SEALED_ONE_SHOT',outer_test_opened_at=marker['outer_test_opened_at'],opening_receipt=binding(REPORT/'OUTER_TEST_OPEN.json'),
        experiment_contract_digest=cp['logical_digest'],model_artifact_digest=dependencies['selected']['point']['logical_digest'],
        preprocessing=dependencies['preprocessing'],OOD_reference=dependencies['ood'],calibration=cal['artifact'],
        prediction_artifact=pr,prediction_digest=prediction['logical_digest'],evaluation_artifact=er,evaluation_digest=evaluation['logical_digest'],
        future_model_changes='NEW_LINEAGE_REQUIRED_TEST_PREVIOUSLY_SEEN',MODEL_DISPLAY='UNGRANTED',PRIORITY_USE='UNGRANTED',production=False))
    registry=[binding(path) for path in sorted((REPORT/'registry').rglob('*.json'))]
    emit('MODEL_REGISTRY_GATE',dict(status='PASS_IMMUTABLE_ENGINEERING_LEDGER',registry=registry,failed_trials_retained=True,
        active_registry=REGISTRY.relative_to(ROOT).as_posix(),active_lineage=cp['lineage_id'],
        prior_lineage='SUPERSEDED_PRE_OUTER_SERIALIZATION_LINEAGE',attempted_fits_all_lineages=24,budget_per_lineage=12,
        prior_outer_openings=0,current_outer_openings=1,
        model_states=['ENGINEERING_ONLY',result['MODEL_EFFECTIVENESS'],'CALIBRATION_DIAGNOSTIC_ONLY','OOD_REFERENCE_INCOMPLETE_JOINT_UNSET'],
        JOINT_OOD='UNSET',CHAMPION=False,MODEL_DISPLAY='UNGRANTED',PRIORITY_USE='UNGRANTED',production=False))
    print('outer sealed',result['MODEL_EFFECTIVENESS'],result['model']['DATE_BALANCED_MAE'],result['baseline']['DATE_BALANCED_MAE'],flush=True)

def tests():
    from scripts import run_fep_e2_r1 as runner
    runner.REPORT=REPORT;runner.BASE=BASELINE;env=os.environ.copy()
    env.update(PYTHONPATH='E:/codex_tmp/fep_e3_deps'+os.pathsep+str(ROOT)+os.pathsep+str(ROOT/'src'),TEMP='E:/codex_tmp/test_temp',TMP='E:/codex_tmp/test_temp',
        WORKBENCH_PG_DSN='host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh',FEP_E1_TEST_DSN='host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh',
        OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2')
    runner.execute([sys.executable,'-B','-m','pytest','tests/fep_e3','tests/fep_e2','tests/fep','tests/test_r20d_settlement.py',
        'tests/test_r25_packet.py::test_actual_authority_inventory_waits_without_target','-q','--basetemp=E:/codex_tmp/test_temp/e3-targeted',
        '--junitxml='+str(REPORT/'targeted.xml')],env,'targeted')
    if sys.argv[2:]==['targeted-only']:return
    prior=load(E2/'SCOPED_REGRESSION_SUMMARY.json');command=[c for c in prior['command'] if not c.startswith(('--basetemp=','--junitxml='))]
    command[0]=sys.executable;command+=['tests/fep_e3','--basetemp=E:/codex_tmp/test_temp/e3-scoped','--junitxml='+str(REPORT/'scoped.xml')]
    runner.execute(command,env,'scoped',prior['failed_nodes'])

def finalize():
    cp=contract()
    folds()  # Readback only; never refit or reopen the sealed outer test.
    for ref in load(REPORT/'E2_INPUT_BINDING.json')['bindings']+load(REPORT/'E2_INPUT_BINDING.json')['old_seal_bindings']+cp['implementation_bindings']:verify_file(ROOT,ref)
    protected_e2=load(E2/'PROTECTED_STATE_READBACK.json')
    for ref in protected_e2['heads']+protected_e2['priority_bindings']:verify_file(ROOT,ref)
    upstream=load(ROOT/'config/fep_e2_historical_dataset_contract_v1.json')
    for ref in [*upstream['source_bindings'].values(),*upstream['owner_runtime_bindings'],*upstream['parameter_bindings']]:verify_file(ROOT,ref)
    import psycopg
    from psycopg import sql
    with psycopg.connect('host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh') as db:
        tables=[r[0] for r in db.execute("select tablename from pg_tables where schemaname='fep' order by tablename")]
        counts={t:db.execute(sql.SQL('select count(*) from fep.{}').format(sql.Identifier(t))).fetchone()[0] for t in tables}
    if len(counts)!=33 or any(counts.values()):raise ValueError('E3_E1_DATABASE_ISOLATION')
    from scripts.validate_r25_preflight import protected,selection
    emit('PROTECTED_STATE_READBACK',dict(status='PASS',heads=protected_e2['heads'],priority_bindings=protected_e2['priority_bindings'],
        real_FEP_table_counts=counts,R25_protected=protected(ROOT),R25_selection=selection(ROOT),TDX='UNTOUCHED',
        FIRST_OBSERVED='NOT_GRANTED',REAL_OOS='NOT_GRANTED',MODEL_DISPLAY='UNGRANTED',PRIORITY_USE='UNGRANTED',production=False,shadow=False,focus=False))
    targeted=load(REPORT/'TARGETED_SUMMARY.json');regression=load(REPORT/'SCOPED_REGRESSION_SUMMARY.json')
    cases=ET.parse(REPORT/'targeted.xml').findall('.//testcase');negatives=[dict(node=c.attrib['classname']+'::'+c.attrib['name'],
        status='PASS' if c.find('failure') is None and c.find('error') is None else 'FAIL') for c in cases if 'test_e3' in c.attrib['classname']]
    emit('NEGATIVE_MATRIX',dict(status='PASS' if len(negatives)>=20 and all(c['status']=='PASS' for c in negatives) else 'FAIL',
        count=len(negatives),cases=negatives,synthetic_vectors_tests_only=True))
    seal=load(REPORT/'OUTER_TEST_SEAL.json');comparison=load(REPORT/'BASELINE_COMPARISON.json')
    for ref in load(REPORT/'MODEL_REGISTRY_GATE.json')['registry']:
        verify_file(ROOT,ref)
        artifact=load(ROOT/ref['path'])
        semantic={k:v for k,v in artifact.items() if k not in ('created_at','run_id','logical_digest','artifact_id','kind')}
        if digest(semantic)!=artifact['logical_digest']:raise ValueError('E3_REGISTRY_LOGICAL_DIGEST_MUTATION')
    for key in ('opening_receipt','preprocessing','OOD_reference','calibration','prediction_artifact','evaluation_artifact'):
        verify_file(ROOT,seal[key])
    if seal['status']!='SEALED_ONE_SHOT' or seal['experiment_contract_digest']!=cp['logical_digest']:
        raise ValueError('E3_OUTER_SEAL_MISMATCH')
    trials=load(REPORT/'TRAINING_TRIAL_LEDGER.json')
    p.ledger_integrity(list(range(12)),[t['index'] for t in trials['trials']])
    if trials['maximum']!=12 or trials['attempted']!=12:raise ValueError('E3_TRIAL_BUDGET_MISMATCH')
    for trial in trials['trials']:verify_file(ROOT,trial['artifact'])
    gates=('DATE_SPLIT_GATE','PURGE_GATE','PREPROCESSING_GATE','POINT_MODEL_GATE','QUANTILE_MODEL_GATE',
        'CALIBRATION_DIAGNOSTIC_GATE','OOD_REFERENCE_GATE','COHERENCE_GATE','MODEL_REGISTRY_GATE','SERIALIZATION_ROUNDTRIP_GATE')
    if any(not load(REPORT/(name+'.json'))['status'].startswith('PASS') for name in gates):raise ValueError('E3_REQUIRED_GATE_FAILED')
    old=load(ROOT/'config/fep_e3_experiment_protocol_v1.json')
    archive=REPORT/'attempts'/'PRE_OUTER_SERIALIZATION_LINEAGE_V1'
    for ref in old['implementation_bindings']:
        import hashlib
        saved=archive/Path(ref['path']).name
        if hashlib.sha256(saved.read_bytes()).hexdigest()!=ref['sha256']:raise ValueError('E3_PRIOR_IMPLEMENTATION_ARCHIVE_MUTATION')
    ready=not targeted['failed_nodes'] and not regression['introduced_active_failures'] and load(REPORT/'NEGATIVE_MATRIX.json')['status']=='PASS'
    status='PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT' if ready else 'BLOCKED';next_stage='STOP_WAIT_V4_15E3_INDEPENDENT_EXTERNAL_AUDIT' if ready else 'STOP_WAIT_EXTERNAL_REPAIR_DISPOSITION'
    emit('LOCAL_ACCEPTANCE_MATRIX',dict(status=status,FEP_MODEL_ENGINEERING='PASS_LOCAL_FIRST_PREWATCH_T1' if ready else 'BLOCKED',
        MODEL_EFFECTIVENESS=comparison['result']['MODEL_EFFECTIVENESS'],checks={name:load(REPORT/(name+'.json'))['status'] for name in
            ('DATE_SPLIT_GATE','PURGE_GATE','PREPROCESSING_GATE','POINT_MODEL_GATE','QUANTILE_MODEL_GATE','CALIBRATION_DIAGNOSTIC_GATE','OOD_REFERENCE_GATE','COHERENCE_GATE','MODEL_REGISTRY_GATE')},
        introduced_active_failures=regression['introduced_active_failures'],external_acceptance=False,next=next_stage))
    emit('INDEPENDENT_AUDIT_ITEMS',dict(items=[dict(audit_id='FEP_E3_RECONSTRUCTED_DUAL_CLOCK_AND_JOINT_OOD',status='OPEN_EXTERNAL_REVIEW',
        scope='Historical event-time split with fixed pre-phase reconstruction knowledge snapshot; JOINT_OOD remains UNSET; no PIT or real OOS promotion',
        evidence=[binding(REPORT/'PURGE_GATE.json'),binding(REPORT/'OOD_REFERENCE_GATE.json')],acceptance='Independent E3 audit; no global OOD/display/effectiveness grant'),
        dict(audit_id='FEP_E2_PRIOR_EPISODE_OWNER_CAPABILITY',status='OPEN_BLOCKS_OTHER_EVENT_STRATA',scope='REENTRY/NEW_CONFIRMED owner debt unchanged',evidence=[binding(E2/'INDEPENDENT_AUDIT_ITEMS.json')])]))
    r=comparison['result'];text=f'''# V4-15E3 R1 completion\n\nStatus: {status}\nScope: FIRST_PREWATCH × ABS_RETURN_N:T1 × CORE × RECONSTRUCTED_CORRECTED.\n\nFrozen chronological TRAIN / INTERNAL_TUNE / CALIBRATION / OUTER_TEST; actual label-end purge, shared episode checks, required feature complete-case ledger and fixed pre-phase actual knowledge cutoff. Dual clocks grant no historical first availability or PIT claim. Feature registry, exact E2 membership and selected label revisions unchanged.\n\nTRAIN-only preprocessing and marginal OOD reference. Six Huber trials and six linear quantile trials retained; selection confined to INTERNAL_TUNE. q25/q50/q75 raw predictions and pre-registered monotone rearrangements retained separately. Calibration is regression diagnostics only. JOINT_OOD UNSET; no global OOD_OK.\n\nOuter test opened/scored once. DATE_BALANCED_MAE: model {r['model']['DATE_BALANCED_MAE']:.10f}; pre-test TRAIN-only E2 baseline {r['baseline']['DATE_BALANCED_MAE']:.10f}. Effectiveness: {r['MODEL_EFFECTIVENESS']}. Coverage: {r['rows']}/{r['outer_total']} observations; {r['dates']} dates. No test-driven revision/refit.\n\nTargeted: {targeted['passed']} passed, {targeted['skipped']} skipped, {len(targeted['failed_nodes'])} failed. Scoped: {regression['passed']} passed, {regression['skipped']} skipped, {len(regression['failed_nodes'])} pre-existing debt failures, {len(regression['introduced_active_failures'])} introduced active failures.\n\nProtected accepted owners/heads, E1, PRIORITY_V1 and R25 WAIT unchanged. Real FEP tables empty. Production/shadow/focus false. MODEL_DISPLAY and PRIORITY_USE UNGRANTED. REAL_OOS/FIRST_OBSERVED NOT_GRANTED. E4 not required and not started.\n\nNext: {next_stage}. Local commit/push is not independent external acceptance.\n'''
    text+='\nA serialization ordering defect was discovered before any outer opening. The original protocol, implementation, twelve trials and quarantined calibration remain archived. A new v1.1 lineage froze its own twelve-trial budget before fitting; exact TRAIN transformation, selected parameters and coefficients match the predecessor. Only the repaired lineage opened the outer test, once. Reproduction uses requirements-fep-e3-r1.txt in the isolated E:/codex_tmp/fep_e3_deps environment; runtime versions and installation recipe are retained in the runtime manifest.\n'
    tmp=REPORT/'COMPLETION_REPORT.md.tmp';tmp.write_bytes(text.encode());tmp.replace(REPORT/'COMPLETION_REPORT.md')
    code=['src/workbench_analysis/fep_e3/__init__.py','src/workbench_analysis/fep_e3/protocol.py','src/workbench_analysis/fep_e3/models.py',
        'scripts/run_fep_e3_r1.py','tests/fep_e3/test_e3_contract.py','config/fep_e3_experiment_protocol_v1.json',PROTOCOL_PATH,'requirements-fep-e3-r1.txt']
    candidate=dict(stage='V4-15E3.R1',baseline=BASELINE,status=status,model_engineering='PASS_LOCAL_FIRST_PREWATCH_T1' if ready else 'BLOCKED',
        effectiveness=r['MODEL_EFFECTIVENESS'],code_bindings=[binding(path) for path in code],
        evidence_bindings=[binding(path) for path in sorted(REPORT.iterdir()) if path.is_file() and path.name!='FEP_E3_R1_CANDIDATE_SEAL.json' and not path.name.endswith('.tmp')],
        external_acceptance=False,REAL_OOS='NOT_GRANTED',FIRST_OBSERVED='NOT_GRANTED',MODEL_DISPLAY='UNGRANTED',PRIORITY_USE='UNGRANTED',
        production=False,shadow=False,next=next_stage,sealed_at=now())
    candidate['logical_digest']=digest(candidate);emit('FEP_E3_R1_CANDIDATE_SEAL',candidate);print(status,flush=True)

if __name__=='__main__':globals()[sys.argv[1]]()
