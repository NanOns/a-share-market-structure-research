"""R4 sequential contracts; immutable accepted inputs and atomic evidence."""
from scripts.next_round_execution_r3 import ROOT,bind,read,write,atomic_bytes,exact,sha,PERMISSIONS
from scripts.next_round_execution_r3 import verify_protected as verify_r3
from datetime import datetime,timezone
from pathlib import Path
import subprocess

P='reports/next_round_r4/'
DOCROOT='docs/evidence/next_round_r4/'
MASTER=DOCROOT+'V4_NEXT_ROUND_EXECUTION_MASTER_R4_20261002.md'
AUDIT=DOCROOT+'V4_R3_INDEPENDENT_EXTERNAL_AUDIT_R1_20261002.md'
TASKS=['V4_11_R4A_ADJUSTMENT_BASIS_PARITY_REPAIR_TASK_20261002.md','V4_11_R4B_REAL_DAG_REBUILD_CAPABILITY_CLOSURE_TASK_20261002.md']
UPGRADE='docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'

def verify_protected():
    verify_r3()
    entry=read(P+'BATCH_STAGE_ENTRY.json')
    for ref in entry['protected_inputs']:
        try:exact(ref)
        except ValueError:
            if ref['path'] in ('data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json','data/v4/V4_03_ACCEPTED_HEAD.json'):
                from workbench_analysis.parallel_scoped_acceptance_r1 import validate_protected_binding
                validate_protected_binding(ROOT,ref)
            else:
                # Preservation proof for three pre-existing CRLF contracts only.
                # Never used by any producer/business source admission.
                proof=read(P+'PROTECTED_CONFIG_BYTE_REPRESENTATIONS.json')
                item=next((x for x in proof['representations'] if x['original_binding']==ref),None)
                if item is None:raise
                raw=exact(item['original_bytes_archive']).read_bytes();current=exact(item['git_representation']).read_bytes()
                if raw.replace(b'\r\n',b'\n')!=current:raise ValueError('EXACT_CONFIG_BYTE_PRESERVATION_REQUIRED')
    if (ROOT/'data/v4/V4_11_ACCEPTED_HEAD.json').exists():raise ValueError('V4_11_HEAD_FORBIDDEN')
    return entry

def prepare():
    baseline='65774de20108beafaa15c0b557b4cd2ee58edb29'
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if head!=baseline:raise ValueError('AUDITED_BASELINE_REQUIRED')
    for name in [Path(MASTER).name,Path(AUDIT).name,*TASKS]:
        atomic_bytes(DOCROOT+name,(Path('D:/Users/lps/Desktop/阶段任务/新建文件夹')/name).read_bytes())
    from workbench_analysis.dm01_accepted_chain_v1 import validate_head_v2
    gate=validate_head_v2(ROOT,read('data/v4/V4_DATA_ACCEPTED_HEAD.json'))
    paths=set(subprocess.check_output(['git','ls-files','data/v4/*HEAD*.json'],cwd=ROOT,text=True).splitlines())
    paths.update(['data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R3.json','reports/v4_11_r3b/R3B_SEALED_PRODUCER_SET.json'])
    paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'config').glob('v4_03*.json'))
    paths.update(['src/v4/factors/core.py','src/v4/research_state.py','src/v4/state_provenance.py','src/workbench_analysis/today_research_scanner_v3_3.py','src/workbench_analysis/today_research_factors_v3_3.py','config/research_attention_v3.yaml'])
    entry=dict(contract_id='V4_NEXT_ROUND_R4_STAGE_ENTRY_V1',baseline=head,authority=bind(AUDIT),master=bind(MASTER),tasks=[bind(DOCROOT+t) for t in TASKS],upgrade=bind(UPGRADE),upgrade_sections=['3B.6','13A','34','34A.2A','78'],observed_at_utc=datetime.now(timezone.utc).isoformat(),phase0=dict(status='DEGRADED_PASS',scope='ACCEPTED_INPUT_PREFLIGHT',data_gate=gate),protected_inputs=[bind(p) for p in sorted(paths)],baseline_unrelated_changes=subprocess.check_output(['git','status','--porcelain=v1'],cwd=ROOT,text=True,encoding='utf8').splitlines(),permissions=PERMISSIONS,acceptance='R4A_PARITY_THEN_SEAL_THEN_R4B_CANDIDATE_ONLY',next_stage='STOP_AFTER_UNIFIED_COMMIT_PUSH_WAIT_EXTERNAL_ACCEPTANCE',V4_12_runtime=False)
    write(P+'BATCH_STAGE_ENTRY.json',entry);verify_protected();print('DEGRADED_PASS')

if __name__=='__main__':prepare()
