"""Promote externally accepted V4-08 engineering scope; validate without mutation."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_v4_08_r2_membership_evidence import atomic_json, atomic_bytes

DECISION = 'V4_08_EXTERNAL_ACCEPTANCE_PASS_R5_2_ENGINEERING_SCOPE'
AUDITED = '8200a775d9c4115f479ee60b4c11a16579e86723'
IMPLEMENTATION = 'b7d904cbff4f1c4b877838bd129f3925f968d858'
HEAD = 'data/v4/V4_08_ACCEPTED_HEAD.json'
GLOBAL = 'data/v4/V4_STAGE_ACCEPTED_HEAD.json'
MANIFEST = 'reports/v4_08/V4_08_R5_2_STAGE_CANDIDATE_MANIFEST.json'
AUDIT = 'docs/evidence/V4_08_R5_2_INDEPENDENT_EXTERNAL_ACCEPTANCE_FINAL_20260930.md'
VALIDATION = 'reports/v4_joint/V4_08_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json'
RECEIPT = 'reports/v4_joint/V4_08_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json'
PROTECTED = ['data/v4/V4_DATA_ACCEPTED_HEAD.json', 'data/v4/V4_DEV_BASELINE_HEAD.json',
             'data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json']
CAPABILITIES = {
    'SECTOR_NATIVE_CORE': 'ENGINEERING_ACCEPTED',
    'B0_SECTOR_PREWATCH_RAW': 'ENGINEERING_ACCEPTED',
    'B1_ROTATION_CORE': 'ENGINEERING_ACCEPTED',
    'ACCEPTED_CONTEXT_ROUTING': 'ENGINEERING_ACCEPTED',
    'B2_LEGACY_CONFIRMED_WARM': 'NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE',
    'B2_AMOUNT_A': 'DIAGNOSTIC_AUDIT_OPEN',
    'REAL_SIGNAL_CAPABILITY': 'DEGRADED_BY_TARGET_CORE_DATA_HEAD_PRIOR_RPS_AND_FORWARD_PIT_HISTORY',
}

def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf8'))

def bind(path):
    payload = (ROOT / path).read_bytes()
    return dict(path=path, sha256=hashlib.sha256(payload).hexdigest(), byte_count=len(payload))

def exact(binding):
    return all(bind(binding['path'])[key] == value for key, value in binding.items()
               if key in ('sha256', 'byte_count'))

def source_checks():
    manifest = read(MANIFEST)
    audit = (ROOT / AUDIT).read_text(encoding='utf8')
    bindings = [*manifest['artifacts'].values(), *manifest['evidence_bindings']]
    bindings += [b for b in manifest['input_bindings'].values() if isinstance(b, dict) and 'path' in b]
    scan = read('reports/v4_08/V4_08_R5_2_NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN.json')
    return {
        'external_acceptance_exact_decision_and_commits': all(x in audit for x in [DECISION, AUDITED, IMPLEMENTATION]),
        'candidate_and_evidence_sha_exact': all(exact(b) for b in bindings),
        'audited_commit_is_ancestor': subprocess.run(['git', 'merge-base', '--is-ancestor', AUDITED, 'HEAD'], cwd=ROOT).returncode == 0,
        'membership_binding_exact': exact(manifest['input_bindings']['membership_head']),
        'parameter_sha_exact': exact(manifest['input_bindings']['parameter_set']),
        'prior_clean_regression_schema_pass': all(read('reports/v4_08/' + name)['status'].startswith('PASS') for name in [
            'V4_08_R5_2_CLEAN_CHECKOUT_RECEIPT.json', 'V4_08_R5_2_ISOLATED_REGRESSION.json', 'V4_08_R5_2_SCHEMA_MIGRATION_RECEIPT.json']),
        'accepted_no_symbol_pass': scan['status'] == 'PASS' and scan['hard_gated_equity_symbol_hits'] == 0 and not scan['unclassified_paths'],
    }

def validate():
    head, global_head, receipt = read(HEAD), read(GLOBAL), read(RECEIPT)
    checks = source_checks()
    checks.update({
        'accepted_head_evidence_exact': all(exact(b) for b in head['evidence_bindings'].values()),
        'external_binding_exact': exact(head['external_acceptance_document']),
        'global_head_parent_exact': head['global_head_parent'] == receipt['global_head_parent'],
        'global_head_parent_archive_exact': exact(head['global_head_parent_archive']) and bind(head['global_head_parent_archive']['path'])['sha256'] == head['global_head_parent']['sha256'],
        'data_dev_membership_byte_unchanged': all(exact(b) for b in head['protected_head_bindings']),
        'capabilities_not_overclaimed': head['capabilities'] == CAPABILITIES,
        'permissions_false': all(head[k] is False for k in ['production_permission', 'shadow_production_permission', 'focus_cutover_permission']),
        'global_range_and_binding_exact': global_head['accepted_stage_range'] == 'V4_00_TO_V4_08_ACCEPTED' and global_head['v4_08_binding'] == bind(HEAD),
        'v4_09_entry_authorized': global_head['v4_09_entry'] == 'AUTHORIZED_AFTER_V4_08_PROMOTION_VALIDATION',
        'promotion_idempotent': receipt['accepted_head'] == bind(HEAD) and receipt['global_head_after'] == bind(GLOBAL),
        'v4_09_not_accepted': not (ROOT / 'data/v4/V4_09_ACCEPTED_HEAD.json').exists(),
    })
    return dict(contract_id='V4_08_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1', status='PASS' if all(checks.values()) else 'FAIL',
                checks=checks, accepted_head=bind(HEAD), global_head=bind(GLOBAL), protected_head_bindings=head['protected_head_bindings'])

def promote():
    if (ROOT / HEAD).exists():
        result = validate()
        if result['status'] != 'PASS': raise ValueError(result)
        return result
    checks = source_checks()
    if not all(checks.values()): raise ValueError(checks)
    old = read(GLOBAL)
    if old['accepted_stage_range'] != 'V4_00_TO_V4_07_ACCEPTED': raise ValueError('WRONG_PROMOTION_PARENT')
    parent = bind(GLOBAL)
    archive = 'reports/v4_joint/V4_08_PROMOTION_PARENT_STAGE_HEAD.json'
    atomic_bytes(ROOT / archive, (ROOT / GLOBAL).read_bytes())
    manifest = read(MANIFEST)
    inputs = manifest['input_bindings']
    paths = {k: b['path'] for k, b in inputs.items() if isinstance(b, dict) and 'path' in b}
    paths.update(r5_2_candidate_manifest=MANIFEST, external_acceptance_document=AUDIT,
                 b0_producer='src/sector/native_r5.py', b2_contract='config/v4_08_b2_machine_ast_r5.json')
    for name, suffix in [('clean_checkout','CLEAN_CHECKOUT_RECEIPT'), ('isolated_regression','ISOLATED_REGRESSION'),
                         ('schema_readback','SCHEMA_MIGRATION_RECEIPT'), ('no_symbol_scan','NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN')]:
        paths[name] = f'reports/v4_08/V4_08_R5_2_{suffix}.json'
    evidence = {name: bind(path) for name, path in paths.items()}
    head = dict(contract_id='V4_08_ACCEPTED_HEAD_V1', stage='V4-08', accepted_at='2026-09-30',
                external_acceptance='EXTERNALLY_ACCEPTED', external_acceptance_decision=DECISION,
                input_head=AUDITED, implementation_commit=IMPLEMENTATION,
                accepted_input_lineage=inputs, global_head_parent=parent, global_head_parent_archive=bind(archive),
                evidence_bindings=evidence, capabilities=CAPABILITIES,
                protected_head_bindings=[bind(p) for p in PROTECTED],
                open_audits=[dict(audit_id=a, status='OPEN') for a in ['V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01', 'AUD-AMOUNT-A-06',
                    'DM01_REAL_INCREMENTAL_BUILDERS', 'LEGACY_VALID_MEMBER_EXACT_PRODUCER', 'FORWARD_PIT_HISTORY_ACCUMULATION']],
                production_permission=False, shadow_production_permission=False, focus_cutover_permission=False,
                status='ENGINEERING_PASS_CAPABILITY_SCOPED', next_stage='V4-09 Stock PREWATCH engineering candidate')
    head.update({name: evidence[key] for name, key in [('membership_binding','membership_head'), ('r5_2_candidate_manifest','r5_2_candidate_manifest'),
        ('parameter_set','parameter_set'), ('field_registry','field_registry'), ('accepted_context_contract','accepted_input_contract'),
        ('native_contract','native_contract'), ('native_producer','native_producer'), ('b0_contract','b0_contract'), ('b0_producer','b0_producer'),
        ('rotation_contract','rotation_contract'), ('rotation_producer','rotation_producer'), ('b2_contract','b2_contract'), ('b2_producer','b2_producer'),
        ('clean_checkout','clean_checkout'), ('isolated_regression','isolated_regression'), ('schema_readback','schema_readback'), ('no_symbol_scan','no_symbol_scan'),
        ('external_acceptance_document','external_acceptance_document')]})
    head['external_acceptance_document'].update(decision=DECISION, audited_head=AUDITED, implementation_commit=IMPLEMENTATION)
    atomic_json(ROOT / HEAD, head)
    old.update(accepted_stage_range='V4_00_TO_V4_08_ACCEPTED', v4_08_binding=bind(HEAD), v4_08_external_acceptance=DECISION,
               v4_08_status=head['status'], v4_08_real_signal_capability=CAPABILITIES['REAL_SIGNAL_CAPABILITY'],
               v4_08_b2_capability=CAPABILITIES['B2_LEGACY_CONFIRMED_WARM'], v4_08_production_permission=False,
               v4_08_production_status='NOT_AUTHORIZED_CAPABILITY_SCOPED_ENGINEERING_ONLY',
               v4_08_sector_entry='COMPLETED_EXTERNALLY_ACCEPTED_ENGINEERING_SCOPE',
               v4_09_entry='AUTHORIZED_AFTER_V4_08_PROMOTION_VALIDATION')
    atomic_json(ROOT / GLOBAL, old)
    atomic_json(ROOT / RECEIPT, dict(contract_id='V4_08_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1', status='PASS',
                global_head_parent=parent, global_head_after=bind(GLOBAL), accepted_head=bind(HEAD),
                external_acceptance_decision=DECISION, protected_head_bindings=head['protected_head_bindings']))
    result = validate()
    atomic_json(ROOT / VALIDATION, result)
    if result['status'] != 'PASS': raise ValueError(result)
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--promote', action='store_true'); args = parser.parse_args()
    result = promote() if args.promote else validate()
    print(json.dumps(result, ensure_ascii=False)); sys.exit(0 if result['status'] == 'PASS' else 1)
