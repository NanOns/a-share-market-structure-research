"""Chunked, byte-preserving PG storage for operational period artifacts."""
import base64
import hashlib
from pathlib import Path

from .v4_forward_pg_r1 import ForwardFactStore, canonical, digest
from .v4_operational_owner_pg_closeout import inline_descriptor, read as read_owner_fact
from workbench_analysis.r43_owner_replay import checked

KEY = 'native_period_artifacts'
CONTRACT = 'V4_OPERATIONAL_PERIOD_ARTIFACT_PG_R1'
DOMAIN = 'period_artifact_chunk'
FOLDER = 'data/v4/operational_period_artifact_pg_r1'
ARTIFACTS = ('input_history', 'verifier')
CHUNK_BYTES = 1024 * 1024


def _fact_key(day, name, source_binding, index):
    return digest(canonical(dict(contract_id=CONTRACT, T0=day, artifact=name,
        source_binding=source_binding, chunk_index=index)))


def prepare(root, candidate):
    """Append exact source bytes in bounded chunks and bind descriptors to Head."""
    root = Path(root).resolve()
    day = candidate['accepted_trade_date']
    from .v4_operational_daily_evidence_pg_v1 import read as read_daily_evidence
    period = read_daily_evidence(root, candidate, 'period_numeric_oracle')
    if KEY in candidate:
        for name in ARTIFACTS:
            attest(root, candidate, name, period[name])
        return dict(contract_id=CONTRACT, T0=day, artifacts=list(ARTIFACTS), reused=True, publication=False)

    store = None
    entries = {}
    for name in ARTIFACTS:
        source_binding = period[name]
        source_path = checked(root, source_binding)
        total_hash = hashlib.sha256()
        total_bytes = 0
        chunks = []
        with source_path.open('rb') as stream:
            index = 0
            while True:
                raw = stream.read(CHUNK_BYTES)
                if not raw:
                    break
                total_hash.update(raw)
                total_bytes += len(raw)
                chunk_sha = digest(raw)
                fact_key = _fact_key(day, name, source_binding, index)
                payload = dict(contract_id=CONTRACT, head_token=fact_key, T0=day,
                    domain=DOMAIN, source_binding=source_binding, PIT_ELIGIBLE=False,
                    AS_RECORDED=False, rows=[dict(chunk_index=index, chunk_bytes=len(raw),
                        chunk_sha256=chunk_sha, data_base64=base64.b64encode(raw).decode('ascii'))])
                if store is None:
                    store = ForwardFactStore(root, FOLDER)
                binding = store.append(DOMAIN, fact_key, payload, migration_timeout_seconds=120)
                descriptor = inline_descriptor(root, binding)
                chunks.append(dict(index=index, bytes=len(raw), sha256=chunk_sha,
                    fact_key=fact_key, descriptor=descriptor))
                index += 1
        if total_bytes != source_binding['bytes'] or total_hash.hexdigest() != source_binding['sha256']:
            raise ValueError('PERIOD_ARTIFACT_SOURCE_BINDING_CHANGED')
        entries[name] = dict(source_binding=source_binding, total_bytes=total_bytes,
            total_sha256=total_hash.hexdigest(), chunks=chunks)
    candidate[KEY] = dict(contract_id=CONTRACT, T0=day, chunk_bytes=CHUNK_BYTES, entries=entries)
    for name in ARTIFACTS:
        attest(root, candidate, name, period[name])
    return dict(contract_id=CONTRACT, T0=day, artifacts=list(ARTIFACTS),
        chunk_bytes=CHUNK_BYTES, publication=False)


def attest(root, candidate, name, source_binding, *, workspace_root=None):
    """Hash the complete PG byte stream without opening its original source file."""
    authority = candidate.get(KEY)
    day = candidate.get('accepted_trade_date')
    if (not isinstance(authority, dict) or authority.get('contract_id') != CONTRACT
            or authority.get('T0') != day or name not in ARTIFACTS):
        raise ValueError('PERIOD_ARTIFACT_PG_AUTHORITY_REQUIRED_NO_FALLBACK')
    entry = authority.get('entries', {}).get(name)
    if not isinstance(entry, dict) or entry.get('source_binding') != source_binding:
        raise ValueError('PERIOD_ARTIFACT_SOURCE_BINDING_MISMATCH')
    chunks = entry.get('chunks')
    if not isinstance(chunks, list) or not chunks or authority.get('chunk_bytes') != CHUNK_BYTES:
        raise ValueError('PERIOD_ARTIFACT_CHUNK_MANIFEST_INVALID')
    hasher = hashlib.sha256()
    total_bytes = 0
    for index, chunk in enumerate(chunks):
        if (chunk.get('index') != index
                or chunk.get('fact_key') != _fact_key(day, name, source_binding, index)):
            raise ValueError('PERIOD_ARTIFACT_CHUNK_ORDER_INVALID')
        rows = read_owner_fact(root, chunk['descriptor'], chunk['fact_key'], day,
            DOMAIN, source_binding, workspace_root=workspace_root)
        if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
            raise ValueError('PERIOD_ARTIFACT_CHUNK_PAYLOAD_INVALID')
        row = rows[0]
        if row.get('chunk_index') != index:
            raise ValueError('PERIOD_ARTIFACT_CHUNK_INDEX_MISMATCH')
        try:
            raw = base64.b64decode(row['data_base64'], validate=True)
        except (KeyError, ValueError) as exc:
            raise ValueError('PERIOD_ARTIFACT_CHUNK_ENCODING_INVALID') from exc
        chunk_sha = digest(raw)
        if (len(raw) != row.get('chunk_bytes') or chunk_sha != row.get('chunk_sha256')
                or len(raw) != chunk.get('bytes') or chunk_sha != chunk.get('sha256')):
            raise ValueError('PERIOD_ARTIFACT_CHUNK_DIGEST_MISMATCH')
        if index < len(chunks) - 1 and len(raw) != authority['chunk_bytes']:
            raise ValueError('PERIOD_ARTIFACT_CHUNK_SIZE_INVALID')
        hasher.update(raw)
        total_bytes += len(raw)
    if (total_bytes != entry.get('total_bytes') or total_bytes != source_binding.get('bytes')
            or hasher.hexdigest() != entry.get('total_sha256')
            or hasher.hexdigest() != source_binding.get('sha256')):
        raise ValueError('PERIOD_ARTIFACT_TOTAL_DIGEST_MISMATCH')
    return dict(name=name, bytes=total_bytes, sha256=hasher.hexdigest(),
        chunks=len(chunks), source_binding=source_binding)
