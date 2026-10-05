"""Exact E3 tree challenger, immutable trials, seen-test diagnostics and stage gate."""
import importlib.metadata,json,os,sys,subprocess,traceback,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scripts import run_fep_e3_r1 as e3
from scripts.build_fep_e2_r1r1_history import ROOT,binding,now
from workbench_analysis.fep_e1.contracts import atomic_json,digest
from workbench_analysis.fep_e1.feature_owner import verify_file
from workbench_analysis.fep_e3 import protocol as p,models as m
from workbench_analysis.fep_e4 import challenger as c

BASE='77c7c2c85a5ff0bbd27bb664900673de7a3bff5a'
REPORT=ROOT/'reports/fep_e4_r1';REGISTRY=REPORT/'registry';CP=ROOT/'config/fep_e4_challenger_protocol_v1.json'
CODE=['src/workbench_analysis/fep_e4/__init__.py','src/workbench_analysis/fep_e4/challenger.py','scripts/run_fep_e4_r1.py']
DOCS=['V4_FEP_EXECUTION_MASTER_V4_15E4_R1_20261005.md','V4_15E4_TREE_CHALLENGER_ENGINEERING_TASK_R1_20261005.md',
      'V4_15E3_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md']

def load(path):return json.loads(Path(path).read_bytes())
def emit(name,value):atomic_json(REPORT/(name+'.json'),value)
def write_bytes(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)
def save(kind,payload):
    artifact,path=p.immutable(REGISTRY,kind,dict(payload,created_at=now()))
    return artifact,binding(path)
def contract():
    verify_file(ROOT,load(REPORT/'CHALLENGER_PROTOCOL_FREEZE.json')['protocol'])
    cp=load(CP);c.claims(cp['claims']);c.split_rule(cp['split_rule']);c.budget(cp['point_grid'],cp['quantile_grid']);c.coherence(cp['coherence'])
    for ref in cp['input_bindings']+cp['implementation_bindings']:verify_file(ROOT,ref)
    if any(importlib.metadata.version(k)!=v for k,v in cp['runtime'].items()):raise ValueError('E4_RUNTIME_CHANGED')
    return cp
def inputs():
    cp=contract();folds=e3.folds();deps=load(e3.REPORT/'PRETEST_DEPENDENCIES.json')
    prep=load(ROOT/deps['preprocessing']['path']);ood=load(ROOT/deps['ood']['path'])
    c.exact(prep['terms'],cp['feature_terms'],'FEATURE_TERMS');c.exact(ood,load(ROOT/cp['ood_reference']['path']),'OOD')
    p.scope([r for group in folds.values() for r in group])
    return cp,folds,deps,prep,ood
def population(partition):
    cp,folds,deps,prep,ood=inputs();allrows={r['observation_id']:r for r in e3.rows()};manifest=load(e3.REPORT/'FOLD_MANIFEST.json')
    valid=set(manifest['retained_ids'][partition]);accepted=[];ledger=[]
    for key in manifest['all_date_ids'][partition]:
        r=allrows[key];check=m.ood_check(r['model_features'],{k:v['quality_state'] for k,v in r['feature_snapshot']['core_envelopes'].items()},ood)
        record=dict(observation_id=key,trade_date=r['trade_date'],status='PREDICTABLE' if key in valid and not check['hard_reasons'] else 'NOT_EVALUABLE',ood=check,label_status=r['status'])
        if record['status']=='PREDICTABLE':accepted.append(r)
        ledger.append(record)
    if not accepted:raise ValueError('E4_EMPTY_POPULATION')
    if partition in ('CALIBRATION','OUTER_TEST'):
        ref=load(e3.REPORT/('CALIBRATION_DIAGNOSTIC_GATE.json' if partition=='CALIBRATION' else 'OUTER_TEST_SEAL.json'))
        old=load(ROOT/ref['artifact' if partition=='CALIBRATION' else 'prediction_artifact']['path'])
        c.exact(ledger,old['population_ledger'],'POPULATION_LEDGER')
        c.exact([r['observation_id'] for r in accepted],[r['observation_id'] for r in old['predictions']],'PREDICTABLE_POPULATION')
    return accepted,ledger,prep

