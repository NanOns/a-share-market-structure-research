"""Prepare and execute the explicitly authorized R6 V4 package cutover."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

import psutil

ROOT = Path(r'G:\codex work\v4-production-20261012')
SOURCE = Path(__file__).resolve().parents[1]
DELIVERY = Path(r'G:\codex work\大A交易_交付\windows_package_v1')
PORT = 28765
JOINT_AUTHORITY = ROOT/'config/v4_current_native_joint_authority_v3.json'
STATIC_MAP = {
    'api.js': 'core-product-r1/api.js', 'app.js': 'core-product-r1/app.js',
    'components.js': 'core-product-r1/components.js', 'labels.js': 'core-product-r1/labels.js',
    'replay.js': 'core-product-r1/replay.js', 'stock.js': 'core-product-r1/stock.js',
    'index.html': 'research/index.html', 'style.css': 'research/style.css',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def atomic(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name+'.r6tmp')
    with temp.open('wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    os.replace(temp, path)


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode()


def process_root(argv):
    if '--workspace' in argv:
        try: return Path(argv[argv.index('--workspace')+1]).resolve()
        except (IndexError, ValueError): return None
    return None


def service_processes():
    result=[]
    for proc in psutil.process_iter(['pid','ppid','name','exe','cmdline']):
        try:
            info=proc.info; argv=info.get('cmdline') or []
            if (info.get('name') or '').lower()!='daav4.exe': continue
            if '--port' not in argv or argv[argv.index('--port')+1]!=str(PORT): continue
            if process_root(argv)!=ROOT.resolve(): continue
            result.append(proc)
        except (psutil.Error,ValueError,IndexError): continue
    return result


def report_path():
    return SOURCE/'reports/audits/v4_r6_closeout_20261014/PRODUCTION_CUTOVER.json'


def read_report():
    path=report_path()
    if not path.is_file(): raise ValueError('R6_CUTOVER_PREPARE_REPORT_MISSING')
    return json.loads(path.read_bytes())


def write_report(value):
    atomic(report_path(),canonical(value))


def prepare(package_id):
    if service_processes().__len__()!=1: raise ValueError('R6_EXPECTED_ONE_28765_SERVICE_PROCESS')
    proc=service_processes()[0]
    exe=Path(proc.exe()).resolve()
    if not exe.is_file(): raise ValueError('R6_OLD_EXECUTABLE_MISSING')
    old_manifest=json.loads((exe.parent/'_internal/resources/package_manifest.json').read_bytes())
    if old_manifest.get('build_release_id') not in (
            'V4_PACKAGE_1.0.0_88cc19deae3b','V4_PACKAGE_1.1.4_4c031f43788d',
            'V4_PACKAGE_1.1.5_ddd35de905bb'):
        raise ValueError('R6_OLD_PACKAGE_IDENTITY_CHANGED')
    status_path=ROOT/'runtime/desktop/status.json'
    status=json.loads(status_path.read_bytes())
    if status.get('auto_daily_enabled') is not False:
        raise ValueError('R6_AUTO_DAILY_NOT_PAUSED')
    head_path=ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    head_raw=head_path.read_bytes();head=json.loads(head_raw)
    active_joint_raw=JOINT_AUTHORITY.read_bytes()
    active_joint=json.loads(active_joint_raw)
    candidate_report=json.loads((SOURCE/'reports/audits/v4_r6_closeout_20261014/NATIVE_JOINT_CANDIDATE.json').read_bytes())
    if candidate_report.get('acceptance')!='PASS_NEW_CURRENT_TOKEN_JOINT_CANDIDATE' or candidate_report.get('active_pointer_changed') is not False:
        raise ValueError('R6_CANDIDATE_JOINT_NOT_READY')
    candidate_binding=candidate_report['candidate_joint']
    candidate_path=ROOT/candidate_binding['path']; candidate_raw=candidate_path.read_bytes()
    if len(candidate_raw)!=candidate_binding['bytes'] or sha(candidate_raw)!=candidate_binding['sha256']:
        raise ValueError('R6_CANDIDATE_JOINT_HASH_MISMATCH')
    candidate=json.loads(candidate_raw)
    if (candidate.get('business_token'),candidate.get('T0'))!=(active_joint.get('business_token'),active_joint.get('T0')):
        raise ValueError('R6_CANDIDATE_BUSINESS_CONTEXT_CHANGED')
    if candidate.get('business_token')!=candidate_report.get('business_token'):
        raise ValueError('R6_CANDIDATE_TOKEN_MISMATCH')
    source_package=DELIVERY/'versions'/package_id
    target_package=ROOT/'versions'/package_id
    if target_package.exists():
        existing_exe=target_package/'DaAV4/DaAV4.exe'
        existing=json.loads((existing_exe.parent/'_internal/resources/package_manifest.json').read_bytes())
        if existing.get('build_release_id')!=package_id: raise ValueError('R6_PACKAGE_DESTINATION_IDENTITY_CONFLICT')
    else:
        shutil.copytree(source_package,target_package)
    new_exe=target_package/'DaAV4/DaAV4.exe'
    manifest=json.loads((new_exe.parent/'_internal/resources/package_manifest.json').read_bytes())
    if manifest.get('build_release_id')!=package_id: raise ValueError('R6_NEW_PACKAGE_MANIFEST_MISMATCH')
    installed_overrides=[]
    if manifest.get('runtime_source_overrides'):
        if manifest.get('runtime_source_override_contract')!='V4_R6_PACKAGE_RUNTIME_SOURCE_OVERRIDES_R1':
            raise ValueError('R6_PACKAGE_RUNTIME_OVERRIDE_CONTRACT_MISMATCH')
        for item in manifest['runtime_source_overrides']:
            source=SOURCE/item['path'];target=ROOT/item['path'];raw=source.read_bytes()
            if len(raw)!=item['bytes'] or sha(raw)!=item['sha256']:
                raise ValueError('R6_RUNTIME_OVERRIDE_SOURCE_HASH_MISMATCH')
            if target.exists() and target.read_bytes()!=raw:
                raise ValueError('R6_RUNTIME_OVERRIDE_IMMUTABLE_CONFLICT')
            if not target.exists():atomic(target,raw)
            installed_overrides.append(dict(path=item['path'],bytes=len(raw),sha256=sha(raw)))
    rollback_root=ROOT/'data/v4/r6_cutover_rollback_20261014'/package_id
    backup_assets={}
    for name,relative in STATIC_MAP.items():
        path=ROOT/'src/workbench_service/static'/relative
        raw=path.read_bytes(); backup=rollback_root/'static'/relative
        if backup.exists() and backup.read_bytes()!=raw: raise ValueError('R6_ROLLBACK_STATIC_IMMUTABLE_CONFLICT')
        if not backup.exists(): atomic(backup,raw)
        backup_assets[name]={'path':backup.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':sha(raw)}
    active_joint_backup=rollback_root/'active_joint.json'
    if active_joint_backup.exists() and active_joint_backup.read_bytes()!=active_joint_raw:
        raise ValueError('R6_ROLLBACK_JOINT_IMMUTABLE_CONFLICT')
    if not active_joint_backup.exists(): atomic(active_joint_backup,active_joint_raw)
    report={
        'contract_id':'V4_R6_PRODUCTION_CUTOVER_R1','phase':'PREPARED',
        'production_root':str(ROOT),'port':PORT,'old_package_id':old_manifest['build_release_id'],
        'old_executable':str(exe),'old_executable_sha256':sha(exe.read_bytes()),
        'old_processes':[{'pid':p.pid,'ppid':p.ppid(),'exe':p.exe(),'cmdline':p.cmdline()} for p in [proc,*proc.children(recursive=True)]],
        'head_path':head_path.relative_to(ROOT).as_posix(),'head_sha256':sha(head_raw),
        'T0':head['accepted_trade_date'],'business_token':candidate['business_token'],
        'old_joint_pointer_sha256':sha(active_joint_raw),'old_joint':active_joint,
        'new_joint_pointer':candidate_binding,'new_joint_sha256':sha(candidate_raw),
        'rollback_joint_path':active_joint_backup.relative_to(ROOT).as_posix(),
        'old_static_assets':backup_assets,'new_ui_release_id':candidate_report['ui_release_id'],
        'new_ui_assets':candidate['ui_assets'],'old_auto_daily_enabled':False,
        'runtime_status_path':status_path.relative_to(ROOT).as_posix(),
        'new_package_id':package_id,'new_executable':str(new_exe),
        'new_runtime_source_overrides':installed_overrides,
        'desktop_shortcut_found':False,
    }
    write_report(report)
    print(json.dumps({'phase':report['phase'],'old_pids':[x['pid'] for x in report['old_processes']],
                      'old_package_id':report['old_package_id'],'new_package_id':package_id,
                      'head_sha256':report['head_sha256'],'joint_sha256':report['new_joint_sha256']},ensure_ascii=False))


def run_http_context():
    url=f'http://127.0.0.1:{PORT}/api/v4/context'
    try:
        with urllib.request.urlopen(url,timeout=8) as response:
            raw=response.read();data=json.loads(raw)
            return response.status,data,sha(raw)
    except urllib.error.HTTPError as exc:
        body=exc.read().decode('utf-8','replace')[:2000]
        raise RuntimeError(f'HTTP_{exc.code}:{body}') from None


def stop_tree(processes):
    targets=[]
    for p in processes:
        targets.extend(p.children(recursive=True));targets.append(p)
    unique={p.pid:p for p in targets}
    ordered=sorted(unique.values(),key=lambda p:len(p.parents()),reverse=True)
    for p in ordered:
        try:p.terminate()
        except psutil.NoSuchProcess:pass
    _,alive=psutil.wait_procs(ordered,timeout=20)
    if alive: raise RuntimeError('R6_SERVICE_STOP_TIMEOUT:'+','.join(str(p.pid) for p in alive))


def launch(exe, env, argv=None):
    args=argv or [str(exe),'--workspace',str(ROOT),'--port',str(PORT),'--no-browser']
    start=subprocess.STARTUPINFO(); start.dwFlags|=subprocess.STARTF_USESHOWWINDOW
    proc=subprocess.Popen(args,cwd=str(ROOT),env=env,stdin=subprocess.DEVNULL,
                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                          startupinfo=start,creationflags=subprocess.CREATE_NO_WINDOW)
    return proc


def wait_context(timeout=60):
    end=time.time()+timeout;last='NOT_READY'
    while time.time()<end:
        try:
            code,data,digest=run_http_context()
            if code==200 and data.get('context',{}).get('trade_date')=='2026-10-13':
                return {'http':code,'T0':data['context']['trade_date'],'context_token':data.get('context_token'),
                        'sha256':digest,'status':data.get('status')}
            last='CONTEXT_MISMATCH'
        except Exception as exc:
            last=type(exc).__name__+':'+str(exc)
            # A 4xx response is an application-level rejection, not a startup
            # race. Preserve its first body instead of replacing it with the
            # connection-refused error after the failed process exits.
            if isinstance(exc,RuntimeError) and str(exc).startswith('HTTP_4'):
                raise RuntimeError('R6_CONTEXT_STARTUP_REJECTED:'+str(exc)) from None
        time.sleep(1)
    raise RuntimeError('R6_CONTEXT_STARTUP_TIMEOUT:'+last)


def restore_files(report):
    for name,relative in STATIC_MAP.items():
        binding=report['old_static_assets'][name];raw=(ROOT/binding['path']).read_bytes()
        if len(raw)!=binding['bytes'] or sha(raw)!=binding['sha256']: raise ValueError('R6_ROLLBACK_STATIC_BACKUP_CORRUPT:'+name)
        atomic(ROOT/'src/workbench_service/static'/relative,raw)
    joint_raw=(ROOT/report['rollback_joint_path']).read_bytes()
    if sha(joint_raw)!=report['old_joint_pointer_sha256']: raise ValueError('R6_ROLLBACK_JOINT_BACKUP_CORRUPT')
    atomic(JOINT_AUTHORITY,joint_raw)


def activate():
    report=read_report()
    if report.get('phase')!='PREPARED': raise ValueError('R6_CUTOVER_NOT_PREPARED')
    procs=service_processes()
    if len(procs)!=1 or procs[0].pid not in [row['pid'] for row in report['old_processes']]:
        raise ValueError('R6_LIVE_SERVICE_IDENTITY_CHANGED')
    env=procs[0].environ()
    if not env.get('V4_NATIVE_PG_DSN') or not env.get('V4_NATIVE_PG_READER_DSN'):
        raise ValueError('R6_CONTROLLED_PG_ENVIRONMENT_UNAVAILABLE')
    pointer=JOINT_AUTHORITY.read_bytes()
    if sha(pointer)!=report['old_joint_pointer_sha256']: raise ValueError('R6_ACTIVE_JOINT_COMPARE_AND_SWAP_FAILED')
    head=ROOT/report['head_path']
    if sha(head.read_bytes())!=report['head_sha256']: raise ValueError('R6_HEAD_CHANGED_BEFORE_CUTOVER')
    status=json.loads((ROOT/report['runtime_status_path']).read_bytes())
    if status.get('auto_daily_enabled') is not False: raise ValueError('R6_AUTO_DAILY_NOT_PAUSED')
    for name,relative in STATIC_MAP.items():
        current=(ROOT/'src/workbench_service/static'/relative).read_bytes()
        binding=report['old_static_assets'][name]
        if len(current)!=binding['bytes'] or sha(current)!=binding['sha256']:
            raise ValueError('R6_STATIC_COMPARE_AND_SWAP_FAILED:'+name)
    report['phase']='STOPPING_OLD_SERVICE';write_report(report)
    stop_tree(procs)
    try:
        report['phase']='INSTALLING_NEW_JOINT_AND_UI';write_report(report)
        for name,relative in STATIC_MAP.items():
            binding=report['new_ui_assets'][name];raw=(ROOT/binding['path']).read_bytes()
            if len(raw)!=binding['bytes'] or sha(raw)!=binding['sha256']: raise ValueError('R6_NEW_UI_ASSET_HASH_MISMATCH:'+name)
            atomic(ROOT/'src/workbench_service/static'/relative,raw)
        # The authority is the Joint document itself. `new_joint_pointer` is
        # only its immutable file binding (path/bytes/hash), and writing that
        # binding as the authority makes readers fail on the missing snapshot.
        pointer_raw=(ROOT/report['new_joint_pointer']['path']).read_bytes()
        if len(pointer_raw)!=report['new_joint_pointer']['bytes'] or sha(pointer_raw)!=report['new_joint_pointer']['sha256']:
            raise ValueError('R6_NEW_JOINT_FILE_BINDING_MISMATCH')
        pointer=json.loads(pointer_raw)
        if (pointer.get('business_token'),pointer.get('T0'))!=(report['business_token'],report['T0']):
            raise ValueError('R6_NEW_JOINT_CONTEXT_MISMATCH')
        atomic(JOINT_AUTHORITY,pointer_raw)
        new_exe=Path(report['new_executable'])
        launched=launch(new_exe,env)
        report['new_launcher_pid']=launched.pid;report['phase']='STARTING_NEW_SERVICE';write_report(report)
        context=wait_context()
        report['new_context_readback']=context;report['phase']='NEW_SERVICE_STARTED';write_report(report)
        print(json.dumps({'phase':report['phase'],'pid':launched.pid,'context':context},ensure_ascii=False))
    except Exception as exc:
        report['cutover_error']=type(exc).__name__+':'+str(exc);report['phase']='ROLLING_BACK';write_report(report)
        new_procs=service_processes()
        if new_procs: stop_tree(new_procs)
        restore_files(report)
        old_exe=Path(report['old_executable'])
        old_argv=report['old_processes'][0]['cmdline']
        old_proc=launch(old_exe,env,old_argv)
        report['rollback_launcher_pid']=old_proc.pid
        report['phase']='ROLLED_BACK';write_report(report)
        raise


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=('prepare','activate'))
    parser.add_argument('--package-id',default='V4_PACKAGE_1.1.4_4c031f43788d')
    args=parser.parse_args()
    if args.mode=='prepare':prepare(args.package_id)
    else:activate()


if __name__=='__main__':main()
