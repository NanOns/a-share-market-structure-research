"""R4.2.1 corrected candidate store. This module cannot publish a production head."""
from pathlib import Path
import hashlib
import json
import os
import re

CONTRACT_ID = 'R421_CORRECTED_SCOPED_SUCCESSOR_V1'
ALLOWED = {'OFFICIAL_TDX_RAW_CURRENT_CANONICAL_SUBSET', 'CORRECTED_CORE_PROFILE'}
ROOT = Path(__file__).resolve().parents[2]

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf8')

def atomic(path, raw):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.staging')
    with temp.open('wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    os.replace(temp, path)

def validate(candidate):
    if candidate.get('contract_id') != CONTRACT_ID:
        raise ValueError('WRONG_SCOPED_CONTRACT')
    if candidate.get('AS_RECORDED') is not False or candidate.get('source_mode') != 'RECONSTRUCTED_CORRECTED':
        raise ValueError('CORRECTED_LINEAGE_REQUIRED')
    if not set(candidate.get('domains', [])) or not set(candidate['domains']) <= ALLOWED:
        raise ValueError('UNAPPROVED_DOMAIN')
    if candidate.get('production_permission') is not False:
        raise ValueError('PRODUCTION_PERMISSION_FORBIDDEN')
    if candidate.get('primary_taxonomy') != 'TDX_INDUSTRY_CONCEPT':
        raise ValueError('PRIMARY_TAXONOMY_REQUIRED')
    def bindings(value):
        if isinstance(value,dict):
            if 'path' in value and 'sha256' in value:
                path=(ROOT/value['path']).resolve()
                if not path.is_relative_to(ROOT):raise ValueError('SCOPED_BINDING_OUTSIDE_PROJECT')
                if not path.is_file() or sha(path)!=value['sha256']:
                    raise ValueError('SCOPED_BINDING_DIGEST_MISMATCH')
            for child in value.values():bindings(child)
        elif isinstance(value,list):
            for child in value:bindings(child)
    bindings(candidate)

def candidate_cas(store, candidate, expected_sha, *, inject_failure=False):
    """CAS an isolated candidate pointer; fixed name cannot address production pointers."""
    store = Path(store).resolve()
    if store.drive.upper() != 'E:':
        raise ValueError('ISOLATED_E_DRIVE_STORE_REQUIRED')
    validate(candidate)
    pointer = store / 'SCOPED_CANDIDATE_POINTER.json'
    raw = canonical(candidate)
    lock = store / 'SCOPED_CANDIDATE.lock'
    store.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.close(fd)
        actual = sha(pointer) if pointer.exists() else None
        if actual != expected_sha:
            raise ValueError('STALE_CANDIDATE_CAS')
        if pointer.exists() and pointer.read_bytes() == raw:
            return {'status': 'NOOP_IDENTICAL', 'sha256': sha(pointer)}
        if pointer.exists():
            archive = store / 'predecessors' / (actual + '.json')
            if archive.exists() and archive.read_bytes() != pointer.read_bytes():
                raise ValueError('PREDECESSOR_COLLISION')
            atomic(archive, pointer.read_bytes())
        if inject_failure:
            raise ValueError('INJECTED_BEFORE_REPLACE')
        atomic(pointer, raw)
        return {'status': 'STAGING_POINTER_UPDATED', 'sha256': sha(pointer), 'predecessor_sha256': actual}
    finally:
        lock.unlink()

def rollback(store, current_sha, predecessor_sha):
    store = Path(store).resolve()
    if store.drive.upper() != 'E:':
        raise ValueError('ISOLATED_E_DRIVE_STORE_REQUIRED')
    if not all(isinstance(x, str) and re.fullmatch(r'[0-9a-f]{64}', x) for x in (current_sha, predecessor_sha)):
        raise ValueError('ROLLBACK_EXACT_PREDECESSOR_REQUIRED')
    pointer = store / 'SCOPED_CANDIDATE_POINTER.json'
    predecessor = store / 'predecessors' / (predecessor_sha + '.json')
    lock = store / 'SCOPED_CANDIDATE.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.close(fd)
        if not pointer.is_file() or not predecessor.is_file() or sha(pointer) != current_sha or sha(predecessor) != predecessor_sha:
            raise ValueError('ROLLBACK_EXACT_PREDECESSOR_REQUIRED')
        validate(json.loads(predecessor.read_bytes()))
        atomic(pointer, predecessor.read_bytes())
        return {'status': 'EXACT_PREDECESSOR_RESTORED', 'sha256': sha(pointer)}
    finally:
        lock.unlink()
