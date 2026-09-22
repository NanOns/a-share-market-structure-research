from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from workbench_db import BackupCatalogRepository, BackupRepository, DuckDBBackupCatalogRepository, DuckDBBackupRepository

from .config import ConfigValidationError, OperationsConfig


def _dump(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


class BackupService:
    """Offline DuckDB backup and restore-drill service.

    The caller must drain the service first.  This deliberately refuses the
    convenient-but-unsafe hot file copy pattern.
    """
    # MIGRATION_CONTRACT: backup remains MIGRATE_TO_PG until catalog writes,
    # verification and restore metadata use a rehearsed PG operations API.
    def __init__(self, root, database_path=None, *, repository: BackupRepository | None = None, catalog: BackupCatalogRepository | None = None):
        self.root=Path(root).resolve()
        self._repository = repository or DuckDBBackupRepository(database_path or self.root/"data/database/market_research.duckdb")
        self.database_path=Path(database_path).resolve() if database_path else self._repository.database_path
        self._catalog = catalog or DuckDBBackupCatalogRepository(self.database_path)
        self.config=OperationsConfig(self.root,self.database_path)

    def _connect(self, path=None, *, read_only=False):
        return self._repository.connect(path, read_only=read_only)

    def _memory(self):
        return self._repository.memory()

    def create_offline_backup(self, *, maintenance_window: bool) -> dict:
        if not maintenance_window:
            raise ConfigValidationError("BACKUP_REQUIRES_DRAINED_MAINTENANCE_WINDOW")
        if not self.database_path.is_file():
            raise ConfigValidationError("BACKUP_DATABASE_MISSING")
        backup_root=Path(self.config.validate(self.config.current()["config"])["resolved_backup_root"])
        backup_root.mkdir(parents=True,exist_ok=True)
        # A full connection is opened only after the operator has drained all
        # service connections. CHECKPOINT produces a self-contained file.
        with self._connect() as con:
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
        self._catalog.upsert(backup_id, record)
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
        with self._connect() as con:
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
        self._catalog.upsert(backup_id, record)
        return record

    def restore_drill(self, backup_id: str, *, drill_root: str | Path) -> dict:
        record=self._catalog.get(backup_id)
        if not record: raise ConfigValidationError("BACKUP_NOT_REGISTERED")
        source=Path(record["path"]).resolve(); raw_root=Path(drill_root)
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
                        with self._memory() as check:
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
        rows=self._catalog.rows()
        records=[]; catalog_db_names=set(); catalog_manifest_names=set(); catalog_object_names=set()
        for backup_id, value in rows:
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
    def classify_catalog_physical_chain(audit: dict) -> dict:
        """Turn a chain audit into a conservative, non-destructive decision list."""
        decisions=[]
        for record in audit.get("records",[]):
            if record.get("chain_status")=="PASS":
                decisions.append({
                    "item_type":"CATALOG_CHAIN",
                    "item_id":record["backup_id"],
                    "category":"MANUAL_RECOVERY_VALIDATION_CANDIDATE",
                    "protection":"RETAIN",
                    "next_action":"OPTIONAL_MANUAL_RECOVERY_DRILL",
                    "deletion_allowed":False,
                    "reason":"DATABASE_MANIFEST_OBJECT_CHAIN_COMPLETE",
                })
            else:
                decisions.append({
                    "item_type":"CATALOG_CHAIN",
                    "item_id":record["backup_id"],
                    "category":"PROTECTED_EVIDENCE",
                    "protection":"RETAIN_UNTIL_DECISION",
                    "next_action":"DO_NOT_DELETE_OR_RECREATE; IDENTIFY_DATABASE_ARTIFACT_SOURCE",
                    "deletion_allowed":False,
                    "reason":"CATALOG_CHAIN_INCOMPLETE",
                    "database_status":record.get("database_status"),
                    "manifest_status":record.get("manifest_status"),
                    "object_status":record.get("object_status"),
                })
        for name in audit.get("orphan_physical_database_files",[]):
            decisions.append({
                "item_type":"ORPHAN_DATABASE",
                "item_id":name,
                "category":"USER_DECISION_REQUIRED",
                "protection":"RETAIN_UNTIL_DECISION",
                "next_action":"IDENTIFY_OWNER_OR_FIXED_RETENTION",
                "deletion_allowed":False,
                "reason":"PHYSICAL_DATABASE_NOT_IN_CATALOG",
            })
        manifest_names={name.removesuffix(".manifest.json") for name in audit.get("orphan_physical_manifest_files",[])}
        object_names={name.removesuffix(".objects") for name in audit.get("orphan_physical_object_dirs",[])}
        for backup_id in sorted(manifest_names|object_names):
            decisions.append({
                "item_type":"ORPHAN_MANIFEST_OBJECT",
                "item_id":backup_id,
                "category":"USER_DECISION_REQUIRED",
                "protection":"RETAIN_UNTIL_DECISION",
                "next_action":"IDENTIFY_OWNER_OR_FIXED_RETENTION",
                "deletion_allowed":False,
                "reason":"PHYSICAL_MANIFEST_OR_OBJECT_NOT_IN_CATALOG",
                "manifest_present":backup_id in manifest_names,
                "objects_present":backup_id in object_names,
            })
        counts={}
        for item in decisions: counts[item["category"]]=counts.get(item["category"],0)+1
        return {
            "contract_version":"v3-p04-03-backup-chain-classification-v1.0",
            "source_contract_version":audit.get("contract_version"),
            "automatic_action":"NONE",
            "deletion_allowed":False,
            "counts":counts,
            "decisions":decisions,
        }

    def audit_orphan_provenance(self, chain_audit: dict) -> dict:
        """Cross-check unregistered backup artifacts without changing ownership.

        This is deliberately narrower than the chain audit: it only inspects
        the six user-decision items, compares their content identities with
        catalog/storage records, and emits a retention recommendation.  It
        never registers, deletes, restores, moves, or rewrites an artifact.
        """
        backup_root=Path(self.config.validate(self.config.current()["config"])["resolved_backup_root"]).resolve()
        catalog_rows=self._catalog.rows()
        with self._connect(read_only=True) as con:
            storage_rows=con.execute("SELECT storage_object_id,payload_json FROM storage_objects ORDER BY storage_object_id").fetchall() if self._has_table(con,"storage_objects") else []
        catalog_records=[]
        catalog_by_sha={}
        catalog_by_id={}
        for backup_id,value in catalog_rows:
            item={"backup_id":backup_id,"created_at_utc":value.get("created_at_utc"),"sha256":value.get("sha256"),"database_name":Path(str(value.get("path", ""))).name}
            catalog_records.append(item)
            catalog_by_id[backup_id]=item
            if item["sha256"]: catalog_by_sha.setdefault(item["sha256"],[]).append(backup_id)
        storage_by_id={}
        for object_id,raw in storage_rows:
            value=json.loads(raw)
            storage_by_id[object_id]={
                "storage_object_id":object_id,
                "state":value.get("state"),
                "referenced":value.get("referenced"),
                "physical_sha256":value.get("physical_sha256"),
                "relative_path":value.get("relative_path"),
                "size_bytes":value.get("size_bytes"),
                "row_count":value.get("row_count"),
                "registered_at_utc":value.get("registered_at_utc"),
                "storage_kind":value.get("storage_kind"),
            }
        retention={
            "recommendation":"RETAIN_UNTIL_OWNER_CONFIRMED",
            "fixed_retention_required":True,
            "fixed_retention_days":None,
            "deletion_allowed":False,
            "automatic_action":"NONE",
            "reason":"V3_17_8_USER_FIXED_RETENTION_ITEM_OR_UNRESOLVED_PROVENANCE",
        }
        items=[]
        orphan_dbs=chain_audit.get("orphan_physical_database_files",[])
        for name in sorted(orphan_dbs):
            path=backup_root/name
            exists=path.is_file()
            digest=self._sha256_file(path) if exists else None
            prefix=name[:-len(".duckdb")].rsplit("-",1)[-1] if name.endswith(".duckdb") else None
            items.append({
                "item_type":"ORPHAN_DATABASE",
                "item_id":name,
                "physical_path":str(path),
                "exists":exists,
                "size_bytes":path.stat().st_size if exists else None,
                "sha256":digest,
                "filename_sha256_prefix":prefix,
                "filename_sha256_prefix_matches":bool(digest and prefix and digest.startswith(prefix)),
                "catalog_backup_ids_by_sha256":catalog_by_sha.get(digest,[]),
                "catalog_backup_ids_by_filename_backup_id":[],
                "provenance_class":"UNOWNED_PHYSICAL_DATABASE",
                "provenance_status":"SELF_HASH_CONSISTENT_BUT_NOT_CATALOGED" if digest and prefix and digest.startswith(prefix) else "NOT_CATALOGED",
                "retention":dict(retention),
            })
        manifest_names={name.removesuffix(".manifest.json") for name in chain_audit.get("orphan_physical_manifest_files",[])}
        object_names={name.removesuffix(".objects") for name in chain_audit.get("orphan_physical_object_dirs",[])}
        for backup_id in sorted(manifest_names|object_names):
            manifest_path=backup_root/(backup_id+".manifest.json") if backup_id in manifest_names else None
            object_root=backup_root/(backup_id+".objects") if backup_id in object_names else None
            manifest=None
            manifest_status="MISSING"
            manifest_sha256=None
            claimed_manifest_sha256=None
            identity_manifest_sha256=None
            if manifest_path and manifest_path.is_file():
                try:
                    manifest_sha256=self._sha256_file(manifest_path)
                    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
                    unsigned=dict(manifest)
                    claimed_manifest_sha256=unsigned.pop("manifest_sha256",None)
                    identity_manifest_sha256=hashlib.sha256(_dump(unsigned).encode()).hexdigest()
                    manifest_status="PASS" if manifest.get("backup_id")==backup_id and claimed_manifest_sha256==identity_manifest_sha256 else "IDENTITY_OR_HASH_MISMATCH"
                except (OSError,json.JSONDecodeError,TypeError,ValueError):
                    manifest_status="UNREADABLE"
            database_sha256=manifest.get("database",{}).get("sha256") if manifest else None
            object_results=[]
            listed_paths=set()
            if manifest:
                for entry in manifest.get("objects",[]):
                    relative=Path(str(entry.get("relative_path","")))
                    if relative.is_absolute() or ".." in relative.parts:
                        object_results.append({"storage_object_id":entry.get("storage_object_id"),"relative_path":str(relative),"status":"INVALID_RELATIVE_PATH","storage_object_match":storage_by_id.get(entry.get("storage_object_id"))})
                        continue
                    listed_paths.add(relative.as_posix())
                    physical_path=object_root.joinpath(*relative.parts) if object_root else None
                    exists=bool(physical_path and physical_path.is_file())
                    actual=self._sha256_file(physical_path) if exists else None
                    expected_size=entry.get("size_bytes")
                    size_status="PASS" if exists and expected_size is not None and physical_path.stat().st_size==int(expected_size) else ("MISSING" if not exists else "SIZE_MISMATCH")
                    hash_status="PASS" if exists and actual==entry.get("sha256") else ("MISSING" if not exists else "HASH_MISMATCH")
                    object_results.append({
                        "storage_object_id":entry.get("storage_object_id"),
                        "relative_path":relative.as_posix(),
                        "physical_path":str(physical_path) if physical_path else None,
                        "exists":exists,
                        "size_bytes":physical_path.stat().st_size if exists else None,
                        "sha256":actual,
                        "manifest_expected_size_bytes":expected_size,
                        "manifest_expected_sha256":entry.get("sha256"),
                        "size_status":size_status,
                        "hash_status":hash_status,
                        "storage_object_match":storage_by_id.get(entry.get("storage_object_id")),
                    })
            physical_files=[]
            if object_root and object_root.is_dir():
                for path in sorted(path for path in object_root.rglob("*") if path.is_file()):
                    relative=path.relative_to(object_root).as_posix()
                    physical_files.append({"relative_path":relative,"size_bytes":path.stat().st_size,"sha256":self._sha256_file(path),"listed_in_manifest":relative in listed_paths})
            storage_matches=[item for item in object_results if item.get("storage_object_match")]
            if database_sha256 and catalog_by_sha.get(database_sha256):
                provenance_class="MANIFEST_DATABASE_HASH_MATCHES_CATALOG"
                provenance_status="CONTENT_IDENTITY_MATCHES_CATALOG_BUT_PHYSICAL_CHAIN_UNREGISTERED"
            elif storage_matches:
                provenance_class="UNREGISTERED_MANIFEST_WITH_REGISTERED_OBJECT_EVIDENCE"
                provenance_status="MANIFEST_OBJECT_HASH_MATCHES_ACTIVE_STORAGE_OBJECT"
            else:
                provenance_class="UNOWNED_MANIFEST_OBJECT"
                provenance_status="NO_CATALOG_OR_STORAGE_OBJECT_MATCH"
            items.append({
                "item_type":"ORPHAN_MANIFEST_OBJECT",
                "item_id":backup_id,
                "manifest_path":str(manifest_path) if manifest_path else None,
                "objects_root":str(object_root) if object_root else None,
                "manifest_status":manifest_status,
                "manifest_sha256":manifest_sha256,
                "manifest_claimed_sha256":claimed_manifest_sha256,
                "manifest_identity_sha256":identity_manifest_sha256,
                "created_at_utc":manifest.get("created_at_utc") if manifest else None,
                "database_sha256":database_sha256,
                "database_name":Path(str(manifest.get("database",{}).get("path",""))).name if manifest else None,
                "catalog_backup_ids_by_database_sha256":catalog_by_sha.get(database_sha256,[]),
                "catalog_backup_id_exact_match":backup_id if backup_id in catalog_by_id else None,
                "object_results":object_results,
                "physical_files":physical_files,
                "provenance_class":provenance_class,
                "provenance_status":provenance_status,
                "retention":dict(retention),
            })
        return {
            "contract_version":"v3-p04-03-backup-orphan-provenance-v1.0",
            "source_contract_version":chain_audit.get("contract_version"),
            "database_path":str(self.database_path),
            "backup_root":str(backup_root),
            "catalog_count":len(catalog_records),
            "storage_object_count":len(storage_by_id),
            "item_count":len(items),
            "retention_policy":retention,
            "items":items,
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
        with self._connect(path, read_only=True) as con:
            actual=self._verify(con)
        if actual != expected: raise ConfigValidationError("BACKUP_VERIFICATION_MISMATCH")
