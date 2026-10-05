"""Narrow immutable event-stratum successor to the audited R1R1 replay."""
from collections import Counter
import json,os,sys,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from scripts.build_fep_e2_r1r1_history import ROOT,binding,now
from workbench_analysis.fep_e1.contracts import atomic_json,digest
from workbench_analysis.fep_e1.feature_owner import verify_file
from workbench_analysis.fep_e2.historical_dataset import read_gzip,write_gzip,verify_stage_order,LINEAGE
from workbench_analysis.fep_e2.event_strata import event_observation,owner_gap,event_dataset,event_policy,event_baseline
from workbench_analysis.fep_e2.support import discover,BASE
from workbench_analysis.fep_e2.registry import register

REPORT=ROOT/'reports/fep_e2_r1r2';PRIOR=ROOT/'reports/fep_e2_r1r1';BASELINE='f8708c34063238547127cab4baefb17c2e5825ac'

def load(path):return json.loads(Path(path).read_bytes())
def emit(name,value):atomic_json(REPORT/(name+'.json'),value)

def prepare():
    REPORT.mkdir(parents=True,exist_ok=True)
    p=REPORT/'.gitattributes.tmp';p.write_bytes(b'* -text\n');p.replace(REPORT/'.gitattributes')
    names=['V4_FEP_EXECUTION_MASTER_V4_15E2_R1R2_REPAIR_20261005.md',
        'V4_15E2_R1R2_ENTRY_EVENT_STRATIFICATION_AND_OWNER_GAP_REPAIR_TASK_20261005.md',
        'V4_15E2_R1R1_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md']
    for name in names:
        p=REPORT/(name+'.tmp');p.write_bytes((Path('D:/Users/lps/Desktop/阶段任务')/name).read_bytes());p.replace(REPORT/name)
    if subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()!=BASELINE:raise ValueError('E2R1R2_BASELINE')
    prior=load(PRIOR/'FEP_E2_R1R1_CANDIDATE_SEAL.json')
    for b in prior['code_bindings']+prior['evidence_bindings']:verify_file(ROOT,b)
    emit('ENTRY_BASELINE',dict(stage='V4-15E2.R1R2',baseline=BASELINE,entered_at=now(),authority=[binding(REPORT/n) for n in names],
        next='STOP_WAIT_V4_15E2_R1R2_INDEPENDENT_EXTERNAL_AUDIT'))
    emit('R1R1_PASS_KEEP_READBACK',dict(status='PASS_KEEP',predecessor_seal=binding(PRIOR/'FEP_E2_R1R1_CANDIDATE_SEAL.json'),
        bindings=prior['code_bindings']+prior['evidence_bindings'],immutable=True))
    emit('ENTRY_EVENT_STRATA_CONTRACT',dict(contract_id='FEP_E2_ENTRY_EVENT_STRATA_V1_1',
        observation_scope='FEP_STOCK_ENTRY_CORE',formal_signals=['FIRST_PREWATCH','NEW_CONFIRMED','REENTRY'],umbrella_only='ENTRY',
        observation_identity='Exact V4-15 enrollment identity: logical event + reconstructed cohort namespace',
        first_prewatch='Accepted Radar ENROLLED + maturity PREWATCH + no parent episode; initial SEED upgrade is not an ENROLLED event',
        completeness='Every entity/date from frozen R1R1 scan; FULL_OWNER_EVALUATION required before any first episode',
        no_prior_owner_fabrication=True,heuristic='ENGINEERING_SUPPORT_HEURISTIC',lineage=LINEAGE,
        window=binding(PRIOR/'HISTORICAL_WINDOW_FREEZE.json'),frozen_at=now()))

