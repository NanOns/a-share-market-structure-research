"""The real current V4 governance file must survive scope selection."""
from scripts import forward_final_v4_scope as scope


def test_v4_uppercase_contract_governance_is_in_execution_scope(monkeypatch):
    monkeypatch.setattr(scope, 'write', lambda *args, **kwargs: None)
    selected = scope.build()
    assert 'tests/test_r17a_historical_governance.py' in selected
    assert 'tests/v4_joint/test_execution_scope_coverage.py' in selected
    assert not any(path.startswith(('tests/r4_01/', 'tests/r4_01a/',
                                    'tests/r4_repair/', 'tests/upgrade_v3/')) for path in selected)
