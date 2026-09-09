from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from .backup import BackupService
from .config import ConfigValidationError, OperationsConfig
from .migration import DatabaseMigration


class MaintenanceService:
    """Serialized M5 operations for the local workbench service."""

    def __init__(self, root, database_path=None):
        self.root=Path(root).resolve()
        self.database_path=Path(database_path).resolve() if database_path else self.root/"data/database/market_research.duckdb"
        self.config=OperationsConfig(self.root,self.database_path)
        self.backups=BackupService(self.root,self.database_path)
        self.migration=DatabaseMigration(self.root,self.database_path)
        self.lock=threading.Lock()
        self.receipt_path=self.root/"runtime/maintenance_last_receipt.json"

    def status(self):
        with duckdb.connect(str(self.database_path)) as con:
            active=con.execute("SELECT count(*) FROM jobs WHERE status IN ('QUEUED','RUNNING','INTERRUPTED')").fetchone()[0]
            objects=con.execute("SELECT count(*) FROM storage_objects").fetchone()[0]
            backups=con.execute("SELECT count(*) FROM backup_catalog").fetchone()[0]
        last=json.loads(self.receipt_path.read_text('utf-8')) if self.receipt_path.is_file() else None
        return {'service_state':'READY' if not active else 'BUSY','active_job_count':active,'database_path':str(self.database_path),'config_revision':self.config.current()['revision'],'storage_object_count':objects,'backup_count':backups,'last_operation':last}

    def _guard(self, confirmation):
        if confirmation != '我确认进入维护窗口': raise ConfigValidationError('MAINTENANCE_CONFIRMATION_REQUIRED')
        status=self.status()
        if status['active_job_count']: raise ConfigValidationError('MAINTENANCE_ACTIVE_JOBS_EXIST')
        if not self.lock.acquire(blocking=False): raise ConfigValidationError('MAINTENANCE_OPERATION_RUNNING')

    def _record(self, kind, result):
        value={'operation':kind,'completed_at_utc':datetime.now(timezone.utc).isoformat(),'result':result}
        self.receipt_path.parent.mkdir(parents=True,exist_ok=True);tmp=self.receipt_path.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(self.receipt_path)
        return value

    def create_backup(self, confirmation):
        self._guard(confirmation)
        try:return self._record('一致性备份',self.backups.create_offline_backup(maintenance_window=True))
        finally:self.lock.release()

    def restore_drill(self, backup_id, confirmation):
        self._guard(confirmation)
        try:
            root=self.root/'runtime/restore_drills'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
            return self._record('恢复演练',self.backups.restore_drill(backup_id,drill_root=root))
        finally:self.lock.release()

    def prepare_migration(self, target_path, confirmation):
        self._guard(confirmation)
        try:return self._record('迁移准备',self.migration.prepare(target_path,maintenance_window=True))
        finally:self.lock.release()
