"""Capture the externally authorized R18 scope and immutable baseline."""
from pathlib import Path
import subprocess
from scripts.prepare_r17_governance import ROOT,atomic,put,bind
BASE='47b7f72f374c059f35a66bf2fe298a3ec5fe7efc'
DOCS=['V4_R17R1_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md','V4_14_R18A_REPLAY_AUTHORITY_RUNTIME_HARNESS_TASK_20261003.md','V4_14_R18B_CROSS_PROCESS_FULL_DAG_REPLAY_E2E_TASK_20261003.md','V4_14_R18C_INDEPENDENT_ORACLE_REAL_SCOPED_REPLAY_SEAL_TASK_20261003.md','V4_NEXT_ROUND_EXECUTION_MASTER_R18_20261003.md']
PROTECTED=['AGENTS.md','data/v4/V4_DATA_ACCEPTED_HEAD.json','data/v4/V4_12_ACCEPTED_HEAD.json','data/v4/V4_13_ACCEPTED_HEAD.json','data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json','data/v4/V4_STAGE_ACCEPTED_HEAD.json']
def prepare():
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==BASE
    for directory in ['docs/evidence/r18','reports/r18a','reports/r18b','reports/r18c']:atomic(directory+'/.gitattributes',b'* -text\n')
    for n in DOCS:atomic('docs/evidence/r18/'+n,(Path('D:/Users/lps/Desktop/阶段任务')/n).read_bytes())
    put('reports/r18a/stage_contract.json',dict(baseline=BASE,task=bind('docs/evidence/r18/'+DOCS[1]),master=bind('docs/evidence/r18/'+DOCS[4]),external_audit=bind('docs/evidence/r18/'+DOCS[0]),protected=[bind(p) for p in PROTECTED],scope='OWNER_ORCHESTRATION_AND_REPLAY_ONLY',next='R18B_AFTER_RUNTIME_GATE_PASS',permissions=dict(production=False,shadow=False,focus=False,global_mandatory_adoption=False,DB_migration=False,Stage_advance=False,Data_advance=False),ALGORITHM_STATE_REPLAY_PASS='NOT_GRANTED_PENDING_EXTERNAL_AUDIT'))
if __name__=='__main__':prepare()
