"""Deliver the S1-bound installer with precise isolated S2 acceptance limits."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from workbench_desktop.storage import atomic

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def copy_atomic(source, target):
    fd, temporary = tempfile.mkstemp(dir=target.parent, prefix=target.name+'.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as output, Path(source).open('rb') as incoming:
            shutil.copyfileobj(incoming, output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)

def main():
    parser = argparse.ArgumentParser()
    for name in ('qa-build', 'qa-report', 'delivery-build'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    os.environ.update(TMP='G:/codex_tmp', TEMP='G:/codex_tmp', TMPDIR='G:/codex_tmp')
    folder = ROOT/'docs/evidence/windows_full_package_20261010'
    s1 = json.loads((folder/'S1_STAGE_RECEIPT.json').read_bytes())
    qa_build = json.loads(Path(args.qa_build).read_bytes())
    qa = json.loads(Path(args.qa_report).read_bytes())
    delivery = json.loads(Path(args.delivery_build).read_bytes())
    if not s1['FROZEN_EXE_END_TO_END_PASS'] or qa['status'] != 'PASS':
        raise ValueError('S1_AND_ACTUAL_ISOLATED_INSTALLER_PASS_REQUIRED')
    if not qa_build['qa'] or delivery['qa'] or qa['build_receipt_sha256'] != sha(args.qa_build):
        raise ValueError('INSTALLER_REPORT_BINDING_MISMATCH')
    if len(qa['checks']) < 13 or qa['production_modified'] or qa['actual_windows_reboot']:
        raise ValueError('ISOLATED_MATRIX_SCOPE_MISMATCH')
    for build in (qa_build, delivery):
        if build['release'] != s1['release'] or build['executable_sha256'] != s1['executable_sha256']:
            raise ValueError('S1_PROGRAM_IDENTITY_CHANGED')
        if sha(build['installer']) != build['installer_sha256'] or sha(build['content_manifest']) != build['content_manifest_sha256']:
            raise ValueError('INSTALLER_OR_FILE_MANIFEST_CHANGED')
    if qa['installer_sha256'] != qa_build['installer_sha256'] or qa_build['content_manifest_sha256'] != delivery['content_manifest_sha256']:
        raise ValueError('QA_DELIVERY_PROGRAM_CONTENT_MISMATCH')
    normalized = []
    source_bindings = []
    for build, path in ((qa_build, args.qa_build), (delivery, args.delivery_build)):
        parent = Path(path).resolve().parent
        script = (parent/'setup.iss').read_text(encoding='utf-8-sig')
        for value, token in ((str(parent), '@BUILD@'), (build['program_root'], '@PROGRAM_ROOT@'),
                             (build['app_id'], '@APP_ID@'), (build['run_key'], '@RUN_KEY@')):
            script = script.replace(value, token)
        flag = 'False' if build['qa'] else 'True'
        script = script.replace('if '+flag+' then begin', 'if @SHORTCUTS@ then begin')
        script = script.replace('and '+flag+' then begin', 'and @SHORTCUTS@ then begin')
        bootstrap = (parent/'setup-bootstrap.cs').read_text(encoding='utf-8-sig')
        bootstrap = bootstrap.replace(build['program_root'], '@PROGRAM_ROOT@').replace(build['payload_sha256'], '@PAYLOAD_SHA@')
        normalized.append((script, bootstrap))
        source_bindings.append(dict(qa=build['qa'], inno_source_sha256=sha(parent/'setup.iss'),
                                    bootstrap_source_sha256=sha(parent/'setup-bootstrap.cs')))
    if normalized[0] != normalized[1]:
        raise ValueError('QA_DELIVERY_INSTALLER_LOGIC_DIFFERS_BEYOND_DECLARED_VARIANTS')
    for binding in s1['protected_production_heads']:
        if sha(ROOT/binding['path']) != binding['sha256']:
            raise ValueError('PRODUCTION_HEAD_CHANGED')
    out = Path('G:/codex work/大A交易_交付/windows_package_v1')/'installer'/s1['release']
    out.mkdir(parents=True, exist_ok=True)
    installer = out/'大A交易系统安装程序.exe'
    copy_atomic(delivery['installer'], installer)
    copy_atomic(delivery['content_manifest'], out/'PACKAGE_FILES_MANIFEST.json')
    copy_atomic(folder/'WINDOWS_PACKAGE_USER_GUIDE.md', out/'使用说明.md')
    evidence = []
    for source, name in ((args.qa_build, 'S2_QA_INSTALLER_BUILD.json'),
                         (args.qa_report, 'S2_ISOLATED_INSTALLER_QA.json'),
                         (args.delivery_build, 'S2_DELIVERY_INSTALLER_BUILD.json')):
        target = folder/name
        copy_atomic(source, target)
        evidence.append(dict(path=target.relative_to(ROOT).as_posix(), sha256=sha(target)))
    receipt = dict(contract_id='V4_WINDOWS_PACKAGE_S2_ENGINEERING_RECEIPT_V1',
        acceptance='S2_ISOLATED_INSTALLER_ENGINEERING_PASS_REAL_MACHINE_ACCEPTANCE_PENDING',
        stage_contract='S2_STAGE_CONTRACT.md', design=s1['design'], release=s1['release'],
        s1_receipt_sha256=sha(folder/'S1_STAGE_RECEIPT.json'), evidence=evidence,
        installer=str(installer), installer_sha256=sha(installer),
        executable_sha256=s1['executable_sha256'],
        complete_program_manifest_sha256=delivery['content_manifest_sha256'],
        complete_program_file_count=delivery['complete_program_file_count'],
        isolated_actual_installer_checks=len(qa['checks']),
        installer_logic_equivalence_verified=True, generated_installer_sources=source_bindings,
        qa_variant_differences=['isolated program root', 'isolated AppId and login value', 'production shortcuts disabled'],
        delivery_installer_actual_install='NOT_EXECUTED',
        actual_windows_reboot_login='NOT_EXECUTED', physical_ui_two_displays='NOT_EXECUTED',
        production_takeover='NOT_EXECUTED', production_heads_unchanged=True,
        historical_binary_schema_rollback_acceptance='NOT_GRANTED', signed=False,
        external_acceptance='NOT_GRANTED',
        next_stage='SEPARATELY_AUTHORIZED_PRODUCTION_TAKEOVER_AND_REAL_MACHINE_ACCEPTANCE',
        observed_at=datetime.now(timezone.utc).isoformat())
    atomic(folder/'S2_STAGE_RECEIPT.json', receipt)
    atomic(out/'交付收据.json', receipt)
    print(json.dumps(dict(installer=str(installer), acceptance=receipt['acceptance']), ensure_ascii=False))

if __name__ == '__main__':
    main()
