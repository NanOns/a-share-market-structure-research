"""Owned worker hard kill, durable PG checkpoint and session lock recovery."""
import argparse,json,os,subprocess,sys,time,uuid,threading
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.audit_full_system_r4_scope import write,OUT,sha

def atomic(path,value):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value),encoding='utf8');os.replace(temp,path)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--child',choices=['crash','contender','restart']);parser.add_argument('--root');parser.add_argument('--job');args=parser.parse_args()
    from tests import v4_native_isolation_plugin_r4 as guard
    from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobs
    candidate=Path(args.root) if args.root else Path('G:/codex_tmp/full_system_r4_fbd23a6b/worker_crash_'+uuid.uuid4().hex[:8])
    candidate.resolve().relative_to(Path('G:/codex_tmp/full_system_r4_fbd23a6b').resolve());candidate.mkdir(parents=True,exist_ok=True)
    tag=args.child or 'parent';ledger=candidate/(tag+'_connections.jsonl')
    os.environ['R4_PG_DATA_DIRECTORY']='G:/codex_tmp/full_system_r4_fbd23a6b/pg_data';os.environ['R4_CONNECTION_LEDGER']=str(ledger)
    config=SimpleNamespace();guard.pytest_configure(config);guard.ACTIVE='OWNED_WORKER_PROCESS_'+tag.upper()
    calls=[]
    def execute(day,mode):
        calls.append(day)
        if args.child=='crash':
            jobs.checkpoint(day,'R4_ENGINEERING_CRASH_CHECKPOINT',dict(evidence_class='ENGINEERING_FIXTURE',source_digest='c'*64))
            atomic(candidate/'checkpoint_marker.json',dict(pid=os.getpid(),calls=calls,fixture=True))
            guard.pytest_sessionfinish(None,0)
            threading.Event().wait(120)
            raise RuntimeError('OWNED_CRASH_PROBE_TIMEOUT')
        return dict(status='PROBED',evidence_class='ENGINEERING_FIXTURE',formal_consumer_enabled=False)
    jobs=DailyJobs(candidate,execute);jobs.settings(False)
    try:
        if args.child:
            if args.child=='contender':
                try:jobs.tick()
                except RuntimeError as exc:
                    if str(exc)!='V4_PG_WORKER_ALREADY_OWNED':raise
                    atomic(candidate/'contender_result.json',dict(worker_rejected=True,calls=calls))
                else:raise ValueError('CONCURRENT_WORKER_NOT_REJECTED')
            else:
                jobs.tick();atomic(candidate/'restart_result.json',dict(calls=calls,job=jobs.job(args.job)))
            return
        job='R4_ENGINEERING_'+uuid.uuid4().hex
        with jobs.connect() as db:
            db.execute('INSERT INTO update_jobs VALUES(?,?,?,?,?,?,?,?,?)',(job,'ENGINEERING_FIXTURE','PROBE','2026-10-09','QUEUED','2026-10-11T00:00:00+00:00',None,job,None))
            db.execute('INSERT INTO update_job_days(job_id,trade_date,state) VALUES(?,?,?)',(job,'2026-09-30','PUBLISHED'))
            db.execute('INSERT INTO update_job_days(job_id,trade_date,state) VALUES(?,?,?)',(job,'2026-10-09','QUEUED'))
        def command(mode):return [sys.executable,'-B',str(Path(__file__)), '--child',mode,'--root',str(candidate),'--job',job]
        flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
        with (candidate/'crash_process.log').open('w',encoding='utf8') as output:
            process=subprocess.Popen(command('crash'),stdout=output,stderr=subprocess.STDOUT,creationflags=flags)
            try:
                deadline=time.monotonic()+30
                while not (candidate/'checkpoint_marker.json').exists():
                    if process.poll() is not None:raise ValueError('CRASH_WORKER_EXITED_EARLY')
                    if time.monotonic()>deadline:raise TimeoutError('CRASH_CHECKPOINT_TIMEOUT')
                    time.sleep(.05)
                before=jobs.job(job)
                if before['status']!='RUNNING' or before['days'][1]['state']!='R4_ENGINEERING_CRASH_CHECKPOINT':raise ValueError('DURABLE_CHECKPOINT_NOT_REACHED')
                with (candidate/'contender.log').open('w',encoding='utf8') as log:subprocess.run(command('contender'),stdout=log,stderr=subprocess.STDOUT,timeout=20,creationflags=flags,check=True)
                contender=json.loads((candidate/'contender_result.json').read_bytes())
                if contender!=dict(worker_rejected=True,calls=[]):raise ValueError('MULTIWORKER_LOCK_PROBE_FAILED')
                process.kill();exit_code=process.wait(timeout=10)
            finally:
                if process.poll() is None:process.kill();process.wait(timeout=10)
        persisted=jobs.job(job)
        if persisted!=before:raise ValueError('CHECKPOINT_CHANGED_AFTER_HARD_KILL')
        with (candidate/'restart.log').open('w',encoding='utf8') as log:subprocess.run(command('restart'),stdout=log,stderr=subprocess.STDOUT,timeout=20,creationflags=flags,check=True)
        resumed=json.loads((candidate/'restart_result.json').read_bytes())
        if resumed['calls']!=['2026-10-09'] or resumed['job']['status']!='PROBE_COMPLETE' or resumed['job']['days'][0]['state']!='PUBLISHED' or resumed['job']['days'][1]['attempt_count']!=2:raise ValueError('WORKER_RESTART_OR_PUBLISHED_DAY_SKIP_FAILED')
        evidence=[]
        for mode in ('crash','contender','restart'):
            source=candidate/(mode+'_connections.jsonl');target=OUT/('R4_WORKER_'+candidate.name+'_'+mode+'_CONNECTIONS.jsonl');target.write_bytes(source.read_bytes());evidence.append(dict(path=target.name,sha256=sha(target)))
        write('R4_02_PROCESS_CRASH_RESULT.json',dict(contract_id='R4_PG_PROCESS_CRASH_CHECKPOINT_R1',current_status='SCOPED_PROCESS_CRASH_LOCK_RECOVERY_PASS',denominator=dict(workers=3,job_days=2),fixture_root=str(candidate),fixture_job=job,before=before,after_kill=persisted,restarted=resumed,owned_killed_pid=process.pid,owned_exit_code=exit_code,negative_vectors=['Concurrent second worker rejected with no executor call','Prior PUBLISHED fixture day never redispatched'],evidence_links=evidence,limitations=['Engineering executor fixture, not actual source pipeline crash, accepted Head publication or CAS checkpoint reuse','Previously PUBLISHED date is a fixture state; no real accepted-T0 no-republish claim'],next_conditions=['Actual source executor immutable-stage resume, accepted-T0 no-redispatch and publication recovery']))
        print(json.dumps(dict(killed_pid=process.pid,restart_calls=resumed['calls'],published_day_preserved=True,multiworker_rejected=True)))
    finally:
        jobs.close();guard.pytest_sessionfinish(None,0);guard.pytest_unconfigure(config)

if __name__=='__main__':main()
