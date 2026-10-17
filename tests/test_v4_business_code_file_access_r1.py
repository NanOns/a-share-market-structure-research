from scripts.audit_v4_business_file_access_r1 import classify, filesystem_absolute
from common.disposable_paths import disposable_bases


def test_business_owner_file_reads_are_database_migration_findings():
    category, _ = classify(
        "src/workbench_analysis/current_authority.py",
        "Path.read_bytes",
        "checked(root, owner_binding)",
        None,
        "READ",
    )
    assert category == "BUSINESS_OWNER_FILE_READ_REQUIRES_DB"


def test_business_artifact_file_reads_and_writes_require_database():
    read_category, _ = classify(
        "src/workbench_analysis/publisher.py", "read_bytes", "root / 'data/v4/result.json'", None, "READ"
    )
    write_category, _ = classify(
        "src/workbench_analysis/publisher.py", "write_bytes", "root / 'reports/result.json'", None, "WRITE"
    )
    assert read_category == "BUSINESS_FILE_READ_REQUIRES_DB"
    assert write_category == "BUSINESS_FILE_WRITE_REQUIRES_DB"


def test_only_filesystem_absolute_paths_are_classified_as_absolute():
    assert filesystem_absolute(chr(68) + ":/new_tdx")
    assert filesystem_absolute("/var/lib/v4/state.json")
    assert not filesystem_absolute(r"\/")
    assert not filesystem_absolute("/api/v4/current/summary")
    assert not filesystem_absolute("relative/config/invariants.json")


def test_config_path_is_reviewed_as_configuration_not_a_business_data_exemption():
    category, _ = classify(
        "src/workbench_analysis/replay.py", "Path.read_bytes", "root / 'config/v4_07_parameter_set_v1.json'", None, "READ"
    )
    assert category == "CONFIG_CLASS_INPUT_REVIEW"


def test_external_market_data_file_read_requires_database_ingestion():
    category, _ = classify(
        "src/workbench_input/pipeline.py", "Path.read_bytes", "tdx_root / 'vipdoc/lday/SH600000.day'", None, "READ"
    )
    assert category == "EXTERNAL_BUSINESS_DATA_FILE_READ_REQUIRES_DB"


def test_disposable_root_comes_from_explicit_environment_configuration(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_DISPOSABLE_TEMP_ROOT", str(tmp_path))
    monkeypatch.delenv("TMPDIR", raising=False)
    assert disposable_bases() == (tmp_path.resolve(),)


def test_disposable_root_fails_closed_without_environment_configuration(monkeypatch):
    monkeypatch.delenv("CODEX_DISPOSABLE_TEMP_ROOT", raising=False)
    monkeypatch.delenv("TMPDIR", raising=False)
    try:
        disposable_bases()
    except ValueError as exc:
        assert str(exc) == "DISPOSABLE_TEMP_ROOT_ENV_REQUIRED"
    else:
        raise AssertionError("DISPOSABLE_TEMP_ROOT_MUST_BE_EXPLICIT")
