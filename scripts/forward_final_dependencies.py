"""Classify missing historical evidence before any formal test supersession."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from scripts.full_chain_repair_io import ROOT, binding, write
from scripts.forward_final_bootstrap import P

BASELINE = 'a775383eabb94e97a6022f34a30de7aa55e3a39c'
ACTIVE_MODEL = 'reports/shadow/v2/20260904/integrated/R3_INTEGRATED_SHADOW_IDENTITY.json'
ARCHIVE = 'docs/evidence/forward_r2_final_blocker_repair_20261007/original_tests/'


def relative_trace(trace):
    names = re.findall(r"No such file or directory: '([^']+)'", trace)
    if 'P09-01-A_SOURCE_REGISTRY.json' in trace:
        names.append('reports/upgrade_v3/P09-01-A_SOURCE_REGISTRY.json')
    result = []
    for name in names:
        name = name.replace('\\\\', '/').replace('\\', '/')
        for prefix in ('reports/', 'data/', 'artifacts/'):
            if prefix in name:
                result.append(name[name.index(prefix):])
                break
    return sorted(set(result))


def current_graph():
    # Include the actual M4 subprocess edge, not merely Python imports.
    entries = ['run_workbench_service.py', 'run_bundle_compute.py', 'run_live_forward.py',
               'src/workbench_service/app.py', 'src/workbench_publish/orchestrator.py',
               'src/workbench_analysis/v4_current_stage_authority.py']
    queue = list(entries); seen = set(); edges = []
    while queue:
        path = queue.pop()
        if path in seen or not (ROOT / path).is_file():
            continue
        seen.add(path)
        tree = ast.parse((ROOT / path).read_text(encoding='utf-8-sig'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    parts = Path(path).with_suffix('').parts
                    if parts and parts[0] == 'src':
                        parts = parts[1:]
                    package = list(parts[:-1])
                    if node.level > 1:
                        package = package[:-(node.level - 1)]
                    prefix = '.'.join(package + ([node.module] if node.module else []))
                    modules = [prefix] + [prefix + '.' + a.name for a in node.names if a.name != '*']
                else:
                    modules = [node.module] if node.module else []
            else:
                continue
            for module in modules:
                for dest in (module.replace('.', '/') + '.py', 'src/' + module.replace('.', '/') + '.py',
                             'src/' + module.replace('.', '/') + '/__init__.py'):
                    if (ROOT / dest).is_file():
                        edges.append(dict(source=path, target=dest, kind='IMPORT'))
                        queue.append(dest)
                        break
    edges.extend([
        dict(source='src/workbench_publish/orchestrator.py', target='run_bundle_compute.py', kind='CONTROLLED_PRODUCTION_SUBPROCESS'),
        dict(source='run_bundle_compute.py', target='run_live_forward.py', kind='ProductionServices.publish_workbench -> identity_layers -> model_identity'),
        dict(source='run_live_forward.py', target=ACTIVE_MODEL, kind='FIXED_ACTIVE_MODEL_APPROVAL_READ'),
    ])
    return dict(entrypoints=entries, modules=sorted(seen), edges=edges,
                active_model_approval=ACTIVE_MODEL, active_model_exists=(ROOT / ACTIVE_MODEL).exists())


def build():
    if (ROOT / (P + 'V4_SCOPE_CORRECTION_RECEIPT.json')).exists():
        raise ValueError('PRE_V4_DEPENDENCY_INVESTIGATION_OUTSIDE_USER_V4_SCOPE')
    if (ROOT / 'config/v4_forward_r3_historical_profile_v1.json').exists():
        raise ValueError('FORMAL_HISTORICAL_PROFILE_EXISTS_USE_A_NEW_VERSION_NOT_OVERWRITE_CLASSIFICATION')
    prior = json.loads((ROOT / 'reports/forward_r2_remainder_consolidated_20261007/OPEN_ISSUES_FINAL_DISPOSITION.json').read_bytes())
    failures = [r for r in prior['issues'] if r.get('category') == 'HISTORICAL_ARTIFACT_UNAVAILABLE']
    assert len(failures) == 60
    graph = current_graph(); rows = []; artifacts = {ACTIVE_MODEL}; archived = set()
    for case in failures:
        module, node = case['node'].split('::', 1)
        path = module.replace('.', '/') + '.py'
        raw = subprocess.check_output(['git', 'show', BASELINE + ':' + path], cwd=ROOT)
        source = raw.decode('utf-8-sig'); function = node.split('[', 1)[0]
        tree = ast.parse(source)
        fn = next(n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == function)
        expectation = ast.get_source_segment(source, fn)
        # The live model approval embeds the old receipt-chain digests and V1
        # baseline identity. Those dependencies cannot be retired merely because
        # the runtime preflight currently checks only sealed source hashes.
        active = path.startswith(('tests/r3_', 'tests/r4_'))
        missing = relative_trace(case['evidence'])
        artifacts.update(missing)
        if path not in archived:
            write(ARCHIVE + path, raw, raw=True); archived.add(path)
        category = ('M14_REQUEST_TIME_NO_PERSISTENCE' if '/upgrade_m14/' in path else
                    'V3_STORAGE_AND_PUBLICATION_BOUNDARY' if '/upgrade_v3/' in path or '/upgrade_m6/' in path else
                    'V1_IMMUTABLE_RELEASE' if 'v1_' in path else
                    'V4_IDENTITY_TAMPER_REJECTION' if '/r4_repair/' in path else
                    'CURRENT_RESEARCH_STRUCTURE_AND_SCOPE')
        rows.append(dict(old_node=case['node'], old_test_path=path, original_function=function,
            original_module=dict(path=path, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()),
            original_archive=binding(ARCHIVE + path), old_expectation=expectation,
            missing_artifacts=missing, historical_identity='20260904_V1_695c7ae5_V2_R3_R4' if '/upgrade_' not in path else 'M5_M6_M14_V3_20260911_TO_20260913_STAGE_RECEIPTS',
            active_owner_input= binding(ACTIVE_MODEL) if active and (ROOT / ACTIVE_MODEL).is_file() else None,
            classification='ACTIVE_CURRENT_AUTHORITY' if active else 'UNKNOWN',
            disposition='BLOCKED_EXACT_ACTIVE_ARTIFACT_RECOVERY_REQUIRED' if active else 'CONSUMER_SUCCESSOR_REVIEW_REQUIRED_NO_SUPERSESSION_GRANTED',
            consumer_evidence=[e for e in graph['edges'] if e['target'] == ACTIVE_MODEL] if active else
                [dict(current_authority='config/v4_current_stage_authority_v2.json', current_data='data/v4/V4_DATA_ACCEPTED_HEAD.json',
                      reason='Fixed old snapshot/stage receipt; current date-scoped SQL/publication readers do not use this literal artifact as authority; original assertion remains an archive requirement')],
            successor_invariant=category,
            successor_current_authority='config/v4_current_stage_authority_v2.json',
            successor_current_test=None if active else path + '::test_current_' + function.removeprefix('test_'),
            original_failure_trace=case['evidence']))
    assert sum(r['classification'] == 'ACTIVE_CURRENT_AUTHORITY' for r in rows) >= 1
    write(P + 'IA05_60_NODE_DEPENDENCY_CLASSIFICATION.json', dict(nodes=rows, consumer_graph=graph,
        unknown_nodes=[r['old_node'] for r in rows if r['classification']=='UNKNOWN'], classification_precedes_supersession=True,
        active_dependencies_not_superseded=True))
    # Exact path + all refs + LFS history lookup. Unindexed local backups are
    # searched separately by bounded basename inventory, never by fabrication.
    search = []
    for path in sorted(artifacts):
        commits = subprocess.check_output(['git', 'log', '--all', '--format=%H', '--', path], cwd=ROOT, text=True).splitlines()
        objects = [line for line in subprocess.check_output(['git', 'rev-list', '--all', '--objects', '--', path], cwd=ROOT, text=True).splitlines()
                   if line.partition(' ')[2] == path]
        search.append(dict(path=path, current_exists=(ROOT / path).exists(), all_ref_commits=commits,
                           all_ref_objects=objects, checked_in_lfs_path_history=objects,
                           original_bytes_recovered=False))
    archive_roots = [ROOT / p for p in ('reports', 'data', 'docs/evidence', 'artifacts')]
    archive_roots += [Path('E:/codex_tmp/test_temp'), Path('G:/codex_tmp/test_temp')]
    names = {Path(p).name for p in artifacts}; candidates = []
    for base in archive_roots:
        for directory, folders, files in os.walk(base):
            folders[:] = [f for f in folders if f not in ('.git', '__pycache__', 'node_modules')]
            for name in set(files) & names:
                candidates.append(str(Path(directory) / name))
    for row in search:
        row['bounded_archive_candidates'] = [p for p in candidates if Path(p).name == Path(row['path']).name]
        row['current_binding'] = binding(row['path']) if (ROOT / row['path']).is_file() else None
        row['candidate_scope_warning'] = 'A basename match alone cannot restore a missing sealed historical identity'
    from run_live_forward import ProductionServices
    try:
        active_validation = dict(status='PASS', model_identity=ProductionServices().model_identity(ROOT))
    except Exception as error:
        active_validation = dict(status='BLOCKED', error_type=type(error).__name__, reason=str(error))
    write(P + 'IA05_ARTIFACT_RECOVERY_SEARCH.json', dict(artifacts=search,
        exact_scope=dict(baseline=BASELINE, git='all currently available local refs', lfs='all-ref path-to-blob/pointer history',
                         approved_archive_roots=[str(p) for p in archive_roots], external_backups='USER_CONFIRMED_NO_OTHER_BACKUP_DIRECTORIES'),
        lfs_object_files=sum(1 for p in (ROOT / '.git/lfs/objects').rglob('*') if p.is_file()),
        fabricated_artifacts=False, active_missing=[p for p in (ACTIVE_MODEL,) if not (ROOT / p).is_file()],
        active_owner_preflight=active_validation,
        classification_acceptance='PRELIMINARY_REQUIRES_PER_NODE_CONSUMER_AND_SUCCESSOR_REVIEW',
        basename_candidates_are_not_proof_of_exact_recovery=True))
    print('classified', len(rows), 'active', sum(r['classification'] == 'ACTIVE_CURRENT_AUTHORITY' for r in rows), flush=True)


if __name__ == '__main__':
    build()
