"""Authorized versioned new-listing package switch and actual daily readback."""
import json,os,sys,time,shutil,subprocess,hashlib,urllib.request
from pathlib import Path
from datetime import datetime,timezone
import psutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/audits/v4_new_listing_daily_20261013_r1'
RUNTIME=Path('G:/codex work/v4-production-20261012')
BUILD=Path('G:/codex_tmp/windows_new_listing_20261013_r2')
manifest=json.loads(next(BUILD.glob('resources_*/package_manifest.json')).read_bytes())
SOURCE=Path('G:/codex work/大A交易_交付/windows_new_listing_20261013_r2/versions')/manifest['build_release_id']
def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    b=v if isinstance(v,bytes) else (json.dumps(v,indent=2,ensure_ascii=False,default=str)+'\n').encode('utf8')
    t=p.with_name(p.name+'.tmp');t.write_bytes(b);os.replace(t,p)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def http(path,body=None,method=None):
    r=urllib.request.Request('http://127.0.0.1:28765'+path,data=json.dumps(body).encode() if body is not None else None,method=method,headers={'Content-Type':'application/json','X-V4-Operation':'daily-update'})
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(r,timeout=120) as response:return json.load(response)
def heads():return {p:sha(RUNTIME/p) for p in ['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json','config/v4_current_native_joint_authority_v3.json']}
def observe(label):
    s=http('/api/v4/operations/daily-update/status');c=http('/api/v4/context');d=http('/api/v4/desktop/status')
    v=dict(observed_at=datetime.now(timezone.utc).isoformat(),daily=s,context=c,desktop=d,heads=heads())
    write(OUT/(label+'.json'),v)
    print(json.dumps(dict(label=label,T0=c['context']['trade_date'],job=s['last_job'],worker_error=s.get('worker_error')),ensure_ascii=False),flush=True)
    return v
def deploy():
    for n in ['IMPORT_QA.json','LIFECYCLE_QA.json']:
        v=json.loads((BUILD/n).read_bytes());assert v['status']=='PASS',v
        write(OUT/('FINAL_'+n),(BUILD/n).read_bytes())
    before=observe('BEFORE_NEW_PACKAGE_R1');assert before['daily']['active_job'] is None or before['daily']['active_job']['status'] not in ['RUNNING','PUBLISHING']
    assert before['desktop']['BUILD_RELEASE_ID']=='V4_PACKAGE_1.0.0_d6b09b5f0e67'
    process=psutil.Process(before['desktop']['pid']);old_exe=process.exe()
    assert Path(old_exe).resolve()==(RUNTIME/'versions/V4_PACKAGE_1.0.0_d6b09b5f0e67/DaAV4/DaAV4.exe').resolve()
    old=json.loads((Path(old_exe).parent/'_internal/resources/package_manifest.json').read_bytes())
    oldfiles={r['path']:r['sha256'] for r in old['resources']};newfiles={r['path']:r['sha256'] for r in manifest['resources']}
    changed=[p for p in oldfiles.keys()&newfiles.keys() if oldfiles[p]!=newfiles[p]]
    assert changed==['src/workbench_desktop/source_adapter.py'],changed
    write(OUT/'PACKAGE_CONSERVATION_R1.json',dict(changed=changed,added=sorted(newfiles.keys()-oldfiles.keys()),immutable_numeric_and_policy_resources_preserved=True))
    destination=RUNTIME/'versions'/SOURCE.name;assert not destination.exists()
    assembling=destination.with_name(destination.name+'.assembling');assert not assembling.exists()
    shutil.copytree(SOURCE,assembling);assert sha(assembling/'DaAV4/DaAV4.exe')==sha(SOURCE/'DaAV4/DaAV4.exe');os.rename(assembling,destination)
    # New sources are provenance originals only. Runtime always executes PYZ.
    new_source=ROOT/'src/workbench_analysis/operational_new_listing_r1.py'
    p=RUNTIME/new_source.relative_to(ROOT);assert not p.exists();write(p,new_source.read_bytes())
    http('/api/v4/operations/daily-update/settings',{'auto_enabled':False},'PUT')
    text="$ErrorActionPreference='Stop'; $task=Get-ScheduledTask -TaskName 'Codex-V4-OperationalDaily-28765'; "
    text+="if ($task.Actions.Execute -notlike '*V4_PACKAGE_1.0.0_d6b09b5f0e67*') {throw 'OLD_TASK_REQUIRED'}; "
    text+="[IO.File]::WriteAllText('"+str(OUT/'OLD_TASK.xml')+"',(Export-ScheduledTask -TaskName $task.TaskName),[Text.Encoding]::Unicode); Stop-ScheduledTask -TaskName $task.TaskName; "
    text+="$a=New-ScheduledTaskAction -Execute '"+str(destination/'DaAV4/DaAV4.exe')+"' -Argument $task.Actions.Arguments -WorkingDirectory $task.Actions.WorkingDirectory; Set-ScheduledTask -TaskName $task.TaskName -Action $a | Out-Null; Start-ScheduledTask -TaskName $task.TaskName"
    write(OUT/'SWITCH_TASK_REVIEWABLE.ps1',text.encode('utf8'))
    subprocess.run(['powershell.exe','-NoProfile','-Command',text],check=True,capture_output=True)
    try:
        if process.is_running():assert process.exe()==old_exe;process.terminate();process.wait(timeout=30)
    except psutil.NoSuchProcess:pass
    deadline=time.monotonic()+150
    while time.monotonic()<deadline:
        try:
            d=http('/api/v4/desktop/status')
            if d['engine_state']=='RUNNING' and d['SOURCE_SHA']==manifest['source_sha']:break
        except Exception:pass
        time.sleep(1)
    else:raise RuntimeError('NEW_PACKAGE_NOT_RUNNING_RESTORE_PRIOR_TASK_REQUIRED')
    assert heads()==before['heads']
    http('/api/v4/operations/daily-update/settings',{'auto_enabled':before['daily']['settings']['auto_enabled']},'PUT')
    after=observe('AFTER_NEW_PACKAGE_R1')
    write(OUT/'DEPLOYMENT_R1.json',dict(acceptance='PASS_NEW_LISTING_PACKAGE_LAST_GOOD_CONSERVED',source_sha=manifest['source_sha'],before_pid=before['desktop']['pid'],after_pid=after['desktop']['pid'],auto_restored=after['daily']['settings']['auto_enabled'],last_good_preserved=True))
def retry():
    s=http('/api/v4/operations/daily-update/status');job=s['last_job']
    if job['status'] in ['RUNNING','PUBLISHING']:print('ALREADY_RUNNING');return
    r=http('/api/v4/operations/daily-update/jobs/'+job['job_id']+'/retry',{},'POST')
    write(OUT/'NEW_LISTING_REAL_RETRY_R1.json',dict(before=job,result=r,authority='User direct new-listing repair and daily validation request'));print(json.dumps(r))
if __name__=='__main__':
    if sys.argv[1]=='deploy':deploy()
    elif sys.argv[1]=='retry':retry()
    elif sys.argv[1]=='observe':observe(sys.argv[2])
