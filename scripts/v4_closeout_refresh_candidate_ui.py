"""Refresh isolated candidate presentation while preserving PG namespace and Head."""
import argparse
import json
import os
from pathlib import Path
import sys

SOURCE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(SOURCE),str(SOURCE/'src')]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();root=Path(args.root).resolve();out=Path(args.out).resolve()
    if not root.is_relative_to(Path('G:/codex_tmp').resolve()) or out.drive.upper()!='G:':raise ValueError('ISOLATED_G_CANDIDATE_REQUIRED')
    out.mkdir(parents=True,exist_ok=False)
    os.environ.update(TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp')
    from workbench_service.current_v4_context import canonical,digest
    from workbench_service.v4_daily_refresh import atomic_bytes
    from workbench_service.joint_release import AUTHORITY,activate,checked_path
    head=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';before=head.read_bytes()
    authority_path=root/AUTHORITY;prior=authority_path.read_bytes();authority=json.loads(prior)
    if authority.get('full_product_release') is not False:raise ValueError('PRESENTATION_ONLY_FULL_RELEASE_FORBIDDEN')
    (out/'AUTHORITY_BEFORE.bin').write_bytes(prior)
    sources={name:SOURCE/'src/workbench_service/static/research'/name for name in ('index.html','style.css')}
    sources.update({name:SOURCE/'src/workbench_service/static/core-product-r1'/name for name in ('app.js','api.js','components.js','stock.js','replay.js','labels.js','rotation-auto-acceptance.js')})
    build=digest(canonical({name:digest(path.read_bytes()) for name,path in sources.items()}))
    assets={}
    for name,path in sources.items():
        raw=path.read_bytes();target=root/'data/v4/ui_releases'/build/name
        atomic_bytes(target,raw)
        assets[name]=dict(path=target.relative_to(root).as_posix(),bytes=len(raw),sha256=digest(raw))
        if name.endswith('.js'):atomic_bytes(root/'src/workbench_service/static/core-product-r1'/name,raw)
    authority.update(ui_build_id=build,ui_assets=assets)
    def health(candidate):
        for binding in candidate['ui_assets'].values():checked_path(root,binding)
        if head.read_bytes()!=before:raise ValueError('PROTECTED_OPERATIONAL_HEAD_CHANGED')
        return dict(pass_=True,**{'pass':True},scope='PRESENTATION_BYTES_ONLY_BROWSER_QA_SEPARATE')
    receipt=activate(root,authority,digest(prior),health)
    if head.read_bytes()!=before:raise ValueError('PROTECTED_OPERATIONAL_HEAD_CHANGED')
    atomic_bytes(out/'RESULT.json',canonical(dict(contract_id='V4_ISOLATED_PRESENTATION_REFRESH_CLOSEOUT_R1',
        root=str(root),ui_build_id=build,assets=assets,head_sha256=digest(before),production_changed=False,
        full_product_release=False,browser_acceptance='REQUIRED_SEPARATELY',receipt=receipt)))

if __name__=='__main__':main()
