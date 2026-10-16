from pathlib import Path

import pytest

from scripts import validate_v4_r8_isolated_schema as runner


def test_runner_plan_contains_ordered_full_001_to_037_migration_set():
    files = [path.name for path, _, _ in runner.migrations()]
    assert len(files) == 38  # 001..037, with the two separately versioned 010 files.
    assert files[0] == "001_v4_phase0_foundation.sql"
    assert files[-1] == "037_daily_core_result_binding_r6.sql"
    assert files.index("034_source_package_revision_authority_r2.sql") < files.index(
        "035_source_manifest_contract_r2.sql"
    ) < files.index("036_source_package_fact_provenance_r6.sql") < files.index(
        "037_daily_core_result_binding_r6.sql"
    )


@pytest.mark.parametrize(
    "dsn, expected",
    [
        ("host=127.0.0.1 port=5432 dbname=v4_r8_validation_test", "DATABASE_PORT_BLOCKED_FOR_ISOLATED_DDL"),
        ("host=127.0.0.1 port=55439 dbname=market_research", "ISOLATED_DATABASE_NAME_REQUIRED"),
        ("host=db.example.invalid port=55439 dbname=v4_r8_validation_test", "ISOLATED_DATABASE_MUST_BE_LOOPBACK"),
    ],
)
def test_runner_rejects_nonisolated_targets_before_connect(monkeypatch, dsn, expected):
    monkeypatch.setenv("V4_R8_ISOLATED_PG_ACK", runner.ACK_VALUE)
    monkeypatch.setenv("V4_R8_ISOLATED_PG_DSN", dsn)
    with pytest.raises(RuntimeError, match=expected):
        runner._target_from_environment()


def test_runner_requires_separate_explicit_ack(monkeypatch):
    monkeypatch.delenv("V4_R8_ISOLATED_PG_ACK", raising=False)
    monkeypatch.setenv("V4_R8_ISOLATED_PG_DSN", "host=127.0.0.1 port=55439 dbname=v4_r8_validation_test")
    with pytest.raises(RuntimeError, match="EXPLICIT_ISOLATED_DDL_ACK_REQUIRED"):
        runner._target_from_environment()
