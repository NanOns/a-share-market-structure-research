"""Versioned scoped dispositions; never a business authority or runtime fallback."""
from copy import deepcopy
from .dm01_accepted_chain_v1 import binding, bound_path, load
from .parallel_scoped_acceptance_r1 import (
    PERMISSIONS, record_path, validate_record, OWNER_PATH, READER_PATH,
    validate_accepted_owner_metadata, validate_reader_manifest,
    validate_protected_binding, PROTECTED_REPRESENTATIONS,
)

DOC = 'docs/evidence/next_round_r3/'
AUDIT = DOC + 'V4_R2_BATCH_INDEPENDENT_EXTERNAL_AUDIT_R2_20261002.md'
TASK = DOC + 'V4_PARALLEL_SCOPED_FORMALIZATION_CONSOLIDATION_TASK_20261002.md'
MASTER = DOC + 'V4_NEXT_ROUND_EXECUTION_MASTER_R3_20261002.md'
BASELINE = 'd119c0526e44a819f85b4917159d3eeb5daadf2a'
PRIOR = 'reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R12_FORMALIZATION_R2.json'
REGISTRY = 'reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R13_CONSOLIDATION_R3.json'
AUTHORITY = 'data/v4/V4_SOURCE_AUTHORITY_SCOPED_DISPOSITION_REGISTRY_R5_INACTIVE.json'
SUMMARY = 'data/v4/V4_PARALLEL_SCOPED_ACCEPTANCE_SUMMARY_HEAD_R3.json'
PREFIX = 'reports/next_round_r3/scoped_consolidation/'
DISPOSITIONS = {
    'A03': 'SCOPED_ACCEPTED / ACCUMULATION_CONTINUES',
    'A06': 'SCOPED_ACCEPTED / FAIL_CLOSED_NO_TOLERANCE',
    'A07': 'SCOPED_ACCEPTED / PERMANENT_PRECAPTURE_LIMITATION',
    'OWNER': 'SCOPED_ACCEPTED_INACTIVE_METADATA',
    'READER': 'SCOPED_ACCEPTED_HISTORY_ONLY',
}
LIMITATIONS = {
    'A03': ['FORWARD_ACCUMULATION_CONTINUES', 'NO_RETROACTIVE_AS_RECORDED_FABRICATION',
            'FUTURE_OBSERVATION_COUNT_IS_NOT_ENGINEERING_OPEN_BLOCKER'],
    'A06': ['ALL_UNDOCUMENTED_TOLERANCES_NULL', 'STRICT_BINDING_FALSE',
            'BAOSTOCK_SUPPLEMENTAL_ONLY', 'TDX_CORE_NEVER_BLOCKED_BY_SUPPLEMENTAL_MISMATCH'],
    'A07': ['PRECAPTURE_HISTORICAL_AS_RECORDED_ABSENCE_PERMANENT',
            'GO_FORWARD_LINEAGE_BEGINS_AT_REAL_CAPTURE_TIME', 'FORMAL_CONSUMER_DISABLED'],
    'OWNER': ['INACTIVE_METADATA', 'NO_GLOBAL_AUTHORITY_CONSUMER', 'FIELD_LIMITATIONS_PRESERVED'],
    'READER': ['ACCEPTED_HISTORY_EXPLICIT_DI_ONLY', 'NO_CURRENT_BUSINESS_RUNTIME_SILENT_FALLBACK'],
}
AUDIT_LITERALS = {
    'A03': 'PASS_SCOPED_FORMALIZATION\nACCUMULATION_CONTINUES',
    'A06': 'PASS_SCOPED_FORMALIZATION\nFAIL_CLOSED_NO_TOLERANCE',
    'A07': 'PASS_SCOPED_FORMALIZATION\nPERMANENT_PRECAPTURE_LIMITATION',
    'OWNER': 'PASS_SCOPED_INACTIVE_METADATA',
    'READER': 'PASS_SCOPED_HISTORY_ONLY',
}


def external_authority(root):
    return dict(authority_kind='INDEPENDENT_EXTERNAL_ACCEPTANCE', audited_head=BASELINE,
                document=binding(root, AUDIT))


