from pathlib import Path

import pytest

from workbench_ops import ConfigValidationError, DatabaseMigration
from test_backup_restore import service


def test_migration_requires_drained_window(tmp_path):
    backup=service(tmp_path)
    with pytest.raises(ConfigValidationError,match="MIGRATION_REQUIRES_DRAINED"):
        DatabaseMigration(tmp_path,backup.database_path).prepare(tmp_path/"other/new.duckdb",maintenance_window=False)


def test_migration_prepares_verified_copy_without_removing_old_database(tmp_path):
    backup=service(tmp_path);source=backup.database_path;target=tmp_path/"other/new.duckdb"
    result=DatabaseMigration(tmp_path,source).prepare(target,maintenance_window=True)
    assert result["status"] == "PREPARED" and source.is_file() and target.is_file()


def test_migration_rejects_configured_tdx_target(tmp_path):
    backup=service(tmp_path);tdx=tmp_path/"immutable-tdx";tdx.mkdir()
    (tmp_path/"config/paths.yaml").write_text(f'tdx:\n  root: "{tdx.as_posix()}"\n',encoding="utf-8")
    with pytest.raises(ConfigValidationError,match="MIGRATION_TARGET_TDX_FORBIDDEN"):
        DatabaseMigration(tmp_path,backup.database_path).prepare(tdx/"market.duckdb",maintenance_window=True)
