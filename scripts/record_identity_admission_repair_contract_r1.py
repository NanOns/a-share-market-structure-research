"""Freeze scope before repair; neither market capture nor admission occurs."""
import json
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.record_next_stage_contract_r1 import text
from workbench_analysis.v4_14_replay_io import publish, ref
OUT='docs/evidence/identity_admission_repair_r1_20261010'
BASE='d7b19feabc8e17ca4948bfdef38047f10fd6f97c'


def main():
    for name in ('TMP','TEMP','TMPDIR'):os.environ[name]='G:/codex_tmp'
    names=['V4_NEXT_ROUND_IDENTITY_SOURCE_AND_ADMISSION_REPAIR_TASK_R1_20261010.md',
           'V4_NEXT_STAGE_A_E_INDEPENDENT_AUDIT_R1_20261010.md']
    sources=[text(OUT+'/task_sources/'+n,(Path('D:/Users/lps/Desktop/阶段任务')/n).read_bytes()) for n in names]
    phase='reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json'
    assert json.loads((ROOT/phase).read_bytes())['phase0_status']=='FULL_PASS'
    heads={p:ref(ROOT,p) for p in ['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json']}
    publish(ROOT,OUT+'/STAGE_CONTRACT.json',dict(contract_id='IDENTITY_SOURCE_ADMISSION_REPAIR_R1',
        exact_BASE=BASE,remote_baseline=BASE,card_BASE_diff=[],sources=sources,
        phase0=ref(ROOT,phase),phase0_status='FULL_PASS',
        latest_upgrade_contract=ref(ROOT,'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'),
        sections=['78','80','81','90'],protected_heads_before=heads,
        allowed=['identity candidate and gate classification','isolated trusted-review contract',
                 'D2 followup classification','read-only scoped product QA'],
        forbidden=['TDX writes','28765 restart','real admission source changes','Writer Grant issuance','historical PIT backfill'],
        next_stage='Independent scoped review; real 10/12 source capture; separately authorized production loading',
        formal_acceptance=False))
    print(json.dumps(dict(exact_BASE=BASE,phase0='FULL_PASS',heads=heads)))


if __name__=='__main__':main()
