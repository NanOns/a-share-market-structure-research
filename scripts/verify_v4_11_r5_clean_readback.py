"""R5 clean independent sealed-source replay; baseline collection limits explicit."""
from scripts.next_round_execution_r5 import *
from scripts.verify_v4_11_r5_capability_closure import bound
from src.v4.confirmation_d2_candidate_r5 import verify_candidate_d2_publication
from src.v4.confirmation_events_candidate_r5 import event_unknown_reasons,events
from src.v4.confirmation import digest
import subprocess,sys,json,os,tempfile,re

def verify_r5():
    verify_protected()
    seal=read('reports/v4_11_r5a/R5A_SEALED_OWNER_PRODUCER_SET.json')
    parity=bound(seal['parity']);owner_oracle=bound(seal['independent_oracle'])
    if not seal['sealed'] or parity['status']!='PASS' or parity['business_mismatches'] or owner_oracle['formal_t_minus_1_known_count']:raise ValueError('CLEAN_R5A_OWNER_PARITY_SEAL_REQUIRED')
    bound(seal['contract'])
    d2=read('reports/v4_11_r5/V4_11_R5_D2_READBACK.json');er=read('reports/v4_11_r5/V4_11_R5_EVENT_REPLAY.json')
    current=bound(d2['current']);prior=bound(d2['prior']);rows=verify_candidate_d2_publication(current,producer_set=d2['source_set']);verify_candidate_d2_publication(prior,producer_set=d2['source_set'])
    frozen=bound(er['frozen_prior']);actual=bound(er['events'])
    if frozen['source_binding']!=prior or frozen['rows']!=prior['rows']:raise ValueError('CLEAN_R5_EXACT_FROZEN_PRIOR_REQUIRED')
    revised=events(current,frozen,revision_of=current['publication_id']);old={r['entity_id']:r for r in prior['rows']};new={r['entity_id']:r for r in rows}
    for event,revision in zip(actual,revised):
        reasons=event_unknown_reasons(new[event['entity_id']],old.get(event['entity_id']))
        if reasons!=event['event_unknown_predicates'] or event['effective_event']!=('UNKNOWN' if reasons else event['primary_event']):raise ValueError('CLEAN_R5_EVENT_UNKNOWN_SAFETY')
        if any(event[k]!=revision[k] for k in ('event_types','primary_event','prior_session_state_head_digest')):raise ValueError('CLEAN_R5_EVENT_REVISION_INVARIANCE')
    oracle=read('reports/v4_11_r5/INDEPENDENT_D2_OWNER_INPUT_ORACLE.json');bound(oracle['proof'])
    if oracle['status']!='PASS' or any(n!=10447 for n in oracle['counts'].values()):raise ValueError('CLEAN_R5_INDEPENDENT_OWNER_INPUT_ORACLE')
    attribution=read('reports/v4_11_r5/RESIDUAL_UNKNOWN_ATTRIBUTION.json')
    if any(attribution[k] for k in ('producer_wiring_missing','unsealed_helper_source','generic_coefficient_gate','raw_reconstruction_fallback','accepted_t_minus_1_known_count')):raise ValueError('CLEAN_R5_RESIDUAL_ATTRIBUTION')
    return dict(status='PASS_R5_EXACT_SEALED_OWNER_D2_REEXECUTION_EVENT_SAFETY',parity_rows=parity['row_scope'],owner_input_rows=oracle['rows'],current_rows=len(rows),prior_rows=len(prior['rows']),event_rows=len(actual),permissions=PERMISSIONS)

def full_repository_collection():
    with tempfile.TemporaryDirectory(prefix='v4_r4_collection_') as temporary:
        guard=Path(temporary)
        (guard/'sitecustomize.py').write_text("import sys,os\ndef forbid(event,args):\n if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):\n  path=os.fsdecode(args[0]).replace('\\\\','/').lower()\n  if path.endswith('config/.env') or path.endswith('/config.env'):raise RuntimeError('CONFIG_ENV_READ_FORBIDDEN_IN_R4_COLLECTION')\nsys.addaudithook(forbid)\n",encoding='utf8')
        env=os.environ.copy()
        for key in ('PGPASSWORD','PGSERVICE','PGSERVICEFILE','PGDATABASE','PGHOST','PGPORT','PGUSER','WORKBENCH_PG_DSN','V4_10_DISPOSABLE_TEST_DSN'):env.pop(key,None)
        env['PYTHONPATH']=str(guard)+os.pathsep+str(ROOT)+os.pathsep+str(ROOT/'src')
        r=subprocess.run([sys.executable,'-m','pytest','--collect-only','-q','tests'],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=120)
    text=r.stdout+'\n'+r.stderr
    prefix='reports/v4_11_r5/FULL_REPOSITORY_COLLECTION'
    atomic_bytes(prefix+'.log',text.encode('utf8'))
    unchanged=[]
    for path in ('tests/upgrade_m14/test_online_batches.py','src/workbench_online/collector.py','tests/upgrade_m2/test_api.py','src/workbench_service/app.py'):
        baseline=subprocess.check_output(['git','show','1dee36a:'+path],cwd=ROOT)
        if baseline.replace(b'\r\n',b'\n')!=(ROOT/path).read_bytes().replace(b'\r\n',b'\n'):raise ValueError('UNRELATED_M14_CHANGED')
        unchanged.append(bind(path))
    error_paths=re.findall(r'^ERROR (tests/\S+)',text,re.MULTILINE)
    expected_errors={'tests/upgrade_m14/test_online_batches.py','tests/upgrade_m2/test_api.py'}
    known=(r.returncode!=0 and "cannot import name '_commit_raw_and_batch'" in text and 'tests/upgrade_m14/test_online_batches.py' in error_paths and set(error_paths)<=expected_errors)
    if r.returncode and not known:raise ValueError('NEW_FULL_REPOSITORY_COLLECTION_ERROR:'+text[-5000:])
    result=dict(status='PREEXISTING_NON_MAINLINE_M14_M2_COLLECTION' if known else 'PASS',exit_code=r.returncode,collection_error_paths=error_paths,log=bind(prefix+'.log'),baseline='1dee36ae83fb63b6a7fe57e05ccb63bb1e0c5099',unchanged_baseline_sources=unchanged,reason='Existing M14 test imports removed persistence API; existing M2 test indexes an empty clean-repository publication_heads table in ignored local DuckDB. No missing data fabricated or production publication initialized; no new deselection.',separate_audit_items=['R5_FULL_REPOSITORY_PREEXISTING_M14_COLLECTION','R5_FULL_REPOSITORY_PREEXISTING_M2_UNTRACKED_PUBLICATION_DEPENDENCY'],full_repository_runtime_pass_claim=False if known else None,configured_or_production_database_used=False,legacy_duckdb_scope='EMPTY_IGNORED_DB_IN_DISPOSABLE_CLEAN_CHECKOUT_ONLY')
    write(prefix+'.json',result);return result
