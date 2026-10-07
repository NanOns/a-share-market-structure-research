"""Literal legacy release source replay; never repairs the current release pointer."""
import hashlib,json,os,subprocess,sys
from tests.final_disposable_paths import resolve_destination_inside_root
from functools import lru_cache
from pathlib import Path,PureWindowsPath
from scripts.full_chain_repair_io import ROOT,write,binding
P='reports/forward_r2_remainder_consolidated_20261007/'


def calculate(root):
    env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME')}
    env['PYTHONPATH']=str(root/'src')
    code="import json,sys;from common.identity import computation_identity;print(json.dumps(computation_identity(sys.argv[1]),sort_keys=True))"
    return json.loads(subprocess.check_output([sys.executable,'-c',code,str(root)],cwd=root,env=env,text=True))


@lru_cache(maxsize=1)
def profile():
    release_path='reports/current/CURRENT_RELEASE.json'
    raw=(ROOT/release_path).read_bytes();release=json.loads(raw)
    expected=release['latest_release']['computation_identity']
    base=Path('G:/codex_tmp/test_temp').resolve();out=resolve_destination_inside_root(base,'remainder_legacy_v1_identity_'+expected['sha256'][:12])
    if not out.is_relative_to(base):raise ValueError('LEGACY_IDENTITY_ROOT_ESCAPE')
    recovered=[]
    for path,sha in expected['files'].items():
        name=PureWindowsPath(path)
        if name.drive or name.root or '..' in name.parts or name.parts[0] not in ('src','config','docs'):raise ValueError('LEGACY_IDENTITY_PATH_ESCAPE')
        commits=['433c3378d4bc4db572f95de20cadbf899c2a04ce']+subprocess.check_output(['git','log','--all','--format=%H','--',path],cwd=ROOT,text=True).splitlines()
        for commit in dict.fromkeys(commits):
            blob=subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT)
            variants=[blob,blob.replace(b'\r\n',b'\n'),blob.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')]
            selected=next((v for v in variants if hashlib.sha256(v).hexdigest()==sha),None)
            if selected is not None:break
        else:raise ValueError('LEGACY_SOURCE_SHA_UNRECOVERABLE:'+path)
        target=resolve_destination_inside_root(out,path);target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and target.read_bytes()!=selected:raise ValueError('LEGACY_IDENTITY_EXISTING_BYTES_CHANGED')
        if not target.exists():
            temp=target.with_name(target.name+'.legacy.tmp');temp.write_bytes(selected);os.replace(temp,target)
        recovered.append(dict(path=path,sha256=sha,bytes=len(selected),source_commit=commit,
            git_blob=subprocess.check_output(['git','rev-parse',commit+':'+path],cwd=ROOT,text=True).strip()))
    target=resolve_destination_inside_root(out,release_path);target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists() and target.read_bytes()!=raw:raise ValueError('LEGACY_RELEASE_CHANGED')
    if not target.exists():
        temp=target.with_name(target.name+'.legacy.tmp');temp.write_bytes(raw);os.replace(temp,target)
    actual=calculate(out)
    if actual!=expected:raise ValueError('LEGACY_IDENTITY_ACTUAL_ENVIRONMENT_OR_SOURCE_MISMATCH')
    current=calculate(ROOT)
    drift=[dict(path=path,legacy_sha256=sha,current_sha256=current['files'].get(path))
           for path,sha in expected['files'].items() if current['files'].get(path)!=sha]
    write(P+'IA05_LEGACY_V1_IDENTITY_REPLAY.json',dict(status='PASS_HISTORICAL_ONLY',root=str(out),
        release=binding(release_path),expected=expected,actual=actual,recovered=recovered,
        current_actual_identity=current,current_source_drift=drift,
        current_release_pointer_updated=False,current_computation_identity_repaired=False,
        environment='Actual system Python without compatible FEP model PYTHONPATH; no mocked dependency metadata'))
    return out


if __name__=='__main__':print(profile())
