"""E5 checkpointed exact artifact projection, isolated PostgreSQL ledger and seal."""
import json,os,sys,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,timedelta,timezone
from collections import Counter
import psycopg
from psycopg import sql
from scripts.build_fep_e2_r1r1_history import ROOT,binding,now
from scripts import run_fep_e3_r1 as e3
from scripts.validate_r25_preflight import protected,selection
from workbench_analysis.fep_e1.contracts import atomic_json,digest
from workbench_analysis.fep_e1.feature_owner import verify_file
from workbench_analysis.fep_e5 import contracts as c,adapters as a,projection as p,fixtures as f
from workbench_analysis.fep_e5.ledger import Ledger,TABLES
from workbench_service.expectancy_service import ExpectancyReadAPI

BASE='adcfa36466e0c33626cc6ffc5fbd37cfd65e98bb'
REPORT=ROOT/'reports/fep_e5_r1';PROTOCOL=ROOT/'config/fep_e5_projection_priority_protocol_v1.json'
EVIDENCE=ROOT/'config/fep_e5_model_evidence_class_v1.json'
DSN='host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh'
CODE=['src/workbench_analysis/fep_e5/'+n for n in ('__init__.py','contracts.py','ledger.py','schema.sql','projection.py','adapters.py','fixtures.py')]+['src/workbench_service/expectancy_service.py','scripts/run_fep_e5_r1.py']
DOCS=['V4_FEP_EXECUTION_MASTER_V4_15E5_R1_20261006.md','V4_15E5_FEP_PROJECTION_PRIORITY_SHADOW_ENGINEERING_TASK_R1_20261006.md']

def load(path):return json.loads(Path(path).read_bytes())
def emit(name,payload):atomic_json(REPORT/(name+'.json'),payload)
def write(path,raw):
    tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    os.replace(tmp,path)
def contract():
    freeze=load(REPORT/'PROTOCOL_FREEZE.json');verify_file(ROOT,freeze['protocol']);verify_file(ROOT,freeze['evidence_class'])
    cp=load(PROTOCOL);c.protocol_guard(cp,cp)
    for ref in cp['implementation_bindings']+cp['upstream_bindings']:verify_file(ROOT,ref)
    return cp
def catalog():return load(REPORT/'MODEL_CATALOG.json')['models']
def selected_inputs():
    cp=contract();allrows={r['observation_id']:r for r in e3.rows()}
    return [a.snapshot(allrows[key],cp['source_model_rows']['sha256']) for key in cp['planned_observation_ids']]