def prepare():
    if (REPORT/'CHALLENGER_PROTOCOL_FREEZE.json').exists():raise ValueError('E4_PROTOCOL_ALREADY_FROZEN')
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=BASE:raise ValueError('E4_BASELINE_MISMATCH')
    REPORT.mkdir(parents=True,exist_ok=True);write_bytes(REPORT/'.gitattributes',b'* -text\n')
    for name in DOCS:write_bytes(REPORT/name,(Path('D:/Users/lps/Desktop/阶段任务')/name).read_bytes())
    authority=(REPORT/DOCS[2]).read_text(encoding='utf-8')
    if 'PASS_FINAL_ENGINEERING_CAPABILITY_SCOPED' not in authority or BASE not in authority:raise ValueError('E4_UPSTREAM_AUTHORITY_MISSING')
    seal=load(e3.REPORT/'FEP_E3_R1_CANDIDATE_SEAL.json')
    if seal['effectiveness']!='NO_INCREMENT':raise ValueError('E4_E3_DISPOSITION_CHANGED')
    # Every accepted E3 code/evidence byte, recursive registry and archived attempts is bound.
    refs=seal['code_bindings']+seal['evidence_bindings']+[binding(e3.REPORT/'FEP_E3_R1_CANDIDATE_SEAL.json')]
    refs += [binding(path) for path in sorted((e3.REPORT/'registry').rglob('*.json'))]
    refs += [binding(path) for path in sorted((e3.REPORT/'attempts').rglob('*')) if path.is_file()]
    for ref in refs:verify_file(ROOT,ref)
    # E2 bindings and protected accepted heads retain their original identities.
    protected=load(e3.REPORT/'PROTECTED_STATE_READBACK.json')
    refs+=protected['heads']+protected['priority_bindings']+load(e3.REPORT/'E2_INPUT_BINDING.json')['bindings']
    unique={ref['path']:ref for ref in refs};refs=list(unique.values())
    for ref in refs:verify_file(ROOT,ref)
    deps=load(e3.REPORT/'PRETEST_DEPENDENCIES.json');prep=load(ROOT/deps['preprocessing']['path']);up=e3.contract();fold=e3.folds()
    emit('ENTRY_BASELINE',dict(stage='V4-15E4.R1',baseline=BASE,entered_at=now(),authority_bindings=[binding(REPORT/n) for n in DOCS],
        E3_external='PASS_FINAL_ENGINEERING_CAPABILITY_SCOPED',E3_MODEL_EFFECTIVENESS='NO_INCREMENT',E4_optional=True,next='STOP_WAIT_V4_15E4_INDEPENDENT_EXTERNAL_AUDIT'))
    emit('E3_INPUT_BINDING',dict(status='PASS_EXACT_ACCEPTED_BYTES',bindings=refs,live_rebuild=False,new_label_resolution=False))
    configurations=[dict(learning_rate=rate,max_leaf_nodes=leaves,max_depth=depth,min_samples_leaf=40,l2_regularization=1.0)
        for rate in (.05,.1) for leaves,depth in ((7,3),(15,4))]
    point=configurations;quantile=[dict(configurations[i],quantile=q) for q in (.25,.5,.75) for i in (0,3)]
    c.budget(point,quantile)
    discovery=dict(status='PASS_ENGINEERING_RESOURCE_BOUNDED',selection_outcome_performance_consumed=False,trial_fits=0,
        reasoning='Small depth/leaf grid, fixed 100 iterations, minimum leaf 40 and two threads bound complexity; 4 point and 2 per quantile.',
        point_trials=4,quantile_trials=6,total_fits=10,upper_bounds=dict(point=8,quantile=12,total=20),
        train_rows=len(fold['TRAIN']),automatic_early_stopping=False,random_validation_split=False)
    emit('CHALLENGER_PROTOCOL_DISCOVERY',discovery)
    cp=dict(contract_id='FEP_E4_HGB_CHALLENGER_V1',lineage_id='FEP_E4_R1_EXACT_E3_SEEN_OUTER',scope=p.SCOPE,
        baseline=BASE,E3_protocol_digest=up['logical_digest'],input_bindings=refs,implementation_bindings=[binding(ROOT/f) for f in CODE],
        runtime=up['runtime'],runtime_binding=binding(e3.REPORT/'RUNTIME_ENVIRONMENT_READBACK.json'),split_rule='EXACT_E3_FOLDS_NO_NEW_SPLIT',
        fold_manifest=binding(e3.REPORT/'FOLD_MANIFEST.json'),feature_manifest=binding(e3.REPORT/'FEATURE_MANIFEST.json'),feature_terms=prep['terms'],
        preprocessing=deps['preprocessing'],ood_reference=deps['ood'],point_grid=point,quantile_grid=quantile,
        fixed_parameters=dict(max_iter=100,max_bins=255,early_stopping=False,categorical_features=None,random_state=20261005,threads=2),
        selection_partition='INTERNAL_TUNE',point_primary='DATE_BALANCED_MAE',quantile_primary='DATE_BALANCED_PINBALL_PER_Q',tie_break='GRID_INDEX',
        calibration='DIAGNOSTIC_ONLY_NO_ADJUSTMENT',coherence=up['rearrangement'],interpretability=dict(partition='TRAIN',seed=20261005,repeats=3,selection=False),
        failed_attempts='APPEND_ONLY_IMMUTABLE_ALL_RETAINED',claims=c.FLAGS,frozen_at=now())
    c.coherence(cp['coherence']);cp['logical_digest']=digest({k:v for k,v in cp.items() if k!='frozen_at'});atomic_json(CP,cp)
    emit('CHALLENGER_PROTOCOL_FREEZE',dict(status='PASS_FROZEN_BEFORE_FIT',protocol=binding(CP),logical_digest=cp['logical_digest'],frozen_at=cp['frozen_at'],fits_before_freeze=0))
    emit('FOLD_REUSE_GATE',dict(status='PASS_EXACT_E3_FOLDS',artifact=cp['fold_manifest'],rows={k:len(v) for k,v in fold.items()},new_split=False))
    emit('FEATURE_REUSE_GATE',dict(status='PASS_EXACT_E3_FEATURES_AND_PREPROCESSING',manifest=cp['feature_manifest'],preprocessing=deps['preprocessing'],feature_terms=prep['terms'],fit=False,imputer=False))
    emit('OOD_REUSE_GATE',dict(status='PASS_EXACT_E3_MARGINAL_JOINT_UNSET',reference=deps['ood'],fit=False,relaxation=False,JOINT_OOD='UNSET',global_OOD_OK=False))
    print('protocol frozen; fits=0; budget=10',flush=True)

