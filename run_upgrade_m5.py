from __future__ import annotations
import json, os, socket, subprocess, sys, tempfile, time, uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'src'))
from workbench_db import WorkbenchRepository
from workbench_ops import BackupService, DatabaseMigration, LocalServiceSupervisor, RestartSupervisor

def port():
 s=socket.socket();s.bind(('127.0.0.1',0));value=s.getsockname()[1];s.close();return value

def main():
 with tempfile.TemporaryDirectory(prefix='m5-acceptance-') as temporary:
  temp=Path(temporary);db=temp/'source/market.duckdb'
  with WorkbenchRepository(ROOT,db): pass
  # Real offline backup, trial restore and cross-volume preparation. The
  # temporary target lives on the system temp volume when it differs.
  backup=BackupService(ROOT,db).create_offline_backup(maintenance_window=True)
  drill=BackupService(ROOT,db).restore_drill(backup['backup_id'],drill_root=temp/'drill')
  migration=DatabaseMigration(ROOT,db).prepare(temp/'target/market.duckdb',maintenance_window=True)
  good=port();command=[sys.executable,str(ROOT/'run_workbench_service.py'),'--port',str(good),'--database',str(db)]
  live=LocalServiceSupervisor(command,f'http://127.0.0.1:{good}/api/publications')
  live.start();success_health=live.healthy();live.stop()
  old=LocalServiceSupervisor(command,f'http://127.0.0.1:{good}/api/publications')
  bad_port=port();bad=LocalServiceSupervisor([sys.executable,str(ROOT/'run_workbench_service.py'),'--port',str(bad_port),'--database',str(db)],f'http://127.0.0.1:{bad_port+1}/api/publications')
  supervisor=RestartSupervisor()
  result=supervisor.restart(drain=lambda:None,close_db=lambda:None,release_owner_lock=lambda:None,start_new=bad.start,health_check=lambda:bad.healthy(2),restore_old=lambda:(bad.stop(),old.start()))
  rollback_health=old.healthy();old.stop();bad.stop()
  checks={'offline_backup_verified':backup['state']=='VERIFIED','restore_drill':drill['status']=='PASS','migration_prepare':migration['status']=='PREPARED','real_service_health':success_health,'restart_failure_rollback':result['status']=='ROLLED_BACK' and rollback_health}
  status='FULL_PASS' if all(checks.values()) else 'BLOCKED'
  receipt={'phase':'M5_OPERATIONS','contract_version':'m5-operations-contract-v1','checks':checks,'backup':backup,'restore_drill':drill,'migration':migration,'restart_failure_rollback':result,'final_status':status,'next_stage':'M6_INDEPENDENT_ACCEPTANCE' if status=='FULL_PASS' else None}
  report=ROOT/'reports/upgrade_m5';report.mkdir(parents=True,exist_ok=True);target=report/'M5_OPERATIONS_RECEIPT.json';temporary=target.with_name(target.name+'.'+uuid.uuid4().hex+'.tmp');temporary.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(temporary,target)
  print(json.dumps(receipt,ensure_ascii=False,indent=2));return 0 if status=='FULL_PASS' else 1
if __name__=='__main__':raise SystemExit(main())
