"""Immutable UI successor for accepted current named membership relations."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.joint_release import AUTHORITY,validate
from workbench_service.current_v4_context import digest,canonical
OUT=ROOT/'docs/evidence/r2_structural_fields_continuation_20261008'

def main():
    if (OUT/'CANDIDATE.json').exists():raise RuntimeError('STRUCTURAL_CANDIDATE_FROZEN')
    before=(ROOT/AUTHORITY).read_bytes();c=json.loads(before);source=ROOT/'src/workbench_service/static/research';build=digest(canonical({p.name:digest(p.read_bytes()) for p in sorted(source.iterdir()) if p.is_file()}));assets={}
    for p in sorted(source.iterdir()):
        if p.is_file():
            target=ROOT/'data/v4/ui_releases'/build/p.name
            if not target.exists():write(target,p.read_bytes())
            assert target.read_bytes()==p.read_bytes();assets[p.name]=ref(target)
    c.update(ui_build_id=build,ui_assets=assets);validate(ROOT,c);assert (ROOT/AUTHORITY).read_bytes()==before
    write(OUT/'CANDIDATE.json',c);write(OUT/'PREDECESSOR.json',dict(sha256=digest(before),authority=json.loads(before)));print(json.dumps(dict(result='STAGED',ui_build_id=build,context_token='research-v4-'+c['snapshot']['manifest']['sha256'])))
if __name__=='__main__':main()
