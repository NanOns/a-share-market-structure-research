"""Independent, read-only V4-22 design oracle; no business/writer imports."""
import hashlib
import json
from pathlib import Path

PARTITION = ('capability', 'evidence_lane', 'model_contract_id', 'parameter_digest', 'state_lineage_id')
REAL_LANES = ('SHADOW_REAL', 'PRODUCTION_REAL')
CAPABILITIES = ('STOCK_CORE','STOCK_SECTOR_DEPENDENT','SECTOR_STAGE','ROTATION','SECTOR_RISK_CHANGE')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def read_binding(root, binding):
    """Exact immutable file readback. No latest, glob, mtime or fallback lookup."""
    root = Path(root).resolve()
    name = Path(binding['path'])
    if name.is_absolute() or '..' in name.parts:
        raise ValueError('AUTHORITY_PATH_OUTSIDE_ROOT')
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError('AUTHORITY_PATH_OUTSIDE_ROOT')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != binding['sha256']:
        raise ValueError('AUTHORITY_DIGEST_MISMATCH')
    value = json.loads(raw)
    if binding.get('contract_id') and value.get('contract_id') != binding['contract_id']:
        raise ValueError('AUTHORITY_ID_MISMATCH')
    return value


def referential_integrity(value, shadow_owner, production_owner=None):
    """Check supplied design/readback rows, without invoking V4-21 business code."""
    findings = []
    accepted = set()
    for row in value.get('sessions', []):
        if not all(k in row for k in PARTITION):
            findings.append(dict(vector='SESSION_SCHEMA', partition=None, reason='MISSING_PARTITION'))
            continue
        if row['evidence_lane'] not in REAL_LANES:
            continue
        owner = shadow_owner if row['evidence_lane'] == 'SHADOW_REAL' else production_owner
        mode = 'SHADOW' if row['evidence_lane'] == 'SHADOW_REAL' else 'PRODUCTION'
        valid = row['capability'] in CAPABILITIES and owner is not None and row.get('native_session_authority_id') == owner['contract_id'] and row.get('native_session_authority_sha256') == owner['sha256'] and row.get('native_session_status') in owner['accepted_statuses'] and row.get('evidence_origin') == 'PIT_OBSERVED' and row.get('accepted_real_publication') is True and row.get('execution_mode') == mode
        # Projection evaluability is a separate dimension. Accepted native rows
        # remain referential parents even when projection_evaluable is false.
        if valid:
            accepted.add(tuple(row[k] for k in PARTITION))
        else:
            findings.append(dict(vector='SESSION_AUTHORITY', partition={k: row[k] for k in PARTITION}, reason='NO_EXACT_ACCEPTED_NATIVE_SESSION_AUTHORITY'))
    for ledger, vector in (('events', 'A22-V421-REFINT-01'), ('outcomes', 'A22-V421-REFINT-02')):
        for index, row in enumerate(value.get(ledger, [])):
            if row.get('evidence_lane') not in REAL_LANES:
                continue
            if not all(k in row for k in PARTITION) or tuple(row[k] for k in PARTITION) not in accepted:
                findings.append(dict(vector=vector, ledger=ledger, row_index=index, partition={k: row.get(k) for k in PARTITION}, reason='ORPHAN_REAL_ROW_WITHOUT_ACCEPTED_SESSION_PARTITION'))
    return dict(status='BLOCKED_AFFECTED_SCOPE' if findings else 'PASS_DESIGN_ONLY', findings=findings, input_sha256=digest(value), actual_real_rows_written=0, production_grant=False, scope='INDEPENDENT_DESIGN_ORACLE_NOT_REAL_AUDIT')


def governance(branch, expected_branch, tested_source, tag_source, annotated, clean, delta):
    evidence_suffixes = ('.json', '.xml', '.txt', '.md')
    evidence_only = all(p.startswith(('reports/r31/', 'docs/evidence/r31/')) and p.endswith(evidence_suffixes) for p in delta)
    ok = branch == expected_branch and tested_source == tag_source and annotated is True and clean is True and evidence_only
    return dict(status='PASS' if ok else 'BLOCKED', branch=branch, tested_source=tested_source, tag_source=tag_source, annotated=annotated, clean=clean, post_test_delta=delta, evidence_only=evidence_only)


def closure_allowed(item, disposition):
    required = ('explicit_disposition', 'exact_evidence', 'authority', 'date_source', 'independent_recheck')
    return all(disposition.get(k) for k in required) and disposition.get('item_id') == item['item_id'] and disposition.get('capability_scope') == item['capability_scope'] and disposition.get('independent_recheck') is True


