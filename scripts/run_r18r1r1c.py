"""Independent canonical-edge verification and exact real evidence readback."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.v4_14_replay_io import ref,publish
from scripts.v4_14_consumption_oracle_r18r1r1 import ConsumptionOracle,read,exact,require

def run():
    o=ConsumptionOracle(ROOT);canonical=ref(ROOT,'reports/r18r1r1b/final_full_dag_gate.json');g=read(ROOT,canonical);o.canonical(ROOT,g)
    vectors_ref=ref(ROOT,'reports/r18a/r3/synthetic_vector_runtime.json');vectors=o.vectors(read(ROOT,vectors_ref))
    real_ref=ref(ROOT,'reports/r18c/real_scoped_gate.json');real=read(ROOT,real_ref);m=read(ROOT,real['publication'])
    o.cross_process(*real['receipts']);read(ROOT,real['receipts'][0]['publication'])
    require(m['accepted_r6_manifest']==o.head['candidate'],'REAL_NOT_ACCEPTED_R6');r6=read(ROOT,m['accepted_r6_manifest'])
    require(m['AS_RECORDED'] is False and m['knowledge_lineage']=='RECONSTRUCTED_CORRECTED' and m['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED','REAL_EVIDENCE_CLASS')
    require(m['previous_market_session']==o.previous(m['trade_date']) and m['profile_count']==5224 and m['context_count']==50162 and m['event_counts']['UNKNOWN']==4683 and m['final_eligibility_counts']['UNKNOWN']==4356,'REAL_CAPABILITY_BOUNDARY')
    checked=[]
    def visit(value):
        if isinstance(value,dict):
            if {'path','sha256'}<=set(value) and ('bytes' in value or 'byte_count' in value):exact(ROOT,value);checked.append(value)
            else:
                for child in value.values():visit(child)
        elif isinstance(value,list):
            for child in value:visit(child)
    visit(r6)
    recheck=publish(ROOT,'reports/r18r1r1c/real_scoped_recheck.json',dict(real_gate=real_ref,publication=real['publication'],accepted_r6_manifest=m['accepted_r6_manifest'],verified_candidate_bindings=checked,readback_only=True,process_receipts=real['receipts'],evidence_class='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED',AS_RECORDED=False,knowledge_lineage='RECONSTRUCTED_CORRECTED',HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',R18_REAL_ACCEPTED_SOURCE_REPLAY='PASS_CAPABILITY_SCOPED',synthetic_completeness_does_not_upgrade_real=True))
    result=dict(R18R1R1C_INDEPENDENT_CONSUMPTION_ORACLE='PASS_LOCAL',EDGE_CONSUMPTION_TRUTH='PASS',canonical_full_dag_gate=canonical,oracle_source=ref(ROOT,'scripts/v4_14_consumption_oracle_r18r1r1.py'),inherited_oracle_source=ref(ROOT,'scripts/v4_14_independent_oracle.py'),expected_authority='DIRECT_FROZEN_DAG_AND_FROZEN_FIELD_MAPPING_PLUS_OWNER_INPUT_SCHEMAS',consumption_mapping=ref(ROOT,'config/v4_14_precall_consumption_mapping_r18r1r1_v1.json'),false_executed_edges=[],unbound_consumer_arguments=[],post_hoc_only_edges=[],calls_replay_evaluator_for_expected=False,EXPECTED_OWNER_EDGE_SET=sorted(o.expected_owner_edges),EXPECTED_REPLAY_REQUIRED_EDGE_SET=sorted(o.expected_replay_edges),missing_edges=[],unexpected_edges=[],synthetic_gate=vectors_ref,real_scoped_recheck=recheck,real_capability_boundary=ref(ROOT,'reports/r18c/real_capability_boundary.json'),dimensions=[dict(dimension=n,status='PASS_LOCAL',case_count=sum(v['dimension']==n for v in vectors),evidence_class='ENGINEERING_SYNTHETIC') for n in sorted({v['dimension'] for v in vectors})],evidence_classes=dict(ENGINEERING_SYNTHETIC=dict(cases=60,market_sessions=len(g['persisted_e2e']['records']),status='PASS_LOCAL'),REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED=dict(profiles=5224,contexts=50162,status='PASS_CAPABILITY_SCOPED'),HISTORICAL_PIT_EFFECTIVENESS=dict(granted=False,status='NOT_GRANTED')),ALGORITHM_STATE_REPLAY_PASS='NOT_GRANTED_PENDING_EXTERNAL_AUDIT',NEXT='CLEAN_DETACHED_REGRESSION_THEN_UNIFIED_COMMIT_PUSH_STOP')
    return publish(ROOT,'reports/r18r1r1c/independent_consumption_oracle_gate.json',result)
if __name__=='__main__':print(json.dumps(run(),sort_keys=True))
