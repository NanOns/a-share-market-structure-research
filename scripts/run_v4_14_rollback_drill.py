"""Execute RB01-RB08 without changing formal heads or replay evidence."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from scripts.prepare_r18_rollback import BASE
from workbench_analysis.v4_14_replay_io import ref,publish,exact
from workbench_analysis.v4_13_io import atomic
from workbench_analysis.v4_14_candidate_rollback_drill import Sandbox,PREFIX

def run():
    stage=json.loads((ROOT/'reports/r18r1r1r1a/stage_contract.json').read_bytes());evidence=stage['keep_evidence'];parent=ref(ROOT,'data/v4/V4_STAGE_ACCEPTED_HEAD.json');candidate=ref(ROOT,'reports/r18r1r1c/V4_14_RUNTIME_CANDIDATE_R18R1R1_SEAL.json');gate=ref(ROOT,'reports/r18r1r1b/final_full_dag_gate.json')
    before=[ref(ROOT,r['path']) for r in stage['protected']]
    for r in [*before,*evidence]:exact(ROOT,r)
    scenarios=[]
    for number in range(1,7):
        sid='RB'+str(number).zfill(2);box=Sandbox(ROOT,PREFIX+sid,parent,candidate,evidence);initial=box.snapshot('before');active=None;rejected=None;failure=None;injected_ref=None
        try:
            if number==1:box.activate(fail_before=True)
            elif number==3:box.activate(expected=dict(parent,sha256='0'*64))
            elif number==4:
                path=box.path+'/faulted_candidate.json';atomic(ROOT,path,exact(ROOT,candidate)+b'corrupt',append_only=True);injected_ref=ref(ROOT,path);box.activate(candidate=dict(candidate,path=path))
            else:
                box.activate();active=box.snapshot('activated')
                if number==5:
                    path=box.path+'/faulted_parent.json';atomic(ROOT,path,exact(ROOT,parent)+b'corrupt',append_only=True);injected_ref=ref(ROOT,path);box.rollback(dict(parent,path=path))
                else:raise ValueError('INJECTED_FAILURE_AFTER_ACTIVATION')
        except ValueError as error:failure=str(error);rejected=box.snapshot('after_fault')
        assert failure
        first=box.rollback();restored=box.snapshot('first_rollback');second=box.rollback();repeated=box.snapshot('second_rollback')
        assert exact(ROOT,restored)==exact(ROOT,repeated)==exact(ROOT,parent)
        failure_receipt=dict(stage_id='V4-14',contract_id='CAPABILITY_CUTOVER_AND_ROLLBACK_V1',capability_scope='SANDBOX_CANDIDATE_ACTIVATION_ONLY',affected_dates=['2026-08-31','2026-09-30'],affected_entities=['V4_14_RUNTIME_CANDIDATE'],affected_fields=['sandbox_candidate_pointer'],status='INJECTED_FAILURE_RECOVERED',reason_codes=[failure],evidence_digests=[initial,rejected,restored,repeated],previous_accepted_head=parent,rollback_action='RESTORE_EXACT_V4_13_PREDECESSOR_KEEP_CANDIDATE_EVIDENCE',recovery_owner='R18R1R1R1_SANDBOX_GOVERNANCE',next_action='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
        scenarios.append(dict(scenario_id=sid,sandbox_path=box.path,head_path=box.head,parent_archive=ref(ROOT,box.archive),before=initial,activation=active,after_fault=rejected,fault_evidence=injected_ref,cas_expected=dict(parent,sha256='0'*64) if number==3 else parent,failure_receipt=failure_receipt,first_rollback=first,first_rollback_snapshot=restored,second_rollback=second,second_rollback_snapshot=repeated))
    after=[ref(ROOT,r['path']) for r in stage['protected']]
    assert before==after
    for r in evidence:exact(ROOT,r)
    scenarios.extend([dict(scenario_id='RB07',status='PASS',candidate_artifacts=evidence),dict(scenario_id='RB08',status='PASS',protected_before=before,protected_after=after)])
    oldseal=json.loads(exact(ROOT,candidate));policy=ref(ROOT,'config/v4_capability_cutover_policy_v1.json')
    receipt=dict(contract_id='CAPABILITY_CUTOVER_AND_ROLLBACK_V1',stage_id='V4-14',capability_scope='ISOLATED_CANDIDATE_ACTIVATION_ROLLBACK_DRILL',execution_baseline=BASE,candidate_seal=candidate,canonical_r5_gate=gate,v4_14_contract_package=oldseal['authority_bindings']['contract_package'],policy=policy,previous_accepted_head=parent,previous_accepted_head_archive=scenarios[1]['parent_archive'],sandbox_root=PREFIX.rstrip('/'),scenarios=scenarios,rollback_authority='EXACT_CURRENT_V4_13_STAGE_PREDECESSOR_ONLY',rollback_action='RESTORE_EXACT_PREDECESSOR_KEEP_ALL_CANDIDATE_EVIDENCE',rollback_result='PASS',affected_dates=['2026-08-31','2026-09-30'],affected_entities=['V4_14_RUNTIME_CANDIDATE'],affected_fields=['sandbox_candidate_pointer'],status='PASS_LOCAL',reason_codes=['CANDIDATE_ACTIVATION_FAILURE_DRILL','NO_PARTIAL_ACCEPTANCE','CANDIDATE_EVIDENCE_RETAINED'],evidence_digests=[candidate,gate,parent,policy],recovery_owner='R18R1R1R1_SANDBOX_GOVERNANCE',protected_heads_before=before,protected_heads_after=after,candidate_artifacts_preserved=evidence,idempotent=True,production=False,shadow=False,focus=False,V4_15=False,Stage_advance=False,Data_advance=False,V4_14_ACCEPTED_HEAD='NOT_CREATED',ALGORITHM_STATE_REPLAY_PASS='NOT_GRANTED_PENDING_EXTERNAL_AUDIT',next_action='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
    result=publish(ROOT,'reports/r18r1r1r1a/V4_14_ROLLBACK_RECEIPT.json',receipt)
    publish(ROOT,'reports/r18r1r1r1a/completion_gate.json',dict(R18R1R1R1A_V4_14_ROLLBACK_DRILL='PASS_LOCAL',V4_14_ROLLBACK_RECEIPT='CREATED',ROLLBACK_TO_EXACT_V4_13_PREDECESSOR='PASS',REAL_PROTECTED_HEADS_UNCHANGED='PASS',CANDIDATE_EVIDENCE_APPEND_ONLY='PASS',receipt=result,NEXT='R18R1R1R1B_INDEPENDENT_ROLLBACK_ORACLE'))
    return result
if __name__=='__main__':print(json.dumps(run()))
