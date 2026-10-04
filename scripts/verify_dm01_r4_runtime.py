"""Read-only real gates plus isolated, explicit historical engineering build evidence."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from workbench_analysis import dm01_runtime_r4 as r
from tests.v4_dm01_r4.test_runtime import env as engineering_inputs


def main():
    folder=ROOT/'reports/dm01_r4'
    write=lambda name,value:r.atomic(ROOT,folder/(name+'.json'),value)
    now=datetime.now(timezone.utc).isoformat()
    cal=r.calendar();parent=r.current_parent();contract=r.validate_registry(r.BUILDERS)
    wait=r.session_gate('2026-10-08',now)
    if wait['status']!='WAIT_MARKET_CLOSE':raise ValueError('THIS_HOLIDAY_EVIDENCE_RECIPE_REQUIRES_FUTURE_SESSION')
    write('CALENDAR_AUTHORITY_GATE',dict(status='LOCAL_READY_FOR_EXTERNAL_AUDIT',calendar=cal,
        old_calendar_immutable=True,external_acceptance=None,activation='EXACT_EXTERNALLY_ACCEPTED_R4_ENVELOPE_REQUIRED'))
    write('CURRENT_V2_PARENT_GATE',dict(status='PASS_LOCAL_REPAIRED',parent=parent,next_session='2026-10-08',v1_scope='EXACT_ARCHIVE_HISTORY_ONLY'))
    write('FUTURE_SESSION_WAIT_READBACK',dict(wait,observed_at=now,real_target_session_package='NOT_CREATED',real_shadow_observations=0))
    write('ALL_NINE_RUNTIME_REGISTRY_GATE',dict(status='PASS_LOCAL_REPAIRED',contract=r.ref(ROOT,ROOT/r.CONTRACT),
        actual_callables={cap:fn.__module__+'.'+fn.__name__ for cap,fn in r.BUILDERS.items()},
        kernel_reuse=contract['kernel_reuse'],runtime_bindings=contract['runtime_bindings']))
    fixture_root=folder/'engineering_simulation_final'/r.sha(ROOT/r.CONTRACT)
    inputs=engineering_inputs.__wrapped__(fixture_root)
    result=r.build_candidate(parent=inputs['parent'],freeze=inputs['freeze'],cal=inputs['calendar'],identity=inputs['identity'],root=fixture_root)
    candidate=r.read(fixture_root,result['candidate'])
    write('PIT_LINEAGE_GATE',dict(status='PASS_LOCAL_REPAIRED',contract=r.ref(ROOT,ROOT/r.CONTRACT),
        historical_lineage='RECONSTRUCTED_CORRECTED',historical_AS_RECORDED=False,
        simulation_candidate=r.ref(ROOT,r.path(fixture_root,result['candidate'])),
        simulation_scope='CONTRACT_DESIGN_OR_ENGINEERING_SIMULATION',real_forward_evidence=False,
        real_PIT_validation='PENDING_EXACT_TARGET_SESSION_AND_EXTERNAL_ENVELOPE'))
    write('DAILY_ENTRYPOINT_GATE',dict(status='PASS_LOCAL_REPAIRED',entrypoint=r.ref(ROOT,ROOT/'scripts/run_v4_dm01_daily_increment.py'),
        future_gate=wait,all_nine_engineering_result=result,engineering_cross_postcheck=r.read(fixture_root,candidate['cross_postcheck']),
        simulation_scope='CONTRACT_DESIGN_OR_ENGINEERING_SIMULATION',real_forward_evidence=False))
    write('V2_PROMOTION_POLICY_GATE',dict(status='PASS_LOCAL_REPAIRED',policy=r.ref(ROOT,ROOT/r.POLICY),
        external_acceptance_head_exists=(ROOT/r.ACCEPTANCE).exists(),external_acceptance='PENDING',
        machine_state_test='ISOLATED_SIMULATION_WITH_REPLACED_PIT_ADMISSION_DEPENDENCIES; NOT_REAL_FORWARD_EVIDENCE',
        data_head_moved=False,stage_head_moved=False,permissions=r.PERMISSIONS,r25_auto_grant=False,real_shadow_counter_increment=0))
    baseline=json.loads((folder/'ENTRY_BASELINE.json').read_bytes())
    allowed={b['path'] for b in contract['runtime_bindings'] if b['path'].startswith('scripts/')}
    allowed.add('.gitattributes')
    changed={p:dict(before=d,after=r.sha(ROOT/p)) for p,d in baseline['tracked'].items() if r.sha(ROOT/p)!=d}
    unexpected=set(changed)-allowed
    unrelated=baseline['unrelated']
    unrelated_changed=[p for p,d in unrelated.items() if not (ROOT/p).is_file() or r.sha(ROOT/p)!=d]
    if unexpected or unrelated_changed:raise ValueError(str((unexpected,unrelated_changed)))
    write('PROTECTED_STATE',dict(status='PASS',baseline=baseline['baseline'],tracked_count=len(baseline['tracked']),
        declared_script_changes=changed,unexpected_tracked_changes=[],unrelated_changes=unrelated_changed,
        data_head=r.ref(ROOT,ROOT/r.HEAD),protected_heads={p:r.ref(ROOT,ROOT/p) for p in contract['protected_runtime_paths']},
        tdx_root_write_count=0,tdx_root_access='NOT_USED_BY_THIS_VERIFICATION',
        real_shadow_execution='NOT_STARTED',real_shadow_observations=0,r25='WAIT_ACCEPTED_DAILY_INPUT'))
    print(json.dumps(dict(status='PASS_LOCAL_ENGINEERING_GATES',real_forward_evidence=False,next='STOP_WAIT_DM01_R4_INDEPENDENT_EXTERNAL_AUDIT')))


if __name__=='__main__':main()
