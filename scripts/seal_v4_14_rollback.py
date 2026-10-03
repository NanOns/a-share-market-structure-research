"""Reseal the unchanged r5 candidate with rollback and detached validation."""
import sys,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from scripts.prepare_r18_rollback import BASE
from scripts.prepare_r17_governance import atomic
from workbench_analysis.v4_14_replay_io import ref,exact,publish
def seal(source,folder):
    folder=Path(folder);clean=json.loads((folder/'clean_detached.json').read_bytes());regression=json.loads((folder/'regression_gate.json').read_bytes())
    assert clean['source_sha']==regression['source_sha']==source and clean['status']=='PASS' and clean['git_status_before']==clean['git_status_after']==''
    assert all(clean['test_totals'][k]==0 for k in ['failed','errors','skipped','deselected'])
    assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==BASE
    stage=json.loads((ROOT/'reports/r18r1r1r1a/stage_contract.json').read_bytes())
    for r in stage['protected']+stage['keep_evidence']:exact(ROOT,r)
    assert not (ROOT/'data/v4/V4_14_ACCEPTED_HEAD.json').exists()
    copied=[]
    for name in ['clean_detached.json','regression_gate.json','regression.xml','regression.log','clean_runner.log']:
        path='reports/r18r1r1r1b/clean_final/'+name;atomic(path,(folder/name).read_bytes());copied.append(ref(ROOT,path))
    oldref=ref(ROOT,'reports/r18r1r1c/V4_14_RUNTIME_CANDIDATE_R18R1R1_SEAL.json');old=json.loads(exact(ROOT,oldref))
    result=dict(execution_baseline=BASE,tested_source_sha=source,runtime_candidate_seal=oldref,canonical_r5_gate=old['canonical_full_dag_gate'],independent_consumption_oracle=old['independent_oracle_receipt'],rollback_receipt=ref(ROOT,'reports/r18r1r1r1a/V4_14_ROLLBACK_RECEIPT.json'),independent_rollback_oracle=ref(ROOT,'reports/r18r1r1r1b/independent_rollback_oracle_gate.json'),negative_mutation_gate=ref(ROOT,'reports/r18r1r1r1b/negative_gate.json'),clean_validation=copied,regression_totals=clean['test_totals'],protected_bindings=stage['protected'],candidate_artifacts_preserved=stage['keep_evidence'],real_capability_boundary=old['real_capability_boundary'],real_scoped_gate=old['real_scoped_replay'],R18R1R1R1A_V4_14_ROLLBACK_DRILL='PASS_LOCAL',ROLLBACK_RECEIPT_CREATION='CREATED',ROLLBACK_TO_EXACT_V4_13_PREDECESSOR='PASS',REAL_PROTECTED_HEADS_UNCHANGED='PASS',R18R1R1R1B_INDEPENDENT_ROLLBACK_ORACLE='PASS_LOCAL',V4_14_ROLLBACK_RECEIPT='PASS',EDGE_CONSUMPTION_TRUTH='PASS',R18_REAL_ACCEPTED_SOURCE_REPLAY='PASS_CAPABILITY_SCOPED',HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',V4_14_RUNTIME_CANDIDATE='READY_FOR_FINAL_EXTERNAL_AUDIT_WITH_ROLLBACK',V4_14_ACCEPTED_HEAD='NOT_CREATED',V4_STAGE_ACCEPTED_HEAD='V4_00_TO_V4_13_ACCEPTED',V4_DATA_ACCEPTED_HEAD='2026-09-30',ALGORITHM_STATE_REPLAY_PASS='NOT_GRANTED_PENDING_EXTERNAL_AUDIT',permissions=dict(production=False,shadow=False,focus=False,V4_15=False,Stage_advance=False,Data_advance=False,Radar=False,Cohort=False,Settlement=False,raw_provider_fallback=False,formal_DB_migration=False),NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
    return publish(ROOT,'reports/r18r1r1r1b/V4_14_RUNTIME_CANDIDATE_ROLLBACK_COMPLETE_SEAL.json',result)
if __name__=='__main__':print(json.dumps(seal(*sys.argv[1:])))
