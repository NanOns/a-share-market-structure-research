"""Read accepted DM01 chains, retaining exact historical moving-head identities."""
from pathlib import Path
import hashlib,json
from .daily_data_head import CAPABILITIES, canonical_digest
from .daily_source_freeze import build_source_freeze_manifest_v2

HEAD_PATH='data/v4/V4_DATA_ACCEPTED_HEAD.json'
ANCHOR_SHA='186b1c88512a5a92e7c4fbd954e5dcd005a0ad03ecbac9c334b05939d9e12de0'
AUDITED_HEAD='ac811e210c66b7ee9446086659dee169ee0f81a8'
AUDIT_PATH='docs/evidence/source_authority/V4_DM01_A01_R3_AND_A13_FORMALIZATION_INDEPENDENT_EXTERNAL_ACCEPTANCE_20261001.md'
AUDIT_SHA='03fd49c643d21304d2e8460cebbeec4b6b3f794ffd28562fdebf3f1ec38f79ef'
HEAD_CONTRACT='V4_DATA_ACCEPTED_HEAD_V2'
ACCEPTED_NODE_SHAS=('b338caaea8f9e41228a62add7e987d946f4dc9a5a5297dbe02e9ee73df525313','0a67e7211572a7057c50ab27e397c3e093f88c24732e8c7be7bdda92952ca1bf','e4ba1fb6d4690b869f98ffc45a8d576a641ef2e9a852a9db97aedd19e043bc81')

class AcceptedChainError(ValueError):pass

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def binding(root,path):
    p=Path(root)/path
    return dict(path=path,sha256=sha(p),bytes=p.stat().st_size)
def bound_path(root,ref):
    root=Path(root).resolve();path=(root/ref['path']).resolve()
    if not path.is_relative_to(root) or not path.is_file() or sha(path)!=ref['sha256']:
        raise AcceptedChainError('EXACT_BINDING_INVALID:'+str(ref.get('path')))
    for key in ('bytes','byte_count'):
        if key in ref and path.stat().st_size!=ref[key]:raise AcceptedChainError('BINDING_SIZE_INVALID')
    return path
def load(root,ref):return json.loads(bound_path(root,ref).read_bytes())

def require_audit(root,authority):
    expected=dict(path=AUDIT_PATH,sha256=AUDIT_SHA,bytes=10761)
    if authority.get('document')!=expected or authority.get('audited_head')!=AUDITED_HEAD or authority.get('authority_kind')!='INDEPENDENT_EXTERNAL_ACCEPTANCE':
        raise AcceptedChainError('INVALID_EXTERNAL_AUTHORITY_BINDING')
    text=bound_path(root,expected).read_text(encoding='utf8')
    for statement in ('DM01_A01_R3_REAL_CONTINUOUS_CHAIN = EXTERNAL_ACCEPTANCE_PASS_SCOPED','AUTHORIZED_TO_2026_09_30_AFTER_FORMALIZATION','A13_EXTERNAL_ACCEPTANCE_FORMALIZATION = EXTERNAL_ACCEPTANCE_PASS'):
        if statement not in text:raise AcceptedChainError('AUDIT_DISPOSITION_MISSING')

def resolve_frozen_binding(root,ref):
    """Only an explicitly promoted V2 anchor may redirect an old namespace binding."""
    root=Path(root);head=json.loads((root/HEAD_PATH).read_bytes())
    if ref.get('path')==HEAD_PATH and ref.get('sha256')==ANCHOR_SHA and head.get('contract_id')==HEAD_CONTRACT:
        archive=head['parent_archive']
        if archive['path']==HEAD_PATH or archive['sha256']!=ANCHOR_SHA or archive.get('bytes')!=2478:
            raise AcceptedChainError('HISTORICAL_ANCHOR_ARCHIVE_INVALID')
        if head.get('external_acceptance')!='EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN':
            raise AcceptedChainError('UNACCEPTED_ARCHIVE_REDIRECTION')
        record=load(root,head['external_acceptance_record']);require_audit(root,record['external_authority'])
        p=bound_path(root,archive)
        if json.loads(p.read_bytes()).get('accepted_trade_date')!='2026-09-24':raise AcceptedChainError('ARCHIVE_CUTOFF_INVALID')
        for key in ('bytes','byte_count'):
            if key in ref and ref[key]!=2478:raise AcceptedChainError('ARCHIVE_NAMESPACE_SIZE_INVALID')
        return p
    return bound_path(root,ref)

