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
    def _v3_json_source_bundle_ids(value: Any, known: set[str]) -> set[str]:
        found: set[str] = set()
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"source_bundle_id", "source_manifest_sha256"} and str(item) in known:
                    found.add(str(item))
                found.update(StorageGovernance._v3_json_source_bundle_ids(item, known))
        elif isinstance(value, list):
            for item in value:
                found.update(StorageGovernance._v3_json_source_bundle_ids(item, known))
        return found

    @staticmethod
    def _v3_bundle_identity(value: dict[str, Any]) -> bool:
        claimed=value.get("source_bundle_id")
        unsigned=dict(value)
        unsigned.pop("source_bundle_id",None)
        actual=hashlib.sha256(_payload(unsigned).encode("utf-8")).hexdigest()
        return bool(claimed and claimed==actual and value.get("contract")=="source-bundle-v1.0" and value.get("read_only") is True)

    def _v3_bundle_package_path(self, bundle: dict[str, Any]) -> Path:
        raw=(bundle.get("package") or {}).get("staged_path")
        if raw:
            candidate=Path(raw)
            candidate=candidate if candidate.is_absolute() else self.root/candidate
        else:
            date_key=str(bundle.get("target_trade_date","")).replace("-","")
            candidate=self.root/"data/input_staging/packages"/date_key/"hsjday.zip"
        if candidate.is_symlink(): raise ConfigValidationError("V3_INPUT_SYMLINK_FORBIDDEN")
        candidate=candidate.resolve()
        staging=(self.root/"data/input_staging").resolve()
        if candidate!=staging and staging not in candidate.parents:
            raise ConfigValidationError("V3_INPUT_PATH_OUTSIDE_STAGING")
        return candidate

    def preview_v3_input_storage(
        self,
        *,
        as_of: date,
        recent_bundle_count: int = 2,
        phase1_cache_budget_bytes: int = 2 * 1024**3,
    ) -> dict[str, Any]:
        """Read-only V3 input/cache retention preview.

        This intentionally does not call :meth:`preview_cleanup`: V3 source
        packages, extracted inputs, metadata snapshots and phase-1 cache have
        different protection contracts from registered analysis objects.  No
        database table is written by this method.
        """
        if recent_bundle_count != 2:
            raise ConfigValidationError("V3_RECENT_BUNDLE_POLICY_MUST_BE_TWO")
        if not isinstance(phase1_cache_budget_bytes,int) or isinstance(phase1_cache_budget_bytes,bool) or phase1_cache_budget_bytes < 1:
            raise ConfigValidationError("V3_CACHE_BUDGET_INVALID")
        data_root=self.root/"data"
        bundle_root=data_root/"source_bundles"
        receipts=sorted(bundle_root.glob("*/source_bundle.json"))
        bundles: dict[str,dict[str,Any]]={}
        issues=[]
        for receipt in receipts:
            try:
                value=json.loads(receipt.read_text(encoding="utf-8"))
                bundle_id=str(value.get("source_bundle_id", ""))
                if not self._v3_bundle_identity(value) or receipt.parent.name!=bundle_id:
                    issues.append({"path":str(receipt),"reason":"BUNDLE_RECEIPT_IDENTITY_INVALID"})
                    continue
                bundles[bundle_id]=value
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
                issues.append({"path":str(receipt),"reason":"BUNDLE_RECEIPT_UNREADABLE","detail":str(exc)})
        known=set(bundles)
        used=set()
        active=set()
        usage_evidence=[]
        database_catalog_ids: set[str] | None = None
        with duckdb.connect(str(self.database_path), read_only=True) as con:
            if self._table_exists(con,"source_bundles"):
                database_catalog_ids={str(row[0]) for row in con.execute("SELECT source_bundle_id FROM source_bundles").fetchall()}
                for bundle_id in sorted(known-database_catalog_ids):
                    issues.append({"bundle_id":bundle_id,"reason":"PHYSICAL_RECEIPT_NOT_IN_DATABASE_CATALOG"})
                for bundle_id in sorted(database_catalog_ids-known):
                    issues.append({"bundle_id":bundle_id,"reason":"DATABASE_CATALOG_RECEIPT_MISSING"})
            if self._table_exists(con,"publications"):
                rows=con.execute("SELECT publication_id,source_manifest_sha256,source_path,status FROM publications WHERE status='SUCCESS'").fetchall()
                for publication_id, manifest_hash, source_path, status in rows:
                    candidates={str(manifest_hash)} if manifest_hash else set()
                    candidates.update(part for part in str(source_path or "").replace("\\","/").split("/") if part in known)
                    matched=candidates&known
                    used.update(matched)
                    if matched: usage_evidence.append({"kind":"publication","id":str(publication_id),"bundle_ids":sorted(matched)})
            if self._table_exists(con,"jobs"):
                rows=con.execute("SELECT job_id,payload_json FROM jobs WHERE status IN ('QUEUED','RUNNING','INTERRUPTED')").fetchall()
                for job_id, raw in rows:
                    try: value=json.loads(raw or "{}")
                    except json.JSONDecodeError: continue
                    matched=self._v3_json_source_bundle_ids(value,known)
                    active.update(matched); used.update(matched)
                    if matched: usage_evidence.append({"kind":"active_job","id":str(job_id),"bundle_ids":sorted(matched)})
        if active:
            issues.append({"reason":"ACTIVE_TASK_BUNDLES_PROTECTED","bundle_ids":sorted(active)})
        ordered_used=sorted(
            (bundles[bundle_id] for bundle_id in used),
            key=lambda value:(str(value.get("target_trade_date","")),str(value.get("source_bundle_id",""))),
            reverse=True,
        )
        retained_ids={str(value["source_bundle_id"]) for value in ordered_used[:recent_bundle_count]}
        retained_roots={str((value.get("extraction") or {}).get("root","")) for value in ordered_used[:recent_bundle_count]}

        package_rows=[]
        package_seen=set()
        extraction_rows=[]
        extraction_seen=set()
        metadata_rows=[]
        metadata_hashes: dict[str,list[dict[str,Any]]]={}
        for bundle_id, bundle in sorted(bundles.items()):
            package=bundle.get("package") or {}
            try:
                package_path=self._v3_bundle_package_path(bundle)
                package_error=None
            except ConfigValidationError as exc:
                package_path=None; package_error=str(exc)
            package_key=str(package_path or package.get("sha256") or f"invalid:{bundle_id}")
            if package_key not in package_seen:
                package_seen.add(package_key)
                package_rows.append({
                    "path":str(package_path) if package_path else None,
                    "sha256":package.get("sha256"),
                    "byte_count":package.get("byte_count"),
                    "exists":bool(package_path and package_path.is_file()),
                    "protected":True,
                    "reason":"UNIQUE_SOURCE_PACKAGE_PROTECTED" if not package_error else package_error,
                })
            extraction=bundle.get("extraction") or {}
            extraction_root=str(extraction.get("root", ""))
            if extraction_root in extraction_seen: continue
            extraction_seen.add(extraction_root)
            extraction_path=(self.root/Path(extraction_root)).resolve() if extraction_root else None
            if extraction_path and extraction_path.exists():
                files=[path for path in extraction_path.rglob("*") if path.is_file()]
                actual_files=len(files); actual_bytes=sum(path.stat().st_size for path in files)
            else:
                actual_files=0; actual_bytes=0
            matching_ids=sorted(x for x,y in bundles.items() if str((y.get("extraction") or {}).get("root",""))==extraction_root)
            if extraction_root in retained_roots:
                decision="PROTECTED_RECENT_USED_BUNDLE"; protected=True
            elif active.intersection(matching_ids):
                decision="PROTECTED_ACTIVE_TASK_REFERENCE"; protected=True
            elif package_error or not package_path or not package_path.is_file():
                decision="PROTECTED_PACKAGE_NOT_RECOVERABLE"; protected=True
            else:
                decision="PREVIEW_RECLAIMABLE_REBUILDABLE"; protected=False
            extraction_rows.append({
                "root":extraction_root,
                "bundle_ids":matching_ids,
                "exists":bool(extraction_path and extraction_path.is_dir()),
                "file_count":actual_files,
                "bytes":actual_bytes,
                "declared_entry_count":extraction.get("entry_count"),
                "declared_expanded_bytes":extraction.get("expanded_bytes"),
                "protected":protected,
                "decision":decision,
            })
            metadata=bundle.get("metadata") or {}
            for relative, descriptor in (metadata.get("files") or {}).items():
                content_hash=str((descriptor or {}).get("sha256", ""))
                metadata_hashes.setdefault(content_hash,[]).append({"bundle_id":bundle_id,"path":relative})
            metadata_rows.append({"bundle_id":bundle_id,"root":metadata.get("root"),"file_count":len(metadata.get("files") or {}),"protected":True,"reason":"METADATA_SNAPSHOT_PROTECTED"})

        cache_root=data_root/".phase1_cache"
        cache_files=[path for path in cache_root.rglob("*") if path.is_file()] if cache_root.is_dir() else []
        cache_bytes=sum(path.stat().st_size for path in cache_files)
        utilization=cache_bytes/phase1_cache_budget_bytes
        if cache_bytes>phase1_cache_budget_bytes:
            cache_decision="BLOCKED_NO_SAFE_CANDIDATE"
            cache_reason="OVER_BUDGET_BUT_NO_ACCESS_ORDER_OR_SAFE_REFERENCE_SET"
            cache_candidates=[]
        elif utilization>=0.9:
            cache_decision="WARNING_90_PERCENT"
            cache_reason="WITHIN_BUDGET_NO_RECLAIM"
            cache_candidates=[]
        else:
            cache_decision="WITHIN_BUDGET"
            cache_reason="NO_RECLAIM_REQUIRED"
            cache_candidates=[]
        return {
            "contract_version":"v3-p04-03-input-storage-preview-v1.0",
            "as_of":as_of.isoformat(),
            "policy":{"recent_used_bundle_count":recent_bundle_count,"phase1_cache_budget_bytes":phase1_cache_budget_bytes,"phase1_cache_selection":"ACCESS_METADATA_ONLY; NEVER_MTIME_DELETE","deletion_executed":False},
            "source_bundles":{"catalog_count":len(database_catalog_ids) if database_catalog_ids is not None else len(bundles),"physical_receipt_count":len(bundles),"database_catalog_count":len(database_catalog_ids) if database_catalog_ids is not None else None,"physical_receipts_not_in_database_catalog":sorted((known-database_catalog_ids) if database_catalog_ids is not None else set()),"database_catalog_receipts_missing_on_disk":sorted((database_catalog_ids-known) if database_catalog_ids is not None else set()),"used_bundle_ids":sorted(used),"active_task_bundle_ids":sorted(active),"retained_bundle_ids":sorted(retained_ids),"usage_evidence":usage_evidence,"issues":issues},
            "packages":{"items":package_rows,"all_unique_source_protected":all(item["protected"] for item in package_rows)},
            "extracted":{"items":extraction_rows,"preview_reclaimable":[item for item in extraction_rows if not item["protected"]]},
            "metadata":{"snapshots":metadata_rows,"unique_content_hash_count":len([key for key in metadata_hashes if key]),"reused_content_hash_groups":{key:value for key,value in metadata_hashes.items() if key and len(value)>1}},
            "phase1_cache":{"root":str(cache_root.resolve()),"file_count":len(cache_files),"bytes":cache_bytes,"budget_bytes":phase1_cache_budget_bytes,"utilization":utilization,"decision":cache_decision,"reason":cache_reason,"preview_reclaimable":cache_candidates},
        }

    def write_v3_input_storage_preview(self, path: str | Path, *, as_of: date, recent_bundle_count: int = 2, phase1_cache_budget_bytes: int = 2 * 1024**3) -> dict[str, Any]:
        target=self._validate_managed_path(path)
        value=self.preview_v3_input_storage(as_of=as_of,recent_bundle_count=recent_bundle_count,phase1_cache_budget_bytes=phase1_cache_budget_bytes)
        target.parent.mkdir(parents=True,exist_ok=True)
        temporary=target.with_name(target.name+"."+uuid.uuid4().hex+".tmp")
        try:
            temporary.write_text(_payload(value)+"\n",encoding="utf-8")
            with temporary.open("r+b") as handle:
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary,target)
        finally:
            temporary.unlink(missing_ok=True)
        return {"status":"PASS","path":str(target),"preview":value}

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