def population():
    from src.v4.confirmation_d2_candidate_r5 import candidate_policy
    gap=candidate_policy()['fields']['frozen_invalidation']
    owner_status={s:owner_gap(s,gap) for s in ('NEW_CONFIRMED','REENTRY')}
    manifest=load(PRIOR/'HISTORICAL_OBSERVATION_POPULATION.json');proofs=[];ledger_receipts=[];events=[];counts=Counter();first_episodes=Counter()
    for n,receipt in enumerate(manifest['receipts']):
        sid=receipt['entity_id'];states=list(read_gzip(PRIOR/'state_scan'/(sid+'.jsonl.gz')))
        if len(states)!=536 or [r['date_ordinal'] for r in states]!=list(range(250,786)):raise ValueError('E2_EVENT_INCOMPLETE_DAILY_SCAN')
        for directory,key in [('state_scan','state_scan_sha256'),('owner_records','bundle_sha256'),('population','population_sha256')]:
            if binding(PRIOR/directory/(sid+'.jsonl.gz'))['sha256']!=receipt[key]:raise ValueError('E2_EVENT_SOURCE_RECEIPT')
        records={r['record_id']:r for r in read_gzip(PRIOR/'owner_records'/(sid+'.jsonl.gz'))}
        def resolve(ref):
            record=records[ref['record_id']]
            if digest(record['payload'])!=ref['sha256'] or record['sha256']!=ref['sha256']:raise ValueError('E2_EVENT_OWNER_RECORD')
            return record['payload']
        labels=list(read_gzip(PRIOR/'labels'/(sid+'.jsonl.gz')))
        enrolled_dates={r['trade_date'] for r in labels}
        prior_episode=None;potential=0;ledger=[];expected_first=set();first_episode=None
        for state in states:
            if not prior_episode:
                if state['upstream_derivation']!='FULL_OWNER_EVALUATION':raise ValueError('E2_FIRST_EPISODE_INPUT_SUPPRESSED')
                if state['episode_id'] and first_episode is None:
                    first_episode=state['episode_id'];first_episodes[state['maturity']]+=1
                if 'ENROLLED' in state['transition_reasons'] and state['maturity']=='PREWATCH' and state['eligibility']=='TRUE':
                    expected_first.add((state['trade_date'],state['episode_id']))
            if state['upstream_derivation']=='NOT_EVALUATED_REQUIRED_UPSTREAM_INCOMPLETE':
                potential+=1
                for signal in ('NEW_CONFIRMED','REENTRY'):
                    ledger.append(dict(entity_id=sid,trade_date=state['trade_date'],episode_id=state['episode_id'],
                        signal_type=signal,status='OWNER_REQUIRED_INPUT_UNAVAILABLE',candidate_semantics='Blocked transition opportunity, NOT an observed event',
                        source_state_publication=state['publication_id'],source_state_digest=state['state_digest'],
                        frozen_invalidation='UNKNOWN',**LINEAGE))
                    counts[signal+'_OWNER_INPUT_UNAVAILABLE']+=1
            elif state['trade_date'] not in enrolled_dates:
                status='INITIAL_CONFIRMED_EVENT_NOT_ENROLLED' if (
                    not prior_episode and state['episode_id'] and state['maturity']=='CONFIRMED') else 'DAILY_STATE_NO_ADMITTED_EVENT'
                ledger.append(dict(entity_id=sid,trade_date=state['trade_date'],episode_id=state['episode_id'],
                    signal_type='NEW_CONFIRMED' if status.startswith('INITIAL_CONFIRMED') else 'DIAGNOSTIC_DAILY_STATE',
                    status=status,eligibility=state['eligibility'],maturity=state['maturity'],
                    unknown_predicates=state['unknown_predicates'],transition_reasons=state['transition_reasons'],
                    source_state_publication=state['publication_id'],source_state_digest=state['state_digest'],**LINEAGE))
                counts[status]+=1
            prior_episode=state['episode_id']
        actual_first=set()
        for row in labels:
            enrollment=resolve(row['enrollment_ref']);event=records['logical_event:'+enrollment['logical_event_id']]['payload']
            state=resolve(row['source_state_ref'])['owner_output']
            successor=event_observation(row,enrollment,event,state)
            if successor['signal_type']=='FIRST_PREWATCH':
                actual_first.add((row['trade_date'],row['episode_key']));events.append(successor)
                status='FIRST_PREWATCH_ADMITTED' if row['training_allowed_engineering_only'] else row['outcome_status']
            else:
                status='NEW_CONFIRMED_EXACT_INITIAL_EVENT_DIAGNOSTIC_ONLY'
                # The original scan emits these before a prior episode. Retain
                # exact owner facts without granting an unclosed stratum policy.
                counts['NEW_CONFIRMED_EXACT_INITIAL_EVENT_DIAGNOSTIC_ONLY']+=1
            counts[status]+=int(status!='NEW_CONFIRMED_EXACT_INITIAL_EVENT_DIAGNOSTIC_ONLY')
            right_censored=row['label_end_ordinal']>785
            counts['RIGHT_CENSORED']+=int(right_censored)
            ledger.append(dict(entity_id=sid,trade_date=row['trade_date'],episode_id=row['episode_key'],
                observation_id=successor['observation_id'],signal_type=successor['signal_type'],status=status,
                label_status=row['outcome_status'],right_censored=right_censored,
                outcome_ref=row['outcome_ref'],source_state_publication=state['publication_id'],**LINEAGE))
        if actual_first!=expected_first:raise ValueError('E2_FIRST_PREWATCH_DENOMINATOR_INCOMPLETE')
        sha=write_gzip(REPORT/'denominator_ledger'/(sid+'.jsonl.gz'),ledger)
        ledger_receipts.append(dict(entity_id=sid,rows=len(ledger),sha256=sha))
        proofs.append(dict(entity_id=sid,dates=len(states),first_prewatch=len(actual_first),first_episode=first_episode,
            blocked_transition_dates=potential,state_receipt=receipt['state_scan_sha256']))
        if n%500==0:print('stratification',n,flush=True)
    pred=next(read_gzip(PRIOR/'HISTORICAL_E1_E2_DATASET.json.gz'));byid={r['observation_id']:r for r in pred['denominator']}
    for row in events:
        original=byid[row['observation_id']]
        for k in ('status','selected_label_revision','selected_label_digest','entity_type','observation_scope','target','horizon','feature_variant','label_quality_policy','contract_versions'):
            row[k]=original[k]
    dataset=event_dataset(pred,events)
    frozen_gate=load(REPORT/'FIRST_PREWATCH_POPULATION_GATE.json') if (REPORT/'FIRST_PREWATCH_POPULATION_GATE.json').exists() else None
    if frozen_gate and frozen_gate['dataset_digest']!=dataset['digest']:raise ValueError('E2_EVENT_FROZEN_DATASET_CHANGED')
    write_gzip(REPORT/'FIRST_PREWATCH_E2_DATASET.json.gz',[dataset])
    dataset_at=frozen_gate['sealed_at'] if frozen_gate else now()
    emit('FIRST_PREWATCH_POPULATION_GATE',dict(status='PASS_COMPLETE_ACCEPTED_EVENT_STRATUM',entities=len(proofs),
        date_entity_states=sum(p['dates'] for p in proofs),rows=len(events),eligible=len(dataset['rows']),proofs=proofs,
        first_episode_maturity_counts=dict(first_episodes),all_pre_episode_dates_full_owner_evaluation=True,
        accepted_first_event_predicate='Radar ENROLLED/PREWATCH/no parent episode',
        later_episode_events='REENTRY NOT_ENABLED; not FIRST_PREWATCH',no_outcome_selection=True,
        dataset=binding(REPORT/'FIRST_PREWATCH_E2_DATASET.json.gz'),dataset_digest=dataset['digest'],sealed_at=dataset_at))
    emit('NEW_CONFIRMED_POPULATION_GATE',dict(status='UNSET_DIAGNOSTIC_ONLY',exact_initial_events=counts['NEW_CONFIRMED_EXACT_INITIAL_EVENT_DIAGNOSTIC_ONLY'],
        admitted=0,affected_prior_episode_input=owner_status['NEW_CONFIRMED'],
        reason='Exact initial owner events retained separately; full NEW_CONFIRMED stratum owner closure and independent policy NOT_ADMITTED'))
    emit('REENTRY_OWNER_INPUT_GATE',dict(owner_status['REENTRY'],accepted_input_contract=binding('config/v4_10_input_provenance_r1_2.json'),admitted=0))
    emit('EVENT_DENOMINATOR_LEDGER',dict(status='PASS_COMPLETE_EVENT_AND_BLOCKED_OPPORTUNITY_ACCOUNTING',counts=dict(counts),receipts=ledger_receipts,
        states_scanned=manifest['state_rows'],blocked_opportunities_are_not_observed_events=True,
        missing_categories={k:counts.get(k,0) for k in ('PENDING','RIGHT_CENSORED','NEW_CONFIRMED_ADMITTED','REENTRY_ADMITTED')},
        exact_source_population=binding(PRIOR/'HISTORICAL_OBSERVATION_POPULATION.json')))
    emit('POOLED_BASELINE_SUPERSESSION',dict(status='SUPERSEDED_DIAGNOSTIC_ONLY',reason=['pooled event estimand','incomplete prior-episode owner capability'],
        baseline=binding(PRIOR/'CONDITIONAL_BASELINE_GATE.json'),policy=binding('config/fep_e2_support_policy_registry_v1.json'),
        may_feed_E3=False,old_artifacts_preserved=True,successor_signal='FIRST_PREWATCH'))