def prepare():
    c.require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==BASE,'BASELINE_MISMATCH')
    c.require(not PROTOCOL.exists() and not (REPORT/'PROTOCOL_FREEZE.json').exists(),'PROTOCOL_ALREADY_FROZEN')
    REPORT.mkdir(parents=True,exist_ok=True);write(REPORT/'.gitattributes',b'* -text\n')
    for name in DOCS:write(REPORT/name,(Path('D:/Users/lps/Desktop/阶段任务')/name).read_bytes())
    closure=load(ROOT/'reports/fep_e4_reconciliation_final_audit_r1/FINAL_AUDIT_ARCHIVE_SEAL.json')
    c.require(closure['final_state']['E4']=='FORMALLY_CLOSED' and closure['final_state']['E5_ENTRY']=='AUTHORIZED','E5_ENTRY_NOT_AUTHORIZED')
    refs=[]
    for folder in ('fep_e2_r1r2','fep_e3_r1','fep_e4_r1','fep_e4_external_acceptance_r1','fep_e4_reconciliation_final_audit_r1'):
        seal_name={'fep_e2_r1r2':'FEP_E2_R1R2_CANDIDATE_SEAL.json','fep_e3_r1':'FEP_E3_R1_CANDIDATE_SEAL.json','fep_e4_r1':'FEP_E4_R1_CANDIDATE_SEAL.json',
            'fep_e4_external_acceptance_r1':'EXTERNAL_ACCEPTANCE_SEAL.json','fep_e4_reconciliation_final_audit_r1':'FINAL_AUDIT_ARCHIVE_SEAL.json'}[folder]
        seal=load(ROOT/'reports'/folder/seal_name)
        refs+=seal.get('code_bindings',[])+seal.get('evidence_bindings',[])+([seal['code_binding']] if 'code_binding' in seal else [])
        refs.append(binding(ROOT/'reports'/folder/seal_name))
    refs+=load(ROOT/'reports/fep_e4_r1/MODEL_REGISTRY_GATE.json')['registry']
    refs+=load(ROOT/'config/fep_e4_challenger_protocol_v1.json')['input_bindings']
    design=[load(ROOT/'config/source_authority_governance_r4.json')['master_contract'],load(ROOT/'config/fep_target_registry_v1.json')['design_module_binding'],
        binding(ROOT/'docs/evidence/fep_e1/V4_2_2_FEP_R2_EXTERNAL_DESIGN_ACCEPTANCE_20260930.md')]
    c.require(design[0]['sha256']=='203ff46075b4039d1e2d45d54fd76ce09509535739cd6aaef4dc394de1015205' and design[1]['sha256']=='f01ac9c550a71b8edb73436969e39172f6809404df9e19ffbfff2306c9456014','DESIGN_AUTHORITY')
    protect=load(ROOT/'reports/fep_e4_r1/PROTECTED_STATE_READBACK.json')
    priority=protect['priority_bindings']+[binding(ROOT/name) for name in ['src/v4/stock_prewatch.py','src/v4/stock_prewatch_persistence.py','src/workbench_analysis/v4_15_radar_cohort.py']]
    refs+=design+priority+protect['heads']
    refs+= [binding(ROOT/name) for name in ['config/fep_e2_support_policy_registry_v1_1.json','config/fep_conditional_statistics_contract_v1.json','config/fep_feature_registry_v1.json','config/fep_target_registry_v1.json']]
    refs=list({ref['path']:ref for ref in refs}.values())
    for ref in refs:verify_file(ROOT,ref)
    baseline_gate=load(ROOT/'reports/fep_e2_r1r2/CONDITIONAL_BASELINE_FIRST_PREWATCH_T1.json');baseline=load(ROOT/baseline_gate['artifact']['path'])
    c.require(baseline['scope']=='FEP_STOCK_ENTRY_CORE' and baseline['base_partition']['target']=='ABS_RETURN_N:T1' and baseline['base_partition']['horizon']==1,'BASELINE_SCOPE')
    e3deps=load(e3.REPORT/'PRETEST_DEPENDENCIES.json');e4deps=load(ROOT/'reports/fep_e4_r1/SELECTED_DEPENDENCIES.json')
    classes=dict(contract_id='FEP_E5_MODEL_EVIDENCE_CLASS_V1',version='1.0.0',champion='NONE',classes=[
        dict(stage='E2',model_family='CONDITIONAL_STATISTICS_BASELINE',evidence_class='ACCEPTED_BASELINE_ENGINEERING',priority_role='PRIMARY_E5_ENGINEERING_SOURCE',production_role='NONE'),
        dict(stage='E3',model_family='INTERPRETABLE_MODEL',evidence_class='ACCEPTED_MODEL_ENGINEERING_NO_INCREMENT',priority_role='DIAGNOSTIC_SHADOW_ONLY',production_role='NONE'),
        dict(stage='E4',model_family='TREE_CHALLENGER',evidence_class='ACCEPTED_CHALLENGER_ENGINEERING_MIXED_NO_INCREMENT_VS_E2',priority_role='DIAGNOSTIC_SHADOW_ONLY',production_role='NONE')])
    atomic_json(EVIDENCE,classes);emit('MODEL_EVIDENCE_CLASS',classes)
    model_sources={'E2':dict(primary=baseline_gate['artifact']), 'E3':{k:v['artifact'] for k,v in e3deps['selected'].items()},'E4':{k:v['artifact'] for k,v in e4deps['selected'].items()}}
    model_set=digest(dict(model_sources=model_sources,evidence_class=classes,scope='FEP_STOCK_ENTRY_CORE',target='ABS_RETURN_N:T1',horizon='T1'))
    models=[]
    for cls in classes['classes']:
        stage=cls['stage'];sources=model_sources[stage]
        models.append(dict(cls,model_id='FEP_E5_'+stage+':'+digest(sources),model_set_id=model_set,scope_id='FEP_STOCK_ENTRY_CORE',observation_scope='FIRST_PREWATCH',
            target_id='ABS_RETURN_N:T1',horizon='T1',feature_contract_id=baseline['feature_contract_id'],namespace='FEP_E5_'+stage+'_HISTORICAL',
            artifact_references=sources,artifact_digest=digest(sources),champion=False,activation_effective_at='SET_BY_ACTUAL_ENGINEERING_ACTIVATION_CHECKPOINT'))
    emit('MODEL_CATALOG',dict(models=models,model_set_id=model_set,champion='NONE'))
    ids=load(e3.REPORT/'FOLD_MANIFEST.json')['all_date_ids']['OUTER_TEST']
    stub=dict(status='NOT_ACTIVE',evaluation_open=False,evaluated=False,dimensions={key:'UNSET' for key in ['scope_id','candidate_day_observation_scope','target','horizon','feature_contract','model_set','K','coverage_floor','primary_return_metric','risk_metric','rejection_abstention_metric','missingness_metric','block_length','minimum_OOS_signal_dates','minimum_OOS_episodes_entities','promotion_margin','risk_noninferiority_boundary']},UNSET_policy='CANNOT_ACTIVATE_EVALUATION',future_task='REQUIRES_SEPARATE_PRE_REGISTERED_OOS_PROTOCOL')
    emit('FUTURE_PRIORITY_OOS_PROTOCOL_STUB',stub)
    cp=dict(contract_id=c.VERSION,baseline=BASE,stage='V4-15E5.R1',design_authority=design,upstream_bindings=refs,priority_bindings=priority,
        implementation_bindings=[binding(ROOT/path) for path in CODE],model_evidence_class=binding(EVIDENCE),model_catalog=binding(REPORT/'MODEL_CATALOG.json'),
        effectiveness_disposition_rule=dict(type='ORDERED_ENGINEERING_GATE',rules=[dict(if_failed=key,disposition='BLOCKED') for key in ('contract','protected','entry_ledger_api_rollback','daily_fail_closed')],otherwise='PASS_ENGINEERING_ONLY_NO_PROMOTION'),
        primary_metric='ENGINEERING_CONTRACT_EXACTNESS',tie_break='NOT_APPLICABLE_ENGINEERING_GATE',promotion_boundary='CLOSED_NO_DAILY_SCOPE_NO_REAL_OOS',
        priority_projection_boundary=dict(real_daily='NOT_ENABLED_NO_ACCEPTED_DAILY_SCOPE',same_day_required=True,preserve_complete_V1=True,priority_protocol=f.priority_protocol()),
        shadow_only_boundary=dict(capability='SHADOW_INFERENCE',production=False,real_shadow=False,synthetic_priority_only=True),
        E5_EFFECTIVENESS_EVALUATION='CLOSED_ENGINEERING_ONLY',future_OOS_protocol=binding(REPORT/'FUTURE_PRIORITY_OOS_PROTOCOL_STUB.json'),
        planned_observation_ids=ids,source_model_rows=binding(e3.REPORT/'EXACT_MODEL_ROWS.jsonl.gz'),feature_manifest=binding(e3.REPORT/'FEATURE_MANIFEST.json'),
        baseline_artifact=baseline_gate['artifact'],preprocessing=e3deps['preprocessing'],ood=e3deps['ood'],rearrangement=e3.contract()['rearrangement'],
        bound_batch=dict(observations=len(ids),namespaces=3,optional_no_model_slots=1,full_E2_population_claim=False,selection='Exact complete pre-existing E3 historical Outer ledger; no effectiveness evaluation'),
        temporal_policy=dict(model_selection_cutoff='Actual UTC after engineering activation commit, before inference',prediction_deadline='Selection cutoff + 60 minutes',
            historical_trade_dates_not_real_prediction_dates=True,prediction_evidence='HISTORICAL_SIMULATION'),
        namespace='fep_e5_engineering',database='ISOLATED_EXPLICIT_ENGINEERING_DSN_ONLY',production_migration=False,
        resources=dict(max_observations=len(ids),new_model_training=0,new_hyperparameter_search=0,new_label_resolution=0,new_E4_trials=0,threads=2),
        entry_thresholds='UNSET_NOT_FROZEN',model_roles=classes,API='EXPLICIT_LEDGER_INJECTION_ENGINEERING_ONLY_NO_PRODUCTION_DEFAULT_ROUTE',frozen_at=now())
    cp['logical_digest']=c.logical(cp);atomic_json(PROTOCOL,cp)
    emit('ENTRY_BASELINE',dict(stage='V4-15E5.R1',baseline=BASE,authority=[binding(REPORT/n) for n in DOCS],entered_at=now(),E5_FORMAL_TASK_CARD='ISSUED',E5_EXECUTION='AUTHORIZED'))
    emit('UPSTREAM_BINDINGS',dict(status='PASS_EXACT_UPSTREAM',bindings=refs,model_sources=model_sources,no_current_head_rebuild=True,new_labels=False))
    emit('PROTOCOL_FREEZE',dict(status='PASS_FROZEN_BEFORE_PROJECTION',protocol=binding(PROTOCOL),evidence_class=binding(EVIDENCE),frozen_at=cp['frozen_at'],logical_digest=cp['logical_digest'],projection_runs_before_freeze=0,effectiveness_evaluation_open=False))
    print('protocol frozen; planned 205 x 3 + 1 missing-model slots',flush=True)