class HistoricalProjectView:
    """Read-only view for the unchanged R1 registry's frozen publication-time heads."""
    def __init__(self,root):self.root=Path(root).resolve()
    def resolve(self):return self
    def __truediv__(self,path):
        if str(path).replace('\\','/')==HEAD_PATH:
            return resolve_frozen_binding(self.root,dict(path=HEAD_PATH,sha256=ANCHOR_SHA))
        return self.root/path

def validate_historical_incremental_registry(root):
    from .dm01_accepted_builder_registry import validate_incremental_registry
    return validate_incremental_registry(project_root=HistoricalProjectView(root))

def permission_from_receipt(root,marker,cap):
    receipt=marker['components'][cap]
    path=str(Path(receipt['artifact_path']).parent/'receipt.json').replace('\\','/')
    ref=binding(root,path)
    if load(root,ref)!=receipt:raise AcceptedChainError('COMPONENT_RECEIPT_NOT_EXACT')
    return dict(status=receipt['status'],cutoff=receipt['target_trade_date'],receipt=ref,
        artifact=dict(path=receipt['artifact_path'],sha256=receipt['artifact_sha256'],bytes=receipt['artifact_bytes']),
        logical_digest=receipt['logical_digest'],row_count=receipt['row_count'],
        quality_counts=receipt['quality_counts'],unknown_reason_counts=receipt['unknown_reason_counts'],
        accepted_algorithm_contract=receipt['accepted_algorithm_contract'],accepted_owner_stage=receipt['accepted_owner_stage'],
        capability_basis='EXACT_EXTERNALLY_ACCEPTED_FINAL_COMPONENT_RECEIPT; ROW_READY_DOES_NOT_UPGRADE_CAPABILITY')

def validate_registry_r10(root,registry):
    require_audit(root,registry['external_authority'])
    entries={e['audit_id']:e for e in registry['entries']}
    a=entries['V4_02_STATUS_ST_SOURCE_AUTHORITY_DIVERGENCE'];d=entries['DM01_REAL_INCREMENTAL_BUILDERS'];e=entries['OFFICIAL_NOTICE_FILENAME_VS_EVENT_SEMANTICS']
    if any(a.get(k)!=v for k,v in dict(status='ACCEPTED_SOURCE_AUTHORITY_SCOPE',external_acceptance='EXTERNALLY_ACCEPTED',historical_path_b='EXTERNALLY_ACCEPTED_RECONSTRUCTED_ONLY',daily_producer_authority='EXTERNALLY_ACCEPTED',observed_daily_producer_acceptance='EXTERNALLY_ACCEPTED_PRODUCER_SOURCE_INSTANCE_MODEL',capability_limitations=[]).items()):raise AcceptedChainError('A12_CURRENT_STATE_CONTRADICTION')
    if 'transition' in a or 'NO_FUNCTIONAL_CLOSURE' in a.get('acceptance_scope','') or 'READY_FOR_EXTERNAL_REAUDIT' in a.get('implementation_status',''):raise AcceptedChainError('A12_STALE_CURRENT_TRANSITION')
    if any(d.get(k)!=v for k,v in dict(status='ACCEPTED',implementation_status='EXTERNAL_ACCEPTANCE_PASS_REAL_CONTINUOUS_CHAIN',external_acceptance='PASS_REAL_INCREMENTAL_CHAIN_20260928_20260930',formal_consumer_authorization=True,dm01_all_nine_accepted=True,accepted_through='2026-09-30',remaining_external_gate=None,production_gate=True).items()):raise AcceptedChainError('DM01_CURRENT_ACCEPTANCE_INVALID')
    if e.get('formalization_external_reaudit')!='PASS' or e.get('external_acceptance')!='PASS_EVIDENCE_GOVERNANCE_NO_BUSINESS_IMPACT' or e.get('v4_08_head_action')!='KEEP':raise AcceptedChainError('A13_CURRENT_ACCEPTANCE_INVALID')
    if entries['OWNER_REGISTRY_BOOTSTRAP_FOR_EXISTING_ACCEPTED_FIELDS']['status']!='OPEN' or registry['global_mandatory_adoption_authorized'] or any(registry['permissions'].values()):raise AcceptedChainError('PRODUCTION_OR_GLOBAL_ADOPTION_OVERCLAIM')
    return True

