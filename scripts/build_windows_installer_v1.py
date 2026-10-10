"""Build the single G-temp-safe installer after binding a passed frozen S1 receipt."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from workbench_desktop.storage import atomic
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--package',required=True)
    parser.add_argument('--s1-report',required=True)
    parser.add_argument('--qa',action='store_true')
    args=parser.parse_args()
    os.environ.update(TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp',PYTHONDONTWRITEBYTECODE='1')
    sys.dont_write_bytecode=True
    package=Path(args.package).resolve()
    receipt=json.loads(Path(args.s1_report).read_bytes())
    if receipt.get('status')!='PASS' or receipt.get('FROZEN_EXE_END_TO_END_PASS') is not True:
        raise ValueError('S1_FROZEN_END_TO_END_PASS_REQUIRED')
    executable=package/'DaAV4.exe'
    if receipt['executable_sha256']!=sha(executable):raise ValueError('S1_EXE_IDENTITY_MISMATCH')
    manifest=json.loads((package/'_internal/resources/package_manifest.json').read_bytes())
    if sha(package/'_internal/resources/package_manifest.json')!=receipt['manifest']['resource_manifest_sha']:
        raise ValueError('S1_PACKAGE_MANIFEST_CHANGED')
    for item in manifest['resources']:
        if sha(package/'_internal/resources'/item['path'])!=item['sha256']:
            raise ValueError('S1_PACKAGE_RESOURCE_CHANGED:'+item['path'])
    release=manifest['build_release_id']
    mode='qa' if args.qa else 'delivery'
    build=Path('G:/codex_tmp/windows_installer_v1')/release/mode
    build.mkdir(parents=True,exist_ok=True)
    contents=dict(contract_id='V4_COMPLETE_INSTALLED_PROGRAM_FILES_V1',release=release,
        files=[dict(path=p.relative_to(package).as_posix(),sha256=sha(p),bytes=p.stat().st_size)
            for p in sorted(package.rglob('*')) if p.is_file()])
    content_manifest=build/'PACKAGE_FILES_MANIFEST.json'
    atomic(content_manifest,contents)
    verify=[];chunks=[]
    for index in range(0,len(contents['files']),128):
        name='VerifyProgramChunk'+str(index//128);chunks.append(name)
        verify.append('procedure '+name+';\nbegin')
        for item in contents['files'][index:index+128]:
            name_path=item['path'].replace('/',chr(92)).replace("'","''").replace('{','{{')
            verify.append("  if GetSHA256OfFile(ExpandConstant('{app}\\"+name_path+"'))<>'"+item['sha256']+
                "' then RaiseException('INSTALLED_PROGRAM_FILE_SHA_MISMATCH:"+name_path+"');")
        verify.append('end;')
    verify.append('procedure VerifyProgramFiles;\nbegin')
    verify.extend('  '+name+';' for name in chunks)
    verify.append("  if GetSHA256OfFile(ExpandConstant('{app}\\PACKAGE_FILES_MANIFEST.json'))<>'"+sha(content_manifest)+
        "' then RaiseException('INSTALLED_CONTENT_MANIFEST_CHANGED');\nend;")
    program_root=r'G:\codex_tmp\test_temp\package_installer_versions' if args.qa else r'G:\codex work\大A交易_安装版\releases'
    app_id='DaAV4PackageIsolatedQA' if args.qa else 'DaAV4FullPackage'
    run_key='DaAV4PackagedIsolatedQA' if args.qa else 'DaAV4Packaged'
    values={'RELEASE':release,'PROGRAM_ROOT':program_root,'APP_ID':app_id,'RUN_KEY':run_key,
            'PACKAGE':str(package),'OUTPUT':str(build),'CONTENT_MANIFEST':str(content_manifest),
            'CONTENT_MANIFEST_SHA':sha(content_manifest),'VERIFY_PROGRAM_FILES_CODE':'\n'.join(verify),
            'WITH_SHORTCUTS':'False' if args.qa else 'True'}
    iss=(ROOT/'scripts/windows_package_setup_v1.iss').read_text(encoding='utf-8')
    for key,value in values.items():iss=iss.replace('@'+key+'@',value)
    script=build/'setup.iss';script.write_text(iss,encoding='utf-8-sig')
    compiler=Path('G:/codex_tmp/installer_tools/inno710/ISCC.exe')
    compiled=subprocess.run([str(compiler),str(script)],capture_output=True,text=True,encoding='utf-8',errors='replace')
    (build/'compile.log').write_text(compiled.stdout+compiled.stderr,encoding='utf-8')
    if compiled.returncode:raise ValueError('INNO_COMPILE_FAILED:'+str(build/'compile.log'))
    core=build/'setup-core.exe'
    wrapper=(ROOT/'scripts/windows_package_setup_bootstrap_v1.cs').read_text(encoding='utf-8')
    values['PAYLOAD_SHA']=sha(core)
    values['CONTENT_MANIFEST_SHA']=sha(content_manifest)
    for key,value in values.items():wrapper=wrapper.replace('@'+key+'@',value)
    source=build/'setup-bootstrap.cs';source.write_text(wrapper,encoding='utf-8-sig')
    target=build/('大A交易系统安装程序_QA.exe' if args.qa else '大A交易系统安装程序.exe')
    csc=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
    command=[str(csc),'/nologo','/target:winexe','/platform:x64','/optimize+',
        '/reference:System.Windows.Forms.dll','/reference:System.Web.Extensions.dll',
        '/out:'+str(target),'/resource:'+str(core)+',setup-core',str(source)]
    result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace')
    (build/'bootstrap_compile.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise ValueError('BOOTSTRAP_COMPILE_FAILED:'+str(build/'bootstrap_compile.log'))
    report=dict(contract_id='V4_G_ONLY_FULL_PACKAGE_INSTALLER_V1',status='BUILT_NOT_ACCEPTED',
        release=release,qa=args.qa,installer=str(target),installer_sha256=sha(target),
        app_id_policy='Prefix plus SHA256 of exact program directory; repairs reuse own uninstall identity; old versions cannot remove newer uninstall entry',
        payload_sha256=sha(core),executable_sha256=sha(executable),s1_report=str(Path(args.s1_report).resolve()),
        s1_report_sha256=sha(args.s1_report),program_root=program_root,run_key=run_key,app_id=app_id,
        build_at=datetime.now(timezone.utc).isoformat(),inno_compiler=str(compiler),
        inno_compiler_sha256=sha(compiler),bootstrap_compiler=str(csc),bootstrap_compiler_sha256=sha(csc),
        content_manifest=str(content_manifest),content_manifest_sha256=sha(content_manifest),
        complete_program_file_count=len(contents['files']),complete_program_bytes=sum(x['bytes'] for x in contents['files']),
        required_os='Windows 10/11 x64 with inbox .NET Framework 4.x',signed=False,
        production_takeover=False,external_acceptance='NOT_GRANTED')
    atomic(build/'INSTALLER_BUILD_RECEIPT.json',report)
    print(json.dumps(report,ensure_ascii=False))
    return 0
if __name__=='__main__':raise SystemExit(main())
