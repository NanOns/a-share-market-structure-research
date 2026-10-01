"""Formalize the real independent audit and validate Phase A before any DM01 build."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
from workbench_analysis.source_authority_producers_r4 import (
    require_external_audit, require_formal_source, OwnerAcceptanceError, AUDIT_PATH, AUDITED_HEAD)
from workbench_analysis.source_authority_governance_r4 import evaluate_consumer_gate

P = 'reports/audits/A10_A12_R3_'
ENTRY = 'reports/audits/DM01_A01_R3_STAGE_ENTRY_R1.json'
TASK = 'docs/evidence/source_authority/V4_A10_A12_R3_ACCEPTANCE_FORMALIZATION_AND_DM01_A01_R3_ENTRY_TASK_20261001.md'
CONSUMER = 'DM01_FINAL_ALL_NINE'

def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf8'))

def write(path, value):
    atomic_json(ROOT / path, value)

def main():
    stamp = datetime.now(timezone.utc).isoformat()
    authority = dict(document=bind(AUDIT_PATH), authority_kind='INDEPENDENT_EXTERNAL_ACCEPTANCE',
                     audited_head=AUDITED_HEAD, recorded_at=stamp,
                     scope='HISTORICAL_RECONSTRUCTED_AND_DAILY_PRODUCER_SEMANTIC_AUTHORITY')
    require_external_audit(ROOT, authority)
    protected = [bind(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT / 'data/v4').glob('*ACCEPTED_HEAD*.json'))
                 if p.name != 'OFFICIAL_EVENT_SEMANTICS_ACCEPTED_HEAD_R1.json']
    protected += [bind(p) for p in ('data/v4/V4_DEV_BASELINE_HEAD.json', 'config/source_authority_governance_r3.json',
        'data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R2.json', 'data/v4/V4_SOURCE_AUTHORITY_GOVERNANCE_HEAD_R2.json',
        P+'EXTERNAL_DISPOSITION_R1.json', 'reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R7.json')]
    for ref in protected:
        committed = subprocess.check_output(['git', 'show', AUDITED_HEAD + ':' + ref['path']], cwd=ROOT)
        ref['git_sha256'] = hashlib.sha256(committed).hexdigest()
        if ref['git_sha256'] != ref['sha256']:
            assert committed == (ROOT/ref['path']).read_bytes().replace(b'\r\n', b'\n')
            ref['representation'] = 'PRE_EXISTING_CRLF_LF_ONLY'
    assert read('reports/v4_phase0/V4_PHASE0_STAGE_RECEIPTS_R5_20260928.json')['phase0_status'] == 'FULL_PASS'
    write(ENTRY, dict(contract_id='WP-A10-A12-R3-FORMALIZE-AND-DM01-A01-R3', baseline_commit=AUDITED_HEAD,
        task=bind(TASK), external_authority=authority, phase0_status='FULL_PASS',
        phase0_evidence=bind('reports/v4_phase0/V4_PHASE0_STAGE_RECEIPTS_R5_20260928.json'),
        stage_contract='FORMALIZE_ACTUAL_EXTERNAL_AUTHORITY_THEN_REAL_ALL_NINE_CONTINUOUS_CANDIDATES',
        protected_bindings=protected, acceptance_result='PHASE_A_VALIDATION_REQUIRED',
        next_stage='PHASE_B_AUTOMATIC_AFTER_PHASE_A_PASS; EXTERNAL_REAUDIT_ONLY'))
    config = deepcopy(read('config/source_authority_governance_r3.json'))
    config.update(contract_id='V4_SOURCE_AUTHORITY_GOVERNANCE_R4', version='4.0.0',
        supersedes=bind('config/source_authority_governance_r3.json'), status='ACCEPTED_PRODUCER_SEMANTIC_SCOPE',
        external_authority=authority, owner_runtime=bind('src/workbench_analysis/source_authority_producers_r4.py'),
        runtime=bind('src/workbench_analysis/source_authority_governance_r4.py'), task=bind(TASK),
        required_owner_registry_contract='SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_V3')
    entries = []
    keys = ('external_acceptance', 'formal_consumer_authorization', 'allowed_consumers', 'historical_modes',
            'source_instance_policy_id', 'role_binding', 'accepted_at', 'external_authority')
    for historical in (True, False):
        rules = config['historical_field_rules'] if historical else config['field_rules']
        for rule in rules:
            field = rule['field_id']
            if field not in ('TRADING_STATUS', 'ISST'):
                continue
            rule.update(enabled_for_formal_consumer=True, authority_status='EXTERNALLY_ACCEPTED')
            old = P + ('HISTORICAL_'+field+'_ACCEPTED_AMENDMENT_R1.json' if historical else 'PRODUCER_'+field+'_CANDIDATE_R1.json')
            owner = deepcopy(read(old))
            owner.update(external_acceptance='EXTERNALLY_ACCEPTED', formal_consumer_authorization=True,
                accepted_at=stamp, external_authority=authority, supersedes=bind(old), role_binding=rule,
                AS_RECORDED=False, first_available_at_target_proven=False)
            path = P + ('HISTORICAL_'+field+'_ACCEPTED_FORMAL_R2.json' if historical else 'PRODUCER_'+field+'_ACCEPTED_R1.json')
            write(path, owner)
            entry = dict(owner_contract_id=owner['contract_id'], field_id=field, producer_contract=bind(path),
                registration_scope='HISTORICAL_PATH_B_ONLY' if historical else 'PRODUCER_SEMANTIC_AUTHORITY',
                **{k:owner[k] for k in keys})
            if historical:
                entry['effective_scope'] = owner['effective_scope']
            entries.append(entry)
    write('config/source_authority_governance_r4.json', config)
    rp = 'data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R3.json'
    write(rp, dict(contract_id='SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_V3', version=3,
        supersedes=bind('data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R2.json'),
        owners=entries, external_authority=authority, historical_invalid_authority_preserved=True))
    hp = 'data/v4/V4_SOURCE_AUTHORITY_GOVERNANCE_HEAD_R3.json'
    write(hp, dict(contract_id='SOURCE_AUTHORITY_GLOBAL_GOVERNANCE_HEAD_V3', registry=bind(rp),
        supersedes=bind('data/v4/V4_SOURCE_AUTHORITY_GOVERNANCE_HEAD_R2.json'), external_authority=authority,
        business_promotion=False, dm01_final_all_nine_accepted=False))
    negatives = []
    for label, bad in [('TASK_CARD', dict(authority, document=bind(TASK))),
                       ('WRONG_AUDIT_SHA', dict(authority, document=dict(authority['document'], sha256='0'*64)))]:
        try:
            require_external_audit(ROOT, bad)
        except OwnerAcceptanceError as exc:
            negatives.append(dict(probe=label, status='PASS_REJECTED', reason=exc.reason))
        else:
            raise AssertionError(label)
    assert len(entries) == 4 and read(hp)['registry'] == bind(rp)
    assert read(hp)['registry']['path'] != read(hp)['supersedes']['path'] and read(hp)['registry']['path'] != read('data/v4/V4_SOURCE_AUTHORITY_GOVERNANCE_HEAD_R2.json')['registry']['path']
    write(P+'REGISTRY_R3_VALIDATION_R1.json', dict(status='PASS', registry=bind(rp), head=bind(hp),
        authority_count=4, external_authority=authority, negative_probes=negatives,
        Registry_R2_active_trust_root=False, head_exact_registry_R3=True, business_promotion=False))
    instances = read(P+'SOURCE_INSTANCE_MANIFEST_R1.json')['instances']
    targets = sorted(set(instances) | set(read(P+'SOURCE_INSTANCE_MANIFEST_R1.json')['missing_target_dates']))
    vectors = []
    for target in targets:
        for rule in config['field_rules']:
            if rule['field_id'] not in ('TRADING_STATUS','ISST'):
                continue
            binding = instances.get(target, {}).get(rule['field_id'])
            gate = evaluate_consumer_gate(rule, project_root=ROOT, consumer_contract_id=CONSUMER,
                target_trade_date=target, availability='AVAILABLE', required=True, source_instance_binding=binding)
            assert gate['formal_authority_authorized'] == (binding is not None), gate
            if binding is None:
                assert gate['owner_acceptance_reason'] == 'SOURCE_INSTANCE_MISSING_FOR_TARGET_DATE', gate
            vectors.append(dict(target=target, field=rule['field_id'], expected='PASS' if binding else 'FAIL', **gate))
    historical = []
    boundary = read('data/v4/source_evidence/a12_r2/REAL_VALIDATION_CASE_SPEC_R1.json')
    dates = sorted({'2023-07-04','2026-09-24'} | {c['day'] for c in boundary['cases']
        if 'ST_REMOVAL' in c['tags'] or 'CODE_CHANGE_BOUNDARY' in c['tags']})
    for rule in config['historical_field_rules']:
        entry = next(e for e in entries if e['owner_contract_id']==rule['owner_contract_id'])
        owner = read(entry['producer_contract']['path'])
        for target in dates:
            proof = require_formal_source(ROOT, rule, consumer_contract_id=CONSUMER, target_trade_date=target,
                instance_binding=owner['historical_source_instance_archive'])
            historical.append(proof['instance'])
    unchanged = all(bind(r['path'])['sha256'] == r['sha256'] for r in protected)
    assert unchanged
    write(P+'REAL_DATE_GLOBAL_GATE_R2.json', dict(status='PASS', validator_scope='ACTUAL_REPOSITORY_R4_R3_HEAD',
        fixture_used=False, network_calls=0, vectors=vectors, historical=historical,
        old_business_heads_unchanged=unchanged, AS_RECORDED=False, first_available_at_target_proven=False))
    write(P+'EXTERNAL_ACCEPTANCE_FORMALIZATION_R1.json', dict(status='PASS', external_authority=authority,
        audited_head=AUDITED_HEAD, registry=bind(rp), head=bind(hp), config=bind('config/source_authority_governance_r4.json'),
        registry_validation=bind(P+'REGISTRY_R3_VALIDATION_R1.json'), real_date_gate=bind(P+'REAL_DATE_GLOBAL_GATE_R2.json'),
        phase_A='PASS', phase_B='GO_WITHOUT_HUMAN_CONFIRMATION', historical_path_b='EXTERNALLY_ACCEPTED_RECONSTRUCTED_ONLY',
        daily_producer_authority='EXTERNALLY_ACCEPTED', dm01_all_nine_accepted=False,
        invalid_R2_history_preserved=True, business_heads_unchanged=True))
    ledger = deepcopy(read('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R7.json'))
    ledger.update(contract_id='V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R8',
        extends=bind('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R7.json'), authority=authority['document'])
    for e in ledger['entries']:
        if e.get('work_package')=='WP-A12-V4-02-STATUS-ST-AUTHORITY' or e.get('audit_id')=='A10_A12_R3_PRODUCER_SOURCE_INSTANCE':
            e.update(status='ACCEPTED_SOURCE_AUTHORITY_SCOPE', external_acceptance='EXTERNALLY_ACCEPTED',
                external_authority=authority, historical_path_b='EXTERNALLY_ACCEPTED_RECONSTRUCTED_ONLY',
                daily_producer_authority='EXTERNALLY_ACCEPTED', dm01_all_nine_accepted=False,
                next_step='DM01 continuous candidates; external reaudit required')
        if e.get('audit_id') in ('A12_R2_INTERIOR_DATA_GAP_SCOPE','A12_R2_POSITIVE_ST_CODE_CHANGE_SCOPE'):
            e['external_authority']=authority
    write('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R8.json',ledger)
    print(json.dumps(dict(phase_A='PASS', actual_daily_vectors=len(vectors), historical_vectors=len(historical), phase_B='GO')))

if __name__=='__main__':
    main()
