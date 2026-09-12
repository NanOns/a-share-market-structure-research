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

    def create_history_backup(self, *, maintenance_window: bool) -> dict:
        """Create a DB backup plus every active, DB-referenced external object.

        The ordinary M5 method remains intentionally unchanged for backwards
        compatibility.  M7B uses this stricter manifest because a DuckDB copy
        without its immutable Parquet objects is not recoverable.
        """
        if not maintenance_window:
            raise ConfigValidationError("BACKUP_REQUIRES_DRAINED_MAINTENANCE_WINDOW")
        if not self.database_path.is_file():
            raise ConfigValidationError("BACKUP_DATABASE_MISSING")
        backup_root=Path(self.config.validate(self.config.current()["config"])["resolved_backup_root"])
        backup_root.mkdir(parents=True,exist_ok=True)
        with duckdb.connect(str(self.database_path)) as con:
            con.execute("CHECKPOINT")
            verification=self._verify(con)
            object_rows=con.execute("SELECT storage_object_id,payload_json FROM storage_objects").fetchall() if self._has_table(con,"storage_objects") else []
            referenced_ids=self._referenced_object_ids(con,object_rows)
        database_sha=hashlib.sha256(self.database_path.read_bytes()).hexdigest()
        backup_id="backup-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+database_sha[:12]
        final=backup_root/(backup_id+".duckdb")
        object_root=backup_root/(backup_id+".objects")
        manifest_path=backup_root/(backup_id+".manifest.json")
        temp_db=final.with_name(final.name+"."+uuid.uuid4().hex+".tmp")
        temp_object_root=object_root.with_name(object_root.name+"."+uuid.uuid4().hex+".tmp")
        temp_manifest=manifest_path.with_name(manifest_path.name+"."+uuid.uuid4().hex+".tmp")
        objects=[]
        try:
            shutil.copy2(self.database_path,temp_db)
            self._verify_file(temp_db,verification)
            for object_id,raw in object_rows:
                item=json.loads(raw)
                if item.get("state") != "ACTIVE" or object_id not in referenced_ids:
                    continue
                source=self._validate_external_object(item.get("path"))
                if not source.is_file():
                    raise ConfigValidationError("BACKUP_REFERENCED_OBJECT_MISSING:"+str(object_id))
                expected=item.get("physical_sha256")
                actual=hashlib.sha256(source.read_bytes()).hexdigest()
                if expected and expected != actual:
                    raise ConfigValidationError("BACKUP_REFERENCED_OBJECT_HASH_MISMATCH:"+str(object_id))
                relative=item.get("relative_path") or str(source.relative_to(self.root)).replace("\\","/")
                relative_path=Path(relative)
                if relative_path.is_absolute() or ".." in relative_path.parts:
                    raise ConfigValidationError("BACKUP_OBJECT_RELATIVE_PATH_INVALID:"+str(object_id))
                target=temp_object_root/relative_path
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source,target)
                copied=hashlib.sha256(target.read_bytes()).hexdigest()
                if copied != actual:
                    raise ConfigValidationError("BACKUP_OBJECT_COPY_HASH_MISMATCH:"+str(object_id))
                objects.append({"storage_object_id":object_id,"source_path":str(source),"relative_path":str(relative_path).replace("\\","/"),"sha256":actual,"size_bytes":source.stat().st_size,"storage_kind":item.get("storage_kind") or item.get("kind"),"row_count":item.get("row_count")})
            temp_object_root.mkdir(parents=True,exist_ok=True)
            manifest={"contract_version":"history-backup-manifest-v1.0","backup_id":backup_id,"created_at_utc":datetime.now(timezone.utc).isoformat(),"database":{"path":str(final),"sha256":database_sha,"verification":verification},"objects_root":str(object_root),"objects":sorted(objects,key=lambda x:x["storage_object_id"])}
            manifest["manifest_sha256"]=hashlib.sha256(_dump(manifest).encode()).hexdigest()
            temp_manifest.write_text(_dump(manifest),encoding="utf-8")
            os.replace(temp_db,final)
            os.replace(temp_object_root,object_root)
            os.replace(temp_manifest,manifest_path)
        finally:
            temp_db.unlink(missing_ok=True)
            temp_manifest.unlink(missing_ok=True)
            if temp_object_root.exists(): shutil.rmtree(temp_object_root)
        record={"backup_id":backup_id,"path":str(final),"sha256":database_sha,"manifest_path":str(manifest_path),"objects_root":str(object_root),"object_count":len(objects),"created_at_utc":datetime.now(timezone.utc).isoformat(),"source_database":str(self.database_path),"verification":verification,"state":"VERIFIED"}
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
        if hashlib.sha256(target.read_bytes()).hexdigest() != record["sha256"]:
            target.unlink(missing_ok=True)
            raise ConfigValidationError("RESTORE_DATABASE_HASH_MISMATCH")
        self._verify_file(target,record["verification"])
        result={"backup_id":backup_id,"restore_drill_path":str(target),"status":"PASS","verification":record["verification"]}
        manifest_path=Path(record["manifest_path"]).resolve() if record.get("manifest_path") else None
        if manifest_path and manifest_path.is_file():
            manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
            expected_manifest_hash=manifest.get("manifest_sha256")
            actual_manifest=dict(manifest);actual_manifest.pop("manifest_sha256",None)
            if expected_manifest_hash != hashlib.sha256(_dump(actual_manifest).encode()).hexdigest():
                raise ConfigValidationError("RESTORE_MANIFEST_HASH_MISMATCH")
            objects_target=target_root/"objects"
            restored=[]
            for item in manifest.get("objects",[]):
                relative=Path(item["relative_path"])
                if relative.is_absolute() or ".." in relative.parts:
                    raise ConfigValidationError("RESTORE_OBJECT_RELATIVE_PATH_INVALID")
                source=Path(record["objects_root"]).resolve()/relative
                destination=objects_target/relative
                if not source.is_file(): raise ConfigValidationError("RESTORE_OBJECT_MISSING:"+item["storage_object_id"])
                destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)
                actual=hashlib.sha256(destination.read_bytes()).hexdigest()
                if actual != item["sha256"]: raise ConfigValidationError("RESTORE_OBJECT_HASH_MISMATCH:"+item["storage_object_id"])
                if item.get("storage_kind") == "PARQUET":
                    try:
                        with duckdb.connect() as check:
                            rows=int(check.execute("select count(*) from read_parquet(?)",[str(destination)]).fetchone()[0])
                    except Exception as exc:
                        raise ConfigValidationError("RESTORE_PARQUET_QUERY_FAILED:"+item["storage_object_id"]) from exc
                    if item.get("row_count") is not None and rows != int(item["row_count"]):
                        raise ConfigValidationError("RESTORE_PARQUET_ROW_COUNT_MISMATCH:"+item["storage_object_id"])
                restored.append({"storage_object_id":item["storage_object_id"],"path":str(destination),"sha256":actual,"size_bytes":destination.stat().st_size})
            result.update({"manifest_path":str(manifest_path),"manifest_sha256":expected_manifest_hash,"restored_objects":restored,"object_count":len(restored)})
        report=target_root/"restore_report.json"
        temporary=report.with_name(report.name+"."+uuid.uuid4().hex+".tmp")
        temporary.write_text(_dump({"contract_version":"history-restore-report-v1.0","completed_at_utc":datetime.now(timezone.utc).isoformat(),**result}),encoding="utf-8")
        os.replace(temporary,report)
        result["restore_report_path"]=str(report)
        return result

    def audit_catalog_physical_chain(self) -> dict:
        """Read-only reconciliation of catalog records and backup files.

        Stored absolute paths may refer to an older checkout spelling.  The
        audit never rewrites them; it uses the recorded basename to locate the
        current managed backup root and reports both facts separately.
        """
        backup_root=Path(self.config.validate(self.config.current()["config"])["resolved_backup_root"]).resolve()
        physical_files={path.name:path for path in backup_root.iterdir() if path.is_file()} if backup_root.is_dir() else {}
        physical_dirs={path.name:path for path in backup_root.iterdir() if path.is_dir()} if backup_root.is_dir() else {}
        with duckdb.connect(str(self.database_path),read_only=True) as con:
            rows=con.execute("SELECT backup_id,payload_json FROM backup_catalog ORDER BY backup_id").fetchall()
        records=[]; catalog_db_names=set(); catalog_manifest_names=set(); catalog_object_names=set()
        for backup_id, raw in rows:
            value=json.loads(raw)
            database_name=Path(str(value.get("path", ""))).name
            manifest_name=Path(str(value.get("manifest_path", ""))).name if value.get("manifest_path") else None
            object_name=Path(str(value.get("objects_root", ""))).name if value.get("objects_root") else None
            if database_name: catalog_db_names.add(database_name)
            if manifest_name: catalog_manifest_names.add(manifest_name)
            if object_name: catalog_object_names.add(object_name)
            database_path=physical_files.get(database_name)
            database_status="MISSING"
            database_sha256=None
            if database_path:
                database_sha256=self._sha256_file(database_path)
                database_status="PASS" if database_sha256==value.get("sha256") else "HASH_MISMATCH"
            manifest_status="NOT_EXPECTED"
            manifest_hash=None
            object_status="NOT_EXPECTED"
            object_results=[]
            manifest_path=physical_files.get(manifest_name) if manifest_name else None
            if manifest_name:
                manifest_status="MISSING"
                if manifest_path:
                    manifest_hash=self._sha256_file(manifest_path)
                    try:
                        manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
                        unsigned=dict(manifest); claimed=unsigned.pop("manifest_sha256",None)
                        identity_hash=hashlib.sha256(_dump(unsigned).encode()).hexdigest()
                        manifest_status="PASS" if (
                            manifest.get("backup_id")==backup_id
                            and claimed==identity_hash
                            and manifest.get("database",{}).get("sha256")==value.get("sha256")
                        ) else "IDENTITY_OR_DATABASE_MISMATCH"
                        object_name=Path(str(manifest.get("objects_root",object_name or ""))).name
                        if object_name: catalog_object_names.add(object_name)
                        object_root=physical_dirs.get(object_name) if object_name else None
                        object_status="MISSING"
                        if object_root:
                            object_status="PASS"
                            for item in manifest.get("objects",[]):
                                relative=Path(str(item.get("relative_path", "")))
                                if relative.is_absolute() or ".." in relative.parts:
                                    item_status="INVALID_RELATIVE_PATH"
                                    actual_path=None
                                else:
                                    actual_path=object_root.joinpath(*relative.parts)
                                    if not actual_path.is_file(): item_status="MISSING"
                                    elif actual_path.stat().st_size!=int(item.get("size_bytes",-1)):
                                        item_status="SIZE_MISMATCH"
                                    elif self._sha256_file(actual_path)!=item.get("sha256"):
                                        item_status="HASH_MISMATCH"
                                    else: item_status="PASS"
                                object_results.append({"storage_object_id":item.get("storage_object_id"),"path":str(actual_path) if actual_path else None,"status":item_status})
                            if any(item["status"]!="PASS" for item in object_results): object_status="OBJECT_MISMATCH"
                    except (OSError, json.JSONDecodeError, TypeError, ValueError, KeyError):
                        manifest_status="UNREADABLE"
            chain_status="PASS" if database_status=="PASS" and manifest_status in ("PASS","NOT_EXPECTED") and object_status in ("PASS","NOT_EXPECTED") else "INCOMPLETE"
            records.append({
                "backup_id":backup_id,
                "created_at_utc":value.get("created_at_utc"),
                "catalog_database_path":value.get("path"),
                "physical_database_path":str(database_path) if database_path else None,
                "database_status":database_status,
                "database_sha256":database_sha256,
                "catalog_manifest_path":value.get("manifest_path"),
                "physical_manifest_path":str(manifest_path) if manifest_path else None,
                "manifest_status":manifest_status,
                "manifest_sha256":manifest_hash,
                "object_status":object_status,
                "objects":object_results,
                "chain_status":chain_status,
            })
        orphan_db=sorted(name for name in physical_files if name.endswith(".duckdb") and name not in catalog_db_names)
        orphan_manifests=sorted(name for name in physical_files if name.endswith(".manifest.json") and name not in catalog_manifest_names)
        orphan_objects=sorted(name for name in physical_dirs if name.endswith(".objects") and name not in catalog_object_names)
        return {
            "contract_version":"v3-p04-03-backup-chain-audit-v1.0",
            "database_path":str(self.database_path),
            "backup_root":str(backup_root),
            "catalog_count":len(records),
            "physical_file_count":sum(1 for path in backup_root.rglob("*") if path.is_file()) if backup_root.is_dir() else 0,
            "physical_file_bytes":sum(path.stat().st_size for path in backup_root.rglob("*") if path.is_file()) if backup_root.is_dir() else 0,
            "physical_top_level_database_count":sum(1 for name in physical_files if name.endswith(".duckdb")),
            "physical_top_level_manifest_count":sum(1 for name in physical_files if name.endswith(".manifest.json")),
            "physical_top_level_object_dir_count":sum(1 for name in physical_dirs if name.endswith(".objects")),
            "chain_pass_count":sum(1 for item in records if item["chain_status"]=="PASS"),
            "chain_incomplete_count":sum(1 for item in records if item["chain_status"]!="PASS"),
            "orphan_physical_database_files":orphan_db,
            "orphan_physical_manifest_files":orphan_manifests,
            "orphan_physical_object_dirs":orphan_objects,
            "records":records,
        }

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest=hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b""): digest.update(chunk)
        return digest.hexdigest()

    def _validate_external_object(self, raw_path: str | None) -> Path:
        if not raw_path:
            raise ConfigValidationError("BACKUP_OBJECT_PATH_MISSING")
        raw=Path(raw_path)
        candidate=(raw if raw.is_absolute() else self.root/raw).resolve()
        tdx_root=Path(self.config._tdx_root()).expanduser().resolve()
        if candidate == tdx_root or tdx_root in candidate.parents:
            raise ConfigValidationError("BACKUP_OBJECT_TDX_FORBIDDEN")
        roots=[Path(x) for x in self.config.validate(self.config.current()["config"])["resolved_managed_write_roots"]]
        if not any(root == candidate or root in candidate.parents for root in roots):
            raise ConfigValidationError("BACKUP_OBJECT_OUTSIDE_MANAGED_ROOT")
        for item in (raw,*raw.parents):
            if item.is_symlink(): raise ConfigValidationError("BACKUP_OBJECT_SYMLINK_FORBIDDEN")
            if item == self.root: break
        return candidate

    @staticmethod
    def _has_table(con, name: str) -> bool:
        return bool(con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name=?",[name]).fetchone()[0])

    def _referenced_object_ids(self, con, object_rows) -> set[str]:
        result={object_id for object_id,raw in object_rows if json.loads(raw).get("referenced")}
        if self._has_table(con,"analysis_slices"):
            result.update(row[0] for row in con.execute("SELECT storage_object_id FROM analysis_slices WHERE storage_object_id IS NOT NULL").fetchall())
        return {str(value) for value in result if value}

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
