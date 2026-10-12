"""Actual Windows/default-engine restart, duplicate-open and PG denial drill.

Runs only an isolated G: workspace; never stops or changes the existing product.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

SOURCE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(SOURCE),str(SOURCE/'src')]
sys.dont_write_bytecode=True
os.environ.update(TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp')


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);p.add_argument('--port',type=int,default=28871);a=p.parse_args()
    root,out=Path(a.root).resolve(),Path(a.out).resolve()
    if any(x.drive.upper()!='G:' for x in (root,out)) or not root.is_relative_to(Path('G:/codex_tmp').resolve()):raise SystemExit('G_ISOLATED_RUNTIME_REQUIRED')
    if os.name!='nt':raise SystemExit('REAL_WINDOWS_REQUIRED')
    out.mkdir(parents=True,exist_ok=True)
    from workbench_desktop.storage import WorkspaceLease
    from workbench_desktop.engine import EngineController
    protected={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','config/v4_joint_release_authority_v1.json')}
    records=[]
    def read(path):
        with urllib.request.urlopen(f'http://127.0.0.1:{a.port}'+path,timeout=30) as response:
            raw=response.read();return dict(http=response.status,sha256=hashlib.sha256(raw).hexdigest(),payload=json.loads(raw) if path.startswith('/api/') else None)
    with WorkspaceLease(root):
        controller=EngineController(root,a.port)
        try:
            controller.perform('start');first=read('/api/v4/context');before=controller.status()
            server,jobs=controller.server,controller.jobs
            controller.perform('start')
            records.append(dict(check='REPEATED_START_IDEMPOTENT',pass_=server is controller.server and jobs is controller.jobs,status=controller.status()))
            command=[sys.executable,'-B',str(SOURCE/'scripts/v4_closeout_ui_server.py'),'--root',str(root),'--evidence',str(out/'duplicate_attempt'),'--port',str(a.port),'--default-engine']
            duplicate=subprocess.run(command,env=os.environ.copy(),capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)
            (out/'DUPLICATE_STDOUT.log').write_text(duplicate.stdout+'\n'+duplicate.stderr,encoding='utf-8')
            records.append(dict(check='SECOND_PROCESS_REFUSED',exit_code=duplicate.returncode,pass_=duplicate.returncode!=0 and ('ALREADY_OWNED' in duplicate.stdout+duplicate.stderr or 'ALREADY_RUNNING' in duplicate.stdout+duplicate.stderr)))
            controller.perform('stop')
            stopped=False
            try:read('/api/v4/context')
            except (OSError,urllib.error.URLError):stopped=True
            records.append(dict(check='STOPPED_SOCKET_UNAVAILABLE',pass_=stopped,state=controller.status()['engine_state']))
            controller.perform('start');after=controller.status();second=read('/api/v4/context')
            records.append(dict(check='DEFAULT_RESTART_CONTEXT_AND_SETTINGS_PERSIST',pass_=first['payload']['context_token']==second['payload']['context_token'] and before['auto_daily_enabled']==after['auto_daily_enabled'] and server is not controller.server and jobs is not controller.jobs,context_token=second['payload']['context_token'],auto_daily_enabled=after['auto_daily_enabled'],before=before,after=after))
            entries={name:read('/v4/research/'+name) for name in ('home','sectors','stocks','focus','market','diagnostics')}
            records.append(dict(check='RESTART_SIX_HTML_ENTRIES',pass_=all(v['http']==200 for v in entries.values()),entries=entries,limit='HTML identity only; browser functional evidence is separate'))
        finally:controller.perform('stop')
    # Missing role is an actual PG authentication refusal; no permissions are
    # granted and no OS or database security setting is modified.
    from psycopg.conninfo import conninfo_to_dict,make_conninfo
    params=conninfo_to_dict(os.environ['V4_NATIVE_PG_DSN']);params['user']='v4_closeout_missing_role'
    env=dict(os.environ,V4_NATIVE_PG_DSN=make_conninfo(**params))
    command=[sys.executable,'-B',str(SOURCE/'scripts/v4_closeout_ui_server.py'),'--root',str(root),'--evidence',str(out/'permission_attempt'),'--port',str(a.port),'--default-engine']
    refused=subprocess.run(command,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)
    text=refused.stdout+'\n'+refused.stderr;(out/'PG_PERMISSION_STDOUT.log').write_text(text,encoding='utf-8')
    records.append(dict(check='PG_MISSING_ROLE_FAIL_CLOSED',pass_=refused.returncode!=0 and 'v4_closeout_missing_role' in text,exit_code=refused.returncode,limit='Isolated role denial; formal production role is a separate gate'))
    after={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in protected}
    records.append(dict(check='PROTECTED_HEAD_BYTES_UNCHANGED',pass_=protected==after,before=protected,after=after))
    result=dict(contract='V4_WINDOWS_DEFAULT_ENGINE_ACTUAL_DRILL_V1',observed_at=datetime.now(timezone.utc).isoformat(),pid=os.getpid(),source_root=str(SOURCE),runtime_root=str(root),port=a.port,records=records,acceptance='PASS' if all(r['pass_'] for r in records) else 'FAIL',limitations=['Isolated root and isolated admin role only','No installed EXE/package-release SOURCE_SHA claim','No real future source capture manufactured'])
    (out/'WINDOWS_ACTUAL.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(dict(status=result['acceptance'],checks=len(records))))


if __name__=='__main__':main()
