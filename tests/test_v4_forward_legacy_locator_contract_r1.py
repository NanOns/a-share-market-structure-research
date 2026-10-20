import pytest

from workbench_db import v4_forward_pg_r1


def test_legacy_forward_locator_accepts_only_frozen_schema_shapes():
    assert v4_forward_pg_r1.is_legacy_forward_schema_locator('v4_forward_0123456789abcdef')
    assert v4_forward_pg_r1.is_legacy_forward_schema_locator('v4_r8_forward_0123456789abcdef')
    for value in (
        'v4', 'v4_forward_test', 'v4_forward_0123456789abcdef_extra',
        'v4_forward_0123456789ABCDEf', 'v4_jobs_0123456789abcdef', None,
    ):
        assert not v4_forward_pg_r1.is_legacy_forward_schema_locator(value)


def test_invalid_legacy_locator_fails_before_database_access(monkeypatch):
    def unexpected_connection(*_args, **_kwargs):
        raise AssertionError('invalid locator must be rejected before connecting')

    monkeypatch.setattr(v4_forward_pg_r1, 'connection', unexpected_connection)
    with pytest.raises(ValueError, match='FORWARD_LEGACY_EXACT_LOCATOR_INVALID'):
        v4_forward_pg_r1.resolve_migrated_legacy_fact(
            'v4_forward_test', 'candidate', 'key', 'a' * 64)
