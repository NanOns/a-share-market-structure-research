"""Capture the repair authority and freeze explicit engineering producer fixtures."""
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from scripts.prepare_r17_governance import atomic
from workbench_analysis.v4_14_replay_io import ref,publish
BASE='70fc9b050497e798d077480d0ae4adf97e9824c6'
DOCS=['V4_R18_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md','V4_14_R18R1A_OWNER_EDGE_COMPLETE_REPLAY_HARNESS_TASK_20261003.md','V4_14_R18R1B_CROSS_PROCESS_FULL_DAG_R4_CANONICAL_EVIDENCE_TASK_20261003.md','V4_14_R18R1C_INDEPENDENT_EDGE_ORACLE_REAL_RECHECK_SEAL_TASK_20261003.md','V4_NEXT_ROUND_EXECUTION_MASTER_R18R1_20261003.md']
def run():
    assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==BASE
    for directory in ['docs/evidence/r18r1','reports/r18r1a','reports/r18r1b','reports/r18r1c']:atomic(directory+'/.gitattributes',b'* -text\n')
    for name in DOCS:atomic('docs/evidence/r18r1/'+name,(Path('D:/Users/lps/Desktop/阶段任务')/name).read_bytes())
    old={}
    for directory in ['full_dag','full_dag_r2','full_dag_r3']:
        prefix='reports/v4_14_replay_r18/'+directory
        old[directory]=[ref(ROOT,p.relative_to(ROOT).as_posix()) for p in sorted((ROOT/prefix).rglob('*')) if p.is_file()]
    publish(ROOT,'reports/r18r1a/stage_contract.json',dict(baseline=BASE,task=ref(ROOT,'docs/evidence/r18r1/'+DOCS[1]),master=ref(ROOT,'docs/evidence/r18r1/'+DOCS[4]),protected=json.loads((ROOT/'reports/r18a/stage_contract.json').read_bytes())['protected'],immutable_old_attempts=old,NEXT='R18R1B_AFTER_EDGE_HARNESS_PASS'))
    from scripts.v4_11_candidate_inputs_r2 import positive_values
    fixture=dict(contract_id='V4_14_R18R1_ENGINEERING_PRODUCER_FIXTURES_V1',version='1.0.0',evidence_class='ENGINEERING_SYNTHETIC',seed=dict(source=ref(ROOT,'config/v4_07_machine_vectors_v1.json'),selector='/base_input'),prewatch=dict(source=ref(ROOT,'config/v4_09_machine_vectors_v1.json'),vector_id='RAW_TRUE_TRUE'),confirmation=dict(values=positive_values(),sources=[ref(ROOT,'scripts/v4_11_candidate_inputs_r1.py'),ref(ROOT,'scripts/v4_11_candidate_inputs_r2.py')],scope='EXACT_FROZEN_OWNER_ENGINEERING_FIXTURE'),structure=dict(source=ref(ROOT,'config/v4_12_machine_vectors_v1.json'),selector='owner_inputs.structure_vector'),transport=dict(C_to_D0='REPLAY_PREWATCH_LINEAGE_READ_ONLY_METADATA; NO_NEW_DETECTOR_PREDICATE',D1_to_D2='DEGRADED_V4_11_ACCEPTED_HEAD_V4_12_STRUCTURE_SUPPORT_NOT_IMPLEMENTED'),historical_PIT=False)
    publish(ROOT,'config/v4_14_edge_producer_fixtures_r18r1_v1.json',fixture)
    fields=['edge_id','producer','consumer','declared_producer','declared_consumer','field','time_role','owner_contract_id','owner_head_ref','owner_contract_ref','target_trade_date','previous_market_session','input_ref','input_digest','output_ref','output_digest','consumer_input_ref','consumer_input_digest','execution_mode','quality','status','reason','source_trade_date','available_at']
    publish(ROOT,'config/v4_14_edge_receipt_schema_r18r1_v1.json',dict(contract_id='V4_14_REPLAY_EDGE_RECEIPT_V1',version='1.0.0',frozen_dag=ref(ROOT,'config/v4_14_temporal_non_edge_registry_v1_1.json'),required=fields,statuses=['EXECUTED','DEGRADED_ACCEPTED_CAPABILITY','NOT_APPLICABLE_BY_FROZEN_CONTRACT'],identity=['producer','consumer','field','time_role'],reference_scopes=['CURRENT_OUTPUT','PREVIOUS_PUBLICATION'],fixture_package=ref(ROOT,'config/v4_14_edge_producer_fixtures_r18r1_v1.json'),raw_provider_fallback=False))
if __name__=='__main__':run()
