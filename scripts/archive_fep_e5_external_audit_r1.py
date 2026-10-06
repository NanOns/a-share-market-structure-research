"""One-shot receipt for the supplied E5 blocked audit; no integration repair."""
import json, os, re, subprocess
from pathlib import Path
from scripts.build_fep_e2_r1r1_history import ROOT, binding, now
from scripts.validate_r25_preflight import protected, selection
from workbench_analysis.fep_e1.contracts import atomic_json, digest
from workbench_analysis.fep_e1.feature_owner import verify_file

AUDITED = '51a1aab3fc9fe5bb390ec768dfd9514a1db6af54'
PARENT = 'adcfa36466e0c33626cc6ffc5fbd37cfd65e98bb'
NAME = 'V4_15E5_INDEPENDENT_EXTERNAL_AUDIT_R1_20261006.md'
REPORT = ROOT / 'reports/fep_e5_external_audit_r1'
OLD = ROOT / 'reports/fep_e5_r1'
NEXT = 'ISSUE_V4_15E5_R1R1_CANONICAL_FEP_INTEGRATION_REPAIR'

def load(path):
    return json.loads(path.read_bytes())

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def require(condition, reason):
    if not condition:
        raise ValueError(reason)

def write(path, raw):
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    os.replace(tmp, path)

def emit(name, payload):
    atomic_json(REPORT / (name + '.json'), payload)

