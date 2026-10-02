"""Independent source/transition guards from sealed R4 evidence in clean checkout."""
from scripts.next_round_execution_r4 import *
from scripts.verify_v4_11_r4_capability_closure import gz
from src.v4.confirmation_d2_candidate_r4 import verify_candidate_d2_publication
from src.v4.confirmation_events_candidate_r4 import event_unknown_reasons,events
from src.v4.confirmation import digest
import subprocess,sys,json,os,tempfile,re

def verify_r4():
    entry=verify_protected();parity=read('reports/v4_11_r4a/V4_03_EXACT_PARITY_R1.json')
    if parity['status']!='PASS' or parity['row_scope']!=5222:raise ValueError('R4A_PARITY_REQUIRED')
    exact(parity['replay']);exact(parity['accepted_artifact']);exact(parity['adapter'])
    independent=[]
    for day in ('2026-09-29','2026-09-30'):
        report=read('reports/v4_11_r4a/INDEPENDENT_ORACLE_'+day+'.json')
        if report['status']!='PASS' or report['mismatches']:raise ValueError('R4_SOURCE_ORACLE_REQUIRED')
        exact(report['publication']);exact(report['calculation_window_evidence']);exact(report['independent_verifier_source'])
        independent.append(dict(day=day,coverage=report['universe_coverage'],source_slots=report['source_slot_checks']))
    d2=read('reports/v4_11_r4/V4_11_R4_D2_READBACK.json');er=read('reports/v4_11_r4/V4_11_R4_EVENT_REPLAY.json')
    current=gz(d2['current']);prior=gz(d2['prior']);frozen=gz(er['frozen_prior']);actual=gz(er['events'])
    rows=verify_candidate_d2_publication(current,producer_set=d2['source_set']);verify_candidate_d2_publication(prior,producer_set=d2['source_set'])
    if frozen['source_binding']!=prior or frozen['rows']!=prior['rows']:raise ValueError('REAL_PRIOR_SOURCE_MISMATCH')
    repeated=events(current,frozen,revision_of=current['publication_id'])
    old={r['entity_id']:r for r in prior['rows']};new={r['entity_id']:r for r in rows}
    for event,revised in zip(actual,repeated):
        sid=event['entity_id'];reasons=event_unknown_reasons(new[sid],old.get(sid))
        if reasons!=event['event_unknown_predicates'] or event['effective_event']!=('UNKNOWN' if reasons else event['primary_event']):raise ValueError('EVENT_UNKNOWN_SAFETY')
        if any(event[k]!=revised[k] for k in ('event_types','primary_event','prior_session_state_head_digest')):raise ValueError('SAME_DAY_REVISION_INVARIANCE')
    attribution=read('reports/v4_11_r4/RESIDUAL_UNKNOWN_ATTRIBUTION.json')
    if attribution['stale_producer_wiring_missing'] or attribution['banned_coefficient_generic_reasons']:raise ValueError('RESIDUAL_SOURCE_ATTRIBUTION_FAILED')
    full=read('reports/v4_11_r4/FULL_SOURCE_WINDOW_ORACLE.json')
    if full['status']!='PASS' or any(r['status']!='PASS' for r in full['dates']):raise ValueError('FULL_SOURCE_WINDOW_ORACLE_REQUIRED')
    for r in full['dates']:exact(r['calculations'])
    return dict(status='PASS_REAL_R4_D2_REEXECUTION_EVENT_GUARDS_SOURCE_ORACLES',parity_rows=5222,source_oracles=independent,full_source_windows=bind('reports/v4_11_r4/FULL_SOURCE_WINDOW_ORACLE.json'),D2_rows=len(rows),event_rows=len(actual),stale_attribution_count=attribution['stale_count'],permissions=PERMISSIONS)

def full_repository_collection():
    with tempfile.TemporaryDirectory(prefix='v4_r4_collection_') as temporary:
        guard=Path(temporary)
        (guard/'sitecustomize.py').write_text("import sys,os\ndef forbid(event,args):\n if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):\n  path=os.fsdecode(args[0]).replace('\\\\','/').lower()\n  if path.endswith('config/.env') or path.endswith('/config.env'):raise RuntimeError('CONFIG_ENV_READ_FORBIDDEN_IN_R4_COLLECTION')\nsys.addaudithook(forbid)\n",encoding='utf8')
        env=os.environ.copy()
        for key in ('PGPASSWORD','PGSERVICE','PGSERVICEFILE','PGDATABASE','PGHOST','PGPORT','PGUSER','WORKBENCH_PG_DSN','V4_10_DISPOSABLE_TEST_DSN'):env.pop(key,None)
        env['PYTHONPATH']=str(guard)+os.pathsep+str(ROOT)+os.pathsep+str(ROOT/'src')
        r=subprocess.run([sys.executable,'-m','pytest','--collect-only','-q','tests'],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=120)
    text=r.stdout+'\n'+r.stderr
    prefix='reports/v4_11_r4/FULL_REPOSITORY_COLLECTION'
    atomic_bytes(prefix+'.log',text.encode('utf8'))
    unchanged=[]
    for path in ('tests/upgrade_m14/test_online_batches.py','src/workbench_online/collector.py'):
        baseline=subprocess.check_output(['git','show','65774de:'+path],cwd=ROOT)
        if baseline.replace(b'\r\n',b'\n')!=(ROOT/path).read_bytes().replace(b'\r\n',b'\n'):raise ValueError('UNRELATED_M14_CHANGED')
        unchanged.append(bind(path))
    error_paths=re.findall(r'^ERROR (tests/\S+)',text,re.MULTILINE)
    known=(r.returncode!=0 and "cannot import name '_commit_raw_and_batch'" in text and error_paths==['tests/upgrade_m14/test_online_batches.py'])
    if r.returncode and not known:raise ValueError('NEW_FULL_REPOSITORY_COLLECTION_ERROR:'+text[-5000:])
    result=dict(status='BLOCKED_PREEXISTING_M14_COLLECTION' if known else 'PASS',exit_code=r.returncode,log=bind(prefix+'.log'),baseline='65774de20108beafaa15c0b557b4cd2ee58edb29',unchanged_baseline_sources=unchanged,reason='Existing upgrade_m14 test imports removed persistence API; no runtime executed during collection; no new deselection',separate_audit_item='R4_FULL_REPOSITORY_PREEXISTING_M14_COLLECTION',full_repository_runtime_pass_claim=False if known else None)
    write(prefix+'.json',result);return result
