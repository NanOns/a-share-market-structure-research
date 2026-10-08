"""Stage-local receipts; never rewrite an earlier task's frozen evidence."""
import json
import subprocess
from pathlib import Path
from scripts.fp01_evidence import ROOT, write, ref

def enter(stage):
    out=ROOT/f'docs/evidence/fp{stage:02d}_20261008'
    cards=ROOT/'docs/evidence/fp01_20261008/tasks'
    phase=json.loads((ROOT/'reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json').read_bytes())
    assert phase['phase0_status']=='FULL_PASS'
    protected=json.loads((ROOT/'docs/evidence/fp02_20261008/ENTRY.json').read_bytes())['protected']
    write(out/'ENTRY.json',dict(stage=f'FP{stage:02d}',contract=f'FP{stage:02d}_DOMAIN_DELIVERY_V1',
        baseline=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        task=ref(next(cards.glob(f'{stage:02d}_*'))),master=ref(next(cards.glob('00_*'))),
        phase0='FULL_PASS',driver_sync='No driver-named chat or repository file in current inventory; latest supplied task cards govern.',
        protected=protected,acceptance='IN_PROGRESS',next_stage='REAL_SOURCE_BINDING_AND_IMPLEMENTATION'))
    return out

def check_protected(out):
    rows=json.loads((out/'ENTRY.json').read_bytes())['protected'];changed=[]
    for old in rows:
        now=ref(old['path'])
        if now['sha256']!=old['sha256']:changed.append(old['path'])
    assert not changed,changed
    return dict(checked=len(rows),changed=changed)
