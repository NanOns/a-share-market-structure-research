"""Build an isolated UI-only engineering successor; never publish production.

Frozen owner bytes remain unchanged. The new UI has no external acceptance and
does not grant full_product_release. Browser QA is a separate required result.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

SOURCE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SOURCE), str(SOURCE / 'src')]
sys.dont_write_bytecode = True
os.environ.update(TMP='G:/codex_tmp', TEMP='G:/codex_tmp', TMPDIR='G:/codex_tmp')


def main():
    p=argparse.ArgumentParser();p.add_argument('--frozen',required=True);p.add_argument('--candidate',required=True);p.add_argument('--out',required=True);p.add_argument('--default-product',action='store_true');a=p.parse_args()
    frozen,candidate,out=(Path(x).resolve() for x in (a.frozen,a.candidate,a.out))
    if any(x.drive.upper()!='G:' for x in (frozen,candidate,out)) or candidate.exists():raise SystemExit('NEW_G_CANDIDATE_REQUIRED')
    if not candidate.is_relative_to(Path('G:/codex_tmp').resolve()):raise SystemExit('ISOLATED_TEMP_CANDIDATE_REQUIRED')
    out.mkdir(parents=True,exist_ok=True)
    from workbench_service.current_v4_context import canonical,digest
    from workbench_service.v4_daily_refresh import atomic_bytes
    from workbench_service.joint_release import AUTHORITY,activate,validate,checked_path
    def ref(path):
        raw=path.read_bytes();return dict(path=path.relative_to(candidate).as_posix(),bytes=len(raw),sha256=digest(raw))
    before={name:digest((frozen/name).read_bytes()) for name in (AUTHORITY,'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json')}
    linked=0
    for directory,subdirs,files in os.walk(frozen):
        relative=Path(directory).relative_to(frozen)
        subdirs[:]=[name for name in subdirs if name not in ('runtime','__pycache__','.git','.pytest_cache')]
        destination=candidate/relative;destination.mkdir(parents=True,exist_ok=True)
        for name in files:
            if name.endswith('.pyc'):continue
            source,target=Path(directory)/name,destination/name
            if relative.parts and relative.parts[0]=='config':shutil.copy2(source,target)
            else:os.link(source,target);linked+=1
    asset_sources={name:SOURCE/'src/workbench_service/static/research'/name for name in ('index.html','style.css','labels.js','stock.js','replay.js')}
    asset_sources.update({name:SOURCE/'src/workbench_service/static'/('core-product-r1' if a.default_product else 'r43-compat')/name for name in ('app.js','api.js','components.js')})
    if a.default_product:
        asset_sources.update({name:SOURCE/'src/workbench_service/static/core-product-r1'/name for name in ('stock.js','replay.js','labels.js')})
    build=digest(canonical({name:digest(path.read_bytes()) for name,path in asset_sources.items()}))
    assets={}
    for name,path in asset_sources.items():
        target=candidate/'data/v4/ui_releases'/build/name;atomic_bytes(target,path.read_bytes());assets[name]=ref(target)
    # The default operational dispatcher binds its three compatibility assets
    # through the owner registry, so update only those presentation bindings.
    head_path=candidate/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';head=json.loads(head_path.read_bytes())
    registry=json.loads(checked_path(candidate,head['registry']).read_bytes())
    ui_changes={}
    for name in (() if a.default_product else ('app.js','api.js','components.js')):
        relative='src/workbench_service/static/r43-compat/'+name
        atomic_bytes(candidate/relative,asset_sources[name].read_bytes())
        new=ref(candidate/relative)
        original=next(b for b in registry['bindings'] if b['path']==relative)
        ui_changes[relative]=dict(before=original,after=new)
        registry['bindings']=[new if b['path']==relative else b for b in registry['bindings']]
        if 'accepted_algorithm_bindings' in head:
            head['accepted_algorithm_bindings']=[new if b['path']==relative else b for b in head['accepted_algorithm_bindings']]
    if not a.default_product:
        registry_path=candidate/'data/v4/ui_engineering_successors'/build/'BUILDER_REGISTRY.json'
        atomic_bytes(registry_path,canonical(registry));head['registry']=ref(registry_path)
        atomic_bytes(head_path,canonical(head))
    from workbench_analysis.operational_successor_v1 import validate as validate_owner
    validate_owner(candidate,head)
    authority=json.loads((candidate/AUTHORITY).read_bytes())
    if authority.get('full_product_release') is not False:raise SystemExit('SCOPED_UI_CANNOT_INHERIT_FULL_RELEASE')
    authority.update(ui_build_id=build,ui_assets=assets)
    expected=digest((candidate/AUTHORITY).read_bytes())
    validate(candidate,authority)
    def byte_health(value):
        if value.get('full_product_release') is not False:raise ValueError('SCOPED_UI_GATE_FULL_RELEASE_FORBIDDEN')
        for binding in value['ui_assets'].values():checked_path(candidate,binding)
        return {'pass':True,'scope':'UI_BYTES_ONLY_BROWSER_ACCEPTANCE_SEPARATE'}
    receipt=activate(candidate,authority,expected,byte_health)
    after={name:digest((frozen/name).read_bytes()) for name in before}
    if before!=after:raise SystemExit('FROZEN_AUTHORITY_CHANGED')
    result=dict(contract='V4_UI_ENGINEERING_ONLY_SUCCESSOR_V1',scope='PRESENTATION_BYTE_BINDING_ONLY; BROWSER_QA_REQUIRED',production_activated=False,full_product_release=False,independent_external_accepted=False,runtime_root=str(candidate),source_root=str(SOURCE),ui_build_id=build,assets=assets,ui_changes=ui_changes,frozen_protected_before=before,frozen_protected_after=after,unchanged_owners=head['owners'],hardlinked_immutable_files=linked,joint_receipt=receipt)
    atomic_bytes(out/'UI_CANDIDATE_BUILD.json',canonical(result));print(json.dumps(dict(candidate=str(candidate),ui_build_id=build,production_activated=False)))


if __name__=='__main__':main()
