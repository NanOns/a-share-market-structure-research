"""Final evidence seal, after clean detached source validation only."""
import sys,json,subprocess,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.v4_14_replay_io import ref,exact,publish
from scripts.prepare_r18 import BASE,PROTECTED

def seal(source,validation_output):
    folder=Path(validation_output);clean=json.loads((folder/'clean_detached.json').read_bytes());regression=json.loads((folder/'regression_gate.json').read_bytes())
    assert clean['source_sha']==regression['source_sha']==source and clean['status']=='PASS'
    assert clean['git_status_before']==clean['git_status_after']=='' and all(clean['test_totals'][k]==0 for k in ['failed','errors','skipped','deselected'])
    baseline=json.loads((ROOT/'reports/r18a/stage_contract.json').read_bytes())
    for r in baseline['protected']:exact(ROOT,r)
    assert not (ROOT/'data/v4/V4_14_ACCEPTED_HEAD.json').exists()
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==BASE
    copied=[]
    for name in ['clean_detached.json','regression_gate.json','regression.xml','regression.log','clean_runner.log']:
        path='reports/r18c/clean_final/'+name;p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True);raw=(folder/name).read_bytes()
        if p.exists():assert p.read_bytes()==raw
        else:
            from scripts.prepare_r17_governance import atomic
            atomic(path,raw)
        copied.append(ref(ROOT,path))
    oracle_ref=ref(ROOT,'reports/r18c/independent_oracle_gate.json');oracle=json.loads(exact(ROOT,oracle_ref));assert oracle['R18C_INDEPENDENT_ORACLE']=='PASS_LOCAL'
    b=json.loads((ROOT/'reports/v4_14_replay_r18/full_dag_r3/completion_gate.json').read_bytes());real=json.loads((ROOT/'reports/r18c/real_scoped_gate.json').read_bytes())
    candidate=dict(execution_baseline=BASE,tested_source_sha=source,clean_validation=copied,clean_git_status_before='',clean_git_status_after='',regression_totals=clean['test_totals'],contract_package_digest=oracle and b['contract_package_digest'],authority_bindings=b['authority_bindings'],input_envelope_contract=ref(ROOT,'config/v4_14_replay_input_envelope_r18_v1.json'),independent_oracle_receipt=oracle_ref,dimensions=oracle['dimensions'],replay_publications=[r['publication'] for r in b['records']]+[b['same_day']['r2'],real['publication']],cross_process_receipt=ref(ROOT,'reports/v4_14_replay_r18/full_dag_r3/completion_gate.json'),same_day_revision=b['same_day'],determinism=b['determinism'],real_scoped_replay=ref(ROOT,'reports/r18c/real_scoped_gate.json'),real_capability_boundary=ref(ROOT,'reports/r18c/real_capability_boundary.json'),protected_bindings=baseline['protected'],R18A_V4_14_RUNTIME_HARNESS='PASS_LOCAL',R18B_CROSS_PROCESS_FULL_DAG_REPLAY='PASS_LOCAL',R18C_INDEPENDENT_ORACLE='PASS_LOCAL',R18_REAL_ACCEPTED_SOURCE_REPLAY='PASS_CAPABILITY_SCOPED',V4_14_RUNTIME_CANDIDATE='READY_FOR_EXTERNAL_AUDIT',V4_14_ACCEPTED_HEAD='NOT_CREATED',V4_STAGE_ACCEPTED_HEAD='V4_00_TO_V4_13_ACCEPTED',V4_DATA_ACCEPTED_HEAD='2026-09-30',HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',ALGORITHM_STATE_REPLAY_PASS='NOT_GRANTED_PENDING_EXTERNAL_AUDIT',permissions=dict(production=False,shadow=False,focus=False,global_mandatory_adoption=False,formal_DB_migration=False,Stage_advance=False,Data_advance=False,Radar=False,Cohort=False,Settlement=False,V4_15=False,raw_provider_fallback=False,algorithm_threshold_redesign=False),NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
    result=publish(ROOT,'reports/r18c/V4_14_RUNTIME_CANDIDATE_R18_SEAL.json',candidate)
    return result
if __name__=='__main__':print(json.dumps(seal(*sys.argv[1:]),sort_keys=True))