def validate_contract(contract, root):
    errors = []
    expected_domains = {'A22-'+d for d in ('DATA','ALGORITHM','PUBLICATION','SHADOW','UI','FORWARD','MIGRATION','CUTOVER','ROLLBACK','GOVERNANCE','REGRESSION')}
    if {d['domain'] for d in contract['audit_domains']} != expected_domains:
        errors.append('DOMAIN_REGISTRY_INCOMPLETE')
    identifiers = set()
    for item in contract['audit_items'] + contract['open_items']:
        if not set(contract['item_required_fields']) <= set(item):
            errors.append('ITEM_SCHEMA_INCOMPLETE')
            continue
        if item['item_id'] in identifiers:
            errors.append('DUPLICATE_ITEM_ID')
        identifiers.add(item['item_id'])
        if item['domain'] not in expected_domains or item['current_status'] not in contract['status_vocabulary']:
            errors.append('UNKNOWN_DOMAIN_OR_STATUS')
        if not set(item['blocking_scope']) <= set(item['capability_scope']):
            errors.append('BLOCKING_SCOPE_OUTSIDE_CAPABILITY')
    if not {f'OPEN-{i:02}' for i in range(1,11)} <= identifiers:
        errors.append('OPEN_ITEM_DISAPPEARED')
    for domain in contract['audit_domains']:
        for b in domain['authority_bindings']:
            try:
                if b['path'].endswith('.json'):
                    read_binding(root,b)
                elif hashlib.sha256((Path(root)/b['path']).read_bytes()).hexdigest() != b['sha256']:
                    raise ValueError('AUTHORITY_DIGEST_MISMATCH')
            except (ValueError, OSError, KeyError):
                errors.append('AUTHORITY_BINDING_INVALID')
    return sorted(set(errors))


def final_verdict(contract, audit_items, gate_receipts, source_governance, unresolved_blockers=()):
    """Evaluate the frozen formula only; never grant acceptance or permissions."""
    required = {item['item_id']: item for item in contract['audit_items'] if item['blocking_scope']}
    seen = {}
    malformed = False
    for item in audit_items:
        identifier = item.get('item_id')
        if identifier in seen or identifier not in required:
            malformed = True
        seen[identifier] = item
    failed = malformed or bool(unresolved_blockers) or source_governance.get('status') != 'PASS'
    missing = []
    for identifier, expected in required.items():
        actual = seen.get(identifier)
        if actual is None or actual.get('current_status') in ('WAIT_REAL_EVIDENCE', 'NOT_VERIFIABLE', 'BLOCKED'):
            missing.append(identifier)
        elif actual.get('current_status') != 'PASS' or actual.get('capability_scope') != expected['capability_scope'] or not actual.get('independent_recheck') or not actual.get('evidence_refs'):
            failed = True
        else:
            binding = contract['audit_receipt_bindings'].get(identifier)
            if binding is None:
                missing.append(identifier + ':EXACT_INDEPENDENT_AUDIT_RECEIPT')
            elif digest(actual) != binding['canonical_sha256'] or actual.get('authority') != binding['authority']:
                failed = True
    bindings = contract['runtime_receipt_bindings']
    for capability in contract['capabilities']:
        for gate in contract['required_real_gates']:
            key = capability + ':' + gate
            binding = bindings.get(key)
            receipt = gate_receipts.get(key)
            if binding is None or receipt is None:
                missing.append(key)
                continue
            if digest(receipt) != binding['canonical_sha256'] or receipt.get('authority_id') != binding['authority_id'] or receipt.get('capability') != capability or receipt.get('gate') != gate or receipt.get('externally_accepted') is not True or receipt.get('status') != 'PASS' or (gate == 'production_permission' and receipt.get('permission') is not True):
                failed = True
    verdict = 'FINAL_AUDIT_BLOCKED' if failed else 'FINAL_AUDIT_NOT_READY' if missing else 'V4_22_FINAL_PASS'
    return dict(formula_result=verdict, current_verdict=verdict if verdict != 'V4_22_FINAL_PASS' else 'FINAL_AUDIT_NOT_READY', missing=sorted(missing), acceptance_granted=False, production_grant=False, evaluation_scope='CONTRACT_DESIGN_ONLY; FORMULA_RESULT_IS_NOT_AN_ACCEPTANCE_RECEIPT')
