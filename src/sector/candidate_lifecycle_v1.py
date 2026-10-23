"""Read-only lifecycle reconstruction from an explicitly bound daily candidate."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from .lifecycle_reconstructed_v1 import evaluate_sector, load_parameters


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _read_bound(root, binding):
    root=Path(root).resolve();path=(root/binding['path']).resolve()
    if not path.is_relative_to(root):raise ValueError('SECTOR_LIFECYCLE_OWNER_OUTSIDE_ROOT')
    raw = path.read_bytes()
    if len(raw) != binding.get('bytes', len(raw)) or hashlib.sha256(raw).hexdigest() != binding['sha256']:
        raise ValueError('SECTOR_LIFECYCLE_OWNER_BYTES_OR_SHA_MISMATCH')
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf-8') as stream:
        return [json.loads(line) for line in stream]


def build_candidate_lifecycle(root, candidate, source_root):
    """Compute one immutable, non-PIT research result from candidate Owners."""
    day = candidate['accepted_trade_date']
    published=candidate['published_sessions']
    if published!=sorted(set(published)):
        raise ValueError('SECTOR_LIFECYCLE_CANDIDATE_CALENDAR_INVALID')
    sessions = [s for s in published if s <= day][-5:]
    if len(sessions) != 5 or sessions[-1] != day:
        raise ValueError('SECTOR_LIFECYCLE_CANDIDATE_DATE_OR_WINDOW_INVALID')
    histories, rotations, bindings = {}, {}, {}
    for session in sessions:
        histories[session], rotations[session], bindings[session] = {}, {}, {}
        owners = candidate.get('owners', {}).get(session) or {}
        for domain, target in (('sector', histories), ('rotation', rotations)):
            binding = owners.get(domain)
            if not binding:
                raise ValueError('SECTOR_LIFECYCLE_CANDIDATE_OWNER_MISSING:' + session + ':' + domain)
            bindings[session][domain] = binding
            rows = _read_bound(root, binding)
            target[session] = {r['sector_id']: r for r in rows if r.get('sector_id')}
            if (not rows or len(target[session]) != len(rows)
                    or any(row.get('trade_date',row.get('target_trade_date'))!=session for row in rows)):
                raise ValueError('SECTOR_LIFECYCLE_CANDIDATE_DENOMINATOR_MISMATCH:' + session + ':' + domain)
        if set(histories[session])!=set(rotations[session]):
            raise ValueError('SECTOR_LIFECYCLE_CANDIDATE_DOMAIN_SCOPE_MISMATCH:'+session)
    params, parameter_sha = load_parameters(source_root)
    producer_sha = hashlib.sha256((Path(source_root) / 'src/sector/lifecycle_reconstructed_v1.py').read_bytes()+
        (Path(source_root) / 'src/sector/candidate_lifecycle_v1.py').read_bytes()).hexdigest()
    sector_ids = sorted(histories[day])
    results = []
    for sector_id in sector_ids:
        history = []
        for session in sessions:
            # A new sector has no earlier Owner. Preserve the missing window;
            # the kernel yields UNKNOWN instead of inventing historical members.
            if sector_id not in histories[session]:continue
            row = dict(histories[session][sector_id])
            rotation = rotations[session][sector_id].get('rotation') or {}
            row['rotation_state'] = rotation.get('output_state')
            history.append(row)
        source_bindings = {s: {'sector': bindings[s]['sector'], 'rotation': bindings[s]['rotation']} for s in sessions}
        results.append(evaluate_sector(sector_id, history, candidate['published_sessions'], source_bindings,
                                       params, producer_sha256=producer_sha))
    if len(results) != len(sector_ids) or {r['sector_id'] for r in results} != set(sector_ids):
        raise ValueError('SECTOR_LIFECYCLE_CANDIDATE_OUTPUT_DENOMINATOR_MISMATCH')
    return {
        'contract_id': 'SECTOR_LIFECYCLE_RECONSTRUCTED_AUDIT_R1',
        'T0': day,
        'input_authority': 'EXPLICIT_SUCCESSOR_CANDIDATE',
        'evidence_scope': 'CURRENT_RECONSTRUCTED_RESEARCH_ONLY',
        'AS_RECORDED': False,
        'PIT_ELIGIBLE': False,
        'production_admission': False,
        'session_window': sessions,
        'candidate_digest': hashlib.sha256(canonical(candidate)).hexdigest(),
        'producer_sha256': producer_sha,
        'parameter_sha256': parameter_sha,
        'source_bindings': {s: bindings[s] for s in sessions},
        'items': {r['sector_id']: r for r in results},
    }
