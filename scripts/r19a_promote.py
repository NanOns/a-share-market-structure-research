"""Explicit R19A promotion writer. Validation lives in a separate module."""
from scripts.r19_io import ROOT, BASE, TESTED, read, ref, atomic, blob

AUDIT = 'docs/evidence/r19/V4_R18R1R1R1_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md'
STAGE = 'data/v4/V4_STAGE_ACCEPTED_HEAD.json'
HEAD = 'data/v4/V4_14_ACCEPTED_HEAD.json'

def promote():
    if (ROOT / HEAD).exists():
        raise ValueError('PROMOTION_ALREADY_EXISTS: run independent validator')
    parent = blob(STAGE)
    if (ROOT / STAGE).read_bytes() != parent:
        raise ValueError('STALE_STAGE_PREDECESSOR')
    atomic('reports/r19a/PARENT_STAGE_HEAD.json', parent, raw=True)
    cap = dict(ENGINEERING_SYNTHETIC_REPLAY='FULL_PASS', FULL_D0_D1_D2_REPLAY='ENGINEERING_ACCEPTED', EDGE_CONSUMPTION_TRUTH='PASS', CROSS_PROCESS_PREVIOUS_SESSION='PASS', SAME_DAY_REVISION_ISOLATION='PASS', DETERMINISTIC_REPLAY='PASS', ROLLBACK_RECEIPT='PASS', REAL_ACCEPTED_SOURCE_REPLAY='PASS_CAPABILITY_SCOPED', HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED', REAL_SIGNAL_CAPABILITY='DEGRADED_BY_ACCEPTED_UPSTREAM_CAPABILITY')
    paths = dict(external_audit=AUDIT, rollback_complete_seal='reports/r18r1r1r1b/V4_14_RUNTIME_CANDIDATE_ROLLBACK_COMPLETE_SEAL.json', runtime_seal='reports/r18r1r1c/V4_14_RUNTIME_CANDIDATE_R18R1R1_SEAL.json', canonical_full_dag_r5='reports/r18r1r1b/final_full_dag_gate.json', consumption_oracle='reports/r18r1r1c/independent_consumption_oracle_gate.json', rollback_receipt='reports/r18r1r1r1a/V4_14_ROLLBACK_RECEIPT.json', rollback_oracle='reports/r18r1r1r1b/independent_rollback_oracle_gate.json', contract_package='config/v4_14_replay_gate_b_contract_v1_1.json', amended_predecessor='data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json', data_head='data/v4/V4_DATA_ACCEPTED_HEAD.json', parent_stage='reports/r19a/PARENT_STAGE_HEAD.json', calendar='config/v4_official_exchange_calendar_v2.json', membership='data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json')
    paths['calendar']=read('data/v4/V4_DATA_ACCEPTED_HEAD.json')['calendar']['path']
    entry = dict(contract_id='V4_14_ACCEPTED_ENTRY_CONTRACT_V1', version='1.0.0', audited_head=BASE, tested_source=TESTED, accepted_head_namespace=HEAD, bindings={k: ref(p) for k,p in paths.items()}, capabilities=cap, evidence_classes=['ENGINEERING_SYNTHETIC', 'REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED'], production=False, shadow=False, focus=False, V4_15_runtime=False)
    atomic('config/v4_14_accepted_entry_contract_v1.json', entry)
    h = dict(contract_id='V4_14_ACCEPTED_HEAD_V1', version='1.0.0', stage='V4-14', status='ALGORITHM_STATE_REPLAY_DEGRADED_PASS', external_acceptance='EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED', external_audit_decision='PASS_FINAL_V4_14_RUNTIME_CAPABILITY_SCOPED', ALGORITHM_STATE_REPLAY_PASS='DEGRADED_PASS_CAPABILITY_SCOPED', HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED', REAL_ACCEPTED_SOURCE_REPLAY='PASS_CAPABILITY_SCOPED', audited_head=BASE, tested_source=TESTED, accepted_trade_date='2026-09-30', bindings=entry['bindings'], capabilities=cap, entry_contract=ref('config/v4_14_accepted_entry_contract_v1.json'), production=False, shadow=False, focus=False, V4_15_runtime=False)
    atomic(HEAD, h)
    stage = read('reports/r19a/PARENT_STAGE_HEAD.json')
    stage.update(accepted_stage_range='V4_00_TO_V4_14_ACCEPTED', v4_14_binding=ref(HEAD), v4_14_status=h['status'], v4_14_external_acceptance=h['external_audit_decision'], v4_14_capabilities=cap, v4_15_entry='CONTRACT_FREEZE_AUTHORIZED_RUNTIME_NOT_AUTHORIZED')
    atomic(STAGE, stage)

if __name__ == '__main__':
    promote()