def project():
    cp=contract();c.require(not (REPORT/'ENTRY_PROJECTION_READBACK.json').exists(),'PROJECTION_ALREADY_CHECKPOINTED')
    baseline=load(ROOT/cp['baseline_artifact']['path']);prep=load(ROOT/cp['preprocessing']['path']);ood=load(ROOT/cp['ood']['path'])
    with psycopg.connect(DSN,autocommit=True) as pg:
        ledger=Ledger(pg);ledger.install()
        with pg.transaction():ledger.put('protocols',cp['logical_digest'],cp)
        clock_path=REPORT/'EXECUTION_CLOCK.json'
        if clock_path.exists():clock=load(clock_path)
        else:
            clock=dict(activation_effective_at=now());emit('EXECUTION_CLOCK',clock)
        models=[]
        for raw in catalog():
            model=dict(raw,activation_effective_at=clock['activation_effective_at']);ledger.register_model(model);models.append(model)
        grant=ledger.grant(models[0]['model_id']);ledger.cas(grant['grant_id'],'E5_ENTRY_ACTIVATE:'+cp['logical_digest'],0,'ALLOW',clock['activation_effective_at'])
        if 'model_selection_cutoff' not in clock:
            clock.update(model_selection_cutoff=now());clock['prediction_deadline']=(c.utc(clock['model_selection_cutoff'])+timedelta(minutes=60)).isoformat();emit('EXECUTION_CLOCK',clock)
        projected=[];inputs=selected_inputs();serialized={model['stage']:{k:load(ROOT/v['path']) for k,v in model['artifact_references'].items()} for model in models if model['stage']!='E2'}
        planned=[]
        for row in inputs:
            for model in models:
                s=dict({k:model[k] for k in c.IDENTITY},namespace=model['namespace'],entity_id=row['entity_id'],observation_id=row['observation_id'],
                    signal_key='FIRST_PREWATCH:'+row['observation_id'],trade_date=row['trade_date'],model_family_scope=model['model_family'],
                    model_selection_cutoff=clock['model_selection_cutoff'],prediction_deadline=clock['prediction_deadline'])
                s=ledger.plan(s);planned.append(s);ledger.bind(s['slot_id'],model['model_id'])
                output=a.inference(model,row,baseline,prep,ood,serialized.get(model['stage']));stamp=now()
                projected.append(p.accept(ledger,s['slot_id'],row,output,stamp,stamp))
        optional=dict(planned[0],namespace='FEP_E5_OPTIONAL_NO_MODEL',model_family_scope='UNAVAILABLE_OPTIONAL_FAMILY');optional.pop('slot_id')
        optional=ledger.plan(optional);planned.append(optional);p.missing(ledger,optional,'NO_ACTIVE_MODEL',now())
        emit('PREDICTION_SLOT_LEDGER',dict(status='PASS_COMPLETE_PLANNED_BATCH',slots=planned,counts=ledger.inventory(),optional_receipt='NO_ACTIVE_MODEL',complete_batch=True,full_E2_population_claim=False))
        emit('PREDICTION_BINDING_READBACK',dict(status='PASS_SELECTION_BEFORE_PREDICTION',bindings=ledger.rows('slot_model_bindings'),models=ledger.rows('models'),clock=clock,model_set_frozen_in_protocol=True))
        emit('ENTRY_PROJECTION_READBACK',dict(status='PASS_ENGINEERING_HISTORICAL_PROJECTION',rows=projected,states=dict(Counter(r['projection_state'] for r in projected)),
            by_family={model['model_family']:dict(Counter(r['projection_state'] for r in projected if r['model_family']==model['model_family'])) for model in models},
            baseline_method='Exact accepted E2 L1 weighted_mean/p25/p50/p75 serialization; not rebuilt or fitted',historical_full_population_claim=False,new_label_reads=False,
            prediction_evidence='HISTORICAL_SIMULATION',FIRST_OBSERVED=False,REAL_OOS=False,thresholds='NOT_FROZEN'))
        # Exact first accepted view and repeat consumption preserve identities and physical receipts.
        first=next(r for r in projected if r['model_family']=='CONDITIONAL_STATISTICS_BASELINE');row=next(r for r in inputs if r['observation_id']==first['observation_id'])
        replay=p.accept(ledger,first['slot_id'],row,a.inference(models[0],row,baseline,prep,ood),now(),now());c.exact(replay,first,'IDEMPOTENT_PROJECTION')
        api=ExpectancyReadAPI(ledger,now());token=api.bootstrap(first['slot_id'])['context']
        emit('API_READBACK',dict(status='PASS_EXPLICIT_ENGINEERING_API',context=token,default_response=api.projection(first['slot_id'],token),
            diagnostic_response=api.projection(first['slot_id'],token,diagnostic=True),today_ENTRY_reuse=api.projection(first['slot_id'],token,diagnostic=True,mode='TODAY_RADAR'),daily_priority=api.priority()))
        emit('PERMISSION_MATRIX',dict(status='PASS_EXACT_SHADOW_ONLY',keys=ledger.rows('permission_keys'),model_members=[m['model_id'] for m in models],
            identity_fields=list(c.GRANT),SHADOW_INFERENCE='ENGINEERING_ONLY',DESCRIPTIVE_DISPLAY='UNGRANTED',MODEL_DISPLAY='UNGRANTED',PRIORITY_USE='UNGRANTED',CHAMPION='NONE',FEP_PRODUCTION='UNGRANTED'))
        emit('PROJECTION_PERSISTENCE_GATE',dict(status='PASS_POSTGRES_APPEND_ONLY_ENGINEERING_NAMESPACE',namespace=cp['namespace'],counts=ledger.inventory(),
            source_schema='fep UNCHANGED',production_database=False,projection_content_digest=digest(ledger.rows('projections')),api_mounted_in_production=False))
    print('projected',len(projected),'slots',len(planned),flush=True)

