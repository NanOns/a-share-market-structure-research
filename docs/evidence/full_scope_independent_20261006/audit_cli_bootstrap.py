"""Read-only --help probes; no capture, candidate build, or promotion is executed."""
import hashlib
import json
import os
import subprocess
import sys
from write_reports import ROOT,EVIDENCE,atomic,HEAD

command=[sys.executable,'-B',str(ROOT/'scripts/run_v4_dm01_daily_increment.py'),'--help']
results=[]
for mode in ('INHERITED_ENV','EXPLICIT_ROOT_AND_SRC_PYTHONPATH'):
    env=os.environ.copy()
    env['PYTHONIOENCODING']='utf-8'
    if mode=='EXPLICIT_ROOT_AND_SRC_PYTHONPATH':
        env['PYTHONPATH']=os.pathsep.join([str(ROOT),str(ROOT/'src')])
    r=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=60)
    results.append(dict(mode=mode,returncode=r.returncode,output_encoding='UTF-8',stdout=r.stdout.decode('utf8'),stderr=r.stderr.decode('utf8')))
value=dict(audit_head=HEAD,evidence_class='READ_ONLY_CLI_IMPORT_HELP_NOT_REAL_DATA_EXECUTION',command=command,results=results,interpretation='Standalone entrypoint inserts src but not repository root; kernels import scripts.*. An explicit launch environment reaches --help, inherited environment does not. No capture flags or data-stage commands executed.')
atomic(EVIDENCE/'cli_bootstrap_probe.json',(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
print(json.dumps([dict(mode=r['mode'],returncode=r['returncode']) for r in results]))
