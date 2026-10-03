"""Local owner-edge contract gate before cross-process R4 stage entry."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.v4_14_authority import ReplayAuthority
from workbench_analysis.v4_14_full_dag import replay
from workbench_analysis.v4_14_publication import publish_replay
from workbench_analysis.v4_14_replay_io import ref,publish,exact
from scripts.v4_14_independent_edge_oracle_r18r1 import EdgeOracle,read
def run():
    a=ReplayAuthority(ROOT);e=dict(target_trade_date='2026-09-29',target_revision='r1',previous_market_session=a.previous('2026-09-29'),cutoff='2026-09-29T16:00:00+00:00',previous_state_publication=None,source_refs=a.refs,source_availability=[],authority_bindings=a.bindings(),contract_package_digest=a.package_digest,evidence_class='ENGINEERING_SYNTHETIC',owner_inputs=dict(owner_edge_complete=True,fixture_package_ref=ref(ROOT,'config/v4_14_edge_producer_fixtures_r18r1_v1.json'),edge_schema_ref=ref(ROOT,'config/v4_14_edge_receipt_schema_r18r1_v1.json')))
    result=replay(a,e,None);publication=publish_replay(ROOT,e,result,a,'reports/r18r1a/local_edge_proof');o=EdgeOracle(ROOT);o.manifest(ROOT,read(ROOT,publication))
    return publish(ROOT,'reports/r18r1a/completion_gate.json',dict(R18R1A_OWNER_EDGE_COMPLETE_HARNESS='PASS_LOCAL',FULL_DAG_EDGE_SCHEMA='FROZEN',OWNER_EDGE_COMPLETENESS_LOCAL='PASS',edge_count=len(o.expected_edges),schema=e['owner_inputs']['edge_schema_ref'],fixture_package=e['owner_inputs']['fixture_package_ref'],proof=publication,NEXT='R18R1B_CROSS_PROCESS_R4'))
if __name__=='__main__':print(json.dumps(run(),sort_keys=True))
