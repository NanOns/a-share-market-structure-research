"""Stage-local receipts; never rewrite an earlier task's frozen evidence."""
import json,os
import subprocess
from pathlib import Path
from scripts.fp01_evidence import ROOT, write, ref

def operational_path(name,*,for_write=False):
    allowed={'v4_market_operational_authority_v1.json','v4_sector_operational_authority_v1.json',
        'v4_stock_operational_authority_v1.json','v4_market_center_authority_v1.json','v4_forward_operational_authority_v1.json'}
    if name not in allowed:raise ValueError('UNAPPROVED_DAILY_OPERATIONAL_AUTHORITY')
    directory=os.environ.get('R2_DAILY_AUTHORITY_DIR')
    if directory:
        base=(ROOT/directory).resolve();scope=(ROOT/'data/v4/r2_daily_candidates').resolve()
        if not base.is_relative_to(scope):raise ValueError('DAILY_AUTHORITY_NAMESPACE_OUTSIDE_APPROVED_ROOT')
        candidate=base/name
        if for_write or candidate.exists():return candidate
    return ROOT/'config'/name

def enter(stage):
    successor=os.environ.get('R2_DAILY_EVIDENCE_DIR')
    if successor:
        base=(ROOT/successor).resolve();allowed=(ROOT/'docs/evidence/r2_daily_runs').resolve()
        if not base.is_relative_to(allowed):raise ValueError('DAILY_EVIDENCE_NAMESPACE_OUTSIDE_APPROVED_ROOT')
        out=base/f'fp{stage:02d}'
    else:out=ROOT/f'docs/evidence/fp{stage:02d}_20261008'
    if (out/'ENTRY.json').exists():raise ValueError('FROZEN_STAGE_RECEIPT_REQUIRES_NEW_NAMESPACE')
    cards=ROOT/'docs/evidence/fp01_20261008/tasks'
    phase=json.loads((ROOT/'reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json').read_bytes())
    assert phase['phase0_status']=='FULL_PASS'
    protected=json.loads((ROOT/'docs/evidence/fp02_20261008/ENTRY.json').read_bytes())['protected']
    write(out/'ENTRY.json',dict(stage=f'FP{stage:02d}',contract=f'FP{stage:02d}_DOMAIN_DELIVERY_V1',
        baseline=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        task=ref(next(cards.glob(f'{stage:02d}_*'))),master=ref(next(cards.glob('00_*'))),
        phase0='FULL_PASS',driver_sync='No driver-named chat or repository file in current inventory; latest supplied task cards govern.',
        protected=protected,acceptance='IN_PROGRESS',next_stage='REAL_SOURCE_BINDING_AND_IMPLEMENTATION',
        successor_upgrade=ref('docs/upgrade/R2_FIELD_ADMISSION_CONTINUATION_20261008.md') if successor else None))
    return out

def check_protected(out):
    rows=json.loads((out/'ENTRY.json').read_bytes())['protected'];changed=[]
    for old in rows:
        now=ref(old['path'])
        if now['sha256']!=old['sha256']:changed.append(old['path'])
    assert not changed,changed
    return dict(checked=len(rows),changed=changed)
