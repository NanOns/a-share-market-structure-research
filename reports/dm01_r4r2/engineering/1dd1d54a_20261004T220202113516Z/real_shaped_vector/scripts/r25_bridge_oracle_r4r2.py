"""Read-only exact R25 bridge oracle. No writer, execution, discovery or grants."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CONTRACT_PATH='config/v4_16_go_forward_input_authority_v1_1.json'
CONTRACT_ID='V4_16_GO_FORWARD_INPUT_AUTHORITY_V1_1'
BRIDGE_ID='DM01_R25_TARGET_SESSION_PIT_BINDING_R4R1_V1'
CAPS={'RAW_DAILY','IDENTITY_UNIVERSE','TRADING_STATUS','ISST','ADJUSTED_DAILY','PERIOD_RAW','PERIOD_ADJUSTED','PRICE_LIMIT','SPECIAL_PHASE'}
MIXED='MIXED_ACCEPTED_PARENT_PLUS_TARGET_SESSION_PIT'
def check(ok,reason):
    if not ok:raise ValueError(reason)
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def binding(root,path):
    p=(Path(root)/path).resolve();check(p.is_relative_to(Path(root).resolve()),'BRIDGE_OUTSIDE_PROJECT')
    raw=p.read_bytes();return dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def exact(root,b):
    check(isinstance(b,dict) and set(b)=={'path','bytes','sha256'},'BRIDGE_EXACT_BINDING_REQUIRED')
    check(binding(root,b['path'])==b,'BRIDGE_EXACT_BINDING_MISMATCH')
    return json.loads((Path(root)/b['path']).read_bytes())
def contract(root,ref):
    check(ref==binding(root,CONTRACT_PATH),'SUCCESSOR_CONTRACT_BINDING_REQUIRED')
    c=exact(root,ref);check(c['contract_id']==CONTRACT_ID and 'target_session_pit_binding' in c['required_fields'],'SUCCESSOR_DAILY_CONTRACT_REQUIRED')
    predecessor=exact(root,c['predecessor']);check(predecessor['contract_id']=='V4_16_GO_FORWARD_INPUT_AUTHORITY_V1','DAILY_PREDECESSOR_MISMATCH')
    archive=exact(root,c['immutable_data_head_readback'])
    check(c['immutable_data_head_readback']['sha256']==c['immutable_data_head_predecessor']['sha256'] and c['immutable_data_head_readback']['bytes']==c['immutable_data_head_predecessor']['bytes'] and archive['accepted_trade_date']=='2026-09-30','IMMUTABLE_DATA_ARCHIVE_MISMATCH')
    return c
def inspect_bridge(root,ref,*,engineering=False,test_only=False):
    return inspect_bridge_object(root,exact(root,ref),engineering=engineering,test_only=test_only)
def inspect_bridge_object(root,b,*,engineering=False,test_only=False):
    check(type(engineering) is bool and type(test_only) is bool,'BRIDGE_MODE_REQUIRES_BOOL')
    check(b.get('contract_id')==BRIDGE_ID,'BRIDGE_CONTRACT_MISMATCH')
    parent=exact(root,b['parent_data_head']);child=exact(root,b['child_data_head']);candidate=exact(root,b['candidate'])
    obs=exact(root,b['target_session_observation_receipt']);source=exact(root,b['target_session_source_manifest'])
    check(child.get('contract_id')=='V4_DATA_ACCEPTED_HEAD_V2','BRIDGE_V2_CHILD_REQUIRED')
    check(b['child_data_head']==binding(root,'data/v4/V4_DATA_ACCEPTED_HEAD.json'),'BRIDGE_CHILD_NOT_CURRENT')
    check(child['parent_archive']==b['parent_data_head'] and child['parent_head_sha256']==b['parent_data_head']['sha256']==candidate['parent_data_head_digest'],'BRIDGE_PARENT_MISMATCH')
    check(child['final_candidate']==b['candidate'],'BRIDGE_CANDIDATE_MISMATCH')
    check(b['target_trade_date']==child['target_session_trade_date']==child['accepted_trade_date']==candidate['target_trade_date']==source['trade_date']==obs['target_trade_date'],'BRIDGE_TARGET_MISMATCH')
    check(child['target_session_source_manifest']==candidate['source_manifest']==b['target_session_source_manifest'],'BRIDGE_SOURCE_MISMATCH')
    check(child['target_session_observation_receipt']==candidate['target_session_observation_receipt']==b['target_session_observation_receipt'],'BRIDGE_OBSERVATION_MISMATCH')
    check(child['target_session_all_nine_receipts']==candidate['components']==b['target_session_all_nine_receipts'] and set(candidate['components'])==CAPS,'BRIDGE_NINE_RECEIPTS_MISMATCH')
    check(child['knowledge_lineage']==MIXED and child['AS_RECORDED'] is False and child['first_available_at_target_proven'] is False,'BRIDGE_WHOLE_HEAD_OVERCLAIM')
    comp=child['lineage_composition'];check(comp['parent_head_lineage']==parent['knowledge_lineage'] and comp['parent_AS_RECORDED']==parent['AS_RECORDED'],'BRIDGE_INHERITED_LINEAGE_MISMATCH')
    check(source['manifest_sha256']==digest({k:v for k,v in source.items() if k!='manifest_sha256'}),'BRIDGE_SOURCE_DIGEST_MISMATCH')
    check(obs['source_manifest_digest']==source['manifest_sha256'] and obs['parent_head']==b['parent_data_head'],'BRIDGE_OBSERVATION_PROVENANCE_MISMATCH')
    for cap,receipt in candidate['components'].items():
        artifact=exact(root,dict(path=receipt['artifact_path'],sha256=receipt['artifact_sha256'],bytes=(Path(root)/receipt['artifact_path']).stat().st_size))
        check(receipt['component_id']==cap and receipt['target_trade_date']==b['target_trade_date'],'BRIDGE_RECEIPT_TARGET_MISMATCH')
        check(digest(artifact['rows'])==receipt['logical_digest'] and len(artifact['rows'])==receipt['row_count'],'BRIDGE_COMPONENT_LOGICAL_MISMATCH')
    if engineering:
        check(candidate['real_forward_evidence'] is False and obs['real_forward_evidence'] is False and child['target_session_real_forward_evidence'] is False and source['engineering_simulation'] is True,'BRIDGE_ENGINEERING_MUST_NOT_BE_REAL')
    else:
        check(candidate['real_forward_evidence'] is True,'BRIDGE_CANDIDATE_REAL_FORWARD_REQUIRED')
        check(obs['real_forward_evidence'] is True,'BRIDGE_OBSERVATION_REAL_FORWARD_REQUIRED')
        check(child['target_session_real_forward_evidence'] is True and child['target_session_observation_proven'] is True and obs['target_session_observation_proven'] is True and candidate['target_session_observation_proven'] is True and source.get('engineering_simulation',False) is False,'BRIDGE_REAL_TARGET_REQUIRED')
        check(child['target_session_evidence_class']=='PIT_OBSERVED' and obs['evidence_class']=='PIT_OBSERVED','BRIDGE_PIT_TARGET_REQUIRED')
        check(obs['engineering_simulation'] is False and candidate.get('engineering_simulation',False) is False and candidate['knowledge_lineage']==MIXED and candidate['AS_RECORDED'] is False and candidate['first_available_at_target_proven'] is False,'BRIDGE_CANDIDATE_LINEAGE_MISMATCH')
        check(candidate['lineage_composition']['parent_head']==b['parent_data_head'] and candidate['lineage_composition']['parent_head_lineage']==parent['knowledge_lineage'] and candidate['lineage_composition']['parent_AS_RECORDED']==parent['AS_RECORDED'],'BRIDGE_CANDIDATE_PARENT_LINEAGE_MISMATCH')
    # All modes validate exact lineage topology. Synthetic flags relax authority only.
    context=exact(root,candidate['parent_context'])
    check(context['head']==parent and context['components']==parent['component_artifacts'],'BRIDGE_PARENT_CONTEXT_MISMATCH')
    calhead=json.loads((Path(root)/'data/v4/DM01_R4_CALENDAR_HEAD_V1.json').read_bytes())
    calref=calhead['calendar'];cal=exact(root,calref)
    check(candidate['calendar']==child['calendar']==calref,'BRIDGE_CALENDAR_MISMATCH')
    sessions=cal['session_dates'];check(sessions[sessions.index(parent['accepted_trade_date'])+1]==b['target_trade_date'],'BRIDGE_NEXT_SESSION_MISMATCH')
    stamp=datetime.fromisoformat(source['observed_at'].replace('Z','+00:00'));local=stamp.astimezone(ZoneInfo('Asia/Shanghai'))
    check(stamp.tzinfo is not None and local.date().isoformat()==b['target_trade_date'] and local.hour>=15,'BRIDGE_BEFORE_CLOSE')
    check(obs['availability_evidence_digest']==digest(source['availability_evidence']) and obs['all_nine_checks_passed'] is True,'BRIDGE_NATIVE_OBSERVATION_MISMATCH')
    check(obs['engineering_observation_checks_passed'] is True and obs['first_available_at_target_proven'] is False,'BRIDGE_OBSERVATION_SCOPE_OVERCLAIM')
    check(obs['target_session_observed_at']==source['observed_at'] and obs['target_session_received_at']=={k:v['received_at'] for k,v in source['availability_evidence'].items()} and obs['native_source_bindings']=={k:v['binding'] for k,v in source['availability_evidence'].items()} and obs['permissions']==dict(production=False,shadow=False,focus=False),'BRIDGE_EXACT_OBSERVATION_SCOPE_MISMATCH')
    if not engineering and not test_only:
        check(not any(v.get('test_vector') or v.get('fixture_only') or v.get('not_real_evidence') for v in (b,parent,child,candidate,obs,source)),'BRIDGE_SYNTHETIC_REAL_FORBIDDEN')
        envelope=json.loads((Path(root)/'data/v4/DM01_R4_RUNTIME_ACCEPTANCE_HEAD_V1.json').read_bytes())
        check(envelope['status']=='EXTERNALLY_ACCEPTED_DM01_R4_RUNTIME' and envelope['external_verdict']=='PASS_DM01_R4R1_GO_FORWARD_RUNTIME','BRIDGE_EXTERNAL_ENVELOPE_REQUIRED')
        for path,key in [('config/dm01_go_forward_runtime_contract_r4r1.json','runtime_contract'),('config/dm01_v2_promotion_policy_r4r1.json','promotion_policy'),('data/v4/DM01_R4_CALENDAR_HEAD_V1.json','calendar_head')]:
            check(envelope[key]==binding(root,path),'BRIDGE_EXTERNAL_ENVELOPE_DIGEST_MISMATCH')
        doc=exact_bytes(root,envelope['independent_external_authority']).decode('utf8')
        check(envelope['external_verdict'] in doc and all(envelope[k]['sha256'] in doc for k in ('runtime_contract','promotion_policy','calendar_head')),'BRIDGE_EXTERNAL_DISPOSITION_MISSING')
        check(envelope['permissions']==dict(production=False,shadow=False,focus=False),'BRIDGE_PERMISSION_ESCALATION')
        check(child['external_acceptance']=='ACCEPTED_UNDER_DM01_R4_MACHINE_POLICY' and child['permissions']==envelope['permissions'],'BRIDGE_CHILD_MACHINE_ACCEPTANCE_REQUIRED')
        record=exact(root,child['external_acceptance_record']);chain=exact(root,child['accepted_chain'])
        check(record['status']=='ACCEPTED_UNDER_DM01_R4_MACHINE_POLICY' and record['candidate']==chain['candidate']==b['candidate'] and chain['acceptance']==child['external_acceptance_record'] and record['permissions']==candidate['permissions']==envelope['permissions'],'BRIDGE_CHILD_ACCEPTANCE_RECORD_MISMATCH')
        check(record['policy']==binding(root,'config/dm01_v2_promotion_policy_r4r1.json') and record['envelope']==binding(root,'data/v4/DM01_R4_RUNTIME_ACCEPTANCE_HEAD_V1.json') and record['parent']==chain['parent_head']==b['parent_data_head'] and chain['parent']==parent['accepted_chain'],'BRIDGE_CHILD_ACCEPTANCE_CHAIN_MISMATCH')
        check(set(child['component_artifacts'])==set(child['component_permissions'])==CAPS,'BRIDGE_CHILD_COMPONENTS_MISSING')
        for cap,receipt in candidate['components'].items():
            permission=child['component_permissions'][cap];artifact=child['component_artifacts'][cap]
            check(permission['artifact']==artifact and artifact['sha256']==receipt['artifact_sha256'] and permission['cutoff']==b['target_trade_date'] and permission['status'] in ('FULL_PASS','DEGRADED_PASS') and exact(root,permission['receipt'])==receipt,'BRIDGE_CHILD_COMPONENT_ACCEPTANCE_MISMATCH')
        check(source['knowledge_lineage']=='PIT_OBSERVED' and source['AS_RECORDED'] is True,'BRIDGE_SOURCE_PIT_REQUIRED')
        for x in [*source['source_families'].values(),*source['inputs'].values()]:exact_bytes(root,x)
        check(len(source['source_authority_bindings'])>=2,'BRIDGE_SOURCE_AUTHORITY_MISSING')
        for x in source['source_authority_bindings']:exact(root,x)
        check({'TDX_FULL_PACKAGE','BAOSTOCK_DAILY_UPDATE'}<=source['availability_evidence'].keys(),'BRIDGE_NATIVE_SOURCES_MISSING')
        for family,e in source['availability_evidence'].items():
            native=exact(root,e['binding']);check(native.get('fixture_scope') is None,'BRIDGE_NATIVE_FIXTURE_FORBIDDEN')
            check(e['target_trade_date']==e['provider_date']==b['target_trade_date'],'BRIDGE_NATIVE_PROVIDER_DATE_MISMATCH')
            check(native.get('target_date',native.get('trade_date'))==b['target_trade_date'],'BRIDGE_NATIVE_DATE_MISMATCH')
            check(native.get('provider_date',native.get('update_date',b['target_trade_date']))==b['target_trade_date'],'BRIDGE_NATIVE_PROVIDER_DATE_MISMATCH')
            check(e['captured_at']==(native.get('captured_at') or native.get('observed_at')) and e['received_at']==(native.get('received_at') or native.get('downloaded_at') or native.get('system_available_at')),'BRIDGE_NATIVE_TIMESTAMP_MISMATCH')
            check(e['system_available_at']==(native.get('system_available_at') or e['received_at']) and e.get('source_provider_available_at')==native.get('source_provider_available_at'),'BRIDGE_NATIVE_AVAILABILITY_MISMATCH')
            times={k:datetime.fromisoformat(e[k].replace('Z','+00:00')) for k in ('captured_at','received_at','system_available_at')}
            check(times['system_available_at']<=times['received_at'] and times['captured_at']<=times['received_at'],'BRIDGE_NATIVE_TIMESTAMP_ORDER')
            if e.get('source_provider_available_at'):check(datetime.fromisoformat(e['source_provider_available_at'].replace('Z','+00:00'))<=stamp,'BRIDGE_NATIVE_FUTURE_PROVIDER_TIMESTAMP')
            for key in ('captured_at','received_at','system_available_at'):
                t=datetime.fromisoformat(e[key].replace('Z','+00:00'));lt=t.astimezone(ZoneInfo('Asia/Shanghai'))
                check(t.tzinfo is not None and t<=stamp and lt.date().isoformat()==b['target_trade_date'] and (key=='system_available_at' or lt.hour>=15),'BRIDGE_NATIVE_TIMESTAMP_BOUNDARY')
        from workbench_analysis.dm01_independent_postcheck_r3_3 import check_cross_components
        identity=exact(root,candidate['identity'])
        post=check_cross_components(candidate['components'],source,context,dict(binding=calref,**cal),dict(binding=candidate['identity'],publication_id=candidate['identity']['sha256'],records=identity['records']))
        check(post['status']=='PASS' and digest(post)==candidate['postcheck_digest'],'BRIDGE_INDEPENDENT_POSTCHECK_FAILED')
    return dict(status='PASS_ENGINEERING_BRIDGE_NOT_REAL' if engineering or test_only else 'PASS_EXACT_TARGET_BRIDGE',r25_grant=False,real_ready=False if engineering or test_only else True,target_trade_date=b['target_trade_date'])
def exact_bytes(root,b):
    check(binding(root,b['path'])==b,'BRIDGE_EXACT_BINDING_MISMATCH');return (Path(root)/b['path']).read_bytes()
def inspect_daily_bridge(root,daily,contract_ref,*,engineering=False,test_only=False):
    c=contract(root,contract_ref)
    check(daily.get('contract_id')==c['contract_id'],'SUCCESSOR_DAILY_CONTRACT_REQUIRED')
    check(isinstance(daily.get('target_session_pit_binding'),dict),'R25_EXACT_TARGET_SESSION_BINDING_REQUIRED')
    check(daily['daily_input_digest']==digest({k:v for k,v in daily.items() if k!='daily_input_digest'}),'DAILY_BRIDGE_DIGEST_MISMATCH')
    result=inspect_bridge(root,daily['target_session_pit_binding'],engineering=engineering,test_only=test_only)
    check(daily['target_trade_date']==result['target_trade_date'],'DAILY_BRIDGE_TARGET_MISMATCH')
    if 'accepted_at' in daily:
        bridge=exact(root,daily['target_session_pit_binding']);obs=exact(root,bridge['target_session_observation_receipt'])
        check(datetime.fromisoformat(daily['accepted_at'].replace('Z','+00:00'))>=datetime.fromisoformat(obs['target_session_observed_at'].replace('Z','+00:00')),'DAILY_ACCEPTED_BEFORE_TARGET_OBSERVATION')
    if 'calendar' in daily:
        bridge=exact(root,daily['target_session_pit_binding']);child=exact(root,bridge['child_data_head'])
        check(daily['calendar']==child['calendar'],'DAILY_BRIDGE_CALENDAR_BINDING_MISMATCH')
        for family,cap in [('TDX_RAW_DAILY','RAW_DAILY'),('ADJUSTED_DAILY','ADJUSTED_DAILY')]:
            check(daily['sources'][family]['binding']==child['component_artifacts'][cap],'DAILY_BRIDGE_SOURCE_BINDING_MISMATCH')
    return dict(result,contract_binding=contract_ref,daily_input_digest=daily['daily_input_digest'])
