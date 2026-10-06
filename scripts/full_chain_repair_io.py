"""Atomic, repository-only repair evidence. Never writes to input directories."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'reports/full_chain_repair_20261006/'

def binding(path):
    raw = (ROOT / path).read_bytes()
    return dict(path=path, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def write(path, value, raw=False):
    target = (ROOT / path).resolve()
    if not target.is_relative_to(ROOT):
        raise ValueError('REPAIR_OUTPUT_OUTSIDE_REPOSITORY')
    data = value if raw else (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)+'\n').encode()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name+'.repair.tmp')
    with temp.open('wb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    os.replace(temp, target)
    return binding(path)

def capture():
    paths = subprocess.check_output(['git','ls-files'], cwd=ROOT, text=True, encoding='utf8').splitlines()
    protected = [p for p in paths if ('HEAD' in p and p.startswith('data/')) or p.startswith('src/workbench_db/migrations/') or p.startswith('migrations/')]
    return dict(baseline_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                protected=[binding(p) for p in protected],
                unrelated_worktree=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True,encoding='utf8').splitlines())

if __name__ == '__main__':
    source=Path('D:/Users/lps/Desktop/阶段任务/V4_00_TO_V4_22_PLUS_FEP_FULL_CHAIN_CODE_ALGORITHM_CONTRACT_AUDIT_AND_REPAIR_MASTER_R1_20261006.md')
    master=write('docs/evidence/full_chain_repair_20261006/'+source.name,source.read_bytes(),raw=True)
    entry=capture()
    entry.update(master=master,stage_contract='FULL_CHAIN_REPAIR_R1_BATCH_A_TO_E',acceptance='AUTHORIZED_CANDIDATE_REPAIR_ONLY',
                 next_stage='INDEPENDENT_EXTERNAL_REAUDIT',user_override='CONTINUE_ALL_REPAIR_BATCHES_WITHOUT_BATCH_A_STOP')
    write(PREFIX+'ENTRY_BASELINE.json',entry)
