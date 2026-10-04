"""R4R1 evidence: read-only real wait gate and explicit historical engineering build."""
from datetime import datetime,timezone
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from workbench_analysis import dm01_runtime_r4 as r
from workbench_analysis import dm01_lineage_r4r1 as l
from tests.v4_dm01_r4r1.test_lineage import env

def main():
    folder=ROOT/'reports/dm01_r4r1'
    write=lambda name,value:r.atomic(ROOT,folder/(name+'.json'),value)
    baseline=json.loads((folder/'ENTRY_BASELINE.json').read_bytes())
    root=folder/'engineering'/r.sha(ROOT/r.CONTRACT)[:8]
    e=env.__wrapped__(root)
    result=r.build_candidate(parent=e['parent'],freeze=e['freeze'],cal=e['calendar'],identity=e['identity'],root=root)
    candidate=r.read(root,result['candidate']);obs=r.read(root,candidate['target_session_observation_receipt'])
    ref=r.ref(ROOT,r.path(root,result['candidate']))
    write('LINEAGE_COMPOSITION_GATE',dict(status='PASS_LOCAL_REPAIRED',engineering_candidate=ref,
        composition=candidate['lineage_composition'],components={k:v['lineage_composition'] for k,v in candidate['components'].items()},
        scope='CONTRACT_DESIGN_OR_ENGINEERING_SIMULATION',real_forward_evidence=False))
    write('TARGET_SESSION_OBSERVATION_GATE',dict(status='PASS_LOCAL_REPAIRED',engineering_observation=obs,
        actual_real_observation='NOT_CREATED',same_day_observation_is_not_first_availability=True))
    write('FIRST_AVAILABILITY_GATE',dict(status='PASS_LOCAL_REPAIRED',engineering_result=l.first_availability(e['freeze'],root),
        whole_head_first_available_at_target_proven=False,accepted_first_availability_authorities=[],missing_proof='FALSE'))
    write('REAL_FORWARD_EVIDENCE_GATE',dict(status='PASS_LOCAL_REPAIRED',engineering_candidate=ref,
        real_forward_evidence=candidate['real_forward_evidence'],real_admission='EXACT_NATIVE_POST_CLOSE_EXTERNAL_AUTHORITY_ALL_NINE_CHECKS',
        false_real_forward_evidence='PROMOTION_REJECTED',external_acceptance_head_exists=(ROOT/r.ACCEPTANCE).exists()))
    template=l.head_lineage(e['parent']['head'],candidate,candidate['target_session_observation_receipt'])
    l.validate_head_lineage(template,e['parent']['head'])
    write('PROMOTED_HEAD_LINEAGE_GATE',dict(status='PASS_LOCAL_REPAIRED',engineering_head_template=template,
        simulated_template_only=True,real_data_head_moved=False))
    child=dict(e['parent']['head'],**template,final_candidate=result['candidate'],parent_archive=e['parent']['binding'],parent_head_sha256=e['parent']['binding']['sha256'])
    child_ref=r.atomic(root,root/'bridge_child.json',child,immutable=True)
    bridge=dict(contract_id='DM01_R25_TARGET_SESSION_PIT_BINDING_R4R1_V1',target_trade_date=candidate['target_trade_date'],
        parent_data_head=e['parent']['binding'],child_data_head=child_ref,candidate=result['candidate'],
        target_session_source_manifest=candidate['source_manifest'],target_session_all_nine_receipts=candidate['components'],
        target_session_observation_receipt=candidate['target_session_observation_receipt'])
    bridge_ref=r.atomic(root,root/'r25_target_bridge.json',bridge,immutable=True)
    value=l.validate_r25_binding(root,bridge_ref,engineering=True)
    write('R25_TARGET_SESSION_BINDING_GATE',dict(status='PASS_LOCAL_REPAIRED',engineering_binding=r.ref(ROOT,r.path(root,bridge_ref)),
        engineering_contract_result=value,R25='WAIT_ACCEPTED_DAILY_INPUT',whole_head_only_admission='REJECTED',real_grant=False))
    wait=r.session_gate('2026-10-08',datetime.now(timezone.utc).isoformat());assert wait['status']=='WAIT_MARKET_CLOSE'
    write('FUTURE_SESSION_WAIT_READBACK',dict(wait,real_target_session_package='NOT_CREATED',real_shadow_observations=0))
    allowed={'.gitattributes','src/workbench_analysis/dm01_runtime_r4.py','scripts/v4_16_go_forward_input_authority.py',
        'scripts/run_dm01_r4_regression.py','tests/v4_dm01_r4/test_runtime.py'}
    changed={p:dict(before=d,after=r.sha(ROOT/p)) for p,d in baseline['tracked'].items() if r.sha(ROOT/p)!=d}
    assert set(changed)<=allowed,changed
    assert all(r.sha(ROOT/p)==d for p,d in baseline['unrelated'].items())
    c=r.validate_registry(r.BUILDERS)
    assert r.sha(ROOT/r.HEAD)==baseline['tracked'][r.HEAD]
    protected={p:r.ref(ROOT,ROOT/p) for p in c['protected_runtime_paths']}
    assert all(b['sha256']==baseline['tracked'][p] for p,b in protected.items())
    write('PROTECTED_STATE',dict(status='PASS',declared_existing_source_changes=changed,protected=protected,
        data_head=r.ref(ROOT,ROOT/r.HEAD),calendar=r.ref(ROOT,ROOT/r.CALENDAR),
        R3_3_kernel=r.ref(ROOT,ROOT/'src/workbench_analysis/dm01_incremental_component_builders_r3_3.py'),
        independent_postcheck=r.ref(ROOT,ROOT/'src/workbench_analysis/dm01_independent_postcheck_r3_3.py'),
        unrelated_preserved=True,tdx_root_write_count=0,tdx_source_access='NOT_USED',real_target_session_package='NOT_CREATED',
        real_shadow_execution='NOT_STARTED',real_shadow_observations=0,R25='WAIT_ACCEPTED_DAILY_INPUT',permissions=r.PERMISSIONS))
    print(json.dumps(dict(status='PASS_R4R1_ENGINEERING_GATES',real_forward_evidence=False,next='STOP_WAIT_DM01_R4R1_INDEPENDENT_EXTERNAL_AUDIT')))

if __name__=='__main__':main()