def train():
    if (REPORT/'TRAINING_TRIAL_LEDGER.json').exists() or any(REGISTRY.glob('trial*')) or any(REGISTRY.glob('attempt*')):raise ValueError('E4_FITS_ALREADY_ATTEMPTED_NEW_LINEAGE_REQUIRED')
    cp,folds,deps,prep,ood=inputs();rows=folds['TRAIN'];tune,_,_=population('INTERNAL_TUNE');ids=[r['observation_id'] for r in rows]
    dependencies=dict(protocol_logical_digest=cp['logical_digest'],preprocessing=deps['preprocessing'],ood=deps['ood'],train_ids_digest=digest(ids),runtime=cp['runtime'])
    grid=[('HGB_ABSOLUTE_ERROR',v) for v in cp['point_grid']]+[('HGB_QUANTILE',v) for v in cp['quantile_grid']];trials=[];successful=[]
    for index,(family,params) in enumerate(grid):
        attempted=now()
        # A durable start receipt prevents silently rerunning a crashed fit.
        write_bytes(REGISTRY/('attempt_'+str(index)+'.json'),json.dumps(dict(index=index,parameters=params,family=family,attempted_at=attempted)).encode())
        try:
            model=c.fit(rows,prep,family,params,dependencies,ids);pred=c.predict(model,tune,prep)
            metric=m.point_metrics(tune,pred)['DATE_BALANCED_MAE'] if family=='HGB_ABSOLUTE_ERROR' else m.pinball(tune,pred,params['quantile'])
            trial=dict(index=index,family=family,parameters=params,status='SUCCESS',model=model,selection_partition='INTERNAL_TUNE',selection_metric=metric)
        except Exception as exc:
            trial=dict(index=index,family=family,parameters=params,status='FAILED',error=type(exc).__name__+':'+str(exc),traceback=traceback.format_exc())
        artifact,ref=save('trial',dict(trial,dependencies=dependencies));trials.append(dict(index=index,status=trial['status'],artifact=ref,logical_digest=artifact['logical_digest'],attempted_at=attempted))
        if trial['status']=='SUCCESS':successful.append(trial)
        emit('TRAINING_TRIAL_LEDGER',dict(status='APPEND_ONLY_IN_PROGRESS',maximum=10,trials=trials,attempted=len(trials),failed=sum(t['status']=='FAILED' for t in trials),deleted_trials=0))
        print('trial',index,family,trial['status'],flush=True)
    p.ledger_integrity(list(range(10)),[t['index'] for t in trials]);ledger=load(REPORT/'TRAINING_TRIAL_LEDGER.json');ledger['status']='PASS_APPEND_ONLY_ALL_ATTEMPTS';emit('TRAINING_TRIAL_LEDGER',ledger)
    selected={}
    for family,q,name in [('HGB_ABSOLUTE_ERROR',None,'point'),('HGB_QUANTILE',.25,'q25'),('HGB_QUANTILE',.5,'q50'),('HGB_QUANTILE',.75,'q75')]:
        winner=c.select(successful,'INTERNAL_TUNE',family,q);model,ref=save('model_'+name,winner['model'])
        selected[name]=dict(artifact=ref,logical_digest=model['logical_digest'],trial_index=winner['index'],parameters=winner['parameters'])
    emit('SELECTED_DEPENDENCIES',dict(protocol_digest=cp['logical_digest'],selected=selected,preprocessing=deps['preprocessing'],ood=deps['ood'],frozen_at=now()))
    emit('POINT_CHALLENGER_GATE',dict(status='PASS_HGB_ABSOLUTE_ENGINEERING',selected=selected['point'],selection='INTERNAL_TUNE_DATE_BALANCED_MAE',TRAIN_only=True))
    emit('QUANTILE_CHALLENGER_GATE',dict(status='PASS_HGB_QUANTILE_ENGINEERING',selected={k:v for k,v in selected.items() if k!='point'},levels=[.25,.5,.75],TRAIN_only=True))

