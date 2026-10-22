from __future__ import annotations

import hashlib
from pathlib import Path

from workbench_analysis.d0_source_seal_r2 import _archive_source_ref, archive_immutable_bytes


def test_archive_is_content_addressed_and_survives_source_change(tmp_path):
    raw = b'producer-version-one\n'
    path, digest, size = archive_immutable_bytes(tmp_path, 'producer', raw)
    source = Path(tmp_path) / 'mutable.py'
    source.write_bytes(raw)
    bound = _archive_source_ref(tmp_path, {
        'source_role': 'producer', 'source_path': str(source), 'source_sha256': digest,
        'source_bytes': size, 'owner_contract_id': 'D0-R2', 'owner_version_token': '2.1.0',
    })
    source.write_bytes(b'producer-version-two\n')
    archive = Path(path)
    assert bound['source_path'] == str(archive)
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == digest
    assert archive.read_bytes() == raw
    assert digest in bound['source_path']


def test_archive_rejects_digest_path_collision(tmp_path):
    raw = b'original-bytes'
    path, _, _ = archive_immutable_bytes(tmp_path, 'producer', raw)
    Path(path).write_bytes(b'corrupted-bytes')
    try:
        archive_immutable_bytes(tmp_path, 'producer', raw)
    except ValueError as exc:
        assert 'D0_IMMUTABLE_ARCHIVE_COLLISION' in str(exc)
    else:
        raise AssertionError('corrupted content-addressed bytes must fail closed')
