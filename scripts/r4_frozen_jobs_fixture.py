"""Bounded, separate pre-R4 V4 SQLite migration oracle on G only."""
import argparse,json,subprocess,sys,types
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
BASE='851770b1932d95836ce76bb44fd292117958bf04'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--scenario',choices=['restore','schema'],required=True);args=ap.parse_args()
    root=Path(args.root).resolve()
    if not root.is_relative_to(Path('G:/codex_tmp/test_temp').resolve()):raise ValueError('G_ISOLATED_FIXTURE_REQUIRED')
    source=subprocess.check_output(['git','show',BASE+':src/workbench_analysis/operational_daily_jobs_v1.py'],cwd=ROOT)
    old=types.ModuleType('workbench_analysis.r4_frozen_jobs');old.__package__='workbench_analysis'
    exec(compile(source,'FROZEN_'+BASE+'_jobs.py','exec'),old.__dict__)
    sessions=['2026-10-08','2026-10-09'] if args.scenario=='restore' else ['2026-10-09']
    old.gap_plan=lambda *a,**k:dict(status='TIME_ELIGIBLE',requested_through_date='2026-10-09',missing_sessions=sessions,eligible_sessions=sessions,last_good_trade_date='2026-09-30' if args.scenario=='restore' else '2026-10-08')
    state={'source':'unavailable'};calls=[]
    def execute(day,mode):
        calls.append(day);return dict(status='FAILED_TERMINAL' if state['source']=='unavailable' else 'PUBLISHED')
    q=old.DailyJobs(root,execute,lambda:datetime.fromisoformat('2026-10-09T22:10:00+08:00'));q.tick()
    if args.scenario=='restore':q.tick();state['source']='restored';q.tick()
    with q.connect() as db:
        wal=db.execute('PRAGMA journal_mode').fetchone()[0]
        before={table:[tuple(r) for r in db.execute('SELECT * FROM '+table)] for table in ('update_jobs','update_job_days','update_events')}
        db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    old_job=q.job(before['update_jobs'][0][0]);q.close()
    # Copy only this newly created fixture to an immutable migration oracle.
    import sqlite3
    snapshot=root/'frozen.sqlite3'
    with sqlite3.connect(q.path) as src,sqlite3.connect(snapshot) as dst:src.backup(dst)
    oracle=root/'oracle.json'
    subprocess.run([sys.executable,'-B',str(ROOT/'scripts/r4_sqlite_readonly_oracle.py'),'--source',str(snapshot),'--output',str(oracle),'--kind','jobs'],check=True,stdout=subprocess.DEVNULL)
    print(json.dumps(dict(source_SHA=BASE,calls=calls,journal_mode=wal,before=before,old_job=old_job,oracle=str(oracle),kind='ISOLATED_MIGRATION_ORACLE_NOT_V4_RUNTIME')))
if __name__=='__main__':main()
