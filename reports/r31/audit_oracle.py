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
    if not isinstance(binding, dict) or not isinstance(binding.get('path'), str) or not binding['path'] or not isinstance(binding.get('sha256'), str) or len(binding['sha256']) != 64 or any(ch not in '0123456789abcdef' for ch in binding['sha256']):
        raise ValueError('MALFORMED_EXACT_BINDING')
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
    value = json.loads(raw) if path.suffix == '.json' else {}
    if value.get('contract_id') and binding.get('contract_id') != value['contract_id']:
        raise ValueError('AUTHORITY_ID_MISSING_OR_MISMATCH')
    if binding.get('contract_id') and value.get('contract_id') != binding['contract_id']:
        raise ValueError('AUTHORITY_ID_MISMATCH')
    return value


def referential_integrity(value, shadow_owner, production_owner=None):
    """Check supplied design/readback rows, without invoking V4-21 business code."""
    root = Path(__file__).resolve().parents[2]
    contract = json.loads((root / 'config/v4_22_independent_audit_contract_v1.json').read_bytes())
    try:
        schema = read_binding(root, contract['ledger_schema_binding'])
    except (ValueError, OSError, KeyError):
        return dict(status='BLOCKED_AFFECTED_SCOPE', findings=[dict(reason='LEDGER_SCHEMA_AUTHORITY_INVALID')], actual_real_rows_written=0, production_grant=False)
    def row_error(row, required):
        if not isinstance(row, dict) or not all(k in row for k in required):
            return 'MISSING_REQUIRED_FIELD'
        lane = schema['evidence_lanes'].get(row['evidence_lane']) if isinstance(row['evidence_lane'], str) else None
        if lane is None:
            return 'UNKNOWN_EVIDENCE_LANE'
        if row['observation_namespace'] != lane['namespace']:
            return 'LANE_NAMESPACE_MISMATCH'
        if not all(isinstance(row.get(k), str) and row[k] for k in PARTITION + ('source_publication','source_digest')):
            return 'MISSING_PUBLICATION_PROVENANCE'
        if lane['real_eligible']:
            if row['evidence_origin'] != lane['required_origin'] or row.get('accepted_real_publication') is not True:
                return 'REAL_LANE_ORIGIN_OR_PUBLICATION_INVALID'
        elif row['evidence_origin'] != row['evidence_lane'] or row.get('accepted_real_publication') is not False:
            return 'DIAGNOSTIC_LANE_ORIGIN_OR_PUBLICATION_INVALID'
        return None
    linkage = PARTITION + ('source_publication', 'source_digest')
    findings = []
    accepted = {}
    countable = 0
    for row in value.get('sessions', []):
        error = row_error(row, schema['session_ledger']['required'])
        if error:
            findings.append(dict(vector='SESSION_SCHEMA', partition=None, reason=error))
            continue
        if not schema['evidence_lanes'][row['evidence_lane']]['real_eligible']:
            continue
        owner = shadow_owner if row['evidence_lane'] == 'SHADOW_REAL' else production_owner
        mode = 'SHADOW' if row['evidence_lane'] == 'SHADOW_REAL' else 'PRODUCTION'
        valid = row['capability'] in CAPABILITIES and owner is not None and row.get('native_session_authority_id') == owner['contract_id'] and row.get('native_session_authority_sha256') == owner['sha256'] and row.get('native_session_status') in owner['accepted_statuses'] and row.get('evidence_origin') == 'PIT_OBSERVED' and row.get('accepted_real_publication') is True and row.get('execution_mode') == mode
        # Projection evaluability is a separate dimension. Accepted native rows
        # remain referential parents even when projection_evaluable is false.
        valid = valid and all(row.get(k) not in (None, '') for k in linkage + ('trade_date','market_session_id','publication_id','publication_revision','session_receipt_id','slot_receipt_digest')) and type(row.get('projection_evaluable')) is bool
        key = tuple(row.get(k) for k in linkage)
        if valid and key not in accepted:
            accepted[key] = row
            countable += int(row['projection_evaluable'])
        elif valid:
            accepted[key] = None
            findings.append(dict(vector='SESSION_AMBIGUITY', reason='MULTIPLE_SESSION_PARENTS'))
        else:
            findings.append(dict(vector='SESSION_AUTHORITY', partition={k: row[k] for k in PARTITION}, reason='NO_EXACT_ACCEPTED_NATIVE_SESSION_AUTHORITY'))
    for ledger, vector in (('events', 'A22-V421-REFINT-01'), ('outcomes', 'A22-V421-REFINT-02')):
        for index, row in enumerate(value.get(ledger, [])):
            required = schema['event_cohort_ledger' if ledger == 'events' else 'due_outcome_ledger']['required']
            error = row_error(row, required)
            if error:
                findings.append(dict(vector=vector, ledger=ledger, row_index=index, reason=error))
                continue
            if not schema['evidence_lanes'][row['evidence_lane']]['real_eligible']:
                continue
            parent = accepted.get(tuple(row.get(k) for k in linkage))
            valid = all(k in row for k in required) and parent is not None
            if valid:
                valid = row.get('observation_namespace') == parent.get('observation_namespace') and row.get('execution_mode') == parent.get('execution_mode') and row.get('evidence_origin') == 'PIT_OBSERVED'
                if ledger == 'events':
                    valid = valid and row.get('T0') == parent['trade_date'] and row.get('calendar_identity') == parent['calendar_identity']
            if not valid:
                findings.append(dict(vector=vector, ledger=ledger, row_index=index, partition={k: row.get(k) for k in PARTITION}, reason='ORPHAN_REAL_ROW_WITHOUT_ACCEPTED_SESSION_PARTITION'))
    return dict(status='BLOCKED_AFFECTED_SCOPE' if findings else 'PASS_DESIGN_ONLY', findings=findings, input_sha256=digest(value), design_countable_sessions=countable, actual_real_rows_written=0, production_grant=False, scope='INDEPENDENT_DESIGN_ORACLE_NOT_REAL_AUDIT')


