"""Reuse the accepted OS launcher; inject only the frozen edge input contract."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from scripts import run_r18b as launcher
from workbench_analysis.v4_14_replay_io import ref,publish,exact
from scripts.v4_14_independent_edge_oracle_r18r1 import EdgeOracle,read
DISPOSITION=dict(full_dag='SUPERSEDED_R18_ATTEMPT',full_dag_r2='SUPERSEDED_R18_ATTEMPT',full_dag_r3='SUPERSEDED_BY_R18R1_EDGE_COMPLETE_REPLAY',full_dag_r4='CURRENT_R18R1_CANDIDATE')

def run():
    entry=ref(ROOT,'reports/r18r1a/completion_gate.json');assert read(ROOT,entry)['R18R1A_OWNER_EDGE_COMPLETE_HARNESS']=='PASS_LOCAL'
    schema=ref(ROOT,'config/v4_14_edge_receipt_schema_r18r1_v1.json');fixture=ref(ROOT,'config/v4_14_edge_producer_fixtures_r18r1_v1.json');original=launcher.invoke
    def inject(a,artifact_root,namespace,date,choice,prior,index,revision='r1'):
        return original(a,artifact_root,namespace,date,dict(choice,owner_edge_complete=True,edge_schema_ref=schema,fixture_package_ref=fixture),prior,index,revision)
    launcher.invoke=inject
    try:receipt=launcher.run(ROOT,'reports/v4_14_replay_r18/full_dag_r4')
    finally:launcher.invoke=original
    persisted=read(ROOT,receipt);oracle=EdgeOracle(ROOT);oracle.gate(ROOT,persisted)
    initial=read(ROOT,ref(ROOT,'reports/r18r1a/stage_contract.json'))
    for attempts in initial['immutable_old_attempts'].values():
        for binding in attempts:exact(ROOT,binding)
    gate=dict(R18R1B_CROSS_PROCESS_FULL_DAG_R4='PASS_LOCAL',OWNER_EDGE_COMPLETENESS='PASS',CANONICAL_FULL_DAG_GATE='CREATED',CROSS_PROCESS_PREVIOUS_SESSION='PASS',SAME_DAY_REVISION_ISOLATION='PASS',entry_gate=entry,candidate_namespace='reports/v4_14_replay_r18/full_dag_r4',attempt_disposition=DISPOSITION,persisted_e2e= persisted,persisted_receipt=receipt,edge_schema=schema,fixture_package=fixture,EXPECTED_OWNER_EDGE_SET=sorted(oracle.expected_owner_edges),EXPECTED_REPLAY_REQUIRED_EDGE_SET=sorted(oracle.expected_replay_edges),missing_edges=[],unexpected_edges=[],NEXT='R18R1C_INDEPENDENT_EDGE_ORACLE')
    oracle.canonical(ROOT,gate)
    return publish(ROOT,'reports/r18r1b/final_full_dag_gate.json',gate)
if __name__=='__main__':print(json.dumps(run(),sort_keys=True))
