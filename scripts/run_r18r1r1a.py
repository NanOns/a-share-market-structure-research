"""Pre-execution stage entry proof before running the r5 trajectory."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.v4_14_authority import ReplayAuthority
from workbench_analysis.v4_14_full_dag import replay
from workbench_analysis.v4_14_publication import publish_replay
from workbench_analysis.v4_14_replay_io import ref,publish
from scripts.v4_14_consumption_oracle_r18r1r1 import ConsumptionOracle,read

def run():
    a=ReplayAuthority(ROOT);date='2026-09-29';ns='reports/r18r1r1a/local_preexec_proof_r2'
    e=dict(target_trade_date=date,target_revision='r1',previous_market_session=a.previous(date),cutoff=date+'T16:00:00+00:00',authority_bindings=a.bindings(),contract_package_digest=a.package_digest,previous_state_publication=None,source_refs=[*a.refs,*a.owners.values()],source_availability=[dict(max_source_trade_date=date,system_available_at=date+'T01:00:00+00:00',basis='EXPLICIT_SYNTHETIC_FACTS')],evidence_class='ENGINEERING_SYNTHETIC',owner_inputs=dict(structure_vector='S01',preexec_edge_binding=True,consumption_mapping_ref=ref(ROOT,'config/v4_14_precall_consumption_mapping_r18r1r1_v1.json'),invocation_storage=dict(artifact_root=str(ROOT),namespace=ns)))
    output=replay(a,e,None);proof=publish_replay(ROOT,e,output,a,ns);ConsumptionOracle(ROOT).manifest(ROOT,read(ROOT,proof))
    return publish(ROOT,'reports/r18r1r1a/completion_gate_r2.json',dict(R18R1R1A_PREEXEC_EDGE_BINDING='PASS_LOCAL',EXECUTED_EDGE_CONSUMPTION_TRUTH='PASS_LOCAL',POST_HOC_EDGE_LEDGER_NOT_AUTHORITY='PASS',proof=proof,consumption_mapping=e['owner_inputs']['consumption_mapping_ref'],NEXT='R18R1R1B_FULL_DAG_R5'))
if __name__=='__main__':print(json.dumps(run()))
