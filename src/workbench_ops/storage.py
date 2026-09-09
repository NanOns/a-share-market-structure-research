from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import duckdb

from .config import ConfigValidationError, OperationsConfig


def _payload(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


class StorageGovernance:
    """Catalog-backed cleanup planning.  Planning never unlinks a path."""

    def __init__(self, root: str | Path, database_path: str | Path | None = None):
        self.root = Path(root).resolve()
        self.database_path = Path(database_path).resolve() if database_path else self.root / "data/database/market_research.duckdb"
        self.config = OperationsConfig(self.root, self.database_path)

    def _roots(self) -> list[Path]:
        report = self.config.validate(self.config.current()["config"])
        return [Path(x) for x in report["resolved_managed_write_roots"]]

    def _protected_paths(self) -> set[Path]:
        return {self.database_path, Path(str(self.database_path) + ".wal"), self.database_path.with_suffix(self.database_path.suffix + ".owner.lock")}

    def _validate_managed_path(self, path: str | Path, *, must_exist: bool = False) -> Path:
        raw=Path(path)
        raw=raw if raw.is_absolute() else self.root/raw
        for item in (raw, *raw.parents):
            if item.is_symlink(): raise ConfigValidationError("STORAGE_SYMLINK_FORBIDDEN")
            if item == self.root: break
        candidate=raw.resolve()
        if must_exist and not candidate.exists(): raise ConfigValidationError("CLEANUP_OBJECT_PATH_INVALID")
        if not any(root == candidate or root in candidate.parents for root in self._roots()):
            raise ConfigValidationError("STORAGE_PATH_OUTSIDE_MANAGED_ROOT")
        tdx_root=Path(self.config._tdx_root()).expanduser().resolve()
        if candidate == tdx_root or tdx_root in candidate.parents:
            raise ConfigValidationError("STORAGE_PATH_TDX_FORBIDDEN")
        if candidate in self._protected_paths():
            raise ConfigValidationError("STORAGE_PATH_PROTECTED")
        return candidate

    def register(self, path: str | Path, *, kind: str, successful_date: str, referenced: bool = False, lease_until_utc: str | None = None) -> str:
        candidate = self._validate_managed_path(path)
        object_id = "obj-" + hashlib.sha256(str(candidate).encode()).hexdigest()[:24]
        value = {"storage_object_id": object_id, "path": str(candidate), "kind": kind, "successful_date": successful_date, "referenced": bool(referenced), "lease_until_utc": lease_until_utc, "state": "ACTIVE", "registered_at_utc": datetime.now(timezone.utc).isoformat()}
        with duckdb.connect(str(self.database_path)) as con:
            con.execute("INSERT INTO storage_objects VALUES (?, ?) ON CONFLICT(storage_object_id) DO UPDATE SET payload_json=excluded.payload_json", [object_id, _payload(value)])
        return object_id

    def acquire_lease(self, *, lease_id: str, object_ids: list[str], owner: str, ttl_seconds: int = 300) -> dict[str, Any]:
        """Protect immutable objects for an active reader/job until expiry."""
        if not lease_id or not owner or not isinstance(object_ids,list) or not object_ids:
            raise ConfigValidationError("LEASE_REQUEST_INVALID")
        if not isinstance(ttl_seconds,int) or isinstance(ttl_seconds,bool) or ttl_seconds < 1:
            raise ConfigValidationError("LEASE_TTL_INVALID")
        now=datetime.now(timezone.utc)
        expires=(now+timedelta(seconds=ttl_seconds)).isoformat()
        with duckdb.connect(str(self.database_path)) as con:
            rows=con.execute("SELECT storage_object_id,payload_json FROM storage_objects WHERE storage_object_id IN (SELECT * FROM UNNEST(?))",[object_ids]).fetchall()
            found={row[0] for row in rows}
            missing=sorted(set(object_ids)-found)
            if missing: raise ConfigValidationError("LEASE_OBJECT_NOT_FOUND:"+",".join(missing))
            payload={"lease_id":lease_id,"owner":owner,"storage_object_ids":sorted(set(object_ids)),"acquired_at_utc":now.isoformat(),"expires_at_utc":expires,"state":"ACTIVE"}
            con.execute("INSERT INTO leases VALUES (?, ?) ON CONFLICT(lease_id) DO UPDATE SET payload_json=excluded.payload_json",[lease_id,_payload(payload)])
        return payload

    def release_lease(self, *, lease_id: str, owner: str) -> dict[str, Any]:
        with duckdb.connect(str(self.database_path)) as con:
            row=con.execute("SELECT payload_json FROM leases WHERE lease_id=?",[lease_id]).fetchone()
            if not row: raise ConfigValidationError("LEASE_NOT_FOUND")
            payload=json.loads(row[0])
            if payload.get("owner") != owner: raise ConfigValidationError("LEASE_OWNER_MISMATCH")
            payload.update(state="RELEASED",released_at_utc=datetime.now(timezone.utc).isoformat())
            con.execute("UPDATE leases SET payload_json=? WHERE lease_id=?",[_payload(payload),lease_id])
        return payload

    def preview_cleanup(self, *, as_of: date) -> dict[str, Any]:
        retention = self.config.current()["config"]["retention_successful_days"]
        with duckdb.connect(str(self.database_path)) as con:
            rows = con.execute("SELECT payload_json FROM storage_objects").fetchall()
            referenced=self._database_references(con)
            active_jobs=self._active_job_references(con)
            lease_refs=self._active_lease_references(con)
            object_dates=self._analysis_object_dates(con)
        eligible=[]; protected=[]
        for (raw,) in rows:
            item=json.loads(raw)
            try: object_path=self._validate_managed_path(item.get("path", ""))
            except ConfigValidationError as exc: protected.append({"object":item,"reason":str(exc)}); continue
            if object_path in self._protected_paths(): protected.append({"object":item,"reason":"PROTECTED_RUNTIME_PATH"}); continue
            object_id=item.get("storage_object_id")
            lease=item.get("lease_until_utc")
            object_lease=lease and datetime.fromisoformat(lease.replace("Z","+00:00")) > datetime.now(timezone.utc)
            if item.get("state") != "ACTIVE": protected.append({"object":item,"reason":"NOT_ACTIVE"})
            elif object_id in referenced or (item.get("referenced") and item.get("kind") != "ANALYSIS_SLICE"): protected.append({"object":item,"reason":"DATABASE_REFERENCED"})
            elif object_id in active_jobs: protected.append({"object":item,"reason":"ACTIVE_JOB_REFERENCE"})
            elif object_id in lease_refs or object_lease: protected.append({"object":item,"reason":"ACTIVE_LEASE"})
            else:
                successful_date=item.get("successful_date") or object_dates.get(object_id)
                try: age=(as_of-date.fromisoformat(successful_date)).days
                except (KeyError, TypeError, ValueError): protected.append({"object":item,"reason":"INVALID_SUCCESSFUL_DATE"});continue
                if age < retention: protected.append({"object":item,"reason":"RETENTION_WINDOW"})
                else: eligible.append(item)
        registered={json.loads(raw).get("path") for (raw,) in rows}
        object_root=self.root/"data/analysis_objects"
        unregistered=[{"path":str(path.resolve()),"reason":"UNREGISTERED_REVIEW_REQUIRED"} for path in sorted(object_root.glob("analysis-obj-*.parquet")) if str(path.resolve()) not in registered]
        plan_body={"contract_version":"history-cleanup-preview-v1.0","as_of":as_of.isoformat(),"retention_successful_days":retention,"eligible_object_ids":sorted(x["storage_object_id"] for x in eligible),"reference_audit":{"database":sorted(referenced),"active_jobs":sorted(active_jobs),"leases":sorted(lease_refs)},"unregistered_objects":unregistered}
        created_at=datetime.now(timezone.utc).isoformat()
        # A preview is an immutable decision record.  It must not reuse an
        # earlier plan that may already have been restored or deleted.
        plan_id="cleanup-"+hashlib.sha256(_payload({**plan_body,"created_at_utc":created_at}).encode()).hexdigest()[:24]
        plan={**plan_body,"cleanup_job_id":plan_id,"state":"PLANNED","created_at_utc":created_at,"eligible":eligible,"protected":protected}
        with duckdb.connect(str(self.database_path)) as con:
            con.execute("INSERT INTO cleanup_jobs VALUES (?, ?) ON CONFLICT(cleanup_job_id) DO NOTHING", [plan_id,_payload(plan)])
        return plan

    @staticmethod
    def _table_exists(con, name: str) -> bool:
        return bool(con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name=?",[name]).fetchone()[0])

    def _database_references(self, con) -> set[str]:
        refs=set()
        if self._table_exists(con,"publication_analysis_snapshots") and self._table_exists(con,"analysis_snapshot_entries") and self._table_exists(con,"analysis_slices"):
            refs.update(row[0] for row in con.execute("""
                SELECT s.storage_object_id
                FROM publication_analysis_snapshots p
                JOIN analysis_snapshots a ON a.snapshot_id=p.snapshot_id AND a.status='SUCCESS'
                JOIN analysis_snapshot_entries e ON e.snapshot_id=a.snapshot_id
                JOIN analysis_slices s ON s.slice_id=e.slice_id
                WHERE s.storage_object_id IS NOT NULL
            """).fetchall())
        return {x for x in refs if x}

    def _analysis_object_dates(self, con) -> dict[str,str]:
        if not self._table_exists(con,"analysis_slices"):
            return {}
        return {row[0]:row[1] for row in con.execute("SELECT storage_object_id,cast(max(trade_date) as varchar) FROM analysis_slices WHERE storage_object_id IS NOT NULL GROUP BY storage_object_id").fetchall()}

    def _active_job_references(self, con) -> set[str]:
        refs=set()
        if not self._table_exists(con,"jobs"):
            return refs
        rows=con.execute("SELECT payload_json FROM jobs WHERE status IN ('QUEUED','RUNNING','INTERRUPTED')").fetchall()
        slice_ids=[]
        for (raw,) in rows:
            try:
                payload=json.loads(raw or "{}")
            except json.JSONDecodeError:
                continue
            pending=payload.get("pending_storage_object_ids",[])
            if isinstance(pending,list): refs.update(str(x) for x in pending)
            ids=payload.get("completed_slice_ids",[])
            if isinstance(ids,list): slice_ids.extend(str(x) for x in ids)
        if slice_ids and self._table_exists(con,"analysis_slices"):
            refs.update(row[0] for row in con.execute("SELECT storage_object_id FROM analysis_slices WHERE slice_id IN (SELECT * FROM UNNEST(?)) AND storage_object_id IS NOT NULL",[slice_ids]).fetchall())
        return {x for x in refs if x}

    def _active_lease_references(self, con) -> set[str]:
        if not self._table_exists(con,"leases"):
            return set()
        now=datetime.now(timezone.utc)
        refs=set()
        for (raw,) in con.execute("SELECT payload_json FROM leases").fetchall():
            try: payload=json.loads(raw or "{}")
            except json.JSONDecodeError: continue
            if payload.get("state") != "ACTIVE": continue
            expires=payload.get("expires_at_utc") or payload.get("lease_until_utc")
            try: active=expires and datetime.fromisoformat(str(expires).replace("Z","+00:00")) > now
            except ValueError: active=False
            if active and isinstance(payload.get("storage_object_ids"),list): refs.update(str(x) for x in payload["storage_object_ids"])
        return refs

    def quarantine(self, cleanup_job_id: str) -> dict[str, Any]:
        """Move eligible registered objects to a same-volume trash directory."""
        with duckdb.connect(str(self.database_path)) as con:
            row=con.execute("SELECT payload_json FROM cleanup_jobs WHERE cleanup_job_id=?",[cleanup_job_id]).fetchone()
        if not row: raise ConfigValidationError("CLEANUP_PLAN_NOT_FOUND")
        plan=json.loads(row[0])
        if plan.get("state") != "PLANNED": raise ConfigValidationError("CLEANUP_PLAN_NOT_PLANNED")
        planned=set(plan.get("eligible_object_ids",[])); moved=[]; moves=[]
        with duckdb.connect(str(self.database_path)) as con:
            catalog={object_id:json.loads(payload) for object_id,payload in con.execute("SELECT storage_object_id,payload_json FROM storage_objects").fetchall()}
            referenced=self._database_references(con);active_jobs=self._active_job_references(con);lease_refs=self._active_lease_references(con)
            for object_id in sorted(planned):
                item=catalog.get(object_id)
                legacy_reference=item and item.get("referenced") and item.get("kind") != "ANALYSIS_SLICE"
                if not item or item.get("state") != "ACTIVE" or legacy_reference or object_id in referenced or object_id in active_jobs:
                    raise ConfigValidationError("CLEANUP_PLAN_STALE")
                if object_id in lease_refs: raise ConfigValidationError("CLEANUP_PLAN_STALE_ACTIVE_LEASE")
                lease=item.get("lease_until_utc")
                if lease and datetime.fromisoformat(lease.replace("Z","+00:00")) > datetime.now(timezone.utc):
                    raise ConfigValidationError("CLEANUP_PLAN_STALE_ACTIVE_LEASE")
                source=self._validate_managed_path(item["path"], must_exist=True)
                if source in self._protected_paths(): raise ConfigValidationError("CLEANUP_OBJECT_PROTECTED")
                trash=source.parent/".workbench-trash"/cleanup_job_id/object_id
                if trash.exists(): raise ConfigValidationError("CLEANUP_TRASH_TARGET_EXISTS")
                moves.append((object_id,item,source,trash))
            try:
                for object_id,item,source,trash in moves:
                    trash.parent.mkdir(parents=True,exist_ok=True)
                    os.replace(source,trash)
                    item.update(state="QUARANTINED",original_path=str(source),path=str(trash),quarantined_at_utc=datetime.now(timezone.utc).isoformat())
                    moved.append(item)
                con.execute("BEGIN")
                for item in moved:
                    con.execute("UPDATE storage_objects SET payload_json=? WHERE storage_object_id=?",[_payload(item),item["storage_object_id"]])
                plan.update(state="QUARANTINED",quarantined_object_ids=[x["storage_object_id"] for x in moved])
                con.execute("UPDATE cleanup_jobs SET payload_json=? WHERE cleanup_job_id=?",[_payload(plan),cleanup_job_id])
                con.execute("COMMIT")
            except Exception:
                try: con.execute("ROLLBACK")
                except Exception: pass
                for item in reversed(moved):
                    source=Path(item["original_path"]);trash=Path(item["path"])
                    if trash.exists() and not source.exists(): os.replace(trash,source)
                raise
        return {"cleanup_job_id":cleanup_job_id,"state":"QUARANTINED","objects":moved}

    def restore_quarantine(self, cleanup_job_id: str) -> dict[str, Any]:
        with duckdb.connect(str(self.database_path)) as con:
            rows=con.execute("SELECT storage_object_id,payload_json FROM storage_objects").fetchall();restored=[];moves=[]
            for object_id,raw in rows:
                item=json.loads(raw)
                if item.get("state") != "QUARANTINED" or f"/{cleanup_job_id}/" not in item.get("path","").replace("\\","/"): continue
                source=self._validate_managed_path(item["path"],must_exist=True);target=self._validate_managed_path(item["original_path"])
                if target.exists(): raise ConfigValidationError("CLEANUP_RESTORE_PATH_CONFLICT")
                moves.append((object_id,item,source,target))
            try:
                for object_id,item,source,target in moves:
                    target.parent.mkdir(parents=True,exist_ok=True);os.replace(source,target)
                    item.update(state="ACTIVE",path=str(target));item.pop("quarantined_at_utc",None);restored.append(object_id)
                con.execute("BEGIN")
                for object_id,item,_,_ in moves: con.execute("UPDATE storage_objects SET payload_json=? WHERE storage_object_id=?",[_payload(item),object_id])
                con.execute("UPDATE cleanup_jobs SET payload_json=json_merge_patch(payload_json, ?) WHERE cleanup_job_id=?",[_payload({"state":"RESTORED"}),cleanup_job_id]);con.execute("COMMIT")
            except Exception:
                try: con.execute("ROLLBACK")
                except Exception: pass
                for _,_,source,target in reversed(moves):
                    if target.exists() and not source.exists(): os.replace(target,source)
                raise
        return {"cleanup_job_id":cleanup_job_id,"state":"RESTORED","object_ids":restored}

    def delete_quarantine(self, cleanup_job_id: str) -> dict[str, Any]:
        with duckdb.connect(str(self.database_path)) as con:
            rows=con.execute("SELECT storage_object_id,payload_json FROM storage_objects").fetchall();deleted=[];pending=[]
            for object_id,raw in rows:
                item=json.loads(raw);path=Path(item.get("path",""))
                if item.get("state") != "QUARANTINED" or f"/{cleanup_job_id}/" not in str(path).replace("\\","/"): continue
                path=self._validate_managed_path(path,must_exist=True);temporary=path.with_name(".workbench-deleting-"+uuid.uuid4().hex)
                if temporary.exists(): raise ConfigValidationError("CLEANUP_DELETE_TARGET_EXISTS")
                pending.append((object_id,item,path,temporary))
            try:
                for object_id,item,path,temporary in pending:
                    os.replace(path,temporary);item.update(state="DELETED",deleted_at_utc=datetime.now(timezone.utc).isoformat());deleted.append(object_id)
                con.execute("BEGIN")
                for object_id,item,_,_ in pending: con.execute("UPDATE storage_objects SET payload_json=? WHERE storage_object_id=?",[_payload(item),object_id])
                con.execute("UPDATE cleanup_jobs SET payload_json=json_merge_patch(payload_json, ?) WHERE cleanup_job_id=?",[_payload({"state":"DELETED"}),cleanup_job_id]);con.execute("COMMIT")
            except Exception:
                try: con.execute("ROLLBACK")
                except Exception: pass
                for _,_,path,temporary in reversed(pending):
                    if temporary.exists() and not path.exists(): os.replace(temporary,path)
                raise
            for _,_,_,temporary in pending:
                if temporary.is_dir(): shutil.rmtree(temporary)
                elif temporary.is_file(): temporary.unlink()
        return {"cleanup_job_id":cleanup_job_id,"state":"DELETED","object_ids":deleted}
