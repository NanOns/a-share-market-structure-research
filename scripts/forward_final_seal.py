"""Seal actual final regression and unchanged inputs; preserve honest blockers."""
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from scripts.full_chain_repair_io import ROOT, binding, capture, write
from scripts.forward_final_bootstrap import P


def seal(run='final_blocker_v4_only'):
    temporary = Path('G:/codex_tmp')
    for name, source in [('current_full.log', temporary / (run + '.log')),
                         ('execution_scope.json', ROOT / (P+'V4_ONLY_EXECUTION_SCOPE.json'))]:
        write(P + 'execution/' + name, source.read_bytes(), raw=True)
    cases = ET.fromstring((ROOT / (P+'execution/current_full.xml')).read_bytes()).findall('.//testcase')
    failed = []; errors = []; skipped = []
    for case in cases:
        node = case.attrib['classname'] + '::' + case.attrib['name']
        if case.find('failure') is not None:
            failed.append(dict(node=node, trace=case.find('failure').text))
        if case.find('error') is not None:
            errors.append(dict(node=node, trace=case.find('error').text))
        if case.find('skipped') is not None:
            skipped.append(dict(node=node, reason=case.find('skipped').attrib.get('message')))
    registry = json.loads((ROOT / (P + 'IA05_60_NODE_DEPENDENCY_CLASSIFICATION.json')).read_bytes())
    active = {r['old_node'] for r in registry['nodes'] if r['classification'] == 'ACTIVE_CURRENT_AUTHORITY'}
    introduced = [r for r in failed + errors if r['node'] not in active]
    pre = json.loads((ROOT / (P + 'TDX_PRE_FINGERPRINT.json')).read_bytes())
    post = json.loads((ROOT / (P + 'TDX_POST_FINGERPRINT.json')).read_bytes())
    pre_files = {r['path']: r for r in pre['files']}; post_files = {r['path']: r for r in post['files']}
    changed = sorted(p for p in set(pre_files) | set(post_files) if pre_files.get(p) != post_files.get(p))
    guards = []
    for guard_run in (run,'final_blocker_v4_pg_replay','final_blocker_v4_skip_closure'):
        guard_folder = Path('G:/codex_tmp/test_temp') / (guard_run + '_source_guard')
        for file in sorted(guard_folder.glob('*.json')):
            value = json.loads(file.read_bytes()); guards.append(value)
            write(P + 'execution/source_guard/' + guard_run + '/' + file.name, file.read_bytes(), raw=True)
    if not guards:
        raise ValueError('FINAL_SOURCE_GUARD_LOG_REQUIRED')
    before = json.loads((ROOT / (P + 'PROTECTED_FINGERPRINT_BEFORE_FULL.json')).read_bytes())
    after = json.loads((ROOT / (P + 'PROTECTED_FINGERPRINT_AFTER_FULL.json')).read_bytes())
    protected_equal = before == after
    entry = json.loads((ROOT / (P + 'ENTRY_BASELINE.json')).read_bytes())
    heads = capture()
    heads_equal = entry['protected'] == heads['protected']
    source_executed = sum(r.get('source_mutations_executed', -1) for r in guards)
    fresh_zero = not changed and source_executed == 0 and all(r.get('guard_installed') for r in guards)
    summary = dict(total=len(cases), passed=len(cases)-len(failed)-len(errors)-len(skipped),
                   failed=len(failed), errors=len(errors), skipped=len(skipped), failed_nodes=failed,
                   error_nodes=errors, skips=skipped, introduced_failures=introduced,
                   ignored=[], deselected=[], new_xfail=[], historical_supersession_count=0,
                   version_scope='V4_ONLY_USER_SCOPE_20261007',
                   execution_method='FULL_PROFILE_PLUS_VERIFIED_PG_ENVIRONMENT_REPLAY',
                   replay=binding(P+'V4_PG_ENVIRONMENT_REPLAY_RECEIPT.json'),
                   status='FAIL' if failed else 'PASS' if not errors else 'ERROR',
                   xml=binding(P+'execution/current_full.xml'), log=binding(P+'execution/current_full.log'))
    write(P + 'GLOBAL_CURRENT_REGRESSION_RECEIPT.json', summary)
    write(P + 'TDX_FRESH_ZERO_WRITE_RECEIPT.json', dict(status='PASS' if fresh_zero else 'FAIL',
        before=binding(P+'TDX_PRE_FINGERPRINT.json'), after=binding(P+'TDX_POST_FINGERPRINT.json'),
        file_count=pre['file_count'], total_bytes=pre['total_bytes'], changed_paths=changed,
        executed_source_mutations=source_executed, guarded_python_processes=len(guards),
        rejected_attempts=sum(len(r['rejected']) for r in guards), fresh_TDX_ZERO_WRITE=fresh_zero,
        historical_incident_write_calls=5, historical_incident_unique_files=4,
        historical_incident_TDX_ZERO_WRITE=False, pre_incident_content_trace=binding(P+'TDX_PRE_INCIDENT_CONTENT_TRACE.json')))
    write(P+'PROTECTED_STATE_READBACK.json',dict(protected_runtime_full_bytes_and_mtime_equal=protected_equal,
        accepted_heads_and_migrations_equal=heads_equal, before=binding(P+'PROTECTED_FINGERPRINT_BEFORE_FULL.json'),
        after=binding(P+'PROTECTED_FINGERPRINT_AFTER_FULL.json'), production=False,shadow=False,focus=False,default_ui=False))
    candidate_ready=not (failed or errors or introduced or not fresh_zero or not protected_equal or not heads_equal)
    write(P+'FINAL_DISPOSITION.json',dict(status='CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT' if candidate_ready else 'BLOCKED',
        candidate_ready=candidate_ready, candidate_scope='V4_ONLY_WITH_EXPLICIT_IA07_CAPABILITY_DEBT',
        external_acceptance=False, original_60_nodes=dict(role='PRE_V4_OUTSIDE_USER_EXECUTION_SCOPE',blocks_v4_regression=False),
        current_regression=summary, active_exact_artifacts_not_fabricated=True,
        legacy_model_source_preflight='PRIOR_OUTSIDE_SCOPE_DIAGNOSTIC_PASS',
        complete_historical_approval_chain='PRE_V4_OUTSIDE_EXECUTION_SCOPE_UNAVAILABLE_NOT_FABRICATED',
        IA07='NOT_VERIFIABLE_BY_CURRENT_ACCEPTED_CAPABILITY', IA07_FULL_PASS=False,
        TDX_fresh_zero_write=fresh_zero, historical_incident_erased=False,
        production=False,shadow=False,focus=False,default_ui=False,real_samples_added=False,
        next_stage='IA07_SEPARATE_CAPABILITY_ACCEPTANCE_AND_INDEPENDENT_V4_EXTERNAL_AUDIT'))
    print(json.dumps({k:summary[k] for k in ('total','passed','failed','errors','skipped')},sort_keys=True))


if __name__ == '__main__':
    seal()
