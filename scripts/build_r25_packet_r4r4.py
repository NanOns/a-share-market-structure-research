"""V6 exact packet successor; bridge and daily authority remain R4R2."""
from pathlib import Path
from scripts import r25_bridge_oracle_r4r2 as o
from workbench_analysis import dm01_runtime_r4 as r

def produce_packet(root,*,daily,candidate,sources,predecessor,output,engineering=False):
    from scripts.validate_r25_preflight_v6 import inspect_inputs,dependency_digest
    root=Path(root);deps_ref=o.binding(root,'config/v4_16_runtime_dependencies_v6.json');deps=o.exact(root,deps_ref)
    r.require(type(engineering) is bool and (not engineering or not r.ROOT.resolve().is_relative_to(root.resolve())),'REAL_ROOT_ENGINEERING_PACKET_FORBIDDEN')
    r.require((root/output).resolve().is_relative_to((root/'reports/r25/activation_candidate').resolve()),'PACKET_OUTPUT_ROOT_REQUIRED')
    for reference in deps['bindings']:o.exact_bytes(root,reference)
    r.require(o.exact(root,deps['packet_contract'])['go_forward_input_contract']==deps['go_forward_input'],'PREFLIGHT_RUNTIME_CONTRACT_SPLIT')
    d=o.exact(root,daily);a=o.exact(root,candidate)
    r.require(a['grant']['daily_input_authority']==daily and a['grant']['source_authority']==sources and a['grant']['predecessor']==predecessor,'PACKET_EXACT_GRANT_BINDING_MISMATCH')
    result=inspect_inputs(root,a,d,o.exact(root,sources),deps,o.exact(root,deps['go_forward_input']),o.exact(root,predecessor),test_only=engineering)
    packet=dict(contract_id='V4_16_R25_PACKET_R4R4_V1',packet_contract=deps['packet_contract'],runtime_dependencies=deps_ref,go_forward_contract=deps['go_forward_input'],
        activation_candidate=candidate,daily_input_authority=daily,source_authority=sources,predecessor=predecessor,
        target_session_pit_binding=d['target_session_pit_binding'],daily_input_digest=d['daily_input_digest'],
        authority_digest=result['authority_digest'],dependency_set_digest=dependency_digest(deps),execution_authorized=False,external_acceptance=None,
        storage_identity=a['grant']['storage_identity'],initialization_boundary=deps['initialization_boundary'],rollback_identity=a['grant']['rollback_identity'])
    from scripts.validate_r25_preflight_v6 import packet_protected
    packet.update(protected_state=dict(engineering_only=True,real_shadow_observations=0) if engineering else packet_protected(root,d),r24r1_tested_source='3eb148c3c19ca079fd5986aeb3a1922b9bf43075',
        r24r1_tested_tag='refs/tags/codex/r24r1-go-forward-tested-source-20261004-r3',
        r24r1_external_acceptance=o.binding(root,'docs/evidence/r25/V4_R24R1_GO_FORWARD_INPUT_AUTHORITY_COHORT_IDENTITY_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md'))
    if engineering:packet.update(not_real_evidence=True,evidence_class='ENGINEERING_VECTOR')
    packet['packet_digest']=o.digest(packet)
    return r.atomic(root,root/output,packet,immutable=True)
