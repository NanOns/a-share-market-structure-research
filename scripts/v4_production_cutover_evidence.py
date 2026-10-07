"""Atomic evidence for the explicitly authorized 2026-10-07 product cutover."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/v4_production_cutover_20261007'
sys.path.insert(0, str(ROOT / 'src'))


def write(path, value):
    path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf8')
    temp = path.with_name(path.name + '.tmp')
    with temp.open('wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def binding(path, owner_stage='GOVERNANCE', contract_id=None):
    raw = (ROOT / path).read_bytes()
    return dict(path=path, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                owner_stage=owner_stage, contract_id=contract_id or path)


def entry():
    documents = []
    for path in sorted(Path('D:/Users/lps/Desktop/阶段任务').glob('0[0-5]_V4_*20261007.md')):
        target = 'docs/evidence/v4_production_cutover_20261007/' + path.name
        write(target, path.read_bytes())
        documents.append(binding(target))
    assert len(documents) == 6
    protected = ['AGENTS.md','config/v4_current_stage_authority_v2.json',
        'data/v4/V4_DATA_ACCEPTED_HEAD.json','data/v4/V4_STAGE_ACCEPTED_HEAD.json',
        'data/v4/V4_15_ACCEPTED_HEAD.json','config/v4_19_focus_source_cutover_contract_v1.json',
        'config/v4_20_default_ui_cutover_contract_v1.json','config/v4_17_shadow_ui_source_v1.json',
        'src/workbench_service/shadow_context.py']
    write(REPORT / 'ENTRY_BASELINE.json', dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
        worktree=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True),
        documents=documents, protected=[binding(p) for p in protected],
        stage='P0-1', contract=documents[1], next_stage='P0-2/P0-3_AFTER_READER_GATE'))


def fingerprint(side):
    from scripts.forward_final_bootstrap import source_roots
    rows=[]
    for root in source_roots():
        if not root.is_dir(): raise ValueError('TDX_ROOT_MISSING:'+str(root))
        for directory, folders, files in os.walk(root,followlinks=False):
            folders.sort()
            for name in sorted(files):
                p=Path(directory)/name;s=p.stat();h=hashlib.sha256()
                with p.open('rb') as f:
                    while chunk:=f.read(8*1024*1024):h.update(chunk)
                after=p.stat()
                if (s.st_size,s.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('TDX_CHANGED_DURING_READ')
                rows.append(dict(path=p.as_posix(),size=s.st_size,mtime_ns=s.st_mtime_ns,sha256=h.hexdigest()))
    write(REPORT / ('TDX_'+side+'_FINGERPRINT.json'),dict(files=rows,roots=[str(r) for r in source_roots()]))
    print(side, len(rows), flush=True)


if __name__=='__main__':
    if sys.argv[1]=='entry':entry()
    elif sys.argv[1] in ('PRE','POST'):fingerprint(sys.argv[1])