def dispositions(root):
    return {package: dict(
        disposition=disposition, engineering_task='CLOSED_SCOPED',
        capability_limitations=LIMITATIONS[package], blocks_v4_11_mainline=False,
        reopen_each_round=False, permissions=PERMISSIONS,
        prior_acceptance_record=binding(root, record_path(package)),
        external_authority=external_authority(root),
    ) for package, disposition in DISPOSITIONS.items()}


def protected_bindings(root):
    batch = load(root, binding(root, 'reports/next_round_r3/BATCH_STAGE_ENTRY_R1.json'))
    # Preserve the original pinned bytes from entry, not the checkout's current
    # Git representation. This metadata never changes a business head binding.
    refs = {ref['path']:deepcopy(ref) for ref in batch['protected_heads']}
    extra_paths = {
        PRIOR, 'data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R3.json', OWNER_PATH, READER_PATH,
        'config/baostock_binding_tolerance_policy_r2_candidate.json',
    }
    for path in extra_paths:
        refs.setdefault(path,binding(root,path))
    return [refs[path] for path in sorted(refs)]


def validate_scoped_protected_binding(root, ref, *, approved_representation_map=PROTECTED_REPRESENTATIONS):
    """Only the existing two exact original/archive/Git representations apply.

    Direct bytes are checked first by the pinned metadata helper. Its fallback
    requires both exact archive and Git bytes plus exact CRLF-to-LF equality;
    unknown drift and unregistered paths never resolve. Evidence and runtime
    bindings continue to use strict bound_path; no business resolver is changed.
    """
    if approved_representation_map != PROTECTED_REPRESENTATIONS:
        raise ValueError('SCOPED_UNAPPROVED_PROTECTED_REPRESENTATION_MAP')
    return validate_protected_binding(root,ref)


def supersession_map(root):
    edges = [dict(previous=binding(root, PRIOR), current=binding(root, REGISTRY),
                  action='LATEST_SCOPED_DISPOSITION_OVERLAY; ORIGINAL_REGISTRY_RETAINED')]
    edges.extend(dict(previous=row['prior_acceptance_record'], current=binding(root, REGISTRY),
                      package=package, action='EXTERNAL_R2_SCOPED_DISPOSITION_CONSOLIDATION')
                 for package, row in dispositions(root).items())
    edges.append(dict(previous=binding(root, OWNER_PATH), current=binding(root, AUTHORITY),
                      action='INACTIVE_METADATA_INDEX_ONLY; ORIGINAL_OWNER_FIELDS_RETAINED'))
    edges.append(dict(previous=binding(root, READER_PATH), current=binding(root, AUTHORITY),
                      action='HISTORY_ONLY_EXPLICIT_DI_INDEX; CURRENT_BUSINESS_VALIDATOR_RETAINED'))
    return dict(contract_id='PARALLEL_SCOPED_SUPERSESSION_MAP_R3', history_bytes_preserved=True,
                scope='SCOPED_METADATA_DISPOSITIONS_ONLY', edges=edges, permissions=PERMISSIONS)


