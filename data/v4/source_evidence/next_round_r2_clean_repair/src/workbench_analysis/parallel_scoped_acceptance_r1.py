"""Exact external scope formalization, without movable-head or consumer cutover."""
from copy import deepcopy
from pathlib import Path
import json
from .dm01_accepted_chain_v1 import binding,bound_path,load

AUDITED='66ef2e342dd339cc9795c2d1fd774b8edec4c345'
AUDIT=dict(path='docs/evidence/next_round_r2/V4_NEXT_ROUND_10_CARD_BATCH_INDEPENDENT_EXTERNAL_AUDIT_R1_20261001.md',sha256='7d6c8d3faf64a948d206a318d122d41baf757613d0beb88e6d5bd54fcff96bb3',bytes=8244)
DISPOSITIONS={
    'A03':'PASS_FORWARD_PIT_BUILDER_SCOPE',
    'A06':'PASS_FAIL_CLOSED_NO_TOLERANCE_AUTHORIZED',
    'A07':'PASS_LINEAGE_CAPTURE_SCOPE_WITH_PERMANENT_PRECAPTURE_BLOCK',
    'OWNER':'SCOPED_ACCEPTED_OWNER_BOOTSTRAP_R1',
    'READER':'PASS_HISTORY_ONLY_DI_HARDENING',
}
CURRENT_STATES=dict(A03='ACCUMULATION_CONTINUES',A06='ACCEPTED_SCOPED',A07='PERMANENT_CAPABILITY_BLOCK',OWNER='INACTIVE_ACCEPTED_METADATA',READER='ACCEPTED_SCOPED')
AUDIT_LITERALS={'A03':'PASS_BUILDER_SCOPE_ACCUMULATION_CONTINUES','A06':DISPOSITIONS['A06'],'A07':DISPOSITIONS['A07'],'OWNER':'PASS_SCOPED_INACTIVE_CANDIDATE','READER':DISPOSITIONS['READER']}
PERMISSIONS=dict(production=False,shadow=False,focus=False,global_mandatory_adoption=False,formal_consumer_cutover=False)
RECORD_ROOT='reports/next_round_r2/scoped_acceptance/'
OWNER_PATH='data/v4/SCOPED_ACCEPTED_OWNER_BOOTSTRAP_R1.json'
READER_PATH='config/historical_publication_reader_accepted_history_only_r1.json'


def record_path(package):
    if package not in DISPOSITIONS:raise ValueError('UNKNOWN_SCOPED_PACKAGE')
    return RECORD_ROOT+package+'_EXTERNAL_ACCEPTANCE_RECORD_R1.json'


def validate_record(root,record,package):
    if package not in DISPOSITIONS or record.get('package')!=package or record.get('contract_id')!='PARALLEL_SCOPED_EXTERNAL_ACCEPTANCE_RECORD_R1':raise ValueError('SCOPED_RECORD_IDENTITY_INVALID')
    expected=dict(authority_kind='INDEPENDENT_EXTERNAL_ACCEPTANCE',audited_head=AUDITED,document=AUDIT)
    if record.get('external_authority')!=expected:raise ValueError('SCOPED_EXTERNAL_AUTHORITY_INVALID')
    text=bound_path(root,AUDIT).read_text(encoding='utf8')
    if AUDITED not in text or AUDIT_LITERALS[package] not in text:raise ValueError('SCOPED_EXTERNAL_DISPOSITION_MISSING')
    if record.get('disposition')!=DISPOSITIONS[package] or record.get('external_acceptance')!='EXTERNALLY_ACCEPTED_SCOPED':raise ValueError('SCOPED_ACCEPTANCE_OVERCLAIM')
    if record.get('current_state')!=CURRENT_STATES[package]:raise ValueError('SCOPED_CURRENT_STATE_CONTRADICTION')
    if record.get('permissions')!=PERMISSIONS or record.get('business_reacceptance') is not False or record.get('head_action')!=dict(data='KEEP',stage='KEEP',v4_06='KEEP',v4_09='KEEP',v4_10='KEEP'):raise ValueError('SCOPED_PERMISSION_OVERCLAIM')
    if not record.get('evidence_bindings') or not record.get('runtime_bindings'):raise ValueError('SCOPED_PROOF_REQUIRED')
    for ref in [*record['evidence_bindings'],*record['runtime_bindings'],*record['protected_heads']]:bound_path(root,ref)
    return dict(status='PASS_EXACT_SCOPED_EXTERNAL_ACCEPTANCE',package=package,disposition=record['disposition'])


def require_record(root,package):
    ref=binding(root,record_path(package));record=load(root,ref);validate_record(root,record,package)
    return record


