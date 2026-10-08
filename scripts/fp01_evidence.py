"""FP-01 evidence: atomic project-only writes and read-only source fingerprints."""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/evidence/fp01_20261008'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf8')
    temp = path.with_name(path.name + '.tmp')
    with temp.open('wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def ref(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(8 * 1024 * 1024):
            h.update(block)
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=path.stat().st_size, sha256=h.hexdigest())


def protected():
    paths = set((ROOT / 'config').glob('*.json'))
    paths.update((ROOT / 'data/v4').glob('*.json'))
    paths.update((ROOT / 'docs/evidence').rglob('*.md'))
    paths.update(ROOT / p for p in ['AGENTS.md', 'config/paths.yaml', 'src/workbench_service/current_v4_context.py',
                                  'src/workbench_service/shadow_context.py', 'run_workbench_service.py'])
    return [ref(p) for p in sorted(paths) if 'fp01_20261008' not in p.as_posix()]


def entry():
    source = Path('D:/Users/lps/Desktop/阶段任务/V4_FULL_PRODUCT_PRODUCTION_TASK_CARDS_R1_20261008')
    docs = []
    for path in sorted(source.glob('*.md')):
        target = OUT / 'tasks' / path.name
        write(target, path.read_bytes())
        docs.append(ref(target))
    write(OUT / '.gitattributes', b'* -text whitespace=-blank-at-eol,-blank-at-eof,-space-before-tab\n')
    write(OUT / 'ENTRY.json', dict(stage='FP-01', stage_contract='V4_OPERATIONAL_PRODUCTION_RELEASE_POLICY_V1',
        baseline=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        utc=datetime.now().astimezone().isoformat(), tasks=docs, protected=protected(),
        driver_sync='No driver-named chat or repository file found in available chat inventory; supplied master and FP-01 are latest user authority. No cross-chat message sent.',
        phase0=ref('reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json'),
        scope='FP-01 only; FP-02/03/04 contracts read for boundary, not executed',
        acceptance='IN_PROGRESS', next_stage='FP01_INVENTORY_AND_SUCCESSOR_ADMISSION'))


def fingerprint(side):
    from scripts.forward_final_bootstrap import source_roots
    rows = []
    for root in source_roots():
        if not root.is_dir():
            raise ValueError('TDX_SOURCE_UNAVAILABLE:' + str(root))
        for directory, folders, names in os.walk(root, followlinks=False):
            folders.sort()
            for name in sorted(names):
                p = Path(directory) / name
                before = p.stat()
                h = hashlib.sha256()
                with p.open('rb') as stream:
                    while block := stream.read(8 * 1024 * 1024):
                        h.update(block)
                after = p.stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise ValueError('TDX_CHANGED_DURING_READ')
                rows.append(dict(path=p.as_posix(), bytes=before.st_size, mtime_ns=before.st_mtime_ns, sha256=h.hexdigest()))
    # Keep full fingerprint local; commit compact exact aggregate, counts and roots.
    raw = json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()
    write(ROOT / ('reports/fp01_20261008/TDX_' + side + '.json'), rows)
    value = dict(roots=[p.as_posix() for p in source_roots()], file_count=len(rows),
                 bytes=sum(r['bytes'] for r in rows), aggregate_sha256=hashlib.sha256(raw).hexdigest())
    write(OUT / ('TDX_' + side + '.json'), value)
    print(json.dumps(value), flush=True)


if __name__ == '__main__':
    if sys.argv[1] == 'entry':
        entry()
    elif sys.argv[1] in ('PRE', 'POST'):
        fingerprint(sys.argv[1])
