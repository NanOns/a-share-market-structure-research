"""Record the exact externally authorized repair baseline and immutable history."""
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from scripts.prepare_r17_governance import atomic
from workbench_analysis.v4_14_replay_io import ref,publish
BASE='e07da98989fc9fa30ef2015d6ac4cd3d6e47b798'
DOCS=['V4_R18R1_INDEPENDENT_EXTERNAL_AUDIT_R2_20261003.md','V4_14_R18R1R1A_PREEXEC_EDGE_BINDING_REPAIR_TASK_20261003.md','V4_14_R18R1R1B_CROSS_PROCESS_FULL_DAG_R5_TASK_20261003.md','V4_14_R18R1R1C_INDEPENDENT_CONSUMPTION_ORACLE_TASK_20261003.md','V4_NEXT_ROUND_EXECUTION_MASTER_R18R1R1_20261003.md']

def run():
    assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==BASE
    for folder in ['docs/evidence/r18r1r1','reports/r18r1r1a','reports/r18r1r1b','reports/r18r1r1c']:atomic(folder+'/.gitattributes',b'* -text\n')
    for name in DOCS:atomic('docs/evidence/r18r1r1/'+name,(Path('D:/Users/lps/Desktop/阶段任务')/name).read_bytes())
    prior=json.loads((ROOT/'reports/r18r1a/stage_contract.json').read_bytes());old=prior['immutable_old_attempts'];old['full_dag_r4']=[ref(ROOT,p.relative_to(ROOT).as_posix()) for p in sorted((ROOT/'reports/v4_14_replay_r18/full_dag_r4').rglob('*')) if p.is_file()]
    return publish(ROOT,'reports/r18r1r1a/stage_contract.json',dict(baseline=BASE,master=ref(ROOT,'docs/evidence/r18r1r1/'+DOCS[-1]),task=ref(ROOT,'docs/evidence/r18r1r1/'+DOCS[1]),protected=prior['protected'],immutable_old_attempts=old,NEXT='R18R1R1B_AFTER_PREEXEC_PASS'))
if __name__=='__main__':print(json.dumps(run()))
