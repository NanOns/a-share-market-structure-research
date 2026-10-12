"""Read-only checkpoint recovery under the 2026-10-12 local delivery override."""
import gzip
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
PAUSE = ROOT / 'docs/audits/r4_r3_integration_20261011/PAUSE_CHECKPOINT_20261012_R1'
OUT = ROOT / 'docs/audits/r4_r3_local_delivery_20261012/S0'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    errors, archives, clusters = [], [], []
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if head != 'b1bf89ff7e90a868ec0573d5f0e7f9a916e4327a':
        errors.append('PAUSED_HEAD_CHANGED')
    manifest = json.loads((PAUSE / 'ARCHIVE_MANIFEST.json').read_bytes())
    for item in manifest:
        data = gzip.decompress((PAUSE / item['archive']).read_bytes())
        ok = len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
        archives.append(dict(archive=item['archive'], source=item['source'], verified=ok))
        if not ok:
            errors.append('ARCHIVE_MISMATCH:' + item['archive'])
    if len(manifest) != 432:
        errors.append('ARCHIVE_COUNT_CHANGED')
    receipt = json.loads((ROOT / 'docs/audits/r4_r3_consumers_20261011/FOCUS_RESUME_R1/RESULT.json').read_bytes())
    inputs = []
    for name, expected in receipt['inputs'].items():
        path = Path(name)
        ok = path.is_file() and sha(path) == expected
        inputs.append(dict(path=name, sha256=expected, verified=ok))
        if not ok:
            errors.append('INPUT_MISMATCH:' + name)
    workspace = Path('G:/codex_tmp/r4_r3_pg_publication_v2')
    protected = {}
    for name, expected in receipt['protected_after'].items():
        actual = sha(workspace / name)
        protected[name] = dict(expected=expected, actual=actual, verified=actual == expected)
        if actual != expected:
            errors.append('PROTECTED_HEAD_CHANGED:' + name)
    projection_ref = receipt['result']['focus']
    projection_path = workspace / projection_ref['path']
    if sha(projection_path) != projection_ref['sha256']:
        errors.append('FOCUS_PROJECTION_CHANGED')
    projection = json.loads(gzip.decompress(projection_path.read_bytes()))
    if len(projection['episodes']) != 2805:
        errors.append('FOCUS_EPISODE_COUNT_CHANGED')
    for expected in json.loads((PAUSE / 'CLUSTER_READBACK.json').read_bytes()):
        try:
            with psycopg.connect(host='127.0.0.1', port=expected['port'], user='r4_isolated_admin', dbname='postgres', connect_timeout=5, options='-c default_transaction_read_only=on') as db:
                db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
                directory = db.execute('show data_directory').fetchone()[0].replace('\\', '/')
                identity = db.execute('select system_identifier::text from pg_control_system()').fetchone()[0]
                ok = directory == expected['data_directory'] and identity == expected['system_identifier']
                clusters.append(dict(port=expected['port'], data_directory=directory, system_identifier=identity, verified=ok))
                if not ok:
                    errors.append('PG_IDENTITY_CHANGED:' + str(expected['port']))
        except Exception as exc:
            clusters.append(dict(port=expected['port'], verified=False, error_type=type(exc).__name__, error=str(exc)))
            errors.append('PG_UNAVAILABLE:' + str(expected['port']))
    status = subprocess.check_output(['git', 'status', '--porcelain=v1', '-uall'], cwd=ROOT, text=True)
    (OUT / 'WORKTREE_STATUS.txt').write_text(status, encoding='utf8')
    sources = {p.relative_to(ROOT).as_posix(): sha(p) for folder in ('src', 'scripts', 'tests') for p in (ROOT / folder).rglob('*.py') if '__pycache__' not in p.parts}
    result = dict(contract='R4_R3_LOCAL_RESUME_S0_V1', workflow_override='V4_R4_R3_Codex本地执行与集中交付规则_R4_20261012.md', timestamp=datetime.now(timezone.utc).isoformat(), head=head, status='PASS' if not errors else 'BLOCKED', archive_count=len(archives), archives=archives, inputs=inputs, protected=protected, clusters=clusters, episodes=len(projection['episodes']), actual_source_sha256=sources, errors=errors, next_stage='S1_FOCUS_SEMANTICS' if not errors else 'S0_RESOLVE_IDENTITY_OR_AVAILABILITY', drive_operations=0, production_changed=False)
    temp = OUT / 'RESULT.json.tmp'
    temp.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    os.replace(temp, OUT / 'RESULT.json')
    print(json.dumps({k: result[k] for k in ('status', 'head', 'archive_count', 'episodes', 'errors', 'next_stage')}))
    return 0 if not errors else 1


if __name__ == '__main__':
    raise SystemExit(main())
