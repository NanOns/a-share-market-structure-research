"""Serve a frozen candidate in an E-drive isolated root."""
import json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write
from scripts.run_r2_focus_continuation import OUT
from workbench_service.current_v4_context import digest
from workbench_service.joint_release import AUTHORITY,validate
from workbench_service.v4_server import serve_v4

def main():
    sandbox=Path('E:/codex_tmp/r2_focus_preview');sandbox.mkdir(parents=True,exist_ok=True)
    candidate=json.loads((OUT/'CANDIDATE.json').read_bytes())
    manifest=validate(ROOT,candidate)
    bindings=[candidate['snapshot']['manifest'],manifest['database'],*manifest['sources'].values(),*candidate['ui_assets'].values()]
    for binding in bindings:
        target=sandbox/binding['path'];target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists() or digest(target.read_bytes())!=binding['sha256']:shutil.copyfile(ROOT/binding['path'],target)
    for name in ['v4_research_ui_authority_v1.json','v4_research_snapshot_authority_v1.json']:
        write(sandbox/'config'/name,(ROOT/'config'/name).read_bytes())
    def copy_json(binding):
        target=sandbox/binding['path'];target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/binding['path'],target)
        return json.loads(target.read_bytes())
    name='config/v4_production_runtime_authority_v1.json'
    write(sandbox/name,(ROOT/name).read_bytes())
    runtime=json.loads((ROOT/name).read_bytes());contract=copy_json(runtime['read_authority'])
    heads={k:copy_json(b) for k,b in contract['anchors'].items()}
    for b in contract['owner_heads'].values():copy_json(b)
    copy_json(heads['stage_authority']['calendar'])
    for capability in heads['permission_authority']['capability_registry'].values():
        if capability['production_permission']:
            for b in capability['accepted_receipts'].values():copy_json(b)
    write(sandbox/AUTHORITY,candidate)
    validate(sandbox,candidate)
    write(OUT/'PREVIEW_ROOT.json',dict(root=str(sandbox),url='http://127.0.0.1:28767/v4/research/focus',candidate_digest=digest((OUT/'CANDIDATE.json').read_bytes())))
    serve_v4(sandbox,'127.0.0.1',28767)

if __name__=='__main__':main()
