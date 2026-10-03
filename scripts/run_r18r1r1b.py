"""Keep OS launcher/trajectory; bind the pre-call contract and new r5 sink."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from scripts import run_r18b as launcher
from workbench_analysis.v4_14_replay_io import ref,publish,exact
from scripts.v4_14_consumption_oracle_r18r1r1 import ConsumptionOracle,read

def run():
    entry=ref(ROOT,'reports/r18r1r1a/completion_gate_r2.json');assert read(ROOT,entry)['R18R1R1A_PREEXEC_EDGE_BINDING']=='PASS_LOCAL'
    original=launcher.invoke;mapping=ref(ROOT,'config/v4_14_precall_consumption_mapping_r18r1r1_v1.json');namespace='reports/v4_14_replay_r18/full_dag_r5'
    def inject(a,artifact_root,ns,date,choice,prior,index,revision='r1'):
        return original(a,artifact_root,ns,date,dict(choice,preexec_edge_binding=True,consumption_mapping_ref=mapping,invocation_storage=dict(artifact_root=str(artifact_root),namespace=ns)),prior,index,revision)
    launcher.invoke=inject
    try:receipt=launcher.run(ROOT,namespace)
    finally:launcher.invoke=original
    persisted=read(ROOT,receipt);o=ConsumptionOracle(ROOT);o.gate(ROOT,persisted)
    stage=read(ROOT,ref(ROOT,'reports/r18r1r1a/stage_contract.json'))
    for refs in stage['immutable_old_attempts'].values():
        for r in refs:exact(ROOT,r)
    empty=dict(missing_edges=[],unexpected_edges=[],false_executed_edges=[],unbound_consumer_arguments=[],post_hoc_only_edges=[])
    g=dict(R18R1R1B_CROSS_PROCESS_FULL_DAG_R5='PASS_LOCAL',EDGE_CONSUMPTION_TRUTH='PASS',CANONICAL_FULL_DAG_GATE_R5='CREATED',entry_gate=entry,candidate_namespace=namespace,attempt_disposition=dict(full_dag='HISTORICAL',full_dag_r2='HISTORICAL',full_dag_r3='HISTORICAL',full_dag_r4='SUPERSEDED_BY_R18R1R1_CONSUMPTION_TRUTH_REPAIR',full_dag_r5='CURRENT_R18R1R1_CANDIDATE'),persisted_e2e=persisted,persisted_receipt=receipt,consumption_mapping=mapping,EXPECTED_EDGE_SET=sorted(o.expected_edges),EXPECTED_OWNER_EDGE_SET=sorted(o.expected_owner_edges),EXPECTED_REPLAY_REQUIRED_EDGE_SET=sorted(o.expected_replay_edges),NEXT='R18R1R1C_CONSUMPTION_ORACLE',**empty)
    o.canonical(ROOT,g);return publish(ROOT,'reports/r18r1r1b/final_full_dag_gate.json',g)
if __name__=='__main__':print(json.dumps(run()))
