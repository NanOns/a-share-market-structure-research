"""R5 owner-authority repair: frozen accepted inputs, sequential gates."""
from scripts.next_round_execution_r4 import ROOT, bind, read, write, atomic_bytes, exact, sha, PERMISSIONS
from scripts.next_round_execution_r4 import verify_protected as verify_r4
from pathlib import Path
from datetime import datetime, timezone
import subprocess

P='reports/next_round_r5/'
DOCROOT='docs/evidence/next_round_r5/'
MASTER=DOCROOT+'V4_NEXT_ROUND_EXECUTION_MASTER_R5_20261002.md'
AUDIT=DOCROOT+'V4_R4_INDEPENDENT_EXTERNAL_AUDIT_R1_20261002.md'
TASKS=['V4_11_R5A_OWNER_INPUT_AUTHORITY_PARITY_REPAIR_TASK_20261002.md','V4_11_R5B_D2_EVENT_REBUILD_CAPABILITY_CLOSURE_TASK_20261002.md']
UPGRADE='docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'
BASELINE='1dee36ae83fb63b6a7fe57e05ccb63bb1e0c5099'

def verify_protected():
    verify_r4()
    entry=read(P+'BATCH_STAGE_ENTRY.json')
    for ref in entry['frozen_R4_sources']:exact(ref)
    for ref in entry['owner_authority']:exact(ref)
    return entry

def prepare():
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==BASELINE
    for name in [Path(MASTER).name,Path(AUDIT).name,*TASKS]:
        atomic_bytes(DOCROOT+name,(Path('D:/Users/lps/Desktop/阶段任务/新建文件夹')/name).read_bytes())
    for folder in (P,DOCROOT,'reports/v4_11_r5a/','reports/v4_11_r5/','data/v4/confirmation_candidates_r5/'):
        atomic_bytes(folder+'.gitattributes',b'* -text\n'+(b'*.gz filter=lfs diff=lfs merge=lfs -text\n' if folder.startswith('data/') else b''))
    authority=[bind(p) for p in ('data/v4/V4_07_ACCEPTED_HEAD.json','data/v4/V4_07_ACCEPTED_HEAD_AMENDMENT_A02_R1.json','data/v4/V4_09_ACCEPTED_HEAD.json','data/v4/V4_09_ACCEPTED_HEAD_AMENDMENT_A02_R1.json','data/v4/V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1.json','src/v4/base_seed.py','src/v4/stock_prewatch.py','config/v4_07_base_seed_contract_v1.json','config/v4_07_parameter_set_v1.json','config/v4_09_parameter_set_v1.json')]
    for stage in ('V4_07','V4_09'):
        pointer=read('data/v4/'+stage+'_ACCEPTED_HEAD_AMENDMENT_A02_R1.json');payload=read(exact(pointer['payload']).relative_to(ROOT).as_posix())
        exact(payload['artifact'])
        for ref in payload['algorithm_parameter_bindings']:exact(ref)
    manifest=read('reports/next_round_r4/BATCH_SOURCE_MANIFEST.json')
    from workbench_analysis.dm01_accepted_chain_v1 import validate_head_v2
    gate=validate_head_v2(ROOT,read('data/v4/V4_DATA_ACCEPTED_HEAD.json'))
    write(P+'BATCH_STAGE_ENTRY.json',dict(contract_id='V4_NEXT_ROUND_R5_STAGE_ENTRY_V1',baseline=BASELINE,authority=bind(AUDIT),master=bind(MASTER),tasks=[bind(DOCROOT+t) for t in TASKS],upgrade=bind(UPGRADE),upgrade_sections=['13A','14.2','14.3','22.1','31','34A.2A','78'],phase0=dict(status='DEGRADED_PASS',scope='ACCEPTED_INPUT_PREFLIGHT',data_gate=gate),owner_authority=authority,frozen_R4_sources=manifest['artifacts'],observed_at_utc=datetime.now(timezone.utc).isoformat(),baseline_unrelated_changes=subprocess.check_output(['git','status','--porcelain=v1'],cwd=ROOT,text=True,encoding='utf8').splitlines(),permissions=PERMISSIONS,StageHead='KEEP_V4_00_TO_V4_10_ACCEPTED',DataHead='KEEP_2026-09-30',V4_12_runtime=False,next_stage='R5A_PARITY_PASS_SEAL_THEN_R5B_COMMIT_PUSH_STOP'))
    verify_protected();print('DEGRADED_PASS')

if __name__=='__main__':prepare()