def predictions(partition):
    cp=contract();deps=load(REPORT/'SELECTED_DEPENDENCIES.json');rows,ledger,prep=population(partition)
    for item in deps['selected'].values():verify_file(ROOT,item['artifact'])
    models={k:load(ROOT/v['artifact']['path']) for k,v in deps['selected'].items()}
    point=c.predict(models['point'],rows,prep);raw=np.column_stack([c.predict(models[n],rows,prep) for n in ('q25','q50','q75')])
    diag,coherent=m.distribution_diagnostics(rows,raw,cp['coherence'])
    records=[dict(observation_id=r['observation_id'],trade_date=r['trade_date'],point=float(point[i]),raw_quantiles=list(map(float,raw[i])),coherent_quantiles=list(map(float,coherent[i]))) for i,r in enumerate(rows)]
    return rows,point,diag,records,ledger

def calibrate():
    if (REPORT/'CALIBRATION_DIAGNOSTIC_GATE.json').exists():raise ValueError('E4_CALIBRATION_ALREADY_SEALED')
    rows,point,diag,records,ledger=predictions('CALIBRATION')
    artifact,ref=save('calibration',dict(predictions=records,population_ledger=ledger,diagnostics=diag,point_metrics=m.point_metrics(rows,point),model_adjustment='NONE'))
    emit('CALIBRATION_DIAGNOSTIC_GATE',dict(status='PASS_EXACT_E3_CALIBRATION_DIAGNOSTIC',artifact=ref,rows=len(rows),diagnostics=diag,selection=False,probability_calibration='NOT_APPLICABLE_REGRESSION'))
    cp,folds,deps,prep,ood=inputs();selected=load(REPORT/'SELECTED_DEPENDENCIES.json')['selected'];model=load(ROOT/selected['point']['artifact']['path'])
    importance=c.permutation_diagnostic(model,folds['TRAIN'],prep)
    art,iref=save('feature_importance',dict(importance,selected_point=selected['point'],complexity=model['complexity'],TRAIN_leaf_support=model['TRAIN_leaf_support']))
    emit('FEATURE_IMPORTANCE_DIAGNOSTIC',dict(status='PASS_TRAIN_COMPUTATION_ONLY',artifact=iref,partition='TRAIN',feature_selection=False,causal=False,funding_intent=False))

