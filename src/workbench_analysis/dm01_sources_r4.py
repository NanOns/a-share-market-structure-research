"""Exact current V2 projections and target-session availability for R4 kernels."""
from datetime import datetime
from pathlib import Path
import json
from . import dm01_runtime_r4 as runtime
from .daily_source_manifests import build_current_lifecycle_snapshot
from .source_authority_producers_r4 import require_accepted_producer

def parent_tdx_package(root):
    parent=runtime.current_parent(root)
    candidate=runtime.read(root,parent['head']['final_candidate'])
    if candidate['contract_id']=='DM01_ATOMIC_GO_FORWARD_CANDIDATE_R4':
        freeze=runtime.read(root,candidate['source_manifest'])
        binding=freeze['source_families']['TDX_FULL_PACKAGE']
    else:
        chain=runtime.read(root,parent['head']['accepted_chain'])
        context=runtime.read(root,chain['source_context'])
        binding=context['inputs'][parent['head']['accepted_trade_date']]['families']['TDX_FULL_PACKAGE']
    runtime.path(root,binding)
    return binding

def identity_projection(root, target, observed_at):
    root=Path(root); c=json.loads((runtime.ROOT/runtime.CONTRACT).read_bytes())
    head=runtime.read(root,c['accepted_identity_head']); original=runtime.read(root,head['identity_revision'])
    records=[]
    for row in original['records']:
        available=row.get('system_available_at',head.get('accepted_at'))
        if available is None:
            # Exact accepted identity publication existed before this runtime;
            # use its recorded capture time, never wall-clock promotion time.
            available=c['identity_known_at']
        runtime.require(datetime.fromisoformat(available.replace('Z','+00:00'))<=datetime.fromisoformat(observed_at.replace('Z','+00:00')), 'IDENTITY_FUTURE_KNOWLEDGE')
        records.append(dict(row,board_scope=row.get('board_scope') or (row['exchange']+'_MAIN' if row['board']=='MAIN' else row['board']),system_available_at=available))
    payload=dict(contract_id='DM01_R4_EXACT_IDENTITY_PROJECTION_V1',target_trade_date=target,accepted_head=c['accepted_identity_head'],source_identity=head['identity_revision'],records=records)
    p=root/'data/v4/dm01_r4/source_projections'/runtime.digest(payload)/'identity.json'
    binding=runtime.atomic(root,p,payload,immutable=True)
    return dict(status='ACCEPTED_IDENTITY_SOURCE_PROJECTION',binding=dict(binding,path=str(p)),publication_id=binding['sha256'],records=records)

def lifecycle(root,target,bao,observed_at):
    parent=runtime.current_parent(root); cal=runtime.calendar(root)
    identity=identity_projection(root,target,observed_at)
    rows=runtime.read(root,parent['components']['IDENTITY_UNIVERSE'])['rows']
    return build_current_lifecycle_snapshot(trade_date=target,baseline_date=parent['head']['accepted_trade_date'],baseline_data_head=parent['head'],parent_universe_rows=rows,identity_records=identity['records'],baostock_snapshot=bao,official_session_bridge=dict(status='PASS',latest_completed_official_session=parent['head']['accepted_trade_date'],official_sessions_after_base_cutoff=[d for d in cal['session_dates'] if d>parent['head']['accepted_trade_date']]),source_evidence=dict(parent=parent['binding'],identity=identity['binding'],calendar=cal['binding']),observed_at=observed_at)

def project_source_freeze(root,freeze,tdx_capture_binding,bao_binding,runtime_binding):
    root=Path(root); c=json.loads((runtime.ROOT/runtime.CONTRACT).read_bytes())
    target=freeze['trade_date']; now=freeze['observed_at']; parent=runtime.current_parent(root); cal=runtime.calendar(root)
    identity=identity_projection(root,target,now)
    bao=runtime.read(root,bao_binding); capture=runtime.read(root,tdx_capture_binding)
    acceptance=runtime.read(root,runtime_binding)
    runtime.require(acceptance.get('live_smoke',{}).get('target_date')==target, 'BAOSTOCK_ACCEPTANCE_TARGET_MISMATCH')
    for operation in bao['query_operations']:
        runtime.require(operation['params']['date']==target, 'BAOSTOCK_QUERY_TARGET_MISMATCH')
    runtime.require(bao['query_operations'][0]['response_sha256']==runtime.digest(bao['daily_rows']), 'BAOSTOCK_RAW_RESPONSE_DIGEST_MISMATCH')
    roles=runtime.read(root,c['producer_governance'])['field_rules']
    proofs=[]
    for field in ('TRADING_STATUS','ISST'):
        rule=next(r for r in roles if r['field_id']==field)
        proof=require_accepted_producer(root,rule,consumer_contract_id='DM01_FINAL_ALL_NINE')
        runtime.require(not proof['owner']['OHLC_authority'] and not proof['owner']['adjustment_authority'], 'BAOSTOCK_AUTHORITY_ESCALATION')
        proofs.append(proof['entry']['producer_contract'])
    gbbq_manifest=runtime.read(root,freeze['source_families']['GBBQ']); gbbq_path=runtime.path(root,freeze['source_families']['GBBQ']).parent/'gbbq'
    runtime.require(runtime.sha(gbbq_path)==gbbq_manifest['files']['gbbq']['sha256'], 'GBBQ_BINARY_DIGEST_MISMATCH')
    inputs=dict(TDX_PACKAGE_DELTA=freeze['source_families']['TDX_PACKAGE_DELTA'],BAOSTOCK_DAILY_UPDATE=bao_binding,GBBQ=runtime.ref(root,gbbq_path),PRICE_RULES=c['price_rules'],SPECIAL_PRICE_PHASE=freeze['source_families']['SPECIAL_PRICE_PHASE'])
    # Reuse exact accepted classifications only for the identical GBBQ revision.
    meta=runtime.read(root,c['gbbq_dispositions'])
    runtime.require(meta['gbbq_sha256']==inputs['GBBQ']['sha256'], 'NEW_GBBQ_REQUIRES_ACCEPTED_CLASSIFICATION')
    inputs['GBBQ_DISPOSITIONS']=c['gbbq_dispositions']
    def evidence(binding,native):
        captured=native.get('captured_at') or native.get('observed_at')
        received=native.get('received_at') or native.get('downloaded_at') or native.get('system_available_at')
        runtime.require(captured is not None and received is not None, 'NATIVE_SOURCE_AVAILABILITY_TIMESTAMP_MISSING')
        return dict(binding=binding,target_trade_date=target,provider_date=native.get('provider_date',native.get('update_date')),source_provider_available_at=native.get('source_provider_available_at'),system_available_at=native.get('system_available_at') or received,captured_at=captured,received_at=received)
    result=dict(freeze,inputs=inputs,parent_data_head_digest=parent['binding']['sha256'],calendar_publication_id=cal['publication_id'],identity_publication_id=identity['publication_id'],knowledge_lineage='PIT_OBSERVED',AS_RECORDED=True,availability_evidence={'TDX_FULL_PACKAGE':evidence(tdx_capture_binding,capture),'BAOSTOCK_DAILY_UPDATE':evidence(bao_binding,bao)},source_authority_bindings=proofs+[runtime_binding],tdx_roots=c['read_only_tdx_roots'])
    result['manifest_sha256']=runtime.digest({k:v for k,v in result.items() if k!='manifest_sha256'})
    runtime.validate_lineage(result,root)
    return result,parent,cal,identity