def validate_chain(root,chain,*,source_readback=False):
    require_audit(root,chain['external_authority'])
    archive=chain['anchor']['archive'];old=load(root,archive)
    namespace=chain['anchor']['original_namespace']
    if namespace!=dict(path=HEAD_PATH,sha256=ANCHOR_SHA,bytes=2478) or archive['sha256']!=ANCHOR_SHA or old.get('accepted_trade_date')!='2026-09-24':raise AcceptedChainError('ANCHOR_INVALID')
    record=load(root,chain['external_acceptance_record']);require_audit(root,record['external_authority'])
    for ref in record['evidence_bindings']:bound_path(root,ref)
    for key in ('source_authority_registry','source_authority_governance'):
        if record[key]!=chain[key]:raise AcceptedChainError('RECORD_SOURCE_AUTHORITY_MISMATCH')
        bound_path(root,chain[key])
    if chain['accepted_through']!=record['accepted_through'] or any(chain[k] for k in ('production','shadow','focus')):
        raise AcceptedChainError('CHAIN_SCOPE_OR_PERMISSION_INVALID')
    if tuple(n['candidate']['sha256'] for n in chain['nodes'])!=ACCEPTED_NODE_SHAS or record['audited_head']!=AUDITED_HEAD:raise AcceptedChainError('CANDIDATE_OUTSIDE_EXTERNAL_AUDIT_SCOPE')
    if record['external_acceptance']!='EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN' or record['accepted_through']!='2026-09-30':raise AcceptedChainError('CHAIN_NOT_EXTERNALLY_ACCEPTED')
    context=load(root,chain['source_context']);contract=load(root,chain['builder_contract'])
    if contract['execution_context']!=chain['source_context']:raise AcceptedChainError('SOURCE_CONTEXT_NOT_CONTRACT_BOUND')
    for r in contract['runtime_bindings']:bound_path(root,r)
    calendar=load(root,context['calendar']['binding']);identity=load(root,context['identity']['binding'])
    if calendar['session_dates']!=context['calendar']['session_dates'] or identity['records']!=context['identity']['records']:raise AcceptedChainError('PUBLICATION_CONTENT_MISMATCH')
    expected_sessions=calendar['session_dates'];parent=namespace;parent_date=old['accepted_trade_date'];out=[]
    for node in chain['nodes']:
        target=node['trade_date']
        if next((d for d in expected_sessions if d>parent_date),None)!=target or node['parent']!=parent:raise AcceptedChainError('CHAIN_PARENT_OR_SESSION_GAP')
        marker=load(root,node['candidate']);parent_context=load(root,marker['parent_context_binding'])
        if marker['contract_id']!='DM01_ATOMIC_CONTINUOUS_CANDIDATE_R3_3' or marker['status']!='READY_FOR_EXTERNAL_REAUDIT' or marker['target_trade_date']!=target or marker['parent_data_head_digest']!=parent['sha256'] or parent_context['binding']!=parent or marker['accepted_anchor']!=namespace:raise AcceptedChainError('NODE_NOT_EXACT_AUDITED_CANDIDATE')
        if set(marker['components'])!=set(CAPABILITIES) or node['components']!=marker['components'] or node['source_instances']!=marker['source_instance_digests']:raise AcceptedChainError('INCOMPLETE_NODE_OR_INSTANCE_BINDING')
        manifest=load(root,parent_context['component_manifest_binding'])
        if manifest['components']!=parent_context['components'] or manifest['parent_data_head_digest']!=parent['sha256']:raise AcceptedChainError('PARENT_MANIFEST_MISMATCH')
        post=load(root,marker['cross_postcheck_binding'])
        if post['status']!='PASS' or canonical_digest(post)!=marker['postcheck_digest']:raise AcceptedChainError('NODE_POSTCHECK_NOT_PASS')
        source=context['inputs'][target]
        freeze=build_source_freeze_manifest_v2(trade_date=target,sources=source['families'],changed_tdx_files=[],observed_at=context['observed_at'],ingested_at=context['observed_at'],system_available_at=context['observed_at'])
        freeze.update(inputs=source['inputs'],parent_data_head_digest=parent['sha256'],calendar_publication_id=context['calendar']['publication_id'],identity_publication_id=context['identity']['publication_id'],field_source_instances=source['instances'],tdx_roots=['D:/new_tdx'],knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False)
        freeze['manifest_sha256']=canonical_digest({k:v for k,v in freeze.items() if k!='manifest_sha256'})
        if freeze['manifest_sha256']!=marker['source_freeze_digest'] or freeze['field_source_instances']!=node['source_instances']:raise AcceptedChainError('SOURCE_FREEZE_REVISION_MISMATCH')
        for cap,r in marker['components'].items():
            ref=dict(path=r['artifact_path'],sha256=r['artifact_sha256'],bytes=r['artifact_bytes']);payload=load(root,ref)
            if payload['trade_date']!=target or len(payload['rows'])!=r['row_count'] or canonical_digest(payload['rows'])!=r['logical_digest'] or r['status'] not in ('FULL_PASS','DEGRADED_PASS'):raise AcceptedChainError('COMPONENT_CONTENT_OR_PERMISSION_INVALID')
        if source_readback:
            from .source_authority_producers_r4 import require_formal_source
            governance=load(root,chain['source_authority_governance_config'])
            for family,ref in freeze['source_families'].items():bound_path(root,ref)
            for ref in freeze['inputs'].values():bound_path(root,ref)
            for field,ref in node['source_instances'].items():
                rule=next(r for r in governance['field_rules'] if r['field_id']==field)
                require_formal_source(Path(root),rule,consumer_contract_id='DM01_FINAL_ALL_NINE',target_trade_date=target,instance_binding=ref)
            from .dm01_independent_postcheck_r3_3 import check_cross_components
            fresh=check_cross_components(marker['components'],freeze,parent_context,context['calendar'],context['identity'])
            if fresh['status']!='PASS' or canonical_digest(fresh)!=marker['postcheck_digest']:raise AcceptedChainError('INDEPENDENT_SOURCE_POSTCHECK_MISMATCH')
        out.append(dict(trade_date=target,candidate=node['candidate'],components=9,status='PASS',source_readback=source_readback))
        parent=node['candidate'];parent_date=target
    if len(out)!=3 or parent_date!=record['accepted_through'] or record['candidate_bindings']!=[n['candidate'] for n in chain['nodes']]:raise AcceptedChainError('ACCEPTED_CHAIN_SCOPE_MISMATCH')
    return out