def seen_outer():
    cp=contract();selection=load(REPORT/'SELECTED_DEPENDENCIES.json');cal=load(REPORT/'CALIBRATION_DIAGNOSTIC_GATE.json')
    for ref in [cal['artifact']]+[v['artifact'] for v in selection['selected'].values()]:verify_file(ROOT,ref)
    p.open_outer(REPORT/'SEEN_OUTER_DIAGNOSTIC_OPEN.json',dict(protocol_digest=cp['logical_digest'],selected=selection,calibration=cal['artifact'],opened_at=now(),**c.FLAGS))
    rows,point,diag,records,ledger=predictions('OUTER_TEST');old=load(ROOT/load(e3.REPORT/'OUTER_TEST_SEAL.json')['prediction_artifact']['path'])
    ids=[r['observation_id'] for r in rows];c.exact(ids,[r['observation_id'] for r in old['predictions']],'OUTER_PREDICTABLE_IDS')
    deps=load(e3.REPORT/'PRETEST_DEPENDENCIES.json');baseline=load(ROOT/deps['baseline']['path'])['predictor']
    metrics=dict(E2=m.point_metrics(rows,[baseline]*len(rows)),E3=m.point_metrics(rows,[r['point'] for r in old['predictions']]),E4=m.point_metrics(rows,point))
    c.exact(metrics['E3'],load(e3.REPORT/'BASELINE_COMPARISON.json')['result']['model'],'E3_METRICS')
    c.exact(metrics['E2'],load(e3.REPORT/'BASELINE_COMPARISON.json')['result']['baseline'],'E2_METRICS')
    diffs={k:metrics[k]['DATE_BALANCED_MAE']-metrics['E4']['DATE_BALANCED_MAE'] for k in ('E2','E3')}
    effectiveness='INCREMENT_DIAGNOSTIC' if all(v>0 for v in diffs.values()) else 'NO_INCREMENT' if all(v<=0 for v in diffs.values()) else 'MIXED'
    counts=m.comparison(rows,point,[baseline]*len(rows),ids,ids)
    result=dict(primary_metric='DATE_BALANCED_MAE',metrics=metrics,improvement_delta=diffs,CHALLENGER_EFFECTIVENESS=effectiveness,
        disposition='CHALLENGER_ENGINEERING_PASS_'+effectiveness,E3_MODEL_EFFECTIVENESS='NO_INCREMENT',
        rows=len(rows),outer_total=len(ledger),coverage=len(rows)/len(ledger),dates=counts['dates'],blocks=counts['blocks'],entities=counts['entities'],episodes=counts['episodes'],
        exact_observation_ids=ids,date_weight_digest=digest(list(map(float,m.date_weights(rows)))),
        E3_quantile_diagnostics=load(e3.REPORT/'OUTER_TEST_EVALUATION.json')['result']['quantile_diagnostics'],E4_quantile_diagnostics=diag,
        effectiveness_rule='INCREMENT if beats both E2 and E3 MAE; NO_INCREMENT if beats neither; otherwise MIXED; seen diagnostic only',**c.FLAGS)
    prediction,pref=save('seen_outer_predictions',dict(predictions=records,population_ledger=ledger,protocol_digest=cp['logical_digest'],**c.FLAGS))
    evaluation,eref=save('seen_outer_evaluation',dict(result=result,predictions=pref,protocol_digest=cp['logical_digest'],**c.FLAGS))
    emit('SEEN_OUTER_POPULATION_GATE',dict(status='PASS_EXACT_E3_PREDICTABLE_POPULATION',artifact=pref,rows=len(rows),total=len(ledger),same_ID_order=True,same_weights=True,**c.FLAGS))
    emit('SEEN_OUTER_DIAGNOSTIC_EVALUATION',dict(status='PASS_SEEN_DIAGNOSTIC_ONLY',artifact=eref,result=result,**c.FLAGS))
    emit('BASELINE_E3_E4_COMPARISON',dict(status='PASS_EXACT_SAME_POPULATION',result=result,**c.FLAGS))
    emit('MODEL_REGISTRY_GATE',dict(status='PASS_IMMUTABLE_CHALLENGER_LEDGER',registry=[binding(path) for path in sorted(REGISTRY.glob('*.json'))],
        failed_trials_retained=True,logical_ID_excludes_created_at=True,models_portable_JSON=True,**c.FLAGS))
    print('seen diagnostic',effectiveness,metrics,flush=True)