def governance(branch, expected_branch, tested_source, tag_source, annotated, clean, delta):
    evidence_suffixes = ('.json', '.xml', '.txt', '.md')
    evidence_only = all(p.startswith(('reports/r31/', 'docs/evidence/r31/')) and p.endswith(evidence_suffixes) for p in delta)
    ok = branch == expected_branch and tested_source == tag_source and annotated is True and clean is True and evidence_only
    return dict(status='PASS' if ok else 'BLOCKED', branch=branch, tested_source=tested_source, tag_source=tag_source, annotated=annotated, clean=clean, post_test_delta=delta, evidence_only=evidence_only)


def closure_allowed(item, disposition):
    required = ('explicit_disposition', 'exact_evidence', 'authority', 'date_source', 'independent_recheck')
    return all(disposition.get(k) for k in required) and disposition.get('item_id') == item['item_id'] and disposition.get('capability_scope') == item['capability_scope'] and disposition.get('independent_recheck') is True


def verify_closure(contract, item, receipt, binding, root):
    """Canonical receipt plus independent authority authorization and all raw evidence."""
    try:
        if not isinstance(receipt, dict) or not isinstance(binding, dict):
            return False
        if not closure_allowed(item, receipt) or receipt.get('explicit_disposition') not in ('CLOSED','INDEPENDENTLY_DISPOSED'):
            return False
        if binding.get('item_id') != item['item_id'] or binding.get('capability_scope') != item['capability_scope'] or digest(receipt) != binding.get('canonical_sha256'):
            return False
        authority = binding.get('closure_authority')
        evidence = binding.get('exact_evidence')
        if not isinstance(evidence, list) or not evidence or receipt.get('closure_authority') != authority or receipt.get('authority') != authority or receipt.get('exact_evidence') != evidence:
            return False
        if authority not in contract.get('closure_authority_authorizations', {}).get(item['item_id'], []):
            return False
        owner = read_binding(root, authority)
        for ref in evidence:
            read_binding(root, ref)
        expected = {k: receipt[k] for k in ('item_id','capability_scope','explicit_disposition','exact_evidence','date_source','independent_recheck')}
        if expected not in owner.get('closure_authorizations', []):
            return False
        return True
    except (ValueError, OSError, KeyError, TypeError, AttributeError):
        return False


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
    domains = {d['domain']: d['authority_bindings'] for d in contract['audit_domains']}
    for item in contract['audit_items'] + contract['open_items']:
        allowed = domains.get(item['domain'], []) + contract.get('item_cross_domain_authorizations', {}).get(item['item_id'], [])
        authorities = item.get('authority', {})
        authorities = authorities if isinstance(authorities, list) else [authorities]
        for b in authorities + item.get('evidence_refs', []):
            try:
                read_binding(root, b)
                if b not in allowed:
                    raise ValueError('ITEM_DOMAIN_AUTHORITY_DIVERGENCE')
            except (ValueError, OSError, KeyError, TypeError):
                errors.append('ITEM_AUTHORITY_BINDING_INVALID')
    for domain in contract['audit_domains']:
        for b in domain['authority_bindings']:
            try:
                read_binding(root,b)
            except (ValueError, OSError, KeyError):
                errors.append('AUTHORITY_BINDING_INVALID')
    return sorted(set(errors))


def final_verdict(contract, audit_items, gate_receipts, source_governance, unresolved_blockers=(), open_item_receipts=None, evidence_root=None):
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
    closures = open_item_receipts or {}
    for item in contract['open_items']:
        if not item['blocking_scope'] and item['item_id'] != 'OPEN-10':
            continue
        identifier = item['item_id']
        receipt = closures.get(identifier)
        binding = contract.get('open_item_closure_bindings', {}).get(identifier)
        if receipt is None and binding is None:
            missing.append(identifier + ':EXACT_INDEPENDENT_DISPOSITION')
        elif receipt is None or binding is None:
            failed = True
        elif not verify_closure(contract, item, receipt, binding, evidence_root or Path(__file__).resolve().parents[2]):
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
