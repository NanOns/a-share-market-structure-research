"""Preserve earlier investigation while undoing pre-V4 test retirement."""
import json
from scripts.full_chain_repair_io import ROOT, binding, write
from scripts.forward_final_bootstrap import P


def apply():
    if (ROOT/(P+'V4_SCOPE_CORRECTION_RECEIPT.json')).exists():
        raise ValueError('SCOPE_CORRECTION_ALREADY_RECORDED_DO_NOT_RESTORE_TESTS_AGAIN')
    registry=json.loads((ROOT/(P+'IA05_60_NODE_DEPENDENCY_CLASSIFICATION.json')).read_bytes())
    paths=sorted({r['old_test_path'] for r in registry['nodes']
                  if '/upgrade_' in r['old_test_path']})
    restored=[]
    for path in paths:
        archived='docs/evidence/forward_r2_final_blocker_repair_20261007/original_tests/'+path
        raw=(ROOT/archived).read_bytes()
        write(path,raw,raw=True)
        restored.append(binding(path))
    profile='config/v4_forward_r3_historical_profile_v1.json'
    raw=(ROOT/profile).read_bytes()
    write(P+'scope_correction/RETRACTED_PRE_V4_HISTORICAL_PROFILE.json',raw,raw=True)
    # This newly-created profile was never committed or externally accepted.
    (ROOT/profile).unlink()
    write(P+'V4_SCOPE_CORRECTION_RECEIPT.json',dict(
        authority='USER_EXPLICIT_EXECUTION_SCOPE_CORRECTION',
        execution_scope='V4_ONLY', prior_mixed_full='INTERRUPTED_NOT_ACCEPTANCE',
        pre_v4_historical_replay='PRIOR_INVESTIGATION_ONLY_NOT_V4_ACCEPTANCE',
        pre_v4_test_retirement_retracted=True, restored_original_modules=restored,
        original_60_missing_artifacts='OUTSIDE_V4_EXECUTION_SCOPE_NOT_FABRICATED',
        historical_incident_retained=True, IA07_capability_debt_retained=True))
    write(P+'CROSS_AUDIT_PRE_V4_HISTORY_EVENT_SEQUENCE.json',dict(
        scope='PRE_V4_M7_HISTORY_JOBS',status='OUTSIDE_USER_V4_TASK_SCOPE',
        evidence='G:/codex_tmp/test_temp/final_blocker_full_d',
        issue='Concurrent progress/cancellation may conflict on event sequence; retry catches only TransactionException',
        fixed=False, blocks_v4_regression=False))


if __name__=='__main__': apply()