def validate_head_v2(root,head,*,source_readback=False):
    if head.get('contract_id')!=HEAD_CONTRACT or head.get('version')!='2.0.0':raise AcceptedChainError('DATA_HEAD_V2_CONTRACT_REQUIRED')
    contract=load(root,head['contract'])
    if contract['contract_id']!=HEAD_CONTRACT or set(head)!=set(contract['required_fields']):raise AcceptedChainError('DATA_HEAD_SCHEMA_FIELDS_INVALID')
    for ref in contract['runtime_bindings']:bound_path(root,ref)
    if any(head['permissions'].values()) or head['AS_RECORDED'] or head['first_available_at_target_proven'] or head['knowledge_lineage']!='RECONSTRUCTED_CORRECTED':raise AcceptedChainError('DATA_HEAD_PERMISSION_OR_TEMPORAL_OVERCLAIM')
    chain=load(root,head['accepted_chain']);record=load(root,head['external_acceptance_record']);registry=load(root,head['audit_registry'])
    validate_registry_r10(root,registry);nodes=validate_chain(root,chain,source_readback=source_readback)
    final=load(root,head['final_candidate'])
    if head['accepted_trade_date']!=nodes[-1]['trade_date'] or head['final_candidate']!=chain['nodes'][-1]['candidate'] or head['parent_archive']!=chain['anchor']['archive'] or head['parent_head_sha256']!=ANCHOR_SHA:raise AcceptedChainError('DATA_HEAD_CHAIN_LINEAGE_INVALID')
    if head['manifest_path']!=head['accepted_chain']['path'] or head['manifest_sha256']!=head['accepted_chain']['sha256'] or head['canonical_data_revision']!=final['logical_digest'] or head['source_revision']!=final['source_freeze_digest']:raise AcceptedChainError('DATA_HEAD_REVISION_MISMATCH')
    expected={cap:permission_from_receipt(root,final,cap) for cap in CAPABILITIES}
    if head['component_permissions']!=expected or head['component_artifacts']!={k:v['artifact'] for k,v in expected.items()}:raise AcceptedChainError('CAPABILITY_PERMISSION_UPGRADE_OR_RECEIPT_MISMATCH')
    if head['calendar']!=final['calendar_binding'] or head['identity']!=final['identity_binding'] or head['external_acceptance_record']!=chain['external_acceptance_record'] or head['external_acceptance']!=record['external_acceptance']:raise AcceptedChainError('DATA_HEAD_AUTHORITY_BINDING_MISMATCH')
    for key in ('source_authority_governance','source_authority_registry','stage_head','dev_baseline'):bound_path(root,head[key])
    if head['source_authority_governance']!=chain['source_authority_governance'] or head['source_authority_registry']!=chain['source_authority_registry'] or head['stage_accepted_head_sha256']!=head['stage_head']['sha256'] or head['dev_baseline_sha256']!=head['dev_baseline']['sha256']:raise AcceptedChainError('DATA_HEAD_GOVERNANCE_MISMATCH')
    return dict(status='PASS',accepted_trade_date=head['accepted_trade_date'],nodes=nodes,permissions=head['permissions'])
