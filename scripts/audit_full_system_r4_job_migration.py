"""Real frozen scheduler rows -> G PG candidate; repeat import and recovery."""
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.audit_full_system_r4_scope import write
from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobs
from workbench_db.v4_job_migration_r1 import import_oracle

def main():
    candidate=Path('G:/codex_tmp/full_system_r4_fbd23a6b/jobs_candidate');candidate.mkdir(parents=True,exist_ok=True)
    oracle_path=Path('G:/codex_tmp/full_system_r4_fbd23a6b/job_freeze_01/oracle.json')
    oracle=json.loads(oracle_path.read_bytes());jobs=DailyJobs(candidate)
    result=import_oracle(jobs,oracle);again=import_oracle(jobs,oracle)
    restart=DailyJobs(candidate)
    with restart.connect() as pg:
        counts={table:pg.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in result['counts']}
    if counts!=result['counts']:raise ValueError('JOB_MIGRATION_RESTART_COUNTS_DIFFER')
    if again['status']!='ALREADY_IMPORTED':raise ValueError('JOB_MIGRATION_NOT_IDEMPOTENT')
    write('R4_02_REAL_JOB_MIGRATION.json',dict(current_status='SCOPED_FULL_ROW_MIGRATION_PASS',denominator=counts,result=result,repeat_import=again,restart_counts=counts,pg_schema=jobs.schema,evidence_links=[str(oracle_path)],limitations=['No production switch; recovery counts are verified without dispatching accepted T0; physical restart not exercised'],next_conditions=['Full operational restart and cancellation/rearm/concurrency cases; production switch requires explicit authorization']))
    print(json.dumps(dict(status=result['status'],counts=counts,idempotent=True,restart_counts_equal=True)))
if __name__=='__main__':main()