def statistics():
    if (REPORT/'STATISTICS_PHASE_START.json').exists():raise ValueError('E2_EVENT_POLICY_ALREADY_FROZEN_REUSE_FOR_READBACK_ONLY')
    dataset=next(read_gzip(REPORT/'FIRST_PREWATCH_E2_DATASET.json.gz'));gate=load(REPORT/'FIRST_PREWATCH_POPULATION_GATE.json')
    discovered=discover(dataset['denominator'],dataset['rows']);discovery_at=now()
    emit('SUPPORT_POLICY_DISCOVERY_FIRST_PREWATCH_T1',dict(discovery=discovered,sealed_at=discovery_at,dataset_digest=dataset['digest'],
        numeric_outcomes_consumed=False,pooled_thresholds_reused=False))
    query={k:dataset['denominator'][0][k] for k in BASE};query.update(regime='UNAVAILABLE',trend='UNAVAILABLE',position='UNAVAILABLE',risk='UNAVAILABLE')
    policy_at=now();app=dict({k:query[k] for k in BASE},target_kind='CONTINUOUS');policy=event_policy(discovered,app,policy_at)
    policies=[policy]
    for signal in ('NEW_CONFIRMED','REENTRY'):
        policies.append(dict(policy_id='UNSET:'+signal,applicability=dict(app,signal_type=signal),status='UNSET_DIAGNOSTIC_ONLY',
            values={k:'UNSET' for k in policy['values']},required_classes=[],freeze_before_statistics_at=policy_at,
            reason='OWNER_REQUIRED_INPUT_UNAVAILABLE_OR_STRATUM_NOT_ADMITTED'))
    registry=dict(contract_id='FEP_E2_SUPPORT_POLICY_REGISTRY_V1_1',version='1.1.0',policies=policies,
        predecessor=binding('config/fep_e2_support_policy_registry_v1.json'),pooled_disposition=binding(REPORT/'POOLED_BASELINE_SUPERSESSION.json'),
        default='UNSET_NOT_EVALUABLE',disabled_signals=['ENTRY'],disabled_targets='All except FIRST_PREWATCH ABS_RETURN_N:T1',frozen_at=policy_at)
    atomic_json(ROOT/'config/fep_e2_support_policy_registry_v1_1.json',registry)
    emit('SUPPORT_POLICY_REGISTRY_FREEZE',dict(status='FROZEN_EVENT_SCOPED',frozen_at=policy_at,registry=binding('config/fep_e2_support_policy_registry_v1_1.json'),
        dataset_digest=dataset['digest'],policy_digest=digest(policy),statistics_started=False))
    stats_at=now();verify_stage_order(gate['sealed_at'],discovery_at,policy_at,stats_at)
    emit('STATISTICS_PHASE_START',dict(started_at=stats_at,policy_digest=digest(policy)))
    method=load(ROOT/'config/fep_conditional_statistics_contract_v1.json')
    result=event_baseline(dataset,query,policy,method,stats_at);path=register(REPORT/'registry',result)
    rebuilt=event_baseline(dataset,query,policy,method,now())
    if rebuilt['logical_digest']!=result['logical_digest']:raise ValueError('E2_EVENT_DETERMINISM')
    emit('CONDITIONAL_BASELINE_FIRST_PREWATCH_T1',dict(status='PASS_ENGINEERING_CAPABILITY_SCOPED' if not result['diagnostic_only'] else 'BLOCKED',
        artifact=binding(path),logical_digest=result['logical_digest'],rebuilt_logical_digest=rebuilt['logical_digest'],
        signal_type='FIRST_PREWATCH',selected_level=result['selected_level'],support_state=result['support_state'],
        counts=result['counts'],denominator=result['denominator_summary'],statistics=result['statistics'],backoff_trace=result['backoff_trace']))
    emit('SUPPORT_POLICY_SCOPE_GATE',dict(status='PASS_EXACT_EVENT_APPLICABILITY',admitted=['FIRST_PREWATCH:T1'],
        other_signals='UNSET_NOT_ENABLED',pooled_ENTRY='REJECTED',registry=binding('config/fep_e2_support_policy_registry_v1_1.json')))

