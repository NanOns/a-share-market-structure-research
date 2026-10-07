"""Explicit retirement of dated diagnostic receipts, preserving active approvals."""
import ast
import hashlib
import json
from scripts.full_chain_repair_io import ROOT, binding, write
from scripts.forward_final_bootstrap import P


def successors(row):
    path = row['old_test_path']
    if '/upgrade_m14/' in path:
        return ['tests/upgrade_m14/test_source_registry.py::test_m14_registry_is_fail_closed_and_has_four_datasets',
                'tests/upgrade_m14/test_source_registry.py::test_no_source_or_dataset_can_claim_verified_or_enabled']
    if '/upgrade_m6/' in path:
        return ['tests/test_forward_final_release_scope.py::test_current_authority_separates_immutable_historical_release',
                'tests/test_forward_final_release_scope.py::test_historical_pointer_drift_rejected_before_current_acceptance']
    if 'p09_01_b_lz_ext01' in path:
        return ['tests/upgrade_v3/test_p09_01_b_lz_ext01.py::test_invalid_ext01_response_is_unavailable_and_fail_closed',
                'tests/upgrade_v3/test_p09_01_b_lz_ext01.py::test_valid_current_json_is_degraded_until_field_scale_and_pagination_are_fixed']
    if 'p09_01_source_registry' in path:
        return ['tests/upgrade_v3/test_p09_01_source_registry.py::test_static_registry_matches_v3_known_endpoints_and_is_fail_closed',
                'tests/upgrade_v3/test_p09_01_source_registry.py::test_hot_rank_and_quote_sources_are_request_time_only']
    return ['tests/upgrade_v3/test_p11_02_old_write_recovery_preview.py::test_p11_02_core_migrated_domains_have_no_legacy_writer_call_sites',
            'tests/test_remainder_current_guards.py::test_protected_filesystem_mutation_rejected[open]',
            'tests/test_remainder_current_guards.py::test_protected_filesystem_mutation_rejected[mkdir]',
            'tests/test_remainder_current_guards.py::test_protected_filesystem_mutation_rejected[rename]',
            'tests/test_forward_final_release_scope.py::test_current_authority_separates_immutable_historical_release']


def build():
    if (ROOT / (P + 'V4_SCOPE_CORRECTION_RECEIPT.json')).exists():
        raise ValueError('PRE_V4_HISTORICAL_RETIREMENT_OUTSIDE_USER_V4_SCOPE')
    registry = json.loads((ROOT / (P + 'IA05_60_NODE_DEPENDENCY_CLASSIFICATION.json')).read_bytes())
    rows = [r for r in registry['nodes'] if r['classification'] == 'UNKNOWN']
    assert len(rows) == 22
    modules = registry['consumer_graph']['modules']
    for row in rows:
        assert row['missing_artifacts'], row['old_node']
        hits = [p for p in modules if any(name.rsplit('/', 1)[-1] in (ROOT / p).read_text(encoding='utf-8-sig')
                                        for name in row['missing_artifacts'])]
        if hits:
            raise ValueError('HISTORICAL_ARTIFACT_HAS_CURRENT_CONSUMER:' + repr(hits))
        row.update(classification='HISTORICAL_ONLY_SUPERSEDED',
                   disposition='HISTORICAL_ARTIFACT_UNAVAILABLE_FORMALLY_SUPERSEDED',
                   active_authority_reads=[], consumer_scan_modules=modules,
                   current_successor_tests=successors(row),
                   reason='Dated probe, internal-stage or executed storage-action receipt is historical diagnostic evidence. '
                          'Current source gates, immutable stage authority and protected-storage boundaries replace its default regression role. '
                          'The original historical facts, dates, counts and acceptance remain unverified and are not claimed by successors.')
        row['successor_source_bindings'] = [binding(p) for p in sorted({s.split('::')[0] for s in row['current_successor_tests']})]
    registry.update(unknown_nodes=[], formal_supersession_count=22,
                    active_dependencies_not_superseded=True,
                    current_authority=binding('config/v4_current_stage_authority_v2.json'))
    # Publish the reviewable contract before removing any historical-only test.
    write('config/v4_forward_r3_historical_profile_v1.json', dict(
        contract_id='V4_FORWARD_R3_HISTORICAL_PROFILE_V1', version='1.0.0',
        superseded_nodes=rows, active_nodes=[r['old_node'] for r in registry['nodes'] if r['classification']=='ACTIVE_CURRENT_AUTHORITY'],
        no_active_artifact_supersession=True, missing_original_is_not_current_pass=True,
        historical_execution='scripts.forward_final_historical_replay',
        original_assertions_rewritten=False, original_expected_digests_replaced=False,
        current_default='All current test functions; 22 formally retired historical-only functions remain in exact module archives',
        ignore=[], deselect=[], xfail=[], runtime_permission=False,
        production=False, shadow=False, focus=False, default_ui=False))
    for path in sorted({r['old_test_path'] for r in rows}):
        selected = [r for r in rows if r['old_test_path'] == path]
        raw = (ROOT / selected[0]['original_archive']['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == selected[0]['original_module']['sha256']
        current = (ROOT / path).read_bytes()
        if current != raw:
            raise ValueError('HISTORICAL_TEST_HAS_UNRELATED_CHANGES:' + path)
        source = raw.decode('utf-8-sig'); lines = source.splitlines(keepends=True)
        names = {r['original_function'] for r in selected}
        spans = []
        for fn in ast.parse(source).body:
            if isinstance(fn, ast.FunctionDef) and fn.name in names:
                first = min([fn.lineno] + [d.lineno for d in fn.decorator_list]) - 1
                spans.append((first, fn.end_lineno))
        assert len(spans) == len(names)
        for first, last in sorted(spans, reverse=True):
            lines[first:last] = ['# Historical-only assertion retained in the exact R3 archive and versioned profile contract.\n']
        write(path, ''.join(lines).encode('utf8'), raw=True)
    for row in rows:
        row['pre_scope_change_successor_source_bindings'] = row['successor_source_bindings']
        row['successor_source_bindings'] = [binding(p) for p in sorted({s.split('::')[0] for s in row['current_successor_tests']})]
    contract_path = 'config/v4_forward_r3_historical_profile_v1.json'
    contract = json.loads((ROOT / contract_path).read_bytes())
    contract['superseded_nodes'] = rows
    write(contract_path, contract)
    write(P + 'IA05_60_NODE_DEPENDENCY_CLASSIFICATION.json', registry)
    write(P + 'IA05_FORMAL_HISTORICAL_SUPERSESSION_RECEIPT.json', dict(
        status='FORMALLY_SUPERSEDED_HISTORICAL_DIAGNOSTICS_ONLY', superseded_count=22,
        active_approval_dependency_nodes=38, active_missing_artifacts_retired=False,
        contract=binding('config/v4_forward_r3_historical_profile_v1.json'),
        historical_claims_revalidated=False, current_candidate_ready=False,
        next_stage='CURRENT_SUCCESSOR_TESTS_AND_EXACT_HISTORICAL_PROFILE_EXECUTION'))


if __name__ == '__main__':
    build()
