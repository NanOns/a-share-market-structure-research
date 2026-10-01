"""Authorized R3 batch: atomic evidence, protected heads, no runtime promotion."""
from scripts.next_round_bundle_r1 import ROOT,bind,read,write,atomic_bytes,exact,sha
from datetime import datetime,timezone
from pathlib import Path
import subprocess
P='reports/next_round_r3/'
DOCROOT='docs/evidence/next_round_r3/'
AUDIT=DOCROOT+'V4_R2_BATCH_INDEPENDENT_EXTERNAL_AUDIT_R2_20261002.md'
MASTER=DOCROOT+'V4_NEXT_ROUND_EXECUTION_MASTER_R3_20261002.md'
TASKS=['V4_11_R3A_TARGET_DATE_REQUIRED_FACT_PRODUCERS_TASK_20261002.md','V4_11_R3B_EPISODE_SAFETY_LOO_INPUT_CLOSURE_TASK_20261002.md','V4_11_R3C_REAL_FULL_MARKET_DAG_REPLAY_TASK_20261002.md','V4_A02_DOWNSTREAM_AMENDMENT_PROMOTION_TASK_20261002.md','V4_A05_V4_08_B2_SCOPED_AMENDMENT_PROMOTION_TASK_20261002.md','V4_A04_GO_FORWARD_PRODUCER_SCOPED_ACCEPTANCE_TASK_20261002.md','V4_PARALLEL_SCOPED_FORMALIZATION_CONSOLIDATION_TASK_20261002.md']
PERMISSIONS=dict(production=False,shadow=False,focus=False,global_mandatory_adoption=False)
def verify_protected():
    entry=read(P+'BATCH_STAGE_ENTRY_R1.json')
    for ref in entry['protected_heads']:
        try:exact(ref)
        except ValueError:
            # Reuse only the pre-existing, externally carried original-byte
            # archives. No newly inferred or semantic-equivalence bypass.
            from workbench_analysis.parallel_scoped_acceptance_r1 import validate_protected_binding
            validate_protected_binding(ROOT,ref)
    return entry
def prepare():
    baseline='d119c0526e44a819f85b4917159d3eeb5daadf2a'
    remote=subprocess.check_output(['git','rev-parse','origin/codex/v4-system-reform'],cwd=ROOT,text=True).strip()
    subprocess.run(['git','merge-base','--is-ancestor',baseline,remote],cwd=ROOT,check=True)
    for name in TASKS+[Path(AUDIT).name,Path(MASTER).name]:
        atomic_bytes(DOCROOT+name,(Path('D:/Users/lps/Desktop/阶段任务/新建文件夹')/name).read_bytes())
    from workbench_analysis.dm01_accepted_chain_v1 import validate_head_v2
    data=read('data/v4/V4_DATA_ACCEPTED_HEAD.json');gate=validate_head_v2(ROOT,data)
    entry=dict(contract_id='V4_NEXT_ROUND_EXECUTION_ENTRY_R3',implementation_baseline=baseline,remote_head=remote,descendant_verified=True,
        local_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        authority=bind(AUDIT),master=bind(MASTER),task_bindings=[bind(DOCROOT+n) for n in TASKS],
        observed_at_utc=datetime.now(timezone.utc).isoformat(),
        phase0=dict(status='DEGRADED_PASS',scope='ACCEPTED_DATA_INPUT_PREFLIGHT',head_validation=gate),
        protected_heads=[bind(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT/'data/v4').glob('*HEAD*.json'))],
        baseline_tracked_paths=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True,encoding='utf8').splitlines(),
        baseline_unrelated_changes=subprocess.check_output(['git','status','--porcelain=v1'],cwd=ROOT,text=True,encoding='utf8').splitlines(),
        permissions=PERMISSIONS,DataHead='KEEP_2026-09-30',StageHead='KEEP_V4_00_TO_V4_10_ACCEPTED',
        execution_acceptance='AUTHORIZED_SEVEN_TASKS_CANDIDATE_AND_SCOPED_ONLY',v4_12_authorized=False,
        next_stage='STOP_AFTER_UNIFIED_COMMIT_PUSH_WAIT_EXTERNAL_ACCEPTANCE')
    write(P+'BATCH_STAGE_ENTRY_R1.json',entry);verify_protected();return entry
if __name__=='__main__':print(prepare()['phase0']['status'])