def tests():
    from scripts import run_fep_e2_r1 as runner
    runner.REPORT=REPORT;runner.BASE=BASELINE;env=os.environ.copy()
    env.update(PYTHONPATH=str(ROOT)+os.pathsep+str(ROOT/'src'),TEMP='E:/codex_tmp/test_temp',TMP='E:/codex_tmp/test_temp',
        WORKBENCH_PG_DSN='host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh',
        FEP_E1_TEST_DSN='host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh')
    runner.execute([sys.executable,'-B','-m','pytest','tests/fep_e2','tests/fep',
        'tests/test_r25_packet.py::test_actual_authority_inventory_waits_without_target','tests/test_r20d_settlement.py',
        '-q','--basetemp=E:/codex_tmp/test_temp/e2-r1r2-targeted','--junitxml='+str(REPORT/'targeted.xml')],env,'targeted')
    if sys.argv[2:]==['targeted-only']:return
    prior=load(PRIOR/'SCOPED_REGRESSION_SUMMARY.json')
    command=[c for c in prior['command'] if not c.startswith(('--basetemp=','--junitxml='))];command[0]=sys.executable
    command+=['--basetemp=E:/codex_tmp/test_temp/e2-r1r2-scoped','--junitxml='+str(REPORT/'scoped.xml')]
    runner.execute(command,env,'scoped',prior['failed_nodes'])

