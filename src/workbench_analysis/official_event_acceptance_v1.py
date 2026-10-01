"""Exact external acceptance provenance for the versioned A13 semantic sidecar.

Acceptance covers evidence classification. Trading truth still requires an
individually authorized dated event and the original document proof.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .official_event_semantics_v1 import CONTRACT, require_trading_event as semantic_guard

HEAD = 'data/v4/OFFICIAL_EVENT_SEMANTICS_ACCEPTED_HEAD_R1.json'
CONFIG = 'config/official_event_semantics_accepted_r1.json'
AUDIT = 'docs/evidence/source_authority/V4_A10_A12_R3_AND_A13_INDEPENDENT_EXTERNAL_ACCEPTANCE_20261001.md'
AUDIT_SHA = 'a23789d9de4eb48831125cbb9165964a8dacacb33e9dd30dba0f3bfced681d3a'
AUDITED_HEAD = 'd85f815097a09ca2dceda00d0e29d6ff4fe331d4'
DISPOSITION = 'EXTERNAL_ACCEPTANCE_PASS_EVIDENCE_GOVERNANCE_NO_BUSINESS_IMPACT'


def exact_bytes(root, binding):
    root = Path(root).resolve()
    if not isinstance(binding, dict) or not isinstance(binding.get('path'), str):
        raise ValueError('EVENT_ACCEPTANCE_BINDING_REQUIRED')
    path = (root / binding['path']).resolve()
    if not path.is_relative_to(root):
        raise ValueError('EVENT_ACCEPTANCE_PATH_OUTSIDE_REPOSITORY')
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ValueError('EVENT_ACCEPTANCE_BOUND_ARTIFACT_MISSING') from exc
    if hashlib.sha256(data).hexdigest() != binding.get('sha256') or len(data) != binding.get('bytes'):
        raise ValueError('EVENT_ACCEPTANCE_EXACT_BYTES_MISMATCH')
    return data


def require_accepted_semantic_head(root):
    root = Path(root)
    try:
        head = json.loads((root / HEAD).read_text(encoding='utf8'))
    except (OSError, ValueError) as exc:
        raise ValueError('ACCEPTED_EVENT_SEMANTICS_REQUIRED') from exc
    if (head.get('contract_id') != 'OFFICIAL_EVENT_SEMANTICS_ACCEPTED_HEAD_V1'
            or head.get('external_acceptance') != 'EXTERNALLY_ACCEPTED'
            or head.get('audited_head') != AUDITED_HEAD
            or head.get('acceptance_scope') != 'EVIDENCE_GOVERNANCE_NO_BUSINESS_IMPACT'
            or head.get('business_rebuild_required') is not False
            or head.get('v4_08_head_action') != 'KEEP'
            or any(head.get(k) is not False for k in ('production_permission', 'shadow_permission', 'focus_permission'))):
        raise ValueError('EVENT_ACCEPTANCE_SCOPE_INVALID')
    authority = head.get('external_authority', {})
    if (authority.get('path') != AUDIT or authority.get('sha256') != AUDIT_SHA
            or authority.get('audited_head') != AUDITED_HEAD
            or authority.get('document_role') != 'INDEPENDENT_EXTERNAL_ACCEPTANCE'):
        raise ValueError('INDEPENDENT_EXTERNAL_EVENT_ACCEPTANCE_REQUIRED')
    audit = exact_bytes(root, authority).decode('utf8')
    if ('独立外部验收审计' not in audit or AUDITED_HEAD not in audit or DISPOSITION not in audit):
        raise ValueError('INDEPENDENT_EXTERNAL_EVENT_ACCEPTANCE_REQUIRED')
    config = json.loads(exact_bytes(root, head['config']))
    if (head['config']['path'] != CONFIG or config.get('contract_id') != 'OFFICIAL_EVENT_ACCEPTANCE_V1'
            or config.get('runtime') != head.get('runtime') or config.get('candidate') != head.get('candidate')
            or config.get('filename_or_capture_id_grants_trading_authority') is not False
            or config.get('unknown_event_may_enter_trading_status') is not False):
        raise ValueError('EVENT_ACCEPTANCE_RUNTIME_CONTRACT_MISMATCH')
    exact_bytes(root, head['runtime'])
    exact_bytes(root, config['semantic_runtime'])
    candidate = json.loads(exact_bytes(root, head['candidate']))
    sidecar = json.loads(exact_bytes(root, head['sidecar']))
    content_addressed = head['content_addressed_sidecar']
    if (content_addressed['sha256'] != head['sidecar']['sha256']
            or content_addressed['path'] != 'data/v4/artifact_store/a13/sha256-' + content_addressed['sha256'] + '.json'
            or exact_bytes(root, content_addressed) != exact_bytes(root, head['sidecar'])):
        raise ValueError('EVENT_ACCEPTANCE_CONTENT_ADDRESS_MISMATCH')
    if (sidecar.get('contract_id') != CONTRACT or sidecar.get('external_acceptance') != 'EXTERNALLY_ACCEPTED'
            or sidecar.get('external_authority') != authority or sidecar.get('candidate') != head['candidate']
            or sidecar.get('entries') != candidate.get('entries')
            or sidecar.get('formal_consumer_authorization') is not False):
        raise ValueError('EVENT_ACCEPTANCE_CANDIDATE_LINEAGE_MISMATCH')
    return head, sidecar


def require_trading_event(root, accepted_sidecar_binding, raw_binding, *, security_key, effective_date):
    head, _ = require_accepted_semantic_head(root)
    if accepted_sidecar_binding != head['sidecar']:
        raise ValueError('ACCEPTED_EVENT_SEMANTICS_REQUIRED')
    return semantic_guard(root, accepted_sidecar_binding, raw_binding,
                          security_key=security_key, effective_date=effective_date)
