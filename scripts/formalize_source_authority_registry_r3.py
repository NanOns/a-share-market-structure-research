"""Add external audit dispositions without rewriting historical heads or registries."""
import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_bytes, atomic_json
from scripts.enter_source_authority_remediation_r2 import bind

BASELINE = '1655f84d1a47faca43c281d66e7704f2fa56b1b8'
AUDIT = 'V4_SOURCE_AUTHORITY_8_CARD_BATCH_INDEPENDENT_EXTERNAL_AUDIT_R1_20261001.md'
TASK = 'V4_SOURCE_AUTHORITY_PASS_ITEMS_PROMOTION_AND_REGISTRY_R3_TASK_20261001.md'
REGISTRY = 'reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R3.json'
PREFIX = 'docs/evidence/source_authority/'
PERMISSIONS = dict(production=False, shadow=False, focus_cutover=False)
LIMITATION = 'HISTORICAL_LEGAL_LIFECYCLE_AND_TYPE_NOT_LOCAL_TDX_CONFIRMED'

def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf8'))

def protected_bindings():
    paths = {b['path'] for b in read('config/source_authority_governance_r1.json')['protected_bindings']}
    paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT / 'data/v4').glob('*ACCEPTED_HEAD*.json'))
    paths.add('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R2.json')
    paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT / 'src/workbench_db/migrations/v4_postgres').glob('02[1-5]_*.sql'))
    bindings = []
    for path in sorted(paths):
        binding = bind(path)
        committed = subprocess.check_output(['git', 'show', BASELINE + ':' + path], cwd=ROOT)
        import hashlib
        git_sha = hashlib.sha256(committed).hexdigest()
        if git_sha != binding['sha256']:
            assert committed.replace(b'\r\n', b'\n') == (ROOT / path).read_bytes().replace(b'\r\n', b'\n')
            binding.update(git_sha256=git_sha, representation_difference='PRE_EXISTING_CRLF_LF_ONLY', git_baseline_commit=BASELINE)
        bindings.append(binding)
    return bindings