def drills():
    cp=contract();c.require(not (REPORT/'ROLLBACK_DRILL.json').exists(),'DRILLS_ALREADY_CHECKPOINTED')
    pool,predictions,day,risk=f.fixture();protocol=cp['priority_projection_boundary']['priority_protocol'];before=digest(pool)
    default=c.daily_projection(pool,predictions,day,protocol,synthetic_only=True,risk_events=risk)
    shadow=c.daily_projection(pool,predictions,day,protocol,synthetic_only=True,tie_break_enabled=True,risk_events=risk);c.verify_shadow(pool,shadow,risk)
    real=c.daily_projection(pool,{},day,protocol,risk_events=risk);c.require(digest(pool)==before,'PRIORITY_V1_MUTATION')
    with psycopg.connect(DSN,autocommit=True) as pg:
        ledger=Ledger(pg);fixture_id=c.logical(shadow)
        with pg.transaction():ledger.put('priority_projection',fixture_id,shadow)
        try:
            with pg.transaction():ledger.put('priority_projection','E5_FAILURE_ATOMICITY:'+cp['logical_digest'],dict(status='UNACCEPTED'));raise ValueError('E5_INJECTED_PRIORITY_FAILURE')
        except ValueError:pass
        c.require(ledger.get('priority_projection','E5_FAILURE_ATOMICITY:'+cp['logical_digest']) is None,'HALF_PRIORITY_ACTIVATION')
        existing=digest(ledger.rows('predictions'));model=ledger.rows('models')[0];key=c.permission_key(model,'SHADOW_INFERENCE');grant_id=c.logical(key)
        before_activation=ledger.inventory()
        try:ledger.cas(grant_id,'E5_FAILED_REVOKE:'+cp['logical_digest'],1,'REVOKE',now(),fail_after_receipt=True)
        except ValueError:pass
        c.require(ledger.inventory()==before_activation and ledger.allowed(model['model_id'],key,now()),'PARTIAL_ACTIVATION')
        revoked=ledger.rollback(model['model_id'],'E5_ROLLBACK:'+cp['logical_digest'],now())
        c.require(not ledger.allowed(model['model_id'],key,now()) and digest(ledger.rows('predictions'))==existing,'ROLLBACK_HISTORY')
        emit('DAILY_PRIORITY_CAPABILITY_READBACK',dict(status='PASS_ENGINEERING_FIXTURE_REAL_DISABLED',FEP_STOCK_DAILY_CORE='NOT_ENABLED_NO_ACCEPTED_DAILY_SCOPE',
            REAL_PRIORITY_SHADOW='NOT_GRANTED',synthetic_only=True,fixture_id=fixture_id,fixture=shadow,default_disabled_fixture=default,real_daily_readback=real,API=ExpectancyReadAPI(ledger,now()).priority(fixture_id)))
        emit('ROLLBACK_DRILL',dict(status='PASS_INDEPENDENT_FEP_ROLLBACK_AND_ATOMICITY',receipt=revoked,prediction_history_digest_before=existing,
            prediction_history_digest_after=digest(ledger.rows('predictions')),permission_revoked=True,failed_activation_receipt_absent=True,
            failed_priority_row_absent=True,Core_unaffected=True,PRIORITY_V1_digest_before=before,PRIORITY_V1_digest_after=digest(pool),
            default_API_after_rollback=ExpectancyReadAPI(ledger,now()).priority(),counts=ledger.inventory()))
    emit('PRIORITY_V1_PROTECTED_READBACK',dict(status='PASS_FULL_POOL_AND_SOURCE_PROTECTION',source_bindings=cp['priority_bindings'],fixture_V1=pool,
        original_pool_digest=before,shadow_preserves_risk_events=True,tie_break_default=False,rank_eligibility_feedback=False))
    print('fixture, API and rollback drills PASS; real daily NOT_ENABLED',flush=True)

