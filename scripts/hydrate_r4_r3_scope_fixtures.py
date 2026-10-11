"""Copy missing frozen V4 fixture inputs only; original and existing bytes stay put."""
import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('G:/codex work/大A交易')
OUT = ROOT / 'docs/audits/r4_r3_scope_20261011'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while data := stream.read(1024 * 1024): h.update(data)
    return h.hexdigest()

def main():
    seed = ['reports/r28', 'reports/r29', 'reports/r30', 'reports/r31', 'reports/v4_09', 'reports/v4_12',
            'reports/v4_12_runtime_r1', 'reports/v4_12_runtime_r11', 'reports/v4_12_runtime_r12',
            'reports/dm01/a01_r2/20261001T033251758661Z/normalized_schema_v2_1']
    queue = [p.relative_to(SOURCE).as_posix() for name in seed for p in (SOURCE / name).rglob('*') if p.is_file()]
    visited = set(); records = []; total = 0
    while queue:
        rel = queue.pop()
        if rel in visited: continue
        visited.add(rel)
        source = (SOURCE / rel).resolve(); target = (ROOT / rel).resolve()
        if not source.is_relative_to(SOURCE.resolve()) or not target.is_relative_to(ROOT):
            raise ValueError('FIXTURE_PATH_ESCAPE')
        if not source.is_file(): continue
        if source.stat().st_size > 100 * 1024 * 1024:
            records.append(dict(path=rel, bytes=source.stat().st_size, status='BOUNDED_SOURCE_HASH_COPY_LIMIT_OPEN'))
            continue
        before = sha(source)
        if target.exists():
            outcome = 'PRESENT_IDENTICAL' if sha(target) == before else 'PRESENT_DIFFERENT_PRESERVED'
        elif source.stat().st_size > 100 * 1024 * 1024 or total + source.stat().st_size > 1024 * 1024 * 1024:
            outcome = 'BOUNDED_COPY_LIMIT_OPEN'
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as dest, source.open('rb') as origin: shutil.copyfileobj(origin, dest)
            total += source.stat().st_size
            outcome = 'COPIED_MISSING_ONLY'
            if sha(target) != before: raise ValueError('COPY_DIGEST_MISMATCH')
        after = sha(source)
        if after != before: raise ValueError('SOURCE_CHANGED_DURING_READ')
        records.append(dict(path=rel, bytes=source.stat().st_size, source_sha256_before=before,
                            source_sha256_after=after, target_sha256=sha(target) if target.exists() else None, status=outcome))
        if source.suffix == '.json':
            try: value = json.loads(source.read_bytes())
            except (ValueError, UnicodeError): continue
            def follow(v):
                if isinstance(v, dict):
                    for child in v.values(): follow(child)
                elif isinstance(v, list):
                    for child in v: follow(child)
                elif isinstance(v, str) and v.startswith(('reports/', 'data/v4/', 'config/', 'docs/')):
                    if (SOURCE / v).is_file(): queue.append(v)
            follow(value)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / 'FROZEN_FIXTURE_COPY_RECEIPT.json'; temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(dict(contract_id='R4_R3_FROZEN_FIXTURE_COPY_R1', source_root=str(SOURCE),
        records=records, copied_bytes=total, status='COPIED_NO_AUTHORITY_REBIND_OR_PIT_UPGRADE',
        limits='100 MiB per file, 1 GiB total; exceeding inputs remain explicitly OPEN'), ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    os.replace(temp, path)
    print(json.dumps(dict(records=len(records), copied_bytes=total)))

if __name__ == '__main__': main()