def finalize():
    predecessor=load(PRIOR/'FEP_E2_R1R1_CANDIDATE_SEAL.json')
    for ref in predecessor['code_bindings']+predecessor['evidence_bindings']:verify_file(ROOT,ref)
    contract=load(ROOT/'config/fep_e2_historical_dataset_contract_v1.json')
    for ref in [*contract['source_bindings'].values(),*contract['owner_runtime_bindings'],*contract['parameter_bindings']]:verify_file(ROOT,ref)
    ledger=load(REPORT/'EVENT_DENOMINATOR_LEDGER.json')
    for receipt in ledger['receipts']:
        if binding(REPORT/'denominator_ledger'/(receipt['entity_id']+'.jsonl.gz'))['sha256']!=receipt['sha256']:
            raise ValueError('E2_EVENT_LEDGER_RECEIPT')
    import psycopg
    from psycopg import sql
    with psycopg.connect('host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh') as db:
        tables=[r[0] for r in db.execute("select tablename from pg_tables where schemaname='fep' order by tablename")]
        table_counts={t:db.execute(sql.SQL('select count(*) from fep.{}').format(sql.Identifier(t))).fetchone()[0] for t in tables}
    if len(table_counts)!=33 or any(table_counts.values()):raise ValueError('E2_EVENT_E1_DB_ISOLATION')
    # One ledger record per reconstructed date, except the blocked state has
    # separate NEW_CONFIRMED and REENTRY opportunities. RIGHT_CENSORED is a flag.
    covered_states=sum(r['rows'] for r in ledger['receipts'])-ledger['counts']['REENTRY_OWNER_INPUT_UNAVAILABLE']
    if covered_states!=ledger['states_scanned']:raise ValueError('E2_EVENT_DAILY_DENOMINATOR_COVERAGE')
    priority_paths=['config/research_priority.yaml','src/candidates/research_priority.py',
        'src/shadow_v2/research_priority.py','config/v4_09_priority_provenance_contract_r1_1.json']
    for path in priority_paths:
        if (ROOT/path).read_bytes()!=subprocess.check_output(['git','show',BASELINE+':'+path]):raise ValueError('E2_PRIORITY_MUTATION')
    pop_gate=load(REPORT/'FIRST_PREWATCH_POPULATION_GATE.json')
    discovery=load(REPORT/'SUPPORT_POLICY_DISCOVERY_FIRST_PREWATCH_T1.json')
    policy_freeze=load(REPORT/'SUPPORT_POLICY_REGISTRY_FREEZE.json')
    stats_start=load(REPORT/'STATISTICS_PHASE_START.json')
    verify_stage_order(pop_gate['sealed_at'],discovery['sealed_at'],policy_freeze['frozen_at'],stats_start['started_at'])
    verify_file(ROOT,pop_gate['dataset']);verify_file(ROOT,policy_freeze['registry'])
    prior_protected=load(PRIOR/'PROTECTED_STATE_READBACK.json')
    for ref in prior_protected['heads']:verify_file(ROOT,ref)
    from scripts.validate_r25_preflight import protected,selection
    emit('PROTECTED_STATE_READBACK',dict(status='PASS',heads=prior_protected['heads'],r25_protected=protected(ROOT),r25_selection=selection(ROOT),
        real_database_table_counts=table_counts,accepted_owner_sources_and_parameters_unchanged=True,ledger_receipts_verified=len(ledger['receipts']),
        priority_bindings=[binding(p) for p in priority_paths],stage_order='DATASET_DISCOVERY_POLICY_STATISTICS',
        daily_denominator_coverage=covered_states,
        E1_unchanged=True,PRIORITY_V1='UNCHANGED',real_FIRST_OBSERVED='NOT_GRANTED',real_matured='NOT_GRANTED',TDX='UNTOUCHED',
        model_engineering='NOT_STARTED',MODEL_DISPLAY='UNGRANTED',PRIORITY_USE='UNGRANTED',production=False,shadow=False,focus=False))
    targeted=load(REPORT/'TARGETED_SUMMARY.json');regression=load(REPORT/'SCOPED_REGRESSION_SUMMARY.json')
    cases=ET.parse(REPORT/'targeted.xml').findall('.//testcase');negatives=[dict(node=c.attrib['classname']+'::'+c.attrib['name'],
        status='PASS' if c.find('failure') is None and c.find('error') is None else 'FAIL') for c in cases if 'test_r1r2' in c.attrib['classname']]
    if len(negatives)<15 or any(c['status']!='PASS' for c in negatives):raise ValueError('E2_EVENT_NEGATIVES')
    emit('NEGATIVE_MATRIX',dict(status='PASS',case_count=len(negatives),cases=negatives,synthetic_vectors_are_tests_only=True))
    baseline=load(REPORT/'CONDITIONAL_BASELINE_FIRST_PREWATCH_T1.json');population=load(REPORT/'FIRST_PREWATCH_POPULATION_GATE.json')
    ready=not targeted['failed_nodes'] and not regression['introduced_active_failures'] and baseline['status']=='PASS_ENGINEERING_CAPABILITY_SCOPED'
    status='PASS_LOCAL_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT' if ready else 'BLOCKED'
    next_stage='STOP_WAIT_V4_15E2_R1R2_INDEPENDENT_EXTERNAL_AUDIT' if ready else 'STOP_WAIT_EXTERNAL_REPAIR_DISPOSITION'
    emit('LOCAL_ACCEPTANCE_MATRIX',dict(status=status,admitted_scope=['FIRST_PREWATCH:T1'] if ready else [],
        complete_first_prewatch=population['status'],support=baseline['support_state'],introduced_active_failures=regression['introduced_active_failures'],
        existing_debt_nodes=regression['failed_nodes'],external_acceptance=False,next=next_stage))
    emit('INDEPENDENT_AUDIT_ITEMS',dict(items=[dict(audit_id='FEP_E2_PRIOR_EPISODE_OWNER_CAPABILITY',status='OPEN_BLOCKS_AFFECTED_EVENT_STRATA',
        scope='Accepted frozen episode invalidation/closure input owner; REENTRY and affected NEW_CONFIRMED',
        evidence=[binding(REPORT/'REENTRY_OWNER_INPUT_GATE.json'),binding(REPORT/'EVENT_DENOMINATOR_LEDGER.json')],
        acceptance='Separate versioned owner-input audit; current FIRST_PREWATCH gate does not close this issue')]))
    text=f'''# V4-15E2 R1R2 completion\n\nStatus: {status}\n\nAdmitted event scope: FIRST_PREWATCH:T1 only. {population['rows']} owner events; {population['eligible']} eligible T1 labels. All 5337 entities and 2860632 daily states checked. The exact accepted first-event predicate is ENROLLED/PREWATCH/no parent episode; initial SEED-to-PREWATCH upgrades are not first enrollment events under the frozen Radar owner. No normal pre-episode evaluation is suppressed.\n\nL1 baseline: {baseline['support_state']}. Event-specific discovery and ENGINEERING_SUPPORT_HEURISTIC policy frozen before statistics; deterministic rebuild confirmed. Exact E1 selected revisions, feature replay, SettlementRuntime adapter and historical window remain unchanged. E1 event membership projection does not rebuild E1 or reselect revisions.\n\nNEW_CONFIRMED: UNSET_DIAGNOSTIC_ONLY; exact initial events retained separately, affected later transitions explicitly blocked. REENTRY: NOT_ENABLED_OWNER_INPUT_UNAVAILABLE. Blocked daily transition opportunities are ledger evidence, not invented observed events. No missing invalidation facts are fabricated. Old pooled ENTRY baseline/policy preserved byte for byte and SUPERSEDED_DIAGNOSTIC_ONLY.\n\nTargeted: {targeted['passed']} passed, {targeted['skipped']} skipped, {len(targeted['failed_nodes'])} failed. Scoped regression: {regression['passed']} passed, {regression['skipped']} skipped, {len(regression['failed_nodes'])} existing debt failures, {len(regression['introduced_active_failures'])} introduced active failures. Existing exclusions unchanged.\n\nProtected heads, E1, PRIORITY_V1 and R25 WAIT preserved. FIRST_OBSERVED/real training NOT_GRANTED; production/shadow/focus false; model engineering NOT_STARTED; display/priority UNGRANTED. E3 NOT_AUTHORIZED_UNTIL_EXTERNAL_AUDIT.\n\nNext: {next_stage}. Commit/push is local delivery, not external acceptance.\n'''
    tmp=REPORT/'COMPLETION_REPORT.md.tmp';tmp.write_bytes(text.encode());tmp.replace(REPORT/'COMPLETION_REPORT.md')
    code=['src/workbench_analysis/fep_e2/event_strata.py','scripts/run_fep_e2_r1r2.py','tests/fep_e2/test_r1r2_event_strata.py',
        'config/fep_e2_support_policy_registry_v1_1.json']
    seal=dict(stage='V4-15E2.R1R2',status=status,baseline=BASELINE,code_bindings=[binding(p) for p in code],
        evidence_bindings=[binding(p) for p in sorted(REPORT.iterdir()) if p.is_file() and p.name!='FEP_E2_R1R2_CANDIDATE_SEAL.json' and not p.name.endswith('.tmp')],
        admitted_event_scope=['FIRST_PREWATCH:T1'] if ready else [],pooled_ENTRY='SUPERSEDED_DIAGNOSTIC_ONLY',
        REENTRY='UNSET_OWNER_INPUT_NOT_AVAILABLE',NEW_CONFIRMED='UNSET_DIAGNOSTIC_ONLY',external_acceptance=False,
        E3='NOT_AUTHORIZED',production=False,shadow=False,MODEL_DISPLAY='UNGRANTED',PRIORITY_USE='UNGRANTED',next=next_stage,sealed_at=now())
    seal['logical_digest']=digest(seal);emit('FEP_E2_R1R2_CANDIDATE_SEAL',seal);print(status,flush=True)

if __name__=='__main__':globals()[sys.argv[1]]()
