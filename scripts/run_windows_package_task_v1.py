"""Record real child EXE exit identity, including intentional CAS-pending crash."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from workbench_desktop.storage import atomic

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--exe',required=True);p.add_argument('--workspace',required=True)
    p.add_argument('--report',required=True);p.add_argument('--process-report',required=True)
    p.add_argument('--task',choices=('qa-e2e','qa-tray','qa-daily-replay','inspect-package'),required=True)
    a=p.parse_args();exe=Path(a.exe).resolve();root=Path(a.workspace).resolve()
    delivery=Path('G:/codex work/大A交易_交付/windows_package_v1/versions').resolve()
    temporary=Path('G:/codex_tmp').resolve()
    if not exe.is_relative_to(delivery) or exe.name!='DaAV4.exe':raise ValueError('EXPLICIT_PACKAGED_ENTRY_REQUIRED')
    if not root.is_relative_to(temporary/'test_temp') or not (root/'ISOLATED_PACKAGE_QA.json').is_file():raise ValueError('ISOLATED_QA_ROOT_REQUIRED')
    for output in (a.report,a.process_report):
        if not Path(output).resolve().is_relative_to(temporary):raise ValueError('G_TEMP_REPORT_REQUIRED')
        if Path(output).exists():raise ValueError('FRESH_REPORT_PATH_REQUIRED')
    os.environ.update(TMP=str(temporary),TEMP=str(temporary),TMPDIR=str(temporary),PYTHONDONTWRITEBYTECODE='1')
    sys.dont_write_bytecode=True
    manifest=exe.parent/'_internal/resources/package_manifest.json'
    head=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    info=dict(contract_id='V4_ACTUAL_FROZEN_PROCESS_EXECUTION_V1',task=a.task,executable=str(exe),
        executable_sha256=sha(exe),manifest_sha256=sha(manifest),workspace=str(root),
        started_at=datetime.now(timezone.utc).isoformat(),head_before=sha(head) if head.exists() else None,
        runner_is_orchestration_only=True)
    child=subprocess.Popen([str(exe),'--task',a.task,'--workspace',str(root),'--report',a.report],env=dict(os.environ))
    info['pid']=child.pid;info['exit_code']=child.wait()
    info.update(finished_at=datetime.now(timezone.utc).isoformat(),head_after=sha(head) if head.exists() else None,
        report_exists=Path(a.report).is_file(),intentional_cas_pending_crash=(a.task=='qa-daily-replay' and child.returncode==70))
    atomic(a.process_report,info)
    print(json.dumps(info,ensure_ascii=False),flush=True)
    if Path(a.report).exists():
        report=json.loads(Path(a.report).read_bytes());print(report['status'],report.get('reason',''),flush=True)
    return 0 if child.returncode in (0,70) else child.returncode
if __name__=='__main__':raise SystemExit(main())
