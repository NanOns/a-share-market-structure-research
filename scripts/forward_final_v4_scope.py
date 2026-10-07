"""Explicit V4-only execution scope following the user's scope correction."""
import json
import subprocess
from pathlib import Path
from scripts.full_chain_repair_io import ROOT, binding, write
from scripts.forward_final_bootstrap import P


def build():
    selected = []
    for folder in sorted((ROOT / 'tests').iterdir()):
        if folder.is_dir() and (folder.name.startswith('v4_') or folder.name in
                               ('fep', 'fep_e2', 'fep_e3', 'fep_e4', 'fep_e5')):
            selected.extend(p.relative_to(ROOT).as_posix() for p in sorted(folder.rglob('test_*.py')))
    root_names = ('test_v4_', 'test_forward_', 'test_full_chain_', 'test_remainder_')
    extra = {'test_settlement_r1r1.py', 'test_r20d_settlement.py',
             'test_a08_governance_propagation.py', 'test_pre16_governance.py',
             'test_r6r1_governance_cleanup.py'}
    for path in sorted((ROOT / 'tests').glob('test_*.py')):
        if (path.name.startswith(root_names) or path.name in extra or
                (path.name.startswith('test_r') and 'v4_' in path.read_text(encoding='utf8'))):
            selected.append(path.relative_to(ROOT).as_posix())
    selected = sorted(set(selected))
    all_files = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'tests').rglob('test_*.py'))
    receipt = dict(version='V4_ONLY_USER_SCOPE_20261007',
                   authorization='User: 全量执行和历史测试仅包括V4版本，不包括之前版本',
                   files=selected, bindings=[binding(p) for p in selected],
                   outside_version_scope=[p for p in all_files if p not in selected],
                   fep_scope='V4 integrated successor and PostgreSQL contracts',
                   collection_ignore=[], deselection=[], xfail=[],
                   pre_v4_missing_artifacts_block_v4_regression=False,
                   old_mixed_runs='INTERRUPTED_OR_HISTORICAL_INFORMATION_NOT_V4_ACCEPTANCE')
    write(P + 'V4_ONLY_EXECUTION_SCOPE.json', receipt)
    return selected


if __name__ == '__main__':
    import sys
    paths = build()
    if '--run' in sys.argv:
        import os
        from scripts.forward_final_pg_fixture import prepare
        environment=dict(os.environ)
        environment['V4_10_DISPOSABLE_TEST_DSN']=prepare()
        environment['WORKBENCH_PG_DSN']=environment['V4_10_DISPOSABLE_TEST_DSN']
        raise SystemExit(subprocess.call([sys.executable, '-m', 'pytest', '-q', *paths,
            '--basetemp=G:/codex_tmp/test_temp/final_blocker_v4_only',
            '--junitxml=G:/codex_tmp/final_blocker_v4_only.xml'],env=environment))
    print(json.dumps(dict(selected_files=len(paths)), sort_keys=True))
