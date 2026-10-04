"""Deterministic exact bridge/daily/packet producer; never grants or executes."""
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from scripts import r25_bridge_oracle_r4r2 as o
from workbench_analysis import dm01_runtime_r4 as r

def produce_bridge(root,*,parent,child,candidate,source,receipts,observation,target,observed_at,output,engineering=False):
    root=Path(root).resolve()
    r.require(type(engineering) is bool,'BRIDGE_MODE_REQUIRES_BOOL')
    r.require(not engineering or not r.ROOT.resolve().is_relative_to(root),'REAL_ROOT_ENGINEERING_BRIDGE_FORBIDDEN')
    r.require(engineering or (root/output).resolve().is_relative_to((root/'reports/r25/target_session_bridge').resolve()),'BRIDGE_OUTPUT_ROOT_REQUIRED')
    if not engineering:
        now=datetime.fromisoformat(observed_at.replace('Z','+00:00'))
        r.require(now.tzinfo is not None,'BRIDGE_CLOCK_FUTURE_OR_NAIVE')
        local=now.astimezone(ZoneInfo('Asia/Shanghai'))
        if local.date().isoformat()<target or (local.date().isoformat()==target and local.hour<15):
            return dict(status='WAIT_MARKET_CLOSE',bridge_created=False,r25_grant=False,source_requests=0)
        r.require(now<=datetime.now(timezone.utc),'BRIDGE_CLOCK_FUTURE_OR_NAIVE')
    b=dict(contract_id=o.BRIDGE_ID,parent_data_head=parent,child_data_head=child,candidate=candidate,
           target_trade_date=target,target_session_source_manifest=source,
           target_session_all_nine_receipts=receipts,target_session_observation_receipt=observation)
    # Validate prospective bytes through a memory reference without publishing.
    validate_bridge_object(root,b,engineering=engineering)
    if not engineering:
        r.require(r.current_parent(root)['binding']==child,'BRIDGE_CHILD_NOT_CURRENT')
        r.validate_lineage(o.exact(root,source),root)
    reference=r.atomic(root,root/output,b,immutable=True)
    return dict(status='PASS_ENGINEERING_BRIDGE_NOT_REAL' if engineering else 'PASS_EXACT_TARGET_BRIDGE',binding=reference,r25_grant=False,real_ready=not engineering)

def validate_bridge_object(root,b,*,engineering=False):
    # Pure oracle accepts an explicit in-memory object only at this exact root.
    o.inspect_bridge_object(root,b,engineering=engineering)

def produce_daily(root,template,bridge,*,output,engineering=False):
    root=Path(root).resolve()
    r.require(type(engineering) is bool and (not engineering or not r.ROOT.resolve().is_relative_to(root)),'REAL_ROOT_ENGINEERING_DAILY_FORBIDDEN')
    r.require(engineering or (root/output).resolve().is_relative_to((root/'data/v4/go_forward_inputs/r4r2').resolve()),'DAILY_OUTPUT_ROOT_REQUIRED')
    c=o.contract(root,o.binding(root,o.CONTRACT_PATH))
    daily=dict(template,contract_id=c['contract_id'],target_session_pit_binding=bridge)
    daily.pop('daily_input_digest',None)
    if engineering:daily.update(evidence_class='ENGINEERING_VECTOR',not_real_evidence=True,bridge_mode='ENGINEERING')
    daily['daily_input_digest']=o.digest(daily)
    o.inspect_daily_bridge(root,daily,o.binding(root,o.CONTRACT_PATH),engineering=engineering)
    r.require(set(c['required_fields'])<=daily.keys(),'SUCCESSOR_DAILY_FIELDS_MISSING')
    return r.atomic(Path(root),Path(root)/output,daily,immutable=True)

def produce_packet(root,*,daily,candidate,sources,predecessor,output,engineering=False):
    from scripts.validate_r25_preflight import inspect_inputs,dependency_digest
    root=Path(root);deps_ref=o.binding(root,'config/v4_16_runtime_dependencies_v4.json');deps=o.exact(root,deps_ref)
    r.require(type(engineering) is bool and (not engineering or not r.ROOT.resolve().is_relative_to(root.resolve())),'REAL_ROOT_ENGINEERING_PACKET_FORBIDDEN')
    r.require((root/output).resolve().is_relative_to((root/'reports/r25/activation_candidate').resolve()),'PACKET_OUTPUT_ROOT_REQUIRED')
    for reference in deps['bindings']:o.exact_bytes(root,reference)
    r.require(o.exact(root,deps['packet_contract'])['go_forward_input_contract']==deps['go_forward_input'],'PREFLIGHT_RUNTIME_CONTRACT_SPLIT')
    d=o.exact(root,daily);a=o.exact(root,candidate)
    r.require(a['grant']['daily_input_authority']==daily and a['grant']['source_authority']==sources and a['grant']['predecessor']==predecessor,'PACKET_EXACT_GRANT_BINDING_MISMATCH')
    result=inspect_inputs(root,a,d,o.exact(root,sources),deps,o.exact(root,deps['go_forward_input']),o.exact(root,predecessor),test_only=engineering)
    packet=dict(contract_id='V4_16_R25_PACKET_R4R2_V1',packet_contract=deps['packet_contract'],runtime_dependencies=deps_ref,go_forward_contract=deps['go_forward_input'],
        activation_candidate=candidate,daily_input_authority=daily,source_authority=sources,predecessor=predecessor,
        target_session_pit_binding=d['target_session_pit_binding'],daily_input_digest=d['daily_input_digest'],
        authority_digest=result['authority_digest'],dependency_set_digest=dependency_digest(deps),execution_authorized=False,external_acceptance=None,
        storage_identity=a['grant']['storage_identity'],initialization_boundary=deps['initialization_boundary'],rollback_identity=a['grant']['rollback_identity'])
    from scripts.validate_r25_preflight import protected
    packet.update(protected_state=dict(engineering_only=True,real_shadow_observations=0) if engineering else protected(root),r24r1_tested_source='3eb148c3c19ca079fd5986aeb3a1922b9bf43075',
        r24r1_tested_tag='refs/tags/codex/r24r1-go-forward-tested-source-20261004-r3',
        r24r1_external_acceptance=o.binding(root,'docs/evidence/r25/V4_R24R1_GO_FORWARD_INPUT_AUTHORITY_COHORT_IDENTITY_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md'))
    if engineering:packet.update(not_real_evidence=True,evidence_class='ENGINEERING_VECTOR')
    packet['packet_digest']=o.digest(packet)
    return r.atomic(root,root/output,packet,immutable=True)
