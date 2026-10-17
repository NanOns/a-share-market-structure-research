import hashlib

import pytest

from workbench_db import v4_operational_period_artifact_pg_v1 as artifact


def _binding(root, path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return dict(path=path.relative_to(root).as_posix(),
        sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def test_prepare_chunks_exact_artifact_bytes_and_pg_attests_without_source_open(tmp_path, monkeypatch):
    from workbench_db import v4_operational_daily_evidence_pg_v1 as evidence

    monkeypatch.setattr(artifact, 'CHUNK_BYTES', 3)
    raw_history = b'abcdefgh'
    raw_verifier = b'print(1)'
    history = _binding(tmp_path, tmp_path / 'history.jsonl.gz', raw_history)
    verifier = _binding(tmp_path, tmp_path / 'verifier.py', raw_verifier)
    monkeypatch.setattr(evidence, 'read', lambda *a, **k: {
        'input_history': history, 'verifier': verifier,
    })
    stored = {}

    class Store:
        def __init__(self, root, folder):
            assert folder == artifact.FOLDER

        def append(self, domain, fact_key, payload, *, migration_timeout_seconds):
            assert domain == artifact.DOMAIN and migration_timeout_seconds == 120
            stored[fact_key] = payload
            return dict(path=f'{domain}/{fact_key}.pg.json', fact_key=fact_key)

    monkeypatch.setattr(artifact, 'ForwardFactStore', Store)
    monkeypatch.setattr(artifact, 'inline_descriptor', lambda root, binding: binding)
    monkeypatch.setattr(artifact, 'read_owner_fact',
        lambda root, descriptor, fact_key, *args, **kwargs: stored[fact_key]['rows'])
    candidate = {'accepted_trade_date': '2026-10-17'}
    receipt = artifact.prepare(tmp_path, candidate)

    assert receipt['publication'] is False
    assert len(candidate[artifact.KEY]['entries']['input_history']['chunks']) == 3
    assert len(candidate[artifact.KEY]['entries']['verifier']['chunks']) == 3
    monkeypatch.setattr(artifact, 'checked', lambda *_: pytest.fail('PG attestation opened local source'))
    for name, source in (('input_history', history), ('verifier', verifier)):
        attestation = artifact.attest(tmp_path, candidate, name, source)
        assert attestation['sha256'] == source['sha256']
        assert attestation['bytes'] == source['bytes']


def test_period_artifact_reader_rejects_binding_substitution(tmp_path, monkeypatch):
    source = {'path': 'history.jsonl.gz', 'sha256': 'a' * 64, 'bytes': 8}
    candidate = {
        'accepted_trade_date': '2026-10-17',
        artifact.KEY: {
            'contract_id': artifact.CONTRACT,
            'T0': '2026-10-17',
            'chunk_bytes': artifact.CHUNK_BYTES,
            'entries': {'input_history': {'source_binding': source, 'chunks': []}},
        },
    }
    monkeypatch.setattr(artifact, 'read_owner_fact', lambda *a, **k: pytest.fail('unexpected PG read'))
    with pytest.raises(ValueError, match='PERIOD_ARTIFACT_SOURCE_BINDING_MISMATCH'):
        artifact.attest(tmp_path, candidate, 'input_history', {'path': 'other.gz', 'sha256': 'b' * 64, 'bytes': 8})
