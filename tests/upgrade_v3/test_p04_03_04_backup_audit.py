from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_daily_preview_builder_has_no_automatic_full_backup_call():
    source = (ROOT / "scripts/build_m8_m9_preview.py").read_text(encoding="utf-8")

    assert "BackupService" not in source
    assert "create_history_backup" not in source
    assert '"backup_policy": "MANUAL_ONLY"' in source


def test_manual_recovery_and_migration_paths_remain_explicit_maintenance_operations():
    recovery = (ROOT / "scripts/run_m7b_07_recovery.py").read_text(encoding="utf-8")
    migration = (ROOT / "scripts/apply_m7b_01.py").read_text(encoding="utf-8")
    maintenance = (ROOT / "src/workbench_ops/maintenance.py").read_text(encoding="utf-8")

    assert "create_history_backup(maintenance_window=True)" in recovery
    assert "create_offline_backup(maintenance_window=True)" in migration
    assert "MAINTENANCE_CONFIRMATION_REQUIRED" in maintenance
    assert "MAINTENANCE_ACTIVE_JOBS_EXIST" in maintenance
