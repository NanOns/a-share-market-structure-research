from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from .config import ConfigValidationError, OperationsConfig


def _dump(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


class BackupService:
    """Offline DuckDB backup and restore-drill service.

    The caller must drain the service first.  This deliberately refuses the
    convenient-but-unsafe hot file copy pattern.
    """
    def __init__(self, root, database_path=None):
        self.root=Path(root).resolve()
        self.database_path=Path(database_path).resolve() if database_path else self.root/"data/database/market_research.duckdb"
        self.config=OperationsConfig(self.root,self.database_path)

    def create_offline_backup(self, *, maintenance_window: bool) -> dict:
        if not maintenance_window:
            raise ConfigValidationError("BACKUP_REQUIRES_DRAINED_MAINTENANCE_WINDOW")
        if not self.database_path.is_file():
            raise ConfigValidationError("BACKUP_DATABASE_MISSING")
        backup_root=Path(self.config.validate(self.config.current()["config"])["resolved_backup_root"])
        backup_root.mkdir(parents=True,exist_ok=True)
        # A full connection is opened only after the operator has drained all
        # service connections. CHECKPOINT produces a self-contained file.
        with duckdb.connect(str(self.database_path)) as con:
            con.execute("CHECKPOINT")
            verification=self._verify(con)
        digest=hashlib.sha256(self.database_path.read_bytes()).hexdigest()
        backup_id="backup-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+digest[:12]
        final=backup_root/(backup_id+".duckdb"); temporary=final.with_name(final.name+"."+uuid.uuid4().hex+".tmp")
        try:
            shutil.copy2(self.database_path,temporary)
            self._verify_file(temporary, verification)
            os.replace(temporary,final)
        finally:
            temporary.unlink(missing_ok=True)
        record={"backup_id":backup_id,"path":str(final),"sha256":digest,"created_at_utc":datetime.now(timezone.utc).isoformat(),"source_database":str(self.database_path),"verification":verification,"state":"VERIFIED"}
        with duckdb.connect(str(self.database_path)) as con:
            con.execute("INSERT INTO backup_catalog VALUES (?, ?) ON CONFLICT DO NOTHING",[backup_id,_dump(record)])
        return record

    def restore_drill(self, backup_id: str, *, drill_root: str | Path) -> dict:
        with duckdb.connect(str(self.database_path)) as con:
            row=con.execute("SELECT payload_json FROM backup_catalog WHERE backup_id=?",[backup_id]).fetchone()
        if not row: raise ConfigValidationError("BACKUP_NOT_REGISTERED")
        record=json.loads(row[0]); source=Path(record["path"]).resolve(); raw_root=Path(drill_root)
        for item in (raw_root, *raw_root.parents):
            if item.is_symlink(): raise ConfigValidationError("RESTORE_DRILL_SYMLINK_FORBIDDEN")
        target_root=raw_root.resolve(); tdx_root=Path(self.config._tdx_root()).expanduser().resolve()
        if target_root==tdx_root or tdx_root in target_root.parents: raise ConfigValidationError("RESTORE_DRILL_TDX_FORBIDDEN")
        if target_root==self.root: raise ConfigValidationError("RESTORE_DRILL_WORKSPACE_ROOT_FORBIDDEN")
        target=target_root/(backup_id+".duckdb")
        if not source.is_file(): raise ConfigValidationError("BACKUP_FILE_MISSING")
        if target.exists(): raise ConfigValidationError("RESTORE_DRILL_TARGET_EXISTS")
        target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,target)
        self._verify_file(target,record["verification"])
        return {"backup_id":backup_id,"restore_drill_path":str(target),"status":"PASS","verification":record["verification"]}

    @staticmethod
    def _verify(con):
        tables={x[0] for x in con.execute("SHOW TABLES").fetchall()}
        required={"publication_heads","queue_memberships","membership_entries","outcomes"}
        missing=sorted(required-tables)
        if missing: raise ConfigValidationError("BACKUP_REQUIRED_TABLES_MISSING:"+",".join(missing))
        head_count=con.execute("SELECT count(*) FROM publication_heads").fetchone()[0]
        queue_count=con.execute("SELECT count(*) FROM queue_memberships").fetchone()[0]
        member_count=con.execute("SELECT count(*) FROM membership_entries").fetchone()[0]
        forward_count=con.execute("SELECT count(*) FROM outcomes").fetchone()[0]
        return {"publication_heads":head_count,"queue_memberships":queue_count,"membership_entries":member_count,"outcomes":forward_count}

    def _verify_file(self,path, expected):
        with duckdb.connect(str(path),read_only=True) as con:
            actual=self._verify(con)
        if actual != expected: raise ConfigValidationError("BACKUP_VERIFICATION_MISMATCH")
