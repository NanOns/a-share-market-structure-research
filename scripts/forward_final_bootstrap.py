"""Read-only input fingerprints and atomic evidence for the R3 blocker task."""
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

from scripts.full_chain_repair_io import ROOT, binding, capture, write

P = 'reports/forward_r2_final_blocker_repair_20261007/'
DOCUMENTS = (
    'V4_FORWARD_R2_FINAL_BLOCKER_REPAIR_TASK_R3_20261007.md',
    'V4_FORWARD_R2_REMAINDER_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261007.md',
)


def source_roots():
    import re
    text = (ROOT / 'config/paths.yaml').read_text(encoding='utf8')
    roots = [Path(json.loads(v)) for v in re.findall(r'^  root: ("[^"\n]+")\s*$', text, re.M)]
    for file in (ROOT / 'config').glob('dm01_go_forward_runtime_contract_r4*.json'):
        roots.extend(Path(v) for v in json.loads(file.read_bytes())['read_only_tdx_roots'])
    return sorted(set(p.resolve() for p in roots))


def fingerprint(label):
    rows = []
    roots = source_roots()
    started = time.monotonic()
    for root in roots:
        if not root.is_dir():
            raise ValueError('CONFIGURED_SOURCE_ROOT_UNAVAILABLE:' + str(root))
        for directory, folders, names in os.walk(root, followlinks=False):
            folders.sort()
            for name in sorted(names):
                path = Path(directory) / name
                before = path.stat()
                digest = hashlib.sha256()
                with path.open('rb') as stream:
                    while block := stream.read(8 * 1024 * 1024):
                        digest.update(block)
                after = path.stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise ValueError('SOURCE_CHANGED_DURING_FINGERPRINT:' + str(path))
                rows.append(dict(path=path.as_posix(), size=before.st_size,
                                 sha256=digest.hexdigest(), mtime_ns=before.st_mtime_ns))
                if len(rows) % 10000 == 0:
                    print('READ_ONLY_FINGERPRINT', label, len(rows), flush=True)
    result = dict(roots=[p.as_posix() for p in roots], files=rows,
                  file_count=len(rows), total_bytes=sum(r['size'] for r in rows))
    write(P + 'TDX_' + label + '_FINGERPRINT.json', result)
    print('FINGERPRINT_COMPLETE', label, len(rows), result['total_bytes'],
          round(time.monotonic() - started, 2), flush=True)
    return result


def entry():
    for name in DOCUMENTS:
        source = Path('D:/Users/lps/Desktop/阶段任务') / name
        write('docs/evidence/forward_r2_final_blocker_repair_20261007/' + name,
              source.read_bytes(), raw=True)
    for directory in (P, 'docs/evidence/forward_r2_final_blocker_repair_20261007/'):
        write(directory + '.gitattributes', b'* -text whitespace=-blank-at-eol,-blank-at-eof,-space-before-tab\n', raw=True)
    value = capture()
    assert value['baseline_commit'] == 'a775383eabb94e97a6022f34a30de7aa55e3a39c'
    value.update(task_documents=[binding('docs/evidence/forward_r2_final_blocker_repair_20261007/' + p) for p in DOCUMENTS],
                 stage='R3_P1_A_PRE_TEST_TDX_FINGERPRINT', acceptance='PENDING',
                 next_stage='BOUNDARY_REPAIR_AND_DEPENDENCY_CLASSIFICATION',
                 temporary_root='G:/codex_tmp/test_temp', tests_started=False)
    write(P + 'ENTRY_BASELINE.json', value)
    fingerprint('PRE')


if __name__ == '__main__':
    import sys
    entry() if len(sys.argv) == 1 else fingerprint(sys.argv[1])