def tests():
    from scripts import run_fep_e2_r1 as runner
    runner.REPORT=REPORT;runner.BASE=BASE;env=os.environ.copy()
    env.update(PYTHONPATH='E:/codex_tmp/fep_e3_deps'+os.pathsep+str(ROOT)+os.pathsep+str(ROOT/'src'),TEMP='E:/codex_tmp/test_temp',TMP='E:/codex_tmp/test_temp',
        WORKBENCH_PG_DSN='host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh',FEP_E1_TEST_DSN='host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh',
        OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2')
    runner.execute([sys.executable,'-B','-m','pytest','tests/fep_e4','tests/fep_e3','tests/fep_e2','tests/fep','tests/test_r20d_settlement.py',
        'tests/test_r25_packet.py::test_actual_authority_inventory_waits_without_target','-q','--basetemp=E:/codex_tmp/test_temp/e4-targeted','--junitxml='+str(REPORT/'targeted.xml')],env,'targeted')
    if sys.argv[2:]==['targeted-only']:return
    prior=load(e3.REPORT/'SCOPED_REGRESSION_SUMMARY.json');command=[v for v in prior['command'] if not v.startswith(('--basetemp=','--junitxml='))]
    command[0]=sys.executable;command+=['tests/fep_e4','--basetemp=E:/codex_tmp/test_temp/e4-scoped','--junitxml='+str(REPORT/'scoped.xml')]
    runner.execute(command,env,'scoped',prior['failed_nodes'])

def finalize():
    cp=contract();inputs();protected=load(e3.REPORT/'PROTECTED_STATE_READBACK.json')
    from scripts.validate_r25_preflight import protected as r25_protected,selection
    import psycopg
    from psycopg import sql
    with psycopg.connect('host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh') as db:
        tables=[r[0] for r in db.execute("select tablename from pg_tables where schemaname='fep' order by tablename")]
        counts={t:db.execute(sql.SQL('select count(*) from fep.{}').format(sql.Identifier(t))).fetchone()[0] for t in tables}
    if len(counts)!=33 or any(counts.values()):raise ValueError('E4_DATABASE_ISOLATION_FAILED')
    emit('PROTECTED_STATE_READBACK',dict(status='PASS',heads=protected['heads'],priority_bindings=protected['priority_bindings'],real_FEP_table_counts=counts,
        R25_protected=r25_protected(ROOT),R25_selection=selection(ROOT),E3_MODEL_EFFECTIVENESS='NO_INCREMENT',TDX='UNTOUCHED',FIRST_OBSERVED='NOT_GRANTED',**c.FLAGS))
    targeted=load(REPORT/'TARGETED_SUMMARY.json');regression=load(REPORT/'SCOPED_REGRESSION_SUMMARY.json')
    negatives=[dict(node=t.attrib['classname']+'::'+t.attrib['name'],status='PASS' if t.find('failure') is None and t.find('error') is None and t.find('skipped') is None else 'FAIL')
        for t in ET.parse(REPORT/'targeted.xml').findall('.//testcase') if 'test_e4' in t.attrib['classname']]
    emit('NEGATIVE_MATRIX',dict(status='PASS' if len(negatives)>=20 and all(t['status']=='PASS' for t in negatives) else 'FAIL',cases=negatives,count=len(negatives),synthetic_only=True))
    for ref in load(REPORT/'MODEL_REGISTRY_GATE.json')['registry']:
        verify_file(ROOT,ref);artifact=load(ROOT/ref['path'])
        if 'logical_digest' in artifact:
            semantic={k:v for k,v in artifact.items() if k not in ('created_at','run_id','logical_digest','artifact_id','kind')}
            if digest(semantic)!=artifact['logical_digest']:raise ValueError('E4_LOGICAL_DIGEST_CHANGED')
    trial=load(REPORT/'TRAINING_TRIAL_LEDGER.json');p.ledger_integrity(list(range(10)),[t['index'] for t in trial['trials']])
    gates=('FOLD_REUSE_GATE','FEATURE_REUSE_GATE','OOD_REUSE_GATE','POINT_CHALLENGER_GATE','QUANTILE_CHALLENGER_GATE',
        'CALIBRATION_DIAGNOSTIC_GATE','FEATURE_IMPORTANCE_DIAGNOSTIC','SEEN_OUTER_POPULATION_GATE','MODEL_REGISTRY_GATE','NEGATIVE_MATRIX')
    ready=not targeted['failed_nodes'] and not regression['introduced_active_failures'] and all(load(REPORT/(g+'.json'))['status'].startswith('PASS') for g in gates)
    status='PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT' if ready else 'NO_INCREMENT_OR_BLOCKED_NONBLOCKING';result=load(REPORT/'BASELINE_E3_E4_COMPARISON.json')['result']
    emit('LOCAL_ACCEPTANCE_MATRIX',dict(status=status,FEP_CHALLENGER_ENGINEERING='PASS_LOCAL' if ready else 'BLOCKED',
        CHALLENGER_EFFECTIVENESS=result['CHALLENGER_EFFECTIVENESS'],checks={g:load(REPORT/(g+'.json'))['status'] for g in gates},
        introduced_active_failures=regression['introduced_active_failures'],NEW_INDEPENDENT_OOS_EVIDENCE=False,external_acceptance=False,E5_not_blocked=True,
        next='STOP_WAIT_V4_15E4_INDEPENDENT_EXTERNAL_AUDIT',**c.FLAGS))
    emit('INDEPENDENT_AUDIT_ITEMS',dict(items=[dict(audit_id='FEP_E4_SEEN_HISTORICAL_DIAGNOSTIC_LIMITATION',status='OPEN_EXTERNAL_REVIEW',
        scope='Seen historical rows, low exact E3 coverage, dual clocks and marginal-only JOINT_OOD UNSET; no promotion or independent OOS',
        evidence=[binding(REPORT/'SEEN_OUTER_POPULATION_GATE.json'),binding(REPORT/'BASELINE_E3_E4_COMPARISON.json')],acceptance='Independent E4 audit only; upstream limitations stay open')]))
    text=f'''# V4-15E4 R1 completion\n\nStatus: {status}\n\nExact accepted E3 v1.1 FIRST_PREWATCH × ABS_RETURN_N:T1 × CORE × RECONSTRUCTED_CORRECTED. All fold, feature, preprocessing, OOD, label revision and membership bytes reused. No new split, imputation, OOD relaxation or current-head rebuild.\n\nTen bounded HistGradientBoostingRegressor fits: four absolute-error point and six quantile (two per q25/q50/q75). Fixed 100 iterations, no automatic early stopping/random validation. TRAIN-only fitting; INTERNAL_TUNE-only selection. All attempts retained. Portable JSON trees verified against sklearn TRAIN predictions before selection. TRAIN permutation diagnostics, tree complexity and actual leaf support retained; no causal/资金意图 claim.\n\nCALIBRATION is diagnostics only. Raw and frozen E3 monotone rearranged quantiles retained. Probability calibration NOT_APPLICABLE_REGRESSION.\n\nE3 Outer is previously seen: SEEN_OUTER_DIAGNOSTIC_ONLY, TEST_PREVIOUSLY_SEEN=true, REAL_OOS=false, PROMOTION_EVIDENCE=false. Exact comparable population {result['rows']}/{result['outer_total']} rows, {result['dates']} dates, {result['blocks']} blocks. E2/E3/E4 DATE_BALANCED_MAE: {result['metrics']['E2']['DATE_BALANCED_MAE']:.10f} / {result['metrics']['E3']['DATE_BALANCED_MAE']:.10f} / {result['metrics']['E4']['DATE_BALANCED_MAE']:.10f}. Challenger: {result['CHALLENGER_EFFECTIVENESS']}. E3 stays NO_INCREMENT. No result-driven tuning/refit.\n\nTargeted {targeted['passed']} passed / {targeted['skipped']} skipped / {len(targeted['failed_nodes'])} failed. Scoped {regression['passed']} passed / {regression['skipped']} skipped / {len(regression['failed_nodes'])} existing debt failures / {len(regression['introduced_active_failures'])} introduced active failures; prior exclusions unchanged.\n\nAccepted heads, PRIORITY_V1, E1/E2/E3 artifacts and R25 WAIT preserved; 33 real FEP tables empty, TDX untouched. JOINT_OOD UNSET. CHAMPION=false. Promotion, MODEL_DISPLAY, PRIORITY_USE and production UNGRANTED; production/shadow/focus=false, FIRST_OBSERVED NOT_GRANTED. E4 optional and E5 not blocked.\n\nReproduction: use the exact E3 pinned isolated E:/codex_tmp/fep_e3_deps runtime and E-only temporary roots. Run prepare → train → calibrate → seen_outer → tests → finalize in a new baseline workspace. Freeze and immutable attempt receipts prevent repeating fitting or seen diagnostic phases in this lineage.\n\nNext: STOP_WAIT_V4_15E4_INDEPENDENT_EXTERNAL_AUDIT. Commit/push is not external acceptance.\n'''
    write_bytes(REPORT/'COMPLETION_REPORT.md',text.encode())
    candidate=dict(stage='V4-15E4.R1',baseline=BASE,status=status,effectiveness=result['CHALLENGER_EFFECTIVENESS'],
        code_bindings=[binding(ROOT/f) for f in CODE+['tests/fep_e4/test_e4_contract.py','config/fep_e4_challenger_protocol_v1.json']],
        evidence_bindings=[binding(path) for path in sorted(REPORT.iterdir()) if path.is_file() and path.name!='FEP_E4_R1_CANDIDATE_SEAL.json'],
        external_acceptance=False,next='STOP_WAIT_V4_15E4_INDEPENDENT_EXTERNAL_AUDIT',sealed_at=now(),**c.FLAGS)
    candidate['logical_digest']=digest(candidate);emit('FEP_E4_R1_CANDIDATE_SEAL',candidate);print(status,flush=True)

if __name__=='__main__':globals()[sys.argv[1]]()