def validate_accepted_owner_metadata(root,metadata):
    from .source_authority_owner_bootstrap_r1 import validate_registry
    record=require_record(root,'OWNER')
    if metadata.get('contract_id')!=DISPOSITIONS['OWNER'] or metadata.get('acceptance_record')!=binding(root,record_path('OWNER')):raise ValueError('OWNER_FORMAL_RECORD_INVALID')
    if metadata.get('external_authority')!=record['external_authority'] or metadata.get('registration_status')!='ACCEPTED_SCOPED_INACTIVE_METADATA':raise ValueError('OWNER_FORMAL_AUTHORITY_INVALID')
    if metadata.get('permissions')!=PERMISSIONS or metadata.get('active_global_trust_root') is not False:raise ValueError('OWNER_FORMAL_CUTOVER_FORBIDDEN')
    if metadata.get('accepted_candidate')!=binding(root,'data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R4_CANDIDATE.json'):raise ValueError('OWNER_ACCEPTED_CANDIDATE_BINDING_INVALID')
    original=load(root,metadata['accepted_candidate'])
    validate_registry(root,original)
    if metadata.get('owners')!=original['owners']:raise ValueError('OWNER_LIMITATION_OR_FIELD_SCOPE_CHANGED')
    if metadata.get('field_external_dispositions')!={x['field_id']:'EXTERNALLY_ACCEPTED_SCOPED_INACTIVE_METADATA' for x in original['owners']}:raise ValueError('OWNER_FIELD_EXTERNAL_DISPOSITION_CHANGED')
    if metadata.get('active_registry')!=binding(root,'data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R3.json'):raise ValueError('ACTIVE_REGISTRY_REPLACEMENT_FORBIDDEN')
    return dict(status='PASS_INACTIVE_ACCEPTED_METADATA',fields=len(original['owners']),formal_consumer_cutover=False)


def accepted_forward_append(root,ledger,envelope,**kwargs):
    require_record(root,'A03')
    original='data/v4/a03_forward_pit_r2'
    if (Path(root)/ledger).resolve()==(Path(root)/original).resolve():raise ValueError('HISTORICAL_LEDGER_WRITE_FORBIDDEN_IN_FORMALIZATION')
    from .forward_pit_ledger_r2_1 import append_observation
    return append_observation(root,ledger,envelope,**kwargs)


def accepted_adjusted_lineage(root,record,*,knowledge_time):
    require_record(root,'A07')
    from .adjusted_price_lineage_r2 import classify_lineage
    result=classify_lineage(root,record,knowledge_time=knowledge_time)
    if result['formal_consumer_enabled'] is not False:raise ValueError('ADJUSTED_CONSUMER_CUTOVER_FORBIDDEN')
    return dict(result,external_acceptance_scope=DISPOSITIONS['A07'],pre_capture_permanently_blocked=True)


def validate_reader_manifest(root,manifest):
    require_record(root,'READER')
    if manifest.get('contract_id')!='ACCEPTED_HISTORY_ONLY_PUBLICATION_READER_R1' or manifest.get('accepted_reader_version')!='v2':raise ValueError('HISTORY_READER_VERSION_INVALID')
    if manifest.get('acceptance_record')!=binding(root,record_path('READER')) or manifest.get('validation_scope')!='ACCEPTED_PUBLICATION_HISTORY_ONLY':raise ValueError('HISTORY_READER_ACCEPTANCE_SCOPE_INVALID')
    if manifest.get('permissions')!=PERMISSIONS or manifest.get('business_reacceptance') is not False:raise ValueError('HISTORY_READER_PERMISSION_OVERCLAIM')
    expected=[binding(root,p) for p in ['src/workbench_analysis/dm01_publication_history_reader_v2.py','src/workbench_analysis/dm01_publication_history_reader_v1.py','scripts/promote_v4_09_accepted_head.py','scripts/validate_v4_10_promotion_r1.py']]
    if manifest.get('reader_and_preserved_validator_bindings')!=expected:raise ValueError('HISTORY_READER_RUNTIME_BINDING_INVALID')
    return dict(status='PASS_ACCEPTED_V2_HISTORY_ONLY',business_reacceptance=False,production_authorization=False)


def read_accepted_history(root,stage,candidate=None):
    manifest=load(root,binding(root,READER_PATH));validate_reader_manifest(root,manifest)
    from . import dm01_publication_history_reader_v2 as reader
    if stage=='V4-09':
        if candidate is not None:raise ValueError('V4_09_CUSTOM_PUBLICATION_NOT_AUTHORIZED')
        return reader.validate_v4_09_history(project_root=root)
    if stage=='V4-10':return reader.validate_v4_10_history(candidate,project_root=root)
    raise ValueError('BUSINESS_STAGE_OUTSIDE_ACCEPTED_HISTORY_SCOPE')
