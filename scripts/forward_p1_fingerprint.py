"""Read-only protected runtime inventory; writes only atomic repair evidence."""
import hashlib
import json
from pathlib import Path
from scripts.full_chain_repair_io import ROOT, binding, write

PREFIX = 'reports/forward_p1_repair_r1_20261006/'

def file_state(path):
    before = path.stat()
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(8 * 1024 * 1024):
            h.update(block)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError('PROTECTED_FILE_CHANGED_DURING_READ')
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=after.st_size,
                mtime_ns=after.st_mtime_ns, sha256=h.hexdigest())

def capture():
    paths = set()
    for name in ('data/database', 'data/current', 'data/market', 'data/v4', 'data/shadow', 'artifacts'):
        directory = ROOT / name
        paths.update(p for p in directory.rglob('*') if p.is_file())
    states = [file_state(p) for p in sorted(paths)]
    return dict(coverage='FULL_BYTES_AND_MTIME_ALL_FILES_IN_ENUMERATED_ROOTS',
                roots=['data/database','data/current','data/market','data/v4','data/shadow','artifacts'], files=states)

def supplemental():
    roots = [p for p in (ROOT / 'data').iterdir() if p.is_dir() and p.name != 'input_staging']
    inventory = []
    for directory in sorted(roots):
        states = [file_state(p) for p in sorted(directory.rglob('*')) if p.is_file()]
        raw = json.dumps(states,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
        inventory.append(dict(root=directory.relative_to(ROOT).as_posix(),files=len(states),
                              bytes=sum(s['bytes'] for s in states),catalog_sha256=hashlib.sha256(raw).hexdigest()))
    return dict(coverage='ALL_RUNTIME_DATA_OUTPUT_ROOTS_FULL_BYTES_MTIME_ORDERED_CATALOG_SHA256',
                excluded_read_only_input_root='data/input_staging',roots=inventory)

if __name__ == '__main__':
    import sys
    if sys.argv[1] == 'AFTER_ALL':
        original=file_state
        cache={}
        def file_state(path):
            if path not in cache: cache[path]=original(path)
            return cache[path]
        write(PREFIX+'IA09_PROTECTED_ROOT_FINGERPRINT_AFTER.json',capture())
        write(PREFIX+'IA09_ALL_RUNTIME_ROOTS_AFTER_FINAL_REGRESSION.json',supplemental())
    elif sys.argv[1].startswith('ALL_'):
        write(PREFIX+'IA09_'+sys.argv[1]+'.json',supplemental())
    else:
        write(PREFIX + 'IA09_PROTECTED_ROOT_FINGERPRINT_' + sys.argv[1] + '.json', capture())
