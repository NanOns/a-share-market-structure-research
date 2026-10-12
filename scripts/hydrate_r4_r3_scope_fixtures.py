"""Copy missing frozen V4 fixture inputs only; original and existing bytes stay put."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import argparse
import uuid
from collections import deque
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('G:/codex work/大A交易')
OUT = ROOT / 'docs/audits/r4_r3_scope_20261011'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while data := stream.read(64 * 1024): h.update(data)
    return h.hexdigest()

def main(target_root=ROOT,seed_only=False,selected_seeds=None):
    target_root=Path(target_root).resolve()
    if target_root != ROOT and not target_root.is_relative_to(Path('G:/codex_tmp').resolve()):
        raise ValueError('FIXTURE_TARGET_NOT_G_ISOLATED')
    seed = ['reports/r28', 'reports/r29', 'reports/r30', 'reports/r30r1', 'reports/r31', 'reports/r31r1', 'reports/r31r2', 'reports/v4_09', 'reports/v4_12',
            'reports/v4_12_runtime_r1', 'reports/v4_12_runtime_r11', 'reports/v4_12_runtime_r12',
            'reports/dm01/a01_r2/20261001T033251758661Z/normalized_schema_v2_1']
    if selected_seeds:seed=selected_seeds
    # Visit every direct seed before following transitive source references.
    queue = deque()
    for name in seed:
        seed_path=SOURCE/name
        files=[seed_path] if seed_path.is_file() else seed_path.rglob('*')
        queue.extend(p.relative_to(SOURCE).as_posix() for p in files if p.is_file())
    visited = set(); records = []; total = 0
    while queue:
        rel = queue.popleft()
        if rel in visited: continue
        visited.add(rel)
        source = (SOURCE / rel).resolve(); target = (target_root / rel).resolve()
        if not source.is_relative_to(SOURCE.resolve()) or not target.is_relative_to(target_root):
            raise ValueError('FIXTURE_PATH_ESCAPE')
        if not source.is_file(): continue
        before = sha(source)
        if target.exists():
            outcome = 'PRESENT_IDENTICAL' if sha(target) == before else 'PRESENT_DIFFERENT_PRESERVED'
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary=target.with_name(target.name+'.codex-copy-'+uuid.uuid4().hex+'.tmp')
            try:
                with temporary.open('xb') as dest, source.open('rb') as origin: shutil.copyfileobj(origin, dest)
                if sha(temporary)!=before:raise ValueError('COPY_DIGEST_MISMATCH')
                # Atomic publication refuses to replace a concurrently created
                # input. The temporary path and destination are both on G:.
                try:os.link(temporary,target)
                except FileExistsError:
                    if sha(target)!=before:raise ValueError('CONCURRENT_INPUT_CONTENT_CONFLICT')
            finally:
                if temporary.exists():temporary.unlink()
            total += source.stat().st_size
            outcome = 'COPIED_MISSING_ONLY'
            if sha(target) != before: raise ValueError('COPY_DIGEST_MISMATCH')
        after = sha(source)
        if after != before: raise ValueError('SOURCE_CHANGED_DURING_READ')
        records.append(dict(path=rel, bytes=source.stat().st_size, source_sha256_before=before,
                            source_sha256_after=after, target_sha256=sha(target) if target.exists() else None, status=outcome))
        if source.suffix == '.json' and not seed_only:
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
    path = OUT / ('FROZEN_FIXTURE_COPY_RECEIPT_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '.json'); temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(dict(contract_id='R4_R3_FROZEN_FIXTURE_COPY_R1', source_root=str(SOURCE),
        records=records, target_root=str(target_root),copied_bytes=total, status='COPIED_NO_AUTHORITY_REBIND_OR_PIT_UPGRADE',
        limits='No imposed copy-size limit: user authorization; G-only storage, exact hashes and existing-input preservation enforced'), ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    os.replace(temp, path)
    print(json.dumps(dict(records=len(records), copied_bytes=total)))

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--target',type=Path,default=ROOT);parser.add_argument('--seed-only',action='store_true');parser.add_argument('--seed',action='append')
    args=parser.parse_args();main(args.target,args.seed_only,args.seed)
