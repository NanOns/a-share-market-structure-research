import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write
from workbench_service.joint_release import AUTHORITY,validate
OUT=ROOT/'docs/evidence/r2_structural_fields_continuation_20261008'
def serve():
    import os,shutil
    from workbench_service.v4_server import serve_v4
    sandbox=Path('E:/codex_tmp/r2_structural_preview');previous=Path('E:/codex_tmp/r2_native_core_preview')
    for p in previous.rglob('*'):
        if p.is_file() and p.relative_to(previous).parts[0] in ('data','config'):
            target=sandbox/p.relative_to(previous)
            if not target.exists():
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(p,target) if p.relative_to(previous).parts[0]=='config' else os.link(p,target)
    candidate=json.loads((OUT/'CANDIDATE.json').read_bytes());manifest=validate(ROOT,candidate)
    for binding in [candidate['snapshot']['manifest'],manifest['database'],*manifest['sources'].values(),*candidate['ui_assets'].values()]:
        target=sandbox/binding['path'];target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():shutil.copyfile(ROOT/binding['path'],target)
    write(sandbox/AUTHORITY,candidate);validate(sandbox,candidate);serve_v4(sandbox,'127.0.0.1',28772)


if __name__=='__main__':serve()