def validate_consolidation(root, registry):
    if registry.get('contract_id') != 'PARALLEL_SCOPED_FORMALIZATION_CONSOLIDATION_R3':
        raise ValueError('CONSOLIDATION_CONTRACT_INVALID')
    if registry.get('external_authority') != external_authority(root):
        raise ValueError('CONSOLIDATION_EXTERNAL_AUTHORITY_INVALID')
    audit = bound_path(root, registry['external_authority']['document']).read_text(encoding='utf8')
    if BASELINE not in audit or any(literal not in audit for literal in AUDIT_LITERALS.values()):
        raise ValueError('CONSOLIDATION_EXTERNAL_SCOPE_MISSING')
    if registry.get('permissions') != PERMISSIONS or registry.get('head_action') != dict(data='KEEP', stage='KEEP'):
        raise ValueError('CONSOLIDATION_PERMISSION_OVERCLAIM')
    if registry.get('v4_12_runtime_authorized') is not False or registry.get('formal_v4_11_accepted_head_authorized') is not False:
        raise ValueError('CONSOLIDATION_STAGE_ENTRY_FORBIDDEN')
    if registry.get('supersedes') != binding(root, PRIOR):
        raise ValueError('CONSOLIDATION_PRIOR_REGISTRY_INVALID')
    if registry.get('stage_contract') != binding(root, TASK) or registry.get('master') != binding(root, MASTER):
        raise ValueError('CONSOLIDATION_TASK_BINDING_INVALID')
    expected = deepcopy(load(root, binding(root, PRIOR))['entries'])
    for package, row in dispositions(root).items():
        prior_record = load(root, row['prior_acceptance_record'])
        validate_record(root, prior_record, package)
        expected[package] = dict(expected[package], **row)
    if registry.get('entries') != expected:
        raise ValueError('CONSOLIDATION_DISPOSITION_OR_UNSCOPED_ENTRY_CHANGED')
    if registry.get('protected_bindings') != protected_bindings(root):
        raise ValueError('CONSOLIDATION_PROTECTION_REQUIRED')
    batch = load(root, binding(root, 'reports/next_round_r3/BATCH_STAGE_ENTRY_R1.json'))
    if registry['external_authority']['document'] != batch['authority'] or registry['master'] != batch['master']:
        raise ValueError('CONSOLIDATION_BATCH_AUTHORITY_BINDING_CHANGED')
    for ref in registry.get('protected_bindings', []):
        validate_scoped_protected_binding(root, ref)
    if not registry.get('protected_bindings'):
        raise ValueError('CONSOLIDATION_PROTECTION_REQUIRED')
    if registry.get('status') != 'PARALLEL_SCOPED_FORMALIZATION_CONSOLIDATED':
        raise ValueError('CONSOLIDATION_COMPLETION_INVALID')
    return dict(status='PASS_VERSIONED_SCOPED_CONSOLIDATION', packages=DISPOSITIONS,
                engineering_tasks_closed=5, capability_limitations_retained=True,
                blocks_v4_11_mainline=False, permissions=PERMISSIONS)


def validate_authority_registry(root, registry):
    expected = dict(
        contract_id='V4_SOURCE_AUTHORITY_SCOPED_DISPOSITION_REGISTRY_R5_INACTIVE', version=5,
        registration_status='SCOPED_ACCEPTED_INACTIVE_METADATA', active_global_trust_root=False,
        active_registry=binding(root, 'data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R3.json'),
        accepted_owner_metadata=binding(root, OWNER_PATH), accepted_history_reader=binding(root, READER_PATH),
        remediation_registry=binding(root, REGISTRY), scoped_dispositions=dispositions(root),
        permissions=PERMISSIONS,
    )
    if registry != expected:
        raise ValueError('SCOPED_AUTHORITY_ACTIVATION_OR_SCOPE_INVALID')
    validate_consolidation(root, load(root, registry['remediation_registry']))
    validate_accepted_owner_metadata(root, load(root, registry['accepted_owner_metadata']))
    validate_reader_manifest(root, load(root, registry['accepted_history_reader']))
    return dict(status='PASS_INACTIVE_SCOPED_AUTHORITY_REGISTRY', active_global_trust_root=False,
                current_business_runtime_fallback=False)


def validate_summary(root, head):
    expected = dict(
        contract_id='PARALLEL_SCOPED_ACCEPTANCE_SUMMARY_HEAD_R3', version=3,
        status='PARALLEL_SCOPED_FORMALIZATION_CONSOLIDATED', head_kind='SCOPED_METADATA_SUMMARY_ONLY',
        data_head_action='KEEP', stage_head_action='KEEP', dispositions=DISPOSITIONS,
        remediation_registry=binding(root, REGISTRY), authority_registry=binding(root, AUTHORITY),
        supersession_map=binding(root, PREFIX + 'SUPERSESSION_MAP_R3.json'), permissions=PERMISSIONS,
        business_runtime_authority=False, formal_v4_11_accepted_head=False,
    )
    if head != expected:
        raise ValueError('SCOPED_SUMMARY_HEAD_OVERCLAIM')
    validate_authority_registry(root, load(root, head['authority_registry']))
    supersession = load(root, head['supersession_map'])
    if supersession != supersession_map(root):
        raise ValueError('SCOPED_SUPERSESSION_INVALID')
    for edge in supersession['edges']:
        bound_path(root, edge['previous'])
        bound_path(root, edge['current'])
    return dict(status='PASS_SCOPED_SUMMARY_HEAD', permissions=PERMISSIONS,
                business_runtime_authority=False)
