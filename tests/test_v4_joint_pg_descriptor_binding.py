from contextlib import contextmanager

import pytest

from workbench_service import joint_release
from workbench_service.current_v4_context import SourceInvalid


def test_joint_candidate_accepts_immutable_pg_descriptor(monkeypatch, tmp_path):
    metadata = {
        'context': {'accepted_trade_date': '2026-10-09'},
        'sources': {},
        'domain_features': {},
    }
    snapshot = {
        'contract_id': 'V4_PG_RESEARCH_SNAPSHOT_R2',
        'logical_digest': 'a' * 64,
        'content_manifest': {'metadata': metadata},
    }

    @contextmanager
    def verified_read(descriptor):
        assert descriptor is snapshot
        yield object()

    monkeypatch.setattr('workbench_db.v4_snapshot_pg_r2.read', verified_read)
    monkeypatch.setattr(joint_release, 'checked_bytes', lambda root, binding, cache=None: b'<ui>')
    candidate = {
        'contract_id': 'V4_JOINT_RELEASE_V2_PG_CONTENT',
        'snapshot': snapshot,
        'ui_assets': {'index.html': {'path': 'ui/index.html', 'sha256': 'b' * 64}},
        'trade_date': '2026-10-09',
        'operational_release_scope': ['engineering_candidate'],
        'trading': False,
    }

    assert joint_release.context_token_for_snapshot(snapshot) == 'research-v4-pg-candidate-' + 'a' * 64
    assert joint_release.validate(tmp_path, candidate) is metadata


def test_joint_pg_context_token_rejects_missing_logical_digest():
    with pytest.raises(SourceInvalid, match='DIGEST_INVALID'):
        joint_release.context_token_for_snapshot({
            'contract_id': 'V4_PG_RESEARCH_SNAPSHOT_R2',
            'logical_digest': 'short',
        })
