"""Adversarial scoped authority, permanent limitation, and head preservation gates."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from workbench_analysis.parallel_scoped_consolidation_r3 import (
    REGISTRY, AUTHORITY, SUMMARY, PREFIX, PRIOR, DISPOSITIONS, PERMISSIONS,
    validate_consolidation, validate_authority_registry, validate_summary,
)

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads((ROOT / path).read_bytes())


def test_serialized_latest_registry_retains_external_scopes_and_prior_unscoped_entries():
    registry = read(REGISTRY)
    result = validate_consolidation(ROOT, registry)
    assert result['engineering_tasks_closed'] == 5
    prior = read(PRIOR)
    for package in prior['entries'].keys() - DISPOSITIONS.keys():
        assert registry['entries'][package] == prior['entries'][package]
    for package, disposition in DISPOSITIONS.items():
        row = registry['entries'][package]
        assert row['disposition'] == disposition
        assert row['engineering_task'] == 'CLOSED_SCOPED'
        assert row['blocks_v4_11_mainline'] is False
        assert row['reopen_each_round'] is False
    assert registry['head_action'] == {'data': 'KEEP', 'stage': 'KEEP'}


@pytest.mark.parametrize('fault', [
    'production', 'shadow', 'focus', 'global_mandatory_adoption', 'formal_consumer_cutover',
    'task_authority', 'wrong_audit_head', 'missing_protection', 'reduced_protection',
    'stage_promotion', 'data_promotion', 'v4_12', 'v4_11_head', 'unscoped_a04',
    'a07_limitation_erased', 'a03_future_blocker', 'reader_current_fallback',
])
def test_registry_rejects_authority_or_scope_escalation(fault):
    registry = deepcopy(read(REGISTRY))
    if fault in PERMISSIONS:
        registry['permissions'][fault] = True
    elif fault == 'task_authority':
        registry['external_authority']['authority_kind'] = 'TASK_CARD'
    elif fault == 'wrong_audit_head':
        registry['external_authority']['audited_head'] = '0' * 40
    elif fault == 'missing_protection':
        registry['protected_bindings'] = []
    elif fault == 'reduced_protection':
        registry['protected_bindings'] = registry['protected_bindings'][:1]
    elif fault == 'stage_promotion':
        registry['head_action']['stage'] = 'V4_11_ACCEPTED'
    elif fault == 'data_promotion':
        registry['head_action']['data'] = 'PROMOTE'
    elif fault == 'v4_12':
        registry['v4_12_runtime_authorized'] = True
    elif fault == 'v4_11_head':
        registry['formal_v4_11_accepted_head_authorized'] = True
    elif fault == 'unscoped_a04':
        registry['entries']['A04']['consumer_adoption'] = True
    elif fault == 'a07_limitation_erased':
        registry['entries']['A07']['capability_limitations'] = []
    elif fault == 'a03_future_blocker':
        registry['entries']['A03']['blocks_v4_11_mainline'] = True
    elif fault == 'reader_current_fallback':
        registry['entries']['READER']['capability_limitations'] = ['CURRENT_RUNTIME_FALLBACK']
    with pytest.raises(ValueError):
        validate_consolidation(ROOT, registry)


@pytest.mark.parametrize('fault', ['active', 'runtime', 'owner_hash', 'global', 'reader_business'])
def test_authority_remains_inactive_with_exact_owner_and_reader_scope(fault):
    registry = deepcopy(read(AUTHORITY))
    if fault == 'active':
        registry['active_global_trust_root'] = True
    elif fault == 'runtime':
        registry['registration_status'] = 'GLOBAL_ACTIVE_AUTHORITY'
    elif fault == 'owner_hash':
        registry['accepted_owner_metadata']['sha256'] = '0' * 64
    elif fault == 'global':
        registry['permissions']['global_mandatory_adoption'] = True
    elif fault == 'reader_business':
        registry['scoped_dispositions']['READER']['disposition'] = 'CURRENT_BUSINESS_ACCEPTED'
    with pytest.raises(ValueError):
        validate_authority_registry(ROOT, registry)


@pytest.mark.parametrize('fault', ['stage_kind', 'business', 'v4_11', 'head_promotion', 'permission', 'wrong_binding'])
def test_scoped_summary_cannot_masquerade_as_stage_or_business_authority(fault):
    head = deepcopy(read(SUMMARY))
    if fault == 'stage_kind':
        head['head_kind'] = 'V4_STAGE_ACCEPTED_HEAD'
    elif fault == 'business':
        head['business_runtime_authority'] = True
    elif fault == 'v4_11':
        head['formal_v4_11_accepted_head'] = True
    elif fault == 'head_promotion':
        head['stage_head_action'] = 'PROMOTE'
    elif fault == 'permission':
        head['permissions']['production'] = True
    elif fault == 'wrong_binding':
        head['authority_registry']['sha256'] = '0' * 64
    with pytest.raises(ValueError):
        validate_summary(ROOT, head)


def test_real_independent_readback_preserves_permanent_capability_and_current_fail_closed_gate():
    report = read(PREFIX + 'INDEPENDENT_READBACK_R3.json')
    assert report['status'] == 'PASS' and report['protected_bytes_unchanged']
    assert report['a03']['future_observation_count_is_engineering_blocker'] is False
    assert all(value is None for value in report['a06']['tolerances'].values())
    assert report['a06']['conflict']['strict_binding'] is False
    assert report['a06']['conflict']['tdx_core_blocked'] is False
    assert report['a07']['engineering_task'] == 'CLOSED_SCOPED'
    assert report['a07']['before_capture']['historical_capability'] == 'PERMANENTLY_BLOCKED_PRE_CAPTURE_AS_RECORDED'
    assert report['a07']['at_capture']['lineage'] == 'AS_RECORDED'
    assert report['a07']['at_capture']['formal_consumer_enabled'] is False
    assert report['owner']['fields'] == 7 and report['owner']['inactive_metadata']
    assert report['reader']['silent_fallback'] is False and report['reader']['explicit_di_only']
    assert report['reader']['current_business_validator']['checks']['P19_protected'] == 'FAIL'
    assert report['reader']['module_roots_unchanged']
    assert validate_authority_registry(ROOT, read(AUTHORITY))['active_global_trust_root'] is False
    assert validate_summary(ROOT, read(SUMMARY))['business_runtime_authority'] is False
