"""Exact immutable Forward candidate, using a separate existing preview root."""
import json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write
from workbench_service.joint_release import AUTHORITY,validate
from workbench_service.current_v4_context import digest
from workbench_service.v4_server import serve_v4

if __name__=='__main__':
    sandbox=Path('E:/codex_tmp/r2_focus_preview');out=ROOT/'docs/evidence/r2_forward_continuation_20261008'
    candidate=json.loads((out/'READY_CANDIDATE.json').read_bytes());manifest=validate(ROOT,candidate)
    for binding in [candidate['snapshot']['manifest'],manifest['database'],*manifest['sources'].values(),*candidate['ui_assets'].values()]:
        target=sandbox/binding['path'];target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists() or digest(target.read_bytes())!=binding['sha256']:shutil.copyfile(ROOT/binding['path'],target)
    write(sandbox/AUTHORITY,candidate);validate(sandbox,candidate);serve_v4(sandbox,'127.0.0.1',28767)
