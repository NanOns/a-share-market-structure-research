"""Controlled authorized package repair; preserve failed receipts and last-good."""
import hashlib,json,os,shutil,subprocess,sys,time,urllib.request
from datetime import datetime,timezone
from pathlib import Path
import psutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/audits/v4_daily_package_repair_20261013_r1'
RUNTIME=Path('G:/codex work/v4-production-20261012')
BUILD=Path('G:/codex_tmp/windows_daily_repair_20261013_r3')
SOURCE=Path('G:/codex work/大A交易_交付/windows_daily_repair_20261013_r3/versions/V4_PACKAGE_1.0.0_aa1f959c5e54')
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    raw=v if isinstance(v,bytes) else (json.dumps(v,ensure_ascii=False,indent=2,default=str)+'\n').encode('utf8')
    t=p.with_name(p.name+'.tmp');t.write_bytes(raw);os.replace(t,p)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def http(path,body=None,method=None):
    request=urllib.request.Request('http://127.0.0.1:28765'+path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type':'application/json','X-V4-Operation':'daily-update'},method=method)
    o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with o.open(request,timeout=90) as r:return json.load(r)
def heads():return {p:sha(RUNTIME/p) for p in ['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json','config/v4_current_native_joint_authority_v3.json']}
def observe(label):
    v=dict(observed_at=datetime.now(timezone.utc).isoformat(),desktop=http('/api/v4/desktop/status'),daily=http('/api/v4/operations/daily-update/status'),context=http('/api/v4/context'),heads=heads())
    write(OUT/(label+'.json'),v);print(json.dumps(dict(label=label,source_sha=v['desktop']['SOURCE_SHA'],T0=v['context']['context']['trade_date'],job=v['daily'].get('last_job'),worker_error=v['daily'].get('worker_error')),ensure_ascii=False),flush=True)
    return v
def deploy():
    assert not (OUT/'DEPLOYMENT_R1.json').exists()
    for name in ['SOURCE_IMPORT_QA_R3.json','LIFECYCLE_QA_R3.json']:
        v=json.loads((BUILD/name).read_bytes());assert v['status']=='PASS',v
        write(OUT/name,(BUILD/name).read_bytes())
    before=observe('BEFORE_DEPLOY_R1')
    assert before['desktop']['SOURCE_SHA']=='fe11c18cfdf75e9b0713b43a57139672792df8e11c5002fd67754a26af930744'
    assert before['desktop']['engine_state']=='RUNNING' and before['daily']['active_job'] is None
    process=psutil.Process(before['desktop']['pid']);old_exe=process.exe()
    assert Path(old_exe).resolve()==(RUNTIME/'versions/V4_PACKAGE_1.0.0_fe11c18cfdf7/DaAV4/DaAV4.exe').resolve()
    old_manifest=json.loads((Path(old_exe).parent/'_internal/resources/package_manifest.json').read_bytes())
    new_manifest=json.loads((SOURCE/'DaAV4/_internal/resources/package_manifest.json').read_bytes())
    old={r['path']:r['sha256'] for r in old_manifest['resources']};new={r['path']:r['sha256'] for r in new_manifest['resources']}
    changed=[p for p in old.keys()&new.keys() if old[p]!=new[p]]
    assert set(changed)<={'run_desktop.py','scripts/build_windows_package_v1.py','src/workbench_desktop/qa.py'},changed
    write(OUT/'PACKAGE_RESOURCE_CONSERVATION_R1.json',dict(changed=changed,added=sorted(new.keys()-old.keys()),immutable_policy_and_numeric_resources_preserved=True,old_source_sha=old_manifest['source_sha'],new_source_sha=new_manifest['source_sha']))
    destination=RUNTIME/'versions'/SOURCE.name;assert not destination.exists()
    assembling=destination.with_name(destination.name+'.assembling');assert not assembling.exists()
    shutil.copytree(SOURCE,assembling)
    assert sha(assembling/'DaAV4/DaAV4.exe')==sha(SOURCE/'DaAV4/DaAV4.exe')
    os.rename(assembling,destination)
    action_script=OUT/'SWITCH_TASK_R1.ps1'
    text="$ErrorActionPreference='Stop'\n$task=Get-ScheduledTask -TaskName 'Codex-V4-OperationalDaily-28765'\n"
    text+="if ($task.Actions.Execute -notlike '*V4_PACKAGE_1.0.0_fe11c18cfdf7*') {throw 'OLD_TASK_IDENTITY_REQUIRED'}\n"
    text+="$xml=Export-ScheduledTask -TaskName $task.TaskName\n[IO.File]::WriteAllText('"+str(OUT/'OLD_TASK_R1.xml')+"',$xml,[Text.Encoding]::Unicode)\n"
    text+="Stop-ScheduledTask -TaskName $task.TaskName\n"
    text+="$action=New-ScheduledTaskAction -Execute '"+str(destination/'DaAV4/DaAV4.exe')+"' -Argument $task.Actions.Arguments -WorkingDirectory $task.Actions.WorkingDirectory\nSet-ScheduledTask -TaskName $task.TaskName -Action $action | Out-Null\n"
    write(action_script,text.encode('utf8'))
    http('/api/v4/operations/daily-update/settings',dict(auto_enabled=False),'PUT')
    subprocess.run(['powershell.exe','-NoProfile','-File',str(action_script)],check=True,capture_output=True)
    if process.is_running():
        assert process.exe()==old_exe
        process.terminate();process.wait(timeout=30)
    subprocess.run(['powershell.exe','-NoProfile','-Command',"Start-ScheduledTask -TaskName 'Codex-V4-OperationalDaily-28765'"],check=True,capture_output=True)
    deadline=time.monotonic()+120
    while time.monotonic()<deadline:
        try:
            status=http('/api/v4/desktop/status')
            if status['engine_state']=='RUNNING' and status['SOURCE_SHA']==new_manifest['source_sha']:break
        except Exception:pass
        time.sleep(1)
    else:raise RuntimeError('NEW_PACKAGE_START_TIMEOUT_REQUIRES_OLD_TASK_RESTORE')
    assert heads()==before['heads'],'RESTART_HEAD_DRIFT'
    http('/api/v4/operations/daily-update/settings',dict(auto_enabled=before['desktop']['auto_daily_enabled']),'PUT')
    after=observe('AFTER_DEPLOY_R1')
    assert after['context']['context_token']==before['context']['context_token']
    write(OUT/'DEPLOYMENT_R1.json',dict(acceptance='PASS_NEW_PACKAGE_RESTART_LAST_GOOD_CONSERVED',before_pid=before['desktop']['pid'],after_pid=after['desktop']['pid'],new_source_sha=new_manifest['source_sha'],heads_conserved=True,auto_enabled_restored=after['desktop']['auto_daily_enabled'],old_package_preserved=True))
def retry():
    before=observe('BEFORE_RETRY_R1');job=before['daily']['last_job']
    assert job['status']=='QA_BLOCKED' and job['through_date']=='2026-10-13'
    assert before['desktop']['BUILD_RELEASE_ID']==SOURCE.name
    result=http('/api/v4/operations/daily-update/jobs/'+job['job_id']+'/retry',{},'POST')
    write(OUT/'EXPLICIT_AUTHORIZED_RETRY_R1.json',dict(before=job,result=result,authority='User direct repair instruction',observed_at=datetime.now(timezone.utc).isoformat()))
    print(json.dumps(result))
if __name__=='__main__':
    if sys.argv[1]=='deploy':deploy()
    elif sys.argv[1]=='retry':retry()
    elif sys.argv[1]=='observe':observe(sys.argv[2])
