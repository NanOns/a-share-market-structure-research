"""Freeze the externally authorized rollback-only round and all KEEP evidence."""
import sys,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from scripts.prepare_r17_governance import atomic
from workbench_analysis.v4_14_replay_io import ref,publish
BASE='f7b3402e4fbd5c98f4e76e3a56042a84960e120a'
DOCS=['V4_R18R1R1_INDEPENDENT_EXTERNAL_AUDIT_R3_20261003.md','V4_14_R18R1R1R1A_ROLLBACK_DRILL_RECEIPT_TASK_20261003.md','V4_14_R18R1R1R1B_INDEPENDENT_ROLLBACK_ORACLE_SEAL_TASK_20261003.md','V4_NEXT_ROUND_EXECUTION_MASTER_R18R1R1R1_20261003.md']
def run():
    assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==BASE
    for folder in ['docs/evidence/r18_rollback','reports/r18r1r1r1a','reports/r18r1r1r1b']:atomic(folder+'/.gitattributes',b'* -text\n')
    for name in DOCS:atomic('docs/evidence/r18_rollback/'+name,(Path('D:/Users/lps/Desktop/阶段任务')/name).read_bytes())
    old=json.loads((ROOT/'reports/r18r1r1a/stage_contract.json').read_bytes())
    evidence=[ref(ROOT,p.relative_to(ROOT).as_posix()) for p in sorted((ROOT/'reports/v4_14_replay_r18/full_dag_r5').rglob('*')) if p.is_file()]
    evidence+=[ref(ROOT,p) for p in ['reports/r18r1r1b/final_full_dag_gate.json','reports/r18r1r1c/V4_14_RUNTIME_CANDIDATE_R18R1R1_SEAL.json','reports/r18r1r1c/independent_consumption_oracle_gate.json','reports/r18r1r1c/real_scoped_recheck.json','config/v4_14_precall_consumption_mapping_r18r1r1_v1.json']]
    return publish(ROOT,'reports/r18r1r1r1a/stage_contract.json',dict(baseline=BASE,master=ref(ROOT,'docs/evidence/r18_rollback/'+DOCS[-1]),task=ref(ROOT,'docs/evidence/r18_rollback/'+DOCS[1]),protected=old['protected'],keep_evidence=evidence,governance=[ref(ROOT,p) for p in ['config/v4_capability_cutover_policy_v1.json','scripts/promote_r17b_v4_13.py','src/workbench_analysis/v4_13_io.py']],NEXT='R18R1R1R1B_AFTER_ROLLBACK_DRILL_PASS'))
if __name__=='__main__':print(json.dumps(run()))
