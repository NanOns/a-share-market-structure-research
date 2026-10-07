"""Reproduce explicit historical test profiles outside all protected roots."""
import hashlib,json,subprocess,shutil
from pathlib import Path,PureWindowsPath
from scripts.full_chain_repair_io import ROOT,write
from tests.final_disposable_paths import resolve_destination_inside_root
P='reports/forward_r2_remainder_consolidated_20261007/'
BASE=Path('E:/codex_tmp/test_temp')
def relative_reference(out,rel):
    try:target=resolve_destination_inside_root(out,rel)
    except ValueError:return None
    name=PureWindowsPath(rel);source=ROOT.joinpath(*name.parts).resolve()
    if not source.is_relative_to(ROOT):return None
    return source,target

def git_profile(name,commit):
    out=resolve_destination_inside_root(BASE,name)
    if not out.is_relative_to(BASE.resolve()) or out==BASE.resolve():raise ValueError("DISPOSABLE_PROFILE_ROOT_REQUIRED")
    if not out.exists():
        subprocess.run(['git','clone','--shared','--no-checkout',str(ROOT),str(out)],check=True)
        subprocess.run(['git','-C',str(out),'config','core.longpaths','true'],check=True)
        subprocess.run(['git','-C',str(out),'-c','core.autocrlf=false','checkout','--detach',commit],check=True)
    actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=out,text=True).strip()
    assert actual==commit
    assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=out,text=True)
    return dict(root=str(out),source_commit=commit,tracked_status='CLEAN',grants_current_permission=False)
def simulation_profile():
    out=resolve_destination_inside_root(BASE,'remainder_r24r1_simulation_profile');out.mkdir(exist_ok=True)
    for name in ('config','scripts','src','migrations'):shutil.copytree(ROOT/name,resolve_destination_inside_root(out,name),dirs_exist_ok=True)
    resolve_destination_inside_root(out,'data/v4').mkdir(parents=True,exist_ok=True)
    for path in (ROOT/'data/v4').glob('*.json'):shutil.copyfile(path,resolve_destination_inside_root(out,'data/v4/'+path.name))
    queue=['config/v4_current_stage_authority_v2.json','config/v4_16_runtime_dependencies_v3.json','config/v4_16_r23_owner_fixture_v1.json','config/v4_16_r23_snapshot_fixture_v1.json'];seen=set();refs=[]
    def walk(value):
        if isinstance(value,dict):
            if {'path','sha256'}<=value.keys():queue.append(value['path'])
            for item in value.values():walk(item)
        elif isinstance(value,list):
            for item in value:walk(item)
    while queue:
        rel=queue.pop()
        if rel in seen:continue
        seen.add(rel);pair=relative_reference(out,rel)
        if pair is None:
            print('EXCLUDED_NONRELATIVE_REFERENCE',rel,flush=True);continue
        source,target=pair
        if not source.is_file() or source.stat().st_size>10000000:continue
        raw=source.read_bytes();target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        refs.append(dict(path=rel,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        if rel.endswith('.json'):
            try:walk(json.loads(raw))
            except (ValueError,UnicodeError):pass
    deps=json.loads((ROOT/'config/v4_16_runtime_dependencies_v3.json').read_bytes())
    old=next(b for b in deps['bindings'] if b['path']=='scripts/v4_16_go_forward_input_authority.py')
    for commit in subprocess.check_output(['git','log','--format=%H','--',old['path']],cwd=ROOT,text=True).splitlines():
        raw=subprocess.check_output(['git','show',commit+':'+old['path']],cwd=ROOT)
        if hashlib.sha256(raw).hexdigest()==old['sha256']:
            resolve_destination_inside_root(out,old['path']).write_bytes(raw);old=dict(old,source_commit=commit);break
    else:raise ValueError('EXACT_V3_SOURCE_NOT_FOUND')
    if not (out/'.git').exists():subprocess.run(['git','init',str(out)],check=True)
    (out/'.git/objects/info/alternates').write_bytes(((ROOT/'.git/objects').as_posix()+'\n').encode())
    write(P+'IA05_R24R1_HISTORICAL_SIMULATION_PROFILE.json',dict(root=str(out),historical_dependency=old,inputs=[r for r in refs if r['path']!=old['path']],grants_current_permission=False,reason='Exact V3 simulation dependencies; explicit E-only profile; no current permission'))
def run():
    profiles=[git_profile('remainder_historical_stage13','7986acdb4db19e85f55045dbfc692c932d4e1499'),git_profile('remainder_entry_checkout','433c3378d4bc4db572f95de20cadbf899c2a04ce')]
    simulation_profile()
    write(P+'IA05_PINNED_HISTORICAL_TEST_PROFILES.json',dict(profiles=profiles,source_algorithms_changed=False,reader='EXACT_GIT_CHECKOUT',historical_tests=['V4_13_R15','V4_13_R16','R25_ENTRY_BASELINE','R24R1_V3_SIMULATION'],current_tests='Explicit current reader and fail-closed R25 guard',permission_changes=False))
if __name__=='__main__':run()