def main():
    subprocess.run(['git', 'merge-base', '--is-ancestor', BASELINE, 'HEAD'], cwd=ROOT, check=True)
    for name in (AUDIT, TASK):
        atomic_bytes(ROOT / PREFIX / name, (Path('D:/Users/lps/Desktop/阶段任务') / name).read_bytes())
    authority = dict(document=bind(PREFIX + AUDIT), audited_head=BASELINE, verdict='PARTIAL_PASS_WITH_BLOCKERS')
    atomic_json(ROOT / 'reports/audits/R3_STAGE_ENTRY_R1.json', dict(
        contract_id='SOURCE_AUTHORITY_REGISTRY_R3_FORMALIZATION', baseline_commit=BASELINE,
        task=bind(PREFIX + TASK), external_authority=authority, protected_bindings=protected_bindings(),
        scope='METADATA_PROVENANCE_CAPABILITY_ONLY', permissions=PERMISSIONS,
        next_stage='A10 R2 authorized governance repair; A12 R2 and DM01 final integration remain separately gated'))
    diff = read('reports/audits/A11_DOWNSTREAM_CONSUMER_GRAPH_AND_BUSINESS_DIFF_R1.json')
    assert diff['canonical_old_sha256'] == diff['canonical_candidate_sha256']
    assert diff['identity_rows_changed'] == diff['security_ids_renumbered'] == 0
    assert all(not s[k] for s in diff['stages'].values() for k in ('business_output_changed', 'input_identity_changed', 'logical_digest_changed', 'rebuild_required'))
    common = dict(external_authority=authority, permissions=PERMISSIONS, business_accepted_heads_modified=False)
    amendment = dict(**common, contract_id='V4_01_HISTORICAL_IDENTITY_AUTHORITY_AMENDMENT_R1',
        external_acceptance='PASS_RESULT_C_WITH_CAPABILITY_DOWNGRADE',
        business_identity_bytes_unchanged=True, security_id_unchanged=True,
        go_forward_official_identity_authority_unchanged=True,
        historical_pre_capture_fields=['security_type', 'lifecycle', 'listing_anchor_source_authority'],
        historical_provenance='PROVIDER_RECONSTRUCTED_FACT / RECONSTRUCTED_CORRECTED',
        exceptions='INDEPENDENTLY_OFFICIAL_CONFIRMED_FACTS_ONLY',
        provider_observation_time_is_historical_fact_date=False, AS_RECORDED=False,
        local_tdx_legal_lifecycle_authority=False, capability_limitations=[LIMITATION],
        stable_security_id_policy='DO_NOT_RENUMBER', sh_600018='RETAIN_CURRENT_STABLE_IDENTITY_ANCHOR',
        downstream_business_rebuild_required=False, identity_equivalence=bind('reports/audits/A11_DOWNSTREAM_CONSUMER_GRAPH_AND_BUSINESS_DIFF_R1.json'),
        authority_matrix=bind('reports/audits/V4_01_IDENTITY_FIELD_AUTHORITY_MATRIX_R1.json'),
        official_case=bind('reports/audits/A11_OFFICIAL_ANCHOR_ADJUDICATION_R1.json'),
        go_forward_accepted_head=bind('data/v4/V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1.json'))
    paths = {
        'WP-A11-V4-01-IDENTITY-AUTHORITY': 'config/V4_01_HISTORICAL_IDENTITY_AUTHORITY_AMENDMENT_R1.json',
        'WP-A08-V4-09-N01': 'reports/audits/V4_09_N01_HARDENING_ACCEPTED_RECORD_R1.json',
        'WP-A09-V4-09-N02': 'reports/audits/V4_09_N02_CONSUMER_IDENTITY_HARDENING_ACCEPTED_RECORD_R1.json'}
    atomic_json(ROOT / paths['WP-A11-V4-01-IDENTITY-AUTHORITY'], amendment)
    replay = read('reports/audits/A08_ACCEPTED_REPLAY_AND_AUTHORITY_EVIDENCE_R1.json')
    atomic_json(ROOT / paths['WP-A08-V4-09-N01'], dict(**common,
        contract_id='V4_09_N01_HARDENING_ACCEPTED_RECORD_R1', external_acceptance='PASS',
        acceptance_scope='REPAIR_FREEZE_AUTHORITY_HARDENING_AUDIT_ONLY',
        historical_validation_scope='ACCEPTED_PUBLICATION_HISTORY_ONLY', current_runtime_accepted=False,
        current_runtime_external_acceptance='PENDING_INDEPENDENT_EXTERNAL_AUDIT',
        accepted_artifact=replay['accepted_artifact'], accepted_head=bind('data/v4/V4_09_ACCEPTED_HEAD.json'),
        historical_implementation=bind('config/v4_09_historical_runtime_archive_r1.json'),
        evidence_bindings=[bind('reports/audits/A08_ACCEPTED_REPLAY_AND_AUTHORITY_EVIDENCE_R1.json'), bind('reports/audits/A08_CLEAN_CHECKOUT_R1.json')]))
    sql = read('reports/audits/A09_SCHEMA_LEGACY_READBACK_AND_ROLLBACK_R1.json')
    assert all(sql['checks'].values()) and sql['legacy_row_count'] == 5222
    atomic_json(ROOT / paths['WP-A09-V4-09-N02'], dict(**common,
        contract_id='V4_09_N02_CONSUMER_IDENTITY_HARDENING_ACCEPTED_RECORD_R1', external_acceptance='PASS',
        acceptance_scope='ACCEPTED_FUTURE_SCHEMA_HARDENING', production_database_deployed=False,
        deployment_gate='SEPARATE_DEPLOYMENT_AUTHORIZATION_REQUIRED', migration=sql['migration'], rollback=sql['rollback'],
        legacy_exact_readback_and_rollback=sql['checks'],
        evidence_bindings=[bind('reports/audits/A09_SCHEMA_LEGACY_READBACK_AND_ROLLBACK_R1.json'), bind('reports/audits/A09_CLEAN_CHECKOUT_R1.json')]))
    prior = read('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R2.json')
    registry = dict(contract_id='V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R3', baseline_commit=BASELINE,
        extends=bind('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R2.json'),
        external_authority=authority, authority=bind(PREFIX + TASK), permissions=PERMISSIONS,
        status='EXTERNAL_DISPOSITIONS_FORMALIZED_ENGINEERING_CONFIRMATION_PENDING',
        business_accepted_heads_modified=False, accepted_source_authority_owners=[],
        entries=copy.deepcopy(prior['entries']), audit_count=prior['audit_count'])
    blocked = {'WP-A10-SOURCE-AUTHORITY-GOVERNANCE': 'BLOCKED_R2_OWNER_ACCEPTANCE_GATE',
        'WP-A12-V4-02-STATUS-ST-AUTHORITY': 'BLOCKED_R2_REAL_DATED_OWNER_SEMANTICS',
        'WP-A01-DM01': 'PARTIAL_ENGINEERING_PASS_FINAL_ALL_NINE_BLOCKED'}
    for entry in registry['entries']:
        wp = entry['work_package']
        if wp not in paths and wp not in blocked:
            continue
        previous = entry['status']
        if wp in paths:
            record = read(paths[wp])
            scope = record.get('acceptance_scope', 'RESULT_C_AUDIT_AND_CAPABILITY_DOWNGRADE_ONLY')
            entry.update(status='ACCEPTED', implementation_status='EXTERNAL_AUDIT_DISPOSITION_FORMALIZED',
                external_acceptance=record['external_acceptance'], status_path=paths[wp],
                next_step='Preserve scope and capability limitations; no business promotion or deployment authorized')
            limitations = record.get('capability_limitations', [
                'CURRENT_RUNTIME_NOT_AUTO_ACCEPTED' if 'A08' in wp else 'PRODUCTION_DEPLOYMENT_NOT_AUTHORIZED'])
            evidence = [bind(paths[wp]), *entry['evidence']]
            dependencies = []
        else:
            scope = 'NO_FUNCTIONAL_CLOSURE'
            limitations = ['EXTERNAL_REPAIR_ACCEPTANCE_REQUIRED']
            dependencies = ['A10-R2_EXTERNAL_ACCEPTANCE', 'A12-R2_EXTERNAL_ACCEPTANCE'] if wp == 'WP-A01-DM01' else []
            entry.update(status='OPEN', implementation_status=blocked[wp], external_acceptance='BLOCKED', depends_on=dependencies)
            evidence = entry['evidence']
        transition = dict(previous_status=previous, new_status=entry['status'], acceptance_scope=scope,
            capability_limitations=limitations, external_authority=authority, evidence_bindings=evidence,
            remaining_dependencies=dependencies)
        entry.update(transition=transition, acceptance_scope=scope, capability_limitations=limitations, evidence=evidence)
    registry['dependency_graph'] = {e['work_package']: e.get('depends_on', []) for e in registry['entries']}
    atomic_json(ROOT / REGISTRY, registry)
    atomic_json(ROOT / 'reports/audits/R3_ENGINEERING_GATES_R1.json', dict(
        status='PENDING_CLEAN_DETACHED', allowed_candidate_status='SOURCE_AUTHORITY_REGISTRY_R3_FORMALIZATION_CANDIDATE_READY_FOR_EXTERNAL_CONFIRMATION',
        gates={f'R3-G{i:02d}': 'PENDING_CLEAN_DETACHED' if i == 13 else 'PASS_ENGINEERING' for i in range(1, 14)},
        registry=bind(REGISTRY), next_stage='A10 R2 governance repair; external confirmation of formalization remains pending'))
    print('R3 metadata written; historical registries and business heads preserved')

if __name__ == '__main__':
    main()