def main():
    require(not REPORT.exists(), 'ONE_SHOT_AUDIT_RECEIPT_ALREADY_EXISTS')
    require(git('rev-parse', 'HEAD').decode().strip() == AUDITED, 'AUDITED_HEAD_REQUIRED')
    require(git('rev-parse', AUDITED + '^').decode().strip() == PARENT, 'PARENT_MISMATCH')
    raw = (Path('D:/Users/lps/Desktop/阶段任务') / NAME).read_bytes()
    text = raw.decode('utf-8-sig')
    require(AUDITED in text and PARENT in text, 'AUTHORITY_BASELINE_MISMATCH')
    decisions = dict(V4_15E5_FINAL_EXTERNAL_AUDIT='BLOCKED_R1_CANONICAL_FEP_INTEGRATION',
        E5_PROTOCOL_FREEZE='PASS', E5_MODEL_EVIDENCE_CLASS='PASS',
        E5_HISTORICAL_ENTRY_PROJECTION_PROTOTYPE='PASS_ENGINEERING', E5_ENTRY_DAILY_SEPARATION='PASS',
        E5_PRIORITY_V2_SHADOW_ENGINE='PASS_ENGINEERING_FIXTURE',
        E5_PERMISSION_FAIL_CLOSED='PASS_IN_ISOLATED_ENGINEERING_LEDGER',
        E5_ROLLBACK_ATOMICITY='PASS_IN_ISOLATED_ENGINEERING_LEDGER', E5_NEGATIVE_MATRIX='PASS',
        E5_REGRESSION='PASS_CAPABILITY_SCOPED_WITH_KNOWN_DEBT',
        E5_CANONICAL_FEP_LEDGER_INTEGRATION='FAIL',
        E5_CANONICAL_OBSERVATION_SNAPSHOT_PUBLICATION_BINDING='FAIL',
        E5_CANONICAL_PERMISSION_DEPLOYMENT_INTEGRATION='FAIL')
    for key, value in decisions.items():
        values = re.findall(r'(?m)^' + key + r'\s*=\s*([^\r\n]+)', text)
        require(values and all(v.strip() == value for v in values), 'AUDIT_VERDICT_MISMATCH:' + key)
    require(NEXT in text, 'NEXT_REPAIR_TASK_BOUNDARY_MISSING')
    old = load(OLD / 'FEP_E5_R1_CANDIDATE_SEAL.json')
    refs = old['code_bindings'] + old['evidence_bindings']
    refs += [binding(OLD / 'FEP_E5_R1_CANDIDATE_SEAL.json')]
    cp = load(ROOT / 'config/fep_e5_projection_priority_protocol_v1.json')
    refs += cp['upstream_bindings']
    migrations = ['src/workbench_db/migrations/v4_postgres/' + n for n in
        ('028_fep_schema_v1.sql', '029_fep_append_only_v1.sql', '030_fep_validation_cas_v1.sql', '031_fep_roles_v1.sql')]
    refs += [binding(ROOT / p) for p in migrations]
    refs = list({b['path']: b for b in refs}.values())
    for b in refs:
        verify_file(ROOT, b)
        require(git('rev-parse', AUDITED + ':' + b['path']).strip() ==
            git('hash-object', '--path=' + b['path'], b['path']).strip(), 'AUDITED_BLOB_CHANGED:' + b['path'])
    protected_state = protected(ROOT); wait = selection(ROOT)
    require(not protected_state['historical_git_diff'] and wait['status'] == 'WAIT_ACCEPTED_DAILY_INPUT', 'PROTECTED_STATE_CHANGED')
    require("SCHEMA='fep_e5_engineering'" in (ROOT / 'src/workbench_analysis/fep_e5/ledger.py').read_text(), 'PROTOTYPE_NAMESPACE_MISMATCH')
    require("CHECK(model_role='CHAMPION')" in (ROOT / migrations[0]).read_text(), 'CANONICAL_ROLE_CONFLICT_MISMATCH')
    require('CREATE FUNCTION fep.cas_deploy(' in (ROOT / migrations[2]).read_text(), 'CANONICAL_CAS_MISSING')
    github = 'repos/NanOns/a-share-market-structure-research/'
    ci = {}
    for label, endpoint in dict(workflow=github + 'actions/runs?head_sha=' + AUDITED + '&per_page=100',
            status=github + 'commits/' + AUDITED + '/status', checks=github + 'commits/' + AUDITED + '/check-runs?per_page=100').items():
        ci[label] = json.loads(subprocess.check_output(['gh', 'api', endpoint], cwd=ROOT))
    require(ci['status']['sha'] == AUDITED, 'CI_HEAD_MISMATCH')
    no_ci = all(ci[k]['total_count'] == 0 for k in ci)
    REPORT.mkdir(parents=True)
    write(REPORT / '.gitattributes', b'* -text\n'); write(REPORT / NAME, raw)
    emit('GITHUB_CI_IMPLEMENTATION_READBACK', dict(implementation_head=AUDITED, checked_at=now(),
        workflow_runs=ci['workflow']['workflow_runs'], statuses=ci['status']['statuses'], check_runs=ci['checks']['check_runs'],
        counts={k: ci[k]['total_count'] for k in ci}, combined_status=ci['status']['state'],
        disposition='NO_RUN_NO_STATUS' if no_ci else 'READBACK_PRESENT_REQUIRES_REVIEW', external_acceptance=False))
    scopes = [('E5-B01', 'CANONICAL_FEP_LEDGER_INTEGRATION', 'Use the accepted canonical fep.* projection ledger, not a parallel schema.', ['PROJECTION_PERSISTENCE_GATE', 'FINAL_EXIT_READBACK']),
        ('E5-B02', 'CANONICAL_OBSERVATION_SNAPSHOT_PUBLICATION_BINDING', 'Bind formal observations/revisions/snapshots/publications with canonical FK and triggers; engineering content handles do not satisfy this chain.', ['EMBEDDED_SNAPSHOT_ADAPTER_READBACK']),
        ('E5-B03', 'CANONICAL_PERMISSION_DEPLOYMENT_INTEGRATION', 'Validate canonical permission/activation/deployment receipts and fep.cas_deploy; explicitly repair the CHAMPION-only vs diagnostic SHADOW contract conflict without granting display or priority.', ['PERMISSION_MATRIX', 'ROLLBACK_DRILL'])]
    items = [dict(audit_id=key, status='OPEN_BLOCKER', scope=scope, repair_requirement=repair,
        evidence=[binding(OLD / (name + '.json')) for name in names] + [binding(ROOT / p) for p in migrations],
        acceptance='Separately issued R1R1 task and independent audit; not closed by this receipt') for key, scope, repair, names in scopes]
    emit('AUDIT_ITEM_DISPOSITIONS', dict(blockers=items, notes=[dict(audit_id='AUDIT_NOTE_E5_01',
        status='HEAD_TARGET_CORRECTED_READBACK_NO_CI_RUN', scope='Implementation HEAD CI receipt; prior candidate receipt remains immutable',
        evidence=[binding(REPORT / 'GITHUB_CI_IMPLEMENTATION_READBACK.json')], acceptance='Local readback only; no CI PASS claim'),
        dict(audit_id='AUDIT_NOTE_E4_01', status='EXTERNALLY_CONFIRMED_E5_PROTOCOL_PASS', scope='Seven frozen engineering governance fields',
        evidence=[binding(REPORT / NAME), binding(OLD / 'PROTOCOL_FREEZE.json')], acceptance='Supplied E5 external audit section 2')]))
    state = dict(decisions, E5='BLOCKED_NOT_FORMALLY_ACCEPTED', FEP_E5_ENGINEERING_ACCEPTED=False,
        E5_R1R1_STARTED=False, E5_R1R1_FORMAL_TASK_CARD='NOT_SUPPLIED', NEXT=NEXT,
        REAL_DAILY_PRIORITY_SHADOW='NOT_GRANTED', PRIORITY_USE='UNGRANTED', MODEL_DISPLAY='UNGRANTED',
        CHAMPION=False, REAL_OOS='NOT_GRANTED', FIRST_OBSERVED='NOT_GRANTED', FEP_PRODUCTION='UNGRANTED',
        new_training=0, new_label_resolution=0, production=False, shadow=False, focus=False)
    emit('AUDIT_RECONCILIATION_READBACK', dict(status='PASS_BLOCKED_EXTERNAL_VERDICT_ARCHIVED', state=state,
        authority=binding(REPORT / NAME), audited_implementation=AUDITED, audited_parent=PARENT,
        immutable_upstream_bindings=refs, protected_state=protected_state, R25=wait,
        regression=load(OLD / 'SCOPED_REGRESSION_SUMMARY.json'), targeted=load(OLD / 'TARGETED_SUMMARY.json'),
        test_execution='NOT_RERUN_AUDIT_RECEIPT_ONLY', canonical_schema_changed=False, model_artifacts_changed=False))
    write(REPORT / 'COMPLETION_REPORT.md', f'''# V4-15E5 external audit R1 archive\n\nExternal verdict: BLOCKED_R1_CANONICAL_FEP_INTEGRATION. Audited implementation: {AUDITED}; parent: {PARENT}.\n\nE5 remains unaccepted. E5-B01/B02/B03 are OPEN_BLOCKER: canonical fep ledger, observation/snapshot/publication binding, and permission/deployment/CAS integration. The isolated engineering prototype passed its scoped gates but does not satisfy canonical integration. Existing candidate, inference, models, protocol and tests remain immutable.\n\nAUDIT_NOTE_E5_01 corrected through implementation HEAD CI readback, without rewriting the old base-targeted receipt. No GitHub CI PASS is claimed. Seven governance fields are externally confirmed PASS under AUDIT_NOTE_E4_01.\n\nArchived regression: targeted 306 passed/1 skipped/0 failed; scoped 2665 passed/4 skipped/52 exact existing failures/0 introduced failures. These are inherited results, not a new test run. Protected heads, Priority V1 and R25 WAIT checked; no runtime, schema or database changes.\n\nNext: {NEXT}. No R1R1 task card supplied, no integration repair started. All real Daily, display, Priority, Champion, OOS, first-observed and production permissions remain closed.\n\nThis script is a one-shot, exact-HEAD authority receipt builder. It is not a portable forecast or integration reproduction entry point.\n'''.encode())
    source = 'scripts/archive_fep_e5_external_audit_r1.py'
    paths = [source] + sorted(p.relative_to(ROOT).as_posix() for p in REPORT.iterdir() if p.is_file())
    paths += [(REPORT / n).relative_to(ROOT).as_posix() for n in ('CHANGED_FILE_LIST.json', 'EXTERNAL_AUDIT_ARCHIVE_SEAL.json')]
    emit('CHANGED_FILE_LIST', dict(parent=AUDITED, all_changed_files=sorted(paths)))
    seal = dict(stage='V4-15E5.EXTERNAL_AUDIT.R1', status='BLOCKED_EXTERNAL_AUDIT_ARCHIVED', baseline=AUDITED,
        authority=binding(REPORT / NAME), code_bindings=[binding(ROOT / source)],
        evidence_bindings=[binding(p) for p in sorted(REPORT.iterdir()) if p.is_file()], state=state, sealed_at=now())
    seal['logical_digest'] = digest(seal); emit('EXTERNAL_AUDIT_ARCHIVE_SEAL', seal)
    print('BLOCKED_EXTERNAL_AUDIT_ARCHIVED; THREE OPEN BLOCKERS; STOP WAIT R1R1 TASK')

if __name__ == '__main__':
    main()
