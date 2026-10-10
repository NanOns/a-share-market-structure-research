"""Real isolated install/repair/version rollback/uninstall; never restart Windows."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import winreg
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from workbench_desktop.storage import atomic
KEY=r'Software\Microsoft\Windows\CurrentVersion\Run'
VALUE='DaAV4PackagedIsolatedQA'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def reg():
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,KEY) as key:
        try:return winreg.QueryValueEx(key,VALUE)[0]
        except FileNotFoundError:return None
def uninstall_entry(directory):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Uninstall') as key:
        for i in range(winreg.QueryInfoKey(key)[0]):
            name=winreg.EnumKey(key,i)
            if not name.startswith('DaAV4PackageIsolatedQA_'):continue
            with winreg.OpenKey(key,name) as item:
                try:location=winreg.QueryValueEx(item,'InstallLocation')[0]
                except FileNotFoundError:continue
                if Path(location).resolve()==Path(directory).resolve():return name
    return None
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--build-receipt',required=True)
    parser.add_argument('--workspace',default='G:/codex_tmp/test_temp/package_installer_workspace')
    args=parser.parse_args()
    os.environ.update(TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp',PYTHONDONTWRITEBYTECODE='1')
    receipt=json.loads(Path(args.build_receipt).read_bytes())
    if not receipt.get('qa') or receipt['run_key']!=VALUE:raise ValueError('ISOLATED_QA_INSTALLER_REQUIRED')
    if reg() is not None:raise ValueError('QA_REGISTRY_VALUE_ALREADY_EXISTS')
    installer=Path(receipt['installer']);base=Path(receipt['program_root'])
    if sha(installer)!=receipt['installer_sha256']:raise ValueError('INSTALLER_CHANGED')
    root=Path(args.workspace).resolve()
    if not root.is_relative_to(Path('G:/codex_tmp/test_temp').resolve()) or not root.name.startswith('package_installer_workspace'):
        raise ValueError('EXPLICIT_G_INSTALLER_QA_WORKSPACE_REQUIRED')
    if root.exists():raise ValueError('FRESH_INSTALLER_QA_WORKSPACE_REQUIRED')
    for rel in ('config','data/v4','runtime/desktop','runtime/dynamic_daily'):(root/rel).mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/'config/dm01_go_forward_runtime_contract_r4r1.json',root/'config/dm01_go_forward_runtime_contract_r4r1.json')
    for head in ('V4_OPERATIONAL_RESEARCH_HEAD.json','V4_DATA_ACCEPTED_HEAD.json'):
        shutil.copyfile(ROOT/'data/v4'/head,root/'data/v4'/head)
    (root/'runtime/desktop/app.lock').write_bytes(b'0')
    with sqlite3.connect(root/'runtime/dynamic_daily/qa-retained.sqlite3') as db:
        db.execute('create table retained(k text primary key,v text)')
        db.executemany('insert into retained values (?,?)',[('auto_enabled','false'),('user_cancel','CANCELLED')])
    protected={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}
    checks=[];commands=[];started=datetime.now(timezone.utc).isoformat()
    def unchanged():
        if {str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}!=protected:
            raise ValueError('INSTALLER_CHANGED_PERSISTENT_WORKSPACE')
    def command(exe,argv,expected=0,verify=True):
        result=subprocess.run([str(exe),*argv],env=dict(os.environ),timeout=600)
        commands.append(dict(executable=str(exe),arguments=argv,exit_code=result.returncode,expected=expected))
        if (expected==0 and result.returncode!=0) or (expected=='NONZERO' and result.returncode==0):
            raise ValueError('UNEXPECTED_SETUP_EXIT:'+str(result.returncode))
        # The self-relocated Windows uninstaller releases its cleanup/mutex
        # just after its launching process returns; don't overlap versions.
        if Path(exe).name.lower()=='unins000.exe':time.sleep(1)
        if verify:unchanged()
    a=base/(receipt['release']+'_A');b=base/(receipt['release']+'_B')
    if a.exists() or b.exists():raise ValueError('QA_VERSION_DIRECTORIES_ALREADY_EXIST')
    common=['/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/WORKSPACE='+str(root)]
    import msvcrt
    with (root/'runtime/desktop/app.lock').open('r+b') as held:
        msvcrt.locking(held.fileno(),msvcrt.LK_NBLCK,1)
        try:command(installer,common+['/DIR='+str(a)],'NONZERO',verify=False)
        finally:held.seek(0);msvcrt.locking(held.fileno(),msvcrt.LK_UNLCK,1)
    unchanged()
    if a.exists():raise ValueError('BUSY_INSTALL_WROTE_PROGRAM')
    checks.append('BUSY_WORKSPACE_INSTALL_REFUSED_BEFORE_DEPLOY')
    command(installer,common+['/DIR=C:\\codex_package_forbidden'],'NONZERO')
    checks.append('NON_G_PROGRAM_ROOT_FAILS_BEFORE_EXTRACTION')
    command(installer,['/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',
        '/WORKSPACE='+str(root/'nonexistent'),'/DIR='+str(a)],'NONZERO')
    if (root/'nonexistent').exists():raise ValueError('INSTALLER_CREATED_EMPTY_WORKSPACE')
    checks.append('MISSING_WORKSPACE_FAILS_WITHOUT_EMPTY_DATA_ROOT')
    config=root/'config/dm01_go_forward_runtime_contract_r4r1.json'
    original_config=config.read_bytes();config_key=str(config.relative_to(root))
    source=Path('G:/codex_tmp/package_setup')
    def source_identity():
        return {str(p.relative_to(source)):(p.stat().st_size,p.stat().st_mtime_ns)
                for p in source.rglob('*') if p.is_file()}
    before=source_identity()
    try:
        altered=json.loads(original_config)
        altered['read_only_tdx_roots'].append(str(source))
        config.write_text(json.dumps(altered),encoding='utf-8')
        protected[config_key]=sha(config)
        command(installer,common+['/DIR='+str(a)],'NONZERO')
        if source_identity()!=before:raise ValueError('SETUP_WROTE_CONFIGURED_READ_ONLY_SOURCE')
    finally:
        config.write_bytes(original_config);protected[config_key]=sha(config)
    unchanged()
    checks.append('CONFIGURED_NESTED_G_READ_ONLY_SOURCE_REFUSED_BEFORE_ANY_EXTRACTION')
    command(installer,common+['/DIR='+str(a)])
    if reg() is not None:raise ValueError('FIRST_INSTALL_ENABLED_LOGIN_WITHOUT_CHOICE')
    checks.append('FIRST_INSTALL_LOGIN_DEFAULT_OFF')
    command(installer,common+['/DIR='+str(a),'/TASKS=autologin'])
    if sha(a/'DaAV4.exe')!=receipt['executable_sha256'] or str(a/'DaAV4.exe') not in reg():raise ValueError('INSTALL_OR_LOGIN_BINDING_FAILED')
    checks.append('ACTUAL_INSTALL_AND_ISOLATED_CURRENT_USER_LOGIN_VALUE')
    command(installer,common+['/DIR='+str(a)])
    if str(a/'DaAV4.exe') not in reg():raise ValueError('REPAIR_LOST_LOGIN_CHOICE')
    checks.append('SAME_VERSION_REPAIR_PRESERVES_DATA_AND_LOGIN_CHOICE')
    command(installer,common+['/DIR='+str(a),'/TASKS='])
    if reg() is not None:raise ValueError('EXPLICIT_LOGIN_DISABLE_IGNORED')
    command(installer,common+['/DIR='+str(a),'/TASKS=autologin'])
    if str(a/'DaAV4.exe') not in reg():raise ValueError('EXPLICIT_LOGIN_ENABLE_FAILED')
    checks.append('EXPLICIT_LOGIN_DISABLE_AND_ENABLE_RESPECTED')
    command(installer,common+['/DIR='+str(b)])
    if str(b/'DaAV4.exe') not in (reg() or ''):raise ValueError('NEW_VERSION_LOGIN_NOT_SELECTED')
    if not uninstall_entry(a) or not uninstall_entry(b) or uninstall_entry(a)==uninstall_entry(b):
        raise ValueError('VERSION_UNINSTALL_IDENTITIES_NOT_INDEPENDENT')
    checks.append('INDEPENDENT_VERSION_DEPLOY_AND_LOGIN_SWITCH')
    command(installer,common+['/DIR='+str(a)])
    if str(a/'DaAV4.exe') not in reg():raise ValueError('PROGRAM_ROLLBACK_NOT_SELECTED')
    checks.append('SAME_BINARY_DIRECTORY_ROLLBACK_REHEARSAL_NO_HEAD_RESTORE')
    with (root/'runtime/desktop/app.lock').open('r+b') as held:
        msvcrt.locking(held.fileno(),msvcrt.LK_NBLCK,1)
        try:command(a/'unins000.exe',['/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART'],'NONZERO',verify=False)
        finally:held.seek(0);msvcrt.locking(held.fileno(),msvcrt.LK_UNLCK,1)
    unchanged()
    if not (a/'DaAV4.exe').is_file():raise ValueError('BUSY_UNINSTALL_REMOVED_PROGRAM')
    checks.append('BUSY_WORKSPACE_UNINSTALL_REFUSED')
    command(b/'unins000.exe',['/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART'])
    if str(a/'DaAV4.exe') not in reg():raise ValueError('OLD_UNINSTALL_REMOVED_OTHER_VERSION_LOGIN')
    if not uninstall_entry(a) or uninstall_entry(b):raise ValueError('OTHER_VERSION_UNINSTALL_ENTRY_CHANGED')
    checks.append('UNSELECTED_VERSION_UNINSTALL_PRESERVES_SELECTED_LOGIN')
    command(a/'unins000.exe',['/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART'])
    if reg() is not None or (a/'DaAV4.exe').exists() or (b/'DaAV4.exe').exists() or uninstall_entry(a):raise ValueError('UNINSTALL_CLEANUP_FAILED')
    checks.append('SELECTED_VERSION_UNINSTALL_RETAINS_HEAD_SQLITE_CANCEL_AND_SETTINGS')
    report=dict(status='PASS',contract_id='V4_ISOLATED_ACTUAL_INSTALLER_QA_V1',checks=checks,
        commands=commands,build_receipt_sha256=sha(args.build_receipt),installer_sha256=sha(installer),
        workspace=str(root),protected_files=protected,started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),
        production_modified=False,actual_windows_reboot=False,physical_ui_verified=False,
        compatibility_claim='Same frozen binary in two isolated version directories; actual historical binary/schema compatibility not granted',
        external_acceptance='NOT_GRANTED')
    output=Path(args.build_receipt).parent/'INSTALLER_QA_RECEIPT.json'
    atomic(output,report);print(str(output))
if __name__=='__main__':main()
