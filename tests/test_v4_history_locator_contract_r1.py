from workbench_db.v4_history_pg_r1 import valid_history_schema_locator


def test_history_locator_accepts_canonical_and_frozen_legacy_names_only():
    assert valid_history_schema_locator('v4')
    assert valid_history_schema_locator('v4_history_0123456789abcdef')
    assert not valid_history_schema_locator('v4_forward_0123456789abcdef')
    assert not valid_history_schema_locator('v4_history_not-a-digest')
    assert not valid_history_schema_locator(None)
