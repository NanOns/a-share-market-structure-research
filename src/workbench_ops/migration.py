from __future__ import annotations

import os
import shutil
from pathlib import Path

from workbench_db import default_database_path
from .backup import BackupService
from .config import ConfigValidationError, OperationsConfig


class DatabaseMigration:
    """Prepare a verified database copy; activation is a separate config step."""
    # MIGRATION_CONTRACT: database migration remains an offline preparation
    # step until PG cutover, config activation and rollback are authorized.
    def __init__(self, root, database_path=None, *, backup: BackupService | None = None):
        self.root=Path(root).resolve();self.database_path=Path(database_path).resolve() if database_path else default_database_path(self.root)
        self.config=OperationsConfig(self.root,self.database_path);self.backup=backup or BackupService(self.root,self.database_path)

    def prepare(self, target_path, *, maintenance_window: bool) -> dict:
        if not maintenance_window: raise ConfigValidationError("MIGRATION_REQUIRES_DRAINED_MAINTENANCE_WINDOW")
        raw_target=Path(target_path)
        raw_target=raw_target if raw_target.is_absolute() else self.root/raw_target
        for item in (raw_target, *raw_target.parents):
            if item.is_symlink(): raise ConfigValidationError("MIGRATION_TARGET_SYMLINK_FORBIDDEN")
            if item == self.root: break
        target=raw_target.resolve()
        if target == self.database_path: raise ConfigValidationError("MIGRATION_TARGET_IS_CURRENT_DATABASE")
        if target.exists(): raise ConfigValidationError("MIGRATION_TARGET_EXISTS")
        if target.parent == target or not target.drive: raise ConfigValidationError("MIGRATION_TARGET_INVALID")
        tdx_root=Path(self.config._tdx_root()).expanduser().resolve()
        if target == self.root:
            raise ConfigValidationError("MIGRATION_TARGET_WORKSPACE_FORBIDDEN")
        if target == tdx_root or tdx_root in target.parents:
            raise ConfigValidationError("MIGRATION_TARGET_TDX_FORBIDDEN")
        protected={self.database_path, Path(str(self.database_path)+".wal"), self.database_path.with_suffix(self.database_path.suffix+".owner.lock")}
        if target in protected: raise ConfigValidationError("MIGRATION_TARGET_PROTECTED")
        # This forces a checkpoint and captures the exact validation criteria.
        backup=self.backup.create_offline_backup(maintenance_window=True)
        temporary=target.with_suffix(target.suffix+".migrating")
        target.parent.mkdir(parents=True,exist_ok=True)
        try:
            shutil.copy2(self.database_path,temporary)
            self.backup._verify_file(temporary,backup["verification"])
            os.replace(temporary,target)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return {"status":"PREPARED","source_database":str(self.database_path),"target_database":str(target),"backup_id":backup["backup_id"],"verification":backup["verification"],"activation":"Apply a new configuration revision and use the supervisor restart workflow; the old database remains untouched until that succeeds."}
