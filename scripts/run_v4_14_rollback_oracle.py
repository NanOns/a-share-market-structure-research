import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.v4_14_replay_io import publish,ref,exact
from scripts.v4_14_rollback_oracle import RollbackOracle
def run():
    entry=ref(ROOT,'reports/r18r1r1r1a/completion_gate.json');assert json.loads(exact(ROOT,entry))['R18R1R1R1A_V4_14_ROLLBACK_DRILL']=='PASS_LOCAL'
    receipt=ref(ROOT,'reports/r18r1r1r1a/V4_14_ROLLBACK_RECEIPT.json');RollbackOracle(ROOT).validate(json.loads(exact(ROOT,receipt)))
    return publish(ROOT,'reports/r18r1r1r1b/independent_rollback_oracle_gate.json',dict(R18R1R1R1B_INDEPENDENT_ROLLBACK_ORACLE='PASS_LOCAL',V4_14_ROLLBACK_RECEIPT='PASS',receipt=receipt,oracle_source=ref(ROOT,'scripts/v4_14_rollback_oracle.py'),expected_authority='AUDITED_BASELINE_GIT_BLOBS_PLUS_FROZEN_CUTOVER_POLICY',calls_rollback_implementation_for_expected=False,entry_gate=entry,NEXT='CLEAN_DETACHED_REGRESSION_THEN_SEAL'))
if __name__=='__main__':print(json.dumps(run()))