def tests():
    from scripts import run_fep_e2_r1 as runner
    runner.REPORT=REPORT;runner.BASE=BASE;env=os.environ.copy()
    env.update(PYTHONPATH='E:/codex_tmp/fep_e3_deps'+os.pathsep+str(ROOT)+os.pathsep+str(ROOT/'src'),TEMP='E:/codex_tmp/test_temp',TMP='E:/codex_tmp/test_temp',
        WORKBENCH_PG_DSN=DSN,FEP_E1_TEST_DSN=DSN,FEP_E5_TEST_DSN=DSN,OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2')
    runner.execute([sys.executable,'-B','-m','pytest','tests/fep_e5','tests/fep_e4','tests/fep_e3','tests/fep_e2','tests/fep','tests/test_r20d_settlement.py',
        'tests/test_r25_packet.py::test_actual_authority_inventory_waits_without_target','-q','--basetemp=E:/codex_tmp/test_temp/e5-targeted',
        '--junitxml='+str(REPORT/'targeted.xml')],env,'targeted')
    if sys.argv[2:]==['targeted-only']:return
    prior=load(ROOT/'reports/fep_e4_r1/SCOPED_REGRESSION_SUMMARY.json');command=[v for v in prior['command'] if not v.startswith(('--basetemp=','--junitxml='))]
    command[0]=sys.executable;command+=['tests/fep_e5','--basetemp=E:/codex_tmp/test_temp/e5-scoped','--junitxml='+str(REPORT/'scoped.xml')]
    runner.execute(command,env,'scoped',prior['failed_nodes'])

def finalize():
    cp=contract();targeted=load(REPORT/'TARGETED_SUMMARY.json');scoped=load(REPORT/'SCOPED_REGRESSION_SUMMARY.json');prior=load(ROOT/'reports/fep_e4_r1/SCOPED_REGRESSION_SUMMARY.json')
    c.exact(sorted(scoped['failed_nodes']),sorted(prior['failed_nodes']),'KNOWN_DEBT_IDENTITY')
    c.exact([v for v in scoped['command'] if v.startswith('--deselect=')],[v for v in prior['command'] if v.startswith('--deselect=')],'PRIOR_EXCLUSIONS')
    negatives=[dict(node=t.attrib['classname']+'::'+t.attrib['name'],status='PASS' if all(t.find(k) is None for k in ('failure','error','skipped')) else 'FAIL')
        for t in ET.parse(REPORT/'targeted.xml').findall('.//testcase') if 'test_e5' in t.attrib['classname']]
    emit('NEGATIVE_MATRIX',dict(status='PASS' if len(negatives)>=30 and all(t['status']=='PASS' for t in negatives) else 'FAIL',count=len(negatives),cases=negatives,synthetic_test_vectors_only=True))
    guard=protected(ROOT);wait=selection(ROOT);c.require(not guard['historical_git_diff'] and wait['status']=='WAIT_ACCEPTED_DAILY_INPUT','PROTECTED_CORE')
    database={}
    for port,name in [(55488,'fep_e1_fresh'),(55489,'fep_e1_upgrade')]:
        with psycopg.connect(f'host=127.0.0.1 port={port} user=fep_e1_admin dbname={name}',autocommit=True) as pg:
            tables=[r[0] for r in pg.execute("select tablename from pg_tables where schemaname='fep' order by tablename")]
            counts={t:pg.execute(sql.SQL('select count(*) from fep.{}').format(sql.Identifier(t))).fetchone()[0] for t in tables}
            c.require(len(counts)==33 and not any(counts.values()),'E1_FEP_DATABASE_MUTATION');database[name]=counts
    with psycopg.connect(DSN,autocommit=True) as pg:
        ledger=Ledger(pg);inventory=ledger.inventory();dump={t:ledger.rows(t) for t in TABLES};emit('POSTGRES_LEDGER_EXPORT',dict(namespace=cp['namespace'],tables=dump,logical_digest=digest(dump)))
        slots=dump['prediction_slots'];receipts=dump['slot_receipts'];c.require(len(slots)==616 and len(dump['predictions'])==615,'PREDICTION_DENOMINATOR')
        c.require({r['slot_id'] for r in slots}=={r['slot_id'] for r in receipts},'MISSING_SLOT_RECEIPT')
        c.require(all(h['action']=='REVOKE' for h in dump['deployment_heads']),'FEP_HEAD_NOT_ROLLED_BACK')
    gates=('PREDICTION_SLOT_LEDGER','PREDICTION_BINDING_READBACK','ENTRY_PROJECTION_READBACK','DAILY_PRIORITY_CAPABILITY_READBACK','PRIORITY_V1_PROTECTED_READBACK','PERMISSION_MATRIX','ROLLBACK_DRILL','API_READBACK','PROJECTION_PERSISTENCE_GATE','NEGATIVE_MATRIX')
    ready=not targeted['failed_nodes'] and not scoped['introduced_active_failures'] and all(load(REPORT/(g+'.json'))['status'].startswith('PASS') for g in gates)
    disposition=c.engineering_disposition(dict(contract=ready,protected=True,entry_ledger_api_rollback=ready,daily_fail_closed=ready));status='PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT' if ready else 'BLOCKED_ENGINEERING'
    emit('INDEPENDENT_AUDIT_ITEMS',dict(items=[dict(audit_id='AUDIT_NOTE_E4_01',status='SATISFIED_FOR_E5_ENGINEERING_PROTOCOL_LOCAL_PENDING_EXTERNAL_AUDIT',
        scope='Seven explicit pre-projection disposition/metric/tie/promotion/priority/shadow/evidence fields frozen; effectiveness evaluation remains closed',evidence=[binding(REPORT/'PROTOCOL_FREEZE.json')],acceptance='Independent E5 audit, no retroactive E4 edit'),
        dict(audit_id='FEP_E5_ENGINEERING_NAMESPACE_AND_DAILY_EVIDENCE',status='OPEN_EXTERNAL_REVIEW',scope='Independent isolated PostgreSQL namespace; not a production migration or real Daily grant. Low upstream coverage, weak calibration and joint OOD limitations remain.',
        evidence=[binding(REPORT/'PROJECTION_PERSISTENCE_GATE.json'),binding(REPORT/'FUTURE_PRIORITY_OOS_PROTOCOL_STUB.json')],acceptance='Separate authorized real Daily/OOS/production protocol')]))
    state=dict(V4_15E5_ENGINEERING=status,E5_EFFECTIVENESS_EVALUATION='CLOSED_ENGINEERING_ONLY',disposition=disposition,
        ENTRY_PROJECTION_ENGINEERING='PASS' if ready else 'BLOCKED',PREDICTION_LEDGER='PASS' if ready else 'BLOCKED',MODEL_EVIDENCE_BINDING='PASS' if ready else 'BLOCKED',
        API_READBACK='PASS' if ready else 'BLOCKED',PRIORITY_SHADOW_ENGINE='PASS_ENGINEERING' if ready else 'BLOCKED',ENTRY_DAILY_SEPARATION='PASS',PERMISSION_GOVERNANCE='PASS',ROLLBACK='PASS',PRIORITY_V1_PROTECTED='PASS',
        FEP_STOCK_DAILY_CORE='NOT_ENABLED_NO_ACCEPTED_DAILY_SCOPE',REAL_DAILY_PRIORITY_SHADOW='NOT_GRANTED',REAL_PRIORITY_SHADOW='NOT_GRANTED',
        PRIORITY_USE='UNGRANTED',MODEL_DISPLAY='UNGRANTED',FEP_PRODUCTION='UNGRANTED',REAL_OOS='NOT_GRANTED',FIRST_OBSERVED='NOT_GRANTED',CHAMPION=False,
        production=False,shadow=False,focus=False,new_model_training=0,new_hyperparameter_search=0,new_label_resolution=0,new_E4_trial=0,TDX='UNTOUCHED',BaoStock='NOT_REQUIRED',
        known_debt_nodes=scoped['failed_nodes'],introduced_active_failures=scoped['introduced_active_failures'],repository_all_green=False,GitHub_CI='NO_RUN_NO_STATUS_NOT_USED_AS_EVIDENCE',
        NEXT='STOP_WAIT_V4_15E5_INDEPENDENT_EXTERNAL_AUDIT')
    emit('FINAL_EXIT_READBACK',dict(state=state,gates={g:load(REPORT/(g+'.json'))['status'] for g in gates},protected_heads=guard,R25=wait,
        formal_fep_tables=database,engineering_namespace_inventory=inventory,checkpoints_completed=['protocol','upstream','slots','bindings','runs','projection','fixture','permission','rollback','regression','seal']))
    summary=f'''# V4-15E5 R1 completion\n\nStatus: {status}. Parent/base: {BASE}. Engineering disposition: {disposition}.\n\nFrozen seven machine-readable governance fields before projection. E2 is primary engineering source; E3/E4 are separate diagnostic namespaces, no champion. No model fit, hyperparameter search, label resolution or E4 trial. Exact accepted E2 L1 statistics and exact E3/E4 portable model artifacts consumed; old embedded snapshots adapted with complete byte lineage, no current-head rebuild.\n\nBounded historical ENTRY batch: all 205 rows in the exact pre-existing E3 historical ledger, three model namespaces, 615 projections plus one planned optional no-model slot with receipt. This is not a new evaluation or full E2 population prediction. Unknown/rejected records remain stored. Source knowledge and engineering activation clocks are actual UTC; historical observations never become FIRST_OBSERVED. ENTRY thresholds NOT_FROZEN, diagnostic joint OOD UNSET and calibration limitations retained.\n\nPostgreSQL fep_e5_engineering is an explicit isolated engineering namespace, not a production migration; prior 33-table fep schemas remain empty. Append-only facts, composite identity FKs, fixed slot binding, exact six-part SHADOW permission, transactional acceptance and head CAS, immutable first accepted view and retained rollback history implemented. Both activation-head failure and prediction-persisted/priority-failure drills pass.\n\nRead-only HTTP adapter is explicitly injected and remains unmounted in the production app. Default responses reveal no model axes; diagnostic requests require exact SHADOW permission and immutable context. Today ENTRY reuse and real Daily priority remain disabled.\n\nSynthetic full pool: seven rows, six eligible, three covered; missing prediction/model and OOD rows retained. Exact V1 layer tie-break is off by default, enabled only for fixture. Risk/invalidation/high-extension events and all V1 ranks/eligibility/source hashes preserved. No opaque total score. Real DAILY remains NOT_ENABLED_NO_ACCEPTED_DAILY_SCOPE.\n\nTargeted: {targeted['passed']} passed, {targeted['skipped']} skipped, {len(targeted['failed_nodes'])} failed. Scoped: {scoped['passed']} passed, {scoped['skipped']} skipped, {len(scoped['failed_nodes'])} exact existing debt failures, {len(scoped['introduced_active_failures'])} introduced active failures; two prior exclusions retained. Repository not all green; archived pytest evidence is not a GitHub CI claim.\n\nFuture Priority OOS stub NOT_ACTIVE/NOT_EVALUATED, all dimensions UNSET; cannot open evaluation. CHAMPION, MODEL_DISPLAY, PRIORITY_USE, real Daily shadow, REAL_OOS, FIRST_OBSERVED and production remain ungranted.\n\nReproduction: exact E3 pinned E:/codex_tmp/fep_e3_deps runtime; explicit isolated PostgreSQL on localhost ports 55488/55489. Check out base and run prepare → project → drills → tests → finalize with E-only temporary roots. DB export preserves the engineering evidence; no default or production DSN.\n\nNext: STOP_WAIT_V4_15E5_INDEPENDENT_EXTERNAL_AUDIT. Commit/push is not independent acceptance.\n'''
    write(REPORT/'COMPLETION_REPORT.md',summary.encode())
    changed=CODE+['tests/fep_e5/test_e5_contract.py','config/fep_e5_projection_priority_protocol_v1.json','config/fep_e5_model_evidence_class_v1.json']
    emit('CHANGED_FILE_LIST',dict(code_config_tests=changed,evidence_directory=REPORT.relative_to(ROOT).as_posix(),parent=BASE))
    seal=dict(stage='V4-15E5.R1',baseline=BASE,status=status,state=state,code_bindings=[binding(ROOT/path) for path in changed],
        evidence_bindings=[binding(path) for path in sorted(REPORT.iterdir()) if path.is_file() and path.name!='FEP_E5_R1_CANDIDATE_SEAL.json'],sealed_at=now(),external_acceptance=False)
    seal['logical_digest']=digest(seal);emit('FEP_E5_R1_CANDIDATE_SEAL',seal);print(status,flush=True)

if __name__=='__main__':globals()[sys.argv[1]]()
