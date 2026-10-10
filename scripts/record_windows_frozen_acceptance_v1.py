"""Bind actual S1 reports without granting production or external acceptance."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from workbench_desktop.storage import atomic
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def copy_evidence(source,target):
    import tempfile
    fd,name=tempfile.mkstemp(dir=target.parent,prefix=target.name+'.',suffix='.tmp')
    try:
        with os.fdopen(fd,'wb') as out,Path(source).open('rb') as incoming:
            shutil.copyfileobj(incoming,out);out.flush();os.fsync(out.fileno())
        os.replace(name,target)
    finally:Path(name).unlink(missing_ok=True)
def main():
    p=argparse.ArgumentParser()
    for name in ('runtime','tray','daily','junit','crash-process','recovery-process'):p.add_argument('--'+name,required=True)
    args=p.parse_args();folder=ROOT/'docs/evidence/windows_full_package_20261010'
    os.environ.update(TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp',PYTHONDONTWRITEBYTECODE='1')
    sys.dont_write_bytecode=True
    reports={name:json.loads(Path(getattr(args,name)).read_bytes()) for name in ('runtime','tray','daily')}
    if any(r['status']!='PASS' for r in reports.values()):raise ValueError('ALL_ACTUAL_REPORTS_MUST_PASS')
    daily=reports['daily'];release=daily['manifest']['build_release_id'];exe=Path(daily['executable'])
    if daily.get('FROZEN_EXE_END_TO_END_PASS') is not True or daily.get('failure_matrix_complete') is not True:
        raise ValueError('ACTUAL_NUMERIC_COMPLETE_MATRIX_REQUIRED')
    if not daily.get('packaged_home_capture_notice_present') or not daily.get('paused_daily_status_verified'):
        raise ValueError('REAL_PACKAGED_HOME_AND_PAUSED_CAPTURE_NOTICE_REQUIRED')
    if sha(exe)!=daily['executable_sha256']:raise ValueError('EXE_CHANGED')
    crash=json.loads(Path(args.crash_process).read_bytes());recovery=json.loads(Path(args.recovery_process).read_bytes())
    if crash['exit_code']!=70 or recovery['exit_code']!=0 or not crash['intentional_cas_pending_crash']:
        raise ValueError('ACTUAL_PROCESS_CRASH_AND_RECOVERY_EXITS_REQUIRED')
    if any(r['executable_sha256']!=sha(exe) or Path(r['workspace']).resolve()!=Path(daily['workspace']).resolve()
           for r in (crash,recovery)):
        raise ValueError('CRASH_RECOVERY_PROCESS_IDENTITY_MISMATCH')
    if any(r['manifest']['build_release_id']!=release or Path(r['executable']).resolve()!=exe.resolve() for r in reports.values()):
        raise ValueError('REPORT_RELEASE_MISMATCH')
    if any(c['status']!='PASS' for name in ('runtime','tray') for c in reports[name]['checks']):raise ValueError('CHECK_FAILED')
    junit=ET.parse(args.junit).getroot();suites=[junit] if junit.tag=='testsuite' else junit.findall('testsuite')
    counts={k:sum(int(s.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
    if counts['failures'] or counts['errors'] or counts['tests']<35:raise ValueError('SOURCE_REGRESSION_NOT_PASS')
    previous=json.loads((folder/'S0_STAGE_RECEIPT.json').read_bytes())
    heads=[]
    for binding in previous['protected_heads_before']:
        actual=sha(ROOT/binding['path'])
        if actual!=binding['sha256']:raise ValueError('PRODUCTION_HEAD_CHANGED')
        heads.append(dict(path=binding['path'],sha256=actual,unchanged=True))
    for row in previous['protected_algorithm_bytes']:
        if sha(ROOT/row['binding']['path'])!=row['exact_current_sha256']:raise ValueError('ALGORITHM_ORIGINAL_CHANGED')
    with urlopen('http://127.0.0.1:28765/api/operations/status',timeout=8) as response:production=json.loads(response.read())
    net=subprocess.check_output(['powershell','-NoProfile','-Command',
        '(Get-NetTCPConnection -LocalPort 28765 -State Listen | Select-Object -ExpandProperty OwningProcess -Unique)'],text=True).strip()
    evidence=[]
    for name in ('runtime','tray','daily','junit'):
        output=folder/('S1_'+name.upper()+('.xml' if name=='junit' else '.json'))
        copy_evidence(getattr(args,name),output)
        evidence.append(dict(path=output.relative_to(ROOT).as_posix(),sha256=sha(output),bytes=output.stat().st_size))
    for name in ('crash_process','recovery_process'):
        output=folder/('S1_'+name.upper()+'.json')
        copy_evidence(getattr(args,name),output)
        evidence.append(dict(path=output.relative_to(ROOT).as_posix(),sha256=sha(output),bytes=output.stat().st_size))
    receipt=dict(contract_id='V4_WINDOWS_PACKAGE_S1_STAGE_V1',
        acceptance='S1_PASS_FROZEN_RUNTIME_TRAY_FUNCTIONS_AND_FULL_NUMERIC_REPLAY',
        design=previous['design'],consulted=previous['consulted'],inherited_phase0=previous['inherited_phase0'],
        stage_contract='S1_STAGE_CONTRACT.md',release=release,exe=str(exe),executable_sha256=sha(exe),
        manifest_resource_sha=daily['manifest']['resource_manifest_sha'],
        exact_source_identity=daily['manifest']['source_sha'],evidence=evidence,source_regression=counts,
        runtime_checks=len(reports['runtime']['checks']),native_tray_function_checks=len(reports['tray']['checks']),
        actual_packaged_home_notice_and_pause_readback=True,
        FROZEN_EXE_END_TO_END_PASS=True,actual_numeric=True,first_capture_claim=False,
        evidence_kind=daily['evidence_kind'],failure_matrix_complete=True,
        actual_crash_exit_code=crash['exit_code'],actual_recovery_exit_code=recovery['exit_code'],
        transaction_state=daily['transaction']['state'],replay_head_before=daily['predecessor_sha256'],
        replay_head_after=daily['head_sha256'],protected_production_heads=heads,
        production=dict(pid=int(net),service_state=production.get('service_state'),
            context_token=production.get('context_token'),daily_update=production.get('daily_update'),
            takeover='NOT_EXECUTED',settings_modified_by_packaging=False),
        all_accepted_algorithm_originals_unchanged=True,development_python_or_PATH_used_by_EXE=False,
        remaining=['S2_INSTALLER_VERIFICATION','ACTUAL_WINDOWS_REBOOT_LOGIN','PHYSICAL_UI_TWO_DISPLAY_ENVIRONMENTS','SEPARATELY_AUTHORIZED_PRODUCTION_TAKEOVER'],
        next_stage='S2_INSTALLER_QA_AND_INDEPENDENT_REAL_MACHINE_ACCEPTANCE',
        external_acceptance='NOT_GRANTED',observed_at=datetime.now(timezone.utc).isoformat())
    target=folder/'S1_STAGE_RECEIPT.json';atomic(target,receipt)
    ledger=json.loads((folder/'INDEPENDENT_AUDIT_ITEMS.json').read_bytes())
    for row in ledger['items']:
        row['status']='ENGINEERING_FROZEN_PASS_INDEPENDENT_ACCEPTANCE_PENDING'
        row['frozen_evidence']='S1_STAGE_RECEIPT.json'
        row['external_acceptance']='NOT_GRANTED'
    atomic(folder/'INDEPENDENT_AUDIT_ITEMS.json',ledger)
    print(json.dumps(dict(acceptance=receipt['acceptance'],path=str(target),bytes=target.stat().st_size),ensure_ascii=False))
if __name__=='__main__':main()
