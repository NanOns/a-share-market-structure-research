"""Fail-closed disposable service launcher; production recovery is untouched."""
import json
import os
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
DISPOSABLE_BASE = Path('G:/codex_tmp/test_temp').resolve()
MARKER = '.disposable-runtime.json'

def protected_roots():
    import re
    # This project file has one explicitly quoted TDX root. Unsupported shapes fail closed.
    text = (REPOSITORY / 'config/paths.yaml').read_text(encoding='utf8')
    configured = re.findall(r'^  root: ("[^"\n]+")\s*$', text, re.MULTILINE)
    if len(configured) != 1 or not text.startswith('tdx:'):
        raise ValueError('CONFIGURED_TDX_ROOT_UNREADABLE')
    roots = [REPOSITORY, Path('D:/new_tdx'), Path(json.loads(configured[0]))]
    for name in ('dm01_go_forward_runtime_contract_r4.json', 'dm01_go_forward_runtime_contract_r4r1.json'):
        contract = json.loads((REPOSITORY / 'config' / name).read_text(encoding='utf8'))
        roots.extend(Path(p) for p in contract['read_only_tdx_roots'])
    return [p.resolve() for p in roots]

def validate_root(root):
    root = Path(root).resolve()
    if any(root == p or root.is_relative_to(p) or p.is_relative_to(root) for p in protected_roots()):
        raise ValueError('PROTECTED_ROOT')
    if not root.is_relative_to(DISPOSABLE_BASE) or root == DISPOSABLE_BASE:
        raise ValueError('TEST_ROOT_NOT_DISPOSABLE')
    return root

def guard(root, database, mode='NO_REAL_RECOVERY'):
    root, database = validate_root(root), Path(database).resolve()
    if not database.is_relative_to(root) or database == root:
        raise ValueError('DATABASE_OUTSIDE_TEST_ROOT')
    if mode not in ('NO_REAL_RECOVERY', 'DISPOSABLE_RECOVERY'):
        raise ValueError('RECOVERY_MODE_NOT_EXPLICIT')
    if json.loads((root / MARKER).read_text()) != {'disposable': True}:
        raise ValueError('DISPOSABLE_MARKER_REQUIRED')
    return root, database

def create(root):
    root = validate_root(root)
    root.mkdir(parents=True, exist_ok=True)
    temp = root / (MARKER + '.tmp')
    temp.write_text(json.dumps({'disposable': True}), encoding='utf8')
    os.replace(temp, root / MARKER)
    return root

def environment(root):
    root = Path(root).resolve()
    guard(root, root / 'data/database/test.duckdb')
    result = {k: os.environ[k] for k in ('PATH', 'SystemRoot', 'WINDIR') if k in os.environ}
    result.update(TEMP=str(root), TMP=str(root), PYTHONPATH=str(REPOSITORY / 'src') + os.pathsep + str(REPOSITORY),
                  CODEX_TEST_ROOT=str(root), CODEX_TEST_RECOVERY_MODE='NO_REAL_RECOVERY', WORKBENCH_API_BACKEND='duckdb')
    return result

def serve(root, database, port):
    mode = os.environ.get('CODEX_TEST_RECOVERY_MODE')
    root, database = guard(root, database, mode)
    if Path(os.environ.get('CODEX_TEST_ROOT', '')).resolve() != root:
        raise ValueError('CHILD_TEST_ROOT_MISMATCH')
    if Path.cwd().resolve() != root:
        raise ValueError('CHILD_WORKING_DIRECTORY_MISMATCH')
    from workbench_service import app
    if mode == 'NO_REAL_RECOVERY':
        app._recover_startup = lambda *a, **k: None
        app.HistoryJobService.recover_interrupted = lambda *a, **k: None
    else:
        # Isolated state recovery may mark interruptions; never resume copied
        # production requests or start their background compute.
        original = app.HistoryJobService.recover_interrupted
        app.HistoryJobService.recover_interrupted = lambda self, **kw: original(self, background=False)
        app._recover_startup = lambda root, db: recover_history(root, db)
    app.serve(root, host='127.0.0.1', port=port, database_path=database)

def recover_history(root, database):
    root, database = guard(root, database, 'DISPOSABLE_RECOVERY')
    from workbench_service.history_jobs import HistoryJobService
    return HistoryJobService(root, database).recover_interrupted(background=False)
