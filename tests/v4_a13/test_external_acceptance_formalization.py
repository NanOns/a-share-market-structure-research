"""Real A13 acceptance readback and independently bound provenance guards."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from workbench_analysis.official_event_acceptance_v1 import (
    AUDIT, AUDITED_HEAD, HEAD, require_accepted_semantic_head, require_trading_event)

ROOT = Path(__file__).resolve().parents[2]


def read(root, path):
    return json.loads((root / path).read_text(encoding='utf8'))


def install(root):
    head = read(ROOT, HEAD)
    config = read(ROOT, head['config']['path'])
    bindings = [head[k] for k in ('external_authority', 'sidecar', 'content_addressed_sidecar',
                                 'runtime', 'config', 'candidate')]
    bindings.append(config['semantic_runtime'])
    for binding in bindings:
        path = root / binding['path']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / binding['path']).read_bytes())
    write(root, HEAD, head)
    return head


def write(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True), encoding='utf8')
    data = target.read_bytes()
    return dict(path=path, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def test_real_accepted_sidecar_is_exact_candidate_semantics_with_external_audit():
    head, sidecar = require_accepted_semantic_head(ROOT)
    candidate = read(ROOT, head['candidate']['path'])
    assert candidate['external_acceptance'] is None
    assert head['external_authority']['path'] == AUDIT
    assert head['external_authority']['audited_head'] == AUDITED_HEAD
    assert sidecar['entries'] == candidate['entries']
    assert len(sidecar['entries']) == 134
    assert not sidecar['formal_consumer_authorization']
    assert not sidecar['positive_trading_event_authority_consumed']
    assert not any(e['consumer_permissions']['TRADING_STATUS_TRUTH'] for e in sidecar['entries'])


@pytest.mark.parametrize('kind', [
    'IPO_ISSUANCE_POSTPONEMENT', 'IPO_LISTING_POSTPONEMENT', 'UNKNOWN_EVENT_SEMANTICS'])
def test_real_accepted_head_never_upgrades_non_trading_document(kind):
    head, sidecar = require_accepted_semantic_head(ROOT)
    entries = [e for e in sidecar['entries'] if e['actual_event_type'] == kind]
    assert entries
    for event in entries:
        with pytest.raises(ValueError, match='OFFICIAL_NOTICE_NOT_A_DATED_TRADING_EVENT'):
            require_trading_event(ROOT, head['sidecar'], event['raw_artifact'],
                                  security_key=event['security_key'], effective_date=event['event_effective_date'])


@pytest.mark.parametrize('mutation', [
    'task_card_authority', 'wrong_audit_sha', 'wrong_audited_head', 'audit_role', 'wrong_runtime_sha',
    'wrong_config_sha', 'wrong_candidate_sha', 'wrong_content_address', 'business_rebuild',
    'production_permission', 'shadow_permission', 'focus_permission', 'unaccepted', 'sidecar_entries',
    'sidecar_authority', 'candidate_authorized', 'wrong_scope'])
def test_external_acceptance_provenance_rejects_forged_or_out_of_scope_head(tmp_path, mutation):
    head = install(tmp_path)
    if mutation == 'task_card_authority':
        path = 'docs/evidence/source_authority/REPAIR_TASK_CARD.md'
        value = '修复任务卡，不是独立外部验收'
        target = tmp_path / path
        target.write_text(value, encoding='utf8')
        head['external_authority'].update(path=path, bytes=len(target.read_bytes()),
            sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    elif mutation == 'wrong_audit_sha':
        head['external_authority']['sha256'] = '0' * 64
    elif mutation == 'wrong_audited_head':
        head['audited_head'] = '0' * 40
    elif mutation == 'audit_role':
        head['external_authority']['document_role'] = 'TASK_CARD'
    elif mutation == 'wrong_runtime_sha':
        head['runtime']['sha256'] = '0' * 64
    elif mutation == 'wrong_config_sha':
        head['config']['sha256'] = '0' * 64
    elif mutation == 'wrong_candidate_sha':
        head['candidate']['sha256'] = '0' * 64
    elif mutation == 'wrong_content_address':
        head['content_addressed_sidecar']['path'] = head['sidecar']['path']
    elif mutation == 'business_rebuild':
        head['business_rebuild_required'] = True
    elif mutation in ('production_permission', 'shadow_permission', 'focus_permission'):
        head[mutation] = True
    elif mutation == 'unaccepted':
        head['external_acceptance'] = None
    elif mutation == 'wrong_scope':
        head['acceptance_scope'] = 'TRADING_STATUS_TRUTH'
    else:
        sidecar = read(tmp_path, head['sidecar']['path'])
        if mutation == 'sidecar_entries':
            sidecar['entries'][0]['actual_event_type'] = 'LISTED_STOCK_TRADING_SUSPENSION'
            sidecar['entries'][0]['consumer_permissions']['TRADING_STATUS_TRUTH'] = True
        elif mutation == 'sidecar_authority':
            sidecar['external_authority']['document_role'] = 'TASK_CARD'
        elif mutation == 'candidate_authorized':
            sidecar['formal_consumer_authorization'] = True
        binding = write(tmp_path, head['sidecar']['path'], sidecar)
        head['sidecar'] = binding
        # Rebinding the artifact does not grant new semantic market authority.
        path = 'data/v4/artifact_store/a13/sha256-' + binding['sha256'] + '.json'
        head['content_addressed_sidecar'] = write(tmp_path, path, sidecar)
    write(tmp_path, HEAD, head)
    with pytest.raises(ValueError):
        require_accepted_semantic_head(tmp_path)


def test_fresh_counterfactual_equals_all_accepted_business_outputs():
    proof = read(ROOT, 'reports/audits/A13_FORMALIZATION_COUNTERFACTUAL_REVALIDATION_R1.json')
    assert proof['status'] == 'PASS_NO_BUSINESS_IMPACT_FORMALIZATION'
    assert proof['full_PIT_equal_to_accepted'] and proof['full_PIT_fact_count'] == 50162
    assert len(set(proof['full_admission_business_digests'].values())) == 1
    assert all(v['security_rows_changed'] == 0 and v['old_business_digest'] == v['new_business_digest']
               for v in proof['full_downstream_business_diff'].values())
    assert proof['replay_outputs']['path'].startswith('reports/audits/a13_formalization_counterfactual_r1/')
    assert proof['network_calls'] == 0 and not proof['raw_source_modified']


def test_same_path_audit_replacement_cannot_self_declare_acceptance(tmp_path):
    head = install(tmp_path)
    audit_path = tmp_path / AUDIT
    # Preserve every title/disposition token and use a correct new byte digest:
    # a different document still cannot inherit the independently pinned audit.
    audit_path.write_bytes(audit_path.read_bytes() + b'\nREPLACED_DOCUMENT\n')
    head['external_authority'].update(bytes=len(audit_path.read_bytes()),
        sha256=hashlib.sha256(audit_path.read_bytes()).hexdigest())
    write(tmp_path, HEAD, head)
    with pytest.raises(ValueError, match='INDEPENDENT_EXTERNAL_EVENT_ACCEPTANCE_REQUIRED'):
        require_accepted_semantic_head(tmp_path)
