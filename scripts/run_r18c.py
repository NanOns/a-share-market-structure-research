"""Seal independent local gates without granting algorithm acceptance."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.v4_14_replay_io import ref,publish
from scripts.v4_14_independent_oracle import Oracle,read,require

def run():
    o=Oracle(ROOT);a=ref(ROOT,'reports/r18a/r3/synthetic_vector_runtime.json');b=ref(ROOT,'reports/v4_14_replay_r18/full_dag_r3/completion_gate.json');real=ref(ROOT,'reports/r18c/real_scoped_gate.json')
    vectors=o.vectors(read(ROOT,a));o.gate(ROOT,read(ROOT,b));r=read(ROOT,real);m=read(ROOT,r['publication'])
    o.cross_process(r['receipts'][0],r['receipts'][1])
    require(m['previous_market_session']==o.previous(m['trade_date']) and m['knowledge_lineage']=='RECONSTRUCTED_CORRECTED' and m['AS_RECORDED'] is False and m['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED','ORACLE_REAL_EVIDENCE_CLASS')
    require(m['profile_count']==5224 and m['context_count']==50162 and m['event_counts']['UNKNOWN']==4683 and m['final_eligibility_counts']['UNKNOWN']==4356,'ORACLE_REAL_CAPABILITY_DEGRADATION')
    require(m['accepted_r6_manifest']==o.head['candidate'],'ORACLE_REAL_NOT_ACCEPTED_R6')
    result=dict(R18C_INDEPENDENT_ORACLE='PASS_LOCAL',oracle_source=ref(ROOT,'scripts/v4_14_independent_oracle.py'),expected_authority='FROZEN_LITERAL_BOOKS_PLUS_INDEPENDENT_OWNER_COUNTER_AND_IDENTITY_CHECKS',calls_replay_evaluator_for_expected=False,synthetic_gate=a,persisted_gate=b,real_gate=real,real_capability_boundary=ref(ROOT,'reports/r18c/real_capability_boundary.json'),dimensions=[dict(dimension=n,status='PASS_LOCAL',case_count=sum(v['dimension']==n for v in vectors),evidence_class='ENGINEERING_SYNTHETIC') for n in sorted({v['dimension'] for v in vectors})],evidence_classes=dict(ENGINEERING_SYNTHETIC=dict(cases=60,market_sessions=len(read(ROOT,b)['records']),status='PASS_LOCAL'),REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED=dict(profiles=5224,contexts=50162,owner_state_rows=5224,status='PASS_CAPABILITY_SCOPED'),HISTORICAL_PIT_EFFECTIVENESS=dict(granted=False,status='NOT_GRANTED')),ALGORITHM_STATE_REPLAY_PASS='NOT_GRANTED_PENDING_EXTERNAL_AUDIT',NEXT='CLEAN_DETACHED_REGRESSION_THEN_UNIFIED_COMMIT_PUSH_STOP')
    return publish(ROOT,'reports/r18c/independent_oracle_gate.json',result)
if __name__=='__main__':print(json.dumps(run(),sort_keys=True))
