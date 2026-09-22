"""Prepare and activate immutable historical analysis snapshots (M7B-06)."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from workbench_db import AnalysisActivationRepository, DuckDBAnalysisActivationRepository
from workbench_db.config_store import default_database_path
from .history_jobs import CONTRACT_VERSION as JOB_CONTRACT_VERSION, HistoryJobError
from .source_freezer import SourceFreezeError, verify_source_manifest


CONTRACT_VERSION = "history-snapshot-activation-v1.0"


class AnalysisActivationError(RuntimeError):
    pass


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _hash(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _manifest_hash(value: dict[str, Any]) -> str:
    body = dict(value)
    body.pop("manifest_hash", None)
    return _hash(body)


class AnalysisActivationService:
    """Turn completed slice references into a new, explicitly bound revision."""

    # MIGRATION_CONTRACT: activation remains MIGRATE_TO_PG until the full
    # multi-table transaction is implemented and rehearsed on PostgreSQL.
    def __init__(
        self,
        root: str | Path,
        database_path: str | Path | None = None,
        *,
        repository: AnalysisActivationRepository | None = None,
    ):
        self.root = Path(root).resolve()
        self._repository = repository or DuckDBAnalysisActivationRepository(self.root, database_path)
        repository_path = getattr(self._repository, "database_path", None)
        self.database_path = (
            Path(database_path).resolve()
            if database_path is not None
            else (Path(repository_path).resolve() if repository_path else None)
        )

    def _connect(self):
        return self._repository.connect()

    def _job(self, job_id: str) -> tuple[str, dict[str, Any], int]:
        with self._connect() as connection:
            row = connection.execute("select status,payload_json from jobs where job_id=?", [job_id]).fetchone()
            attempt = connection.execute("select coalesce(max(attempt),0) from job_attempts where job_id=?", [job_id]).fetchone()[0] if row else 0
        if not row:
            raise AnalysisActivationError("JOB_NOT_FOUND")
        payload = row[1] if isinstance(row[1], dict) else json.loads(row[1])
        if payload.get("job_kind") != "HISTORY_ANALYSIS":
            raise AnalysisActivationError("JOB_KIND_UNSUPPORTED")
        return row[0], payload, int(attempt)

    def _build_manifest(self, job_id: str) -> tuple[dict[str, Any], str, str, str, int]:
        status, payload, attempt = self._job(job_id)
        if status != "SUCCESS":
            raise AnalysisActivationError("ANALYSIS_JOB_NOT_SUCCESS")
        request = payload.get("request", {})
        base_publication_id = str(request.get("base_publication_id") or "")
        completed = sorted(set(str(value) for value in payload.get("completed_slice_ids", [])))
        if not base_publication_id or not completed:
            raise AnalysisActivationError("ANALYSIS_NOT_READY")
        source_manifest_path = self.root / str(request.get("source_manifest_path", ""))
        if not source_manifest_path.is_file():
            raise AnalysisActivationError("SOURCE_MANIFEST_NOT_FOUND")
        try:
            source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
            verification = verify_source_manifest(self.root, source_manifest)
            if verification["status"] != "PASS":
                raise SourceFreezeError("SOURCE_MANIFEST_INPUT_MISMATCH")
        except (OSError, json.JSONDecodeError, SourceFreezeError) as exc:
            raise AnalysisActivationError(f"SOURCE_MANIFEST_INVALID:{exc}") from exc
        if source_manifest.get("manifest_sha256") != request.get("source_manifest_sha256"):
            raise AnalysisActivationError("SOURCE_MANIFEST_REQUEST_MISMATCH")
        if source_manifest.get("publication_id") != base_publication_id:
            raise AnalysisActivationError("SOURCE_MANIFEST_PUBLICATION_MISMATCH")
        with self._connect() as connection:
            publication = connection.execute("select cast(trade_date as varchar),source_revision_id,source_manifest_sha256,source_identity_sha256,computation_identity_sha256,render_identity_sha256,production_version,source_path from publications where publication_id=? and status='SUCCESS'", [base_publication_id]).fetchone()
            rows = connection.execute("select slice_id,domain,cast(trade_date as varchar),input_hash,dependency_hash,logical_hash,row_count from analysis_slices where slice_id in (" + ",".join("?" for _ in completed) + ") order by domain,trade_date,slice_id", completed).fetchall()
        if not publication:
            raise AnalysisActivationError("PUBLICATION_NOT_FOUND")
        if len(rows) != len(completed):
            raise AnalysisActivationError("ANALYSIS_SLICE_NOT_FOUND")
        cutoff = publication[0]
        entries = [{"slice_id": row[0], "domain": row[1], "trade_date": row[2], "input_hash": row[3], "dependency_hash": row[4], "logical_hash": row[5], "row_count": int(row[6])} for row in rows]
        if any(item["trade_date"] > cutoff for item in entries):
            raise AnalysisActivationError("ANALYSIS_DATE_AFTER_CUTOFF")
        keys = [(item["domain"], item["trade_date"]) for item in entries]
        if len(keys) != len(set(keys)):
            raise AnalysisActivationError("ANALYSIS_DUPLICATE_DOMAIN_DATE")
        basis = str(request.get("basis") or "OBSERVED").upper()
        if basis == "AUTO":
            basis = "OBSERVED"
        binding_domain = "LOCAL_OBSERVED" if basis == "OBSERVED" else "LOCAL_RECONSTRUCTED"
        manifest = {
            "contract_version": CONTRACT_VERSION,
            "job_contract_version": JOB_CONTRACT_VERSION,
            "job_id": job_id,
            "job_attempt": attempt,
            "request_identity": payload.get("request_identity"),
            "base_publication_id": base_publication_id,
            "cutoff_date": cutoff,
            "query_start": source_manifest["window"]["read_start"],
            "universe_contract": "CN_A_LISTED_V2",
            "basis": basis,
            "binding_domain": binding_domain,
            "source_manifest_sha256": source_manifest["manifest_sha256"],
            "source_identity_sha256": source_manifest.get("source_identity_sha256"),
            "contract_bundle_id": request.get("contract_bundle_id"),
            "entries": entries,
        }
        manifest["manifest_hash"] = _manifest_hash(manifest)
        snapshot_id = "snapshot-" + manifest["manifest_hash"]
        config_hash = _hash({"contract_bundle_id": request.get("contract_bundle_id"), "domains": payload.get("planned_domains", []), "basis": basis})
        return manifest, snapshot_id, config_hash, binding_domain, attempt

    def prepare(self, job_id: str) -> dict[str, Any]:
        manifest, snapshot_id, config_hash, binding_domain, _ = self._build_manifest(job_id)
        path = self.root / "reports/upgrade_m7" / f"analysis_snapshot_{snapshot_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing != manifest:
                raise AnalysisActivationError("SNAPSHOT_MANIFEST_IMMUTABLE_CONFLICT")
        else:
            descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
            os.close(descriptor)
            temporary = Path(temporary_name)
            try:
                temporary.write_bytes(_json(manifest).encode("utf-8"))
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        with self._connect() as connection:
            connection.execute("begin transaction")
            try:
                connection.execute("insert into analysis_snapshots values (?,?,?,?,?,?,?,?) on conflict(snapshot_id) do nothing", [snapshot_id, date.fromisoformat(manifest["cutoff_date"]), date.fromisoformat(manifest["query_start"]), manifest["universe_contract"], config_hash, manifest["manifest_hash"], "PREPARED", datetime.now(timezone.utc)])
                stored = connection.execute("select cutoff_date,query_start,universe_contract,config_hash,manifest_hash,status from analysis_snapshots where snapshot_id=?", [snapshot_id]).fetchone()
                expected = (date.fromisoformat(manifest["cutoff_date"]), date.fromisoformat(manifest["query_start"]), manifest["universe_contract"], config_hash, manifest["manifest_hash"])
                if not stored or stored[:5] != expected or stored[5] == "FAILED":
                    raise AnalysisActivationError("SNAPSHOT_IDENTITY_CONFLICT")
                for entry in manifest["entries"]:
                    trade_date = date.fromisoformat(entry["trade_date"])
                    existing = connection.execute("select slice_id from analysis_snapshot_entries where snapshot_id=? and domain=? and trade_date=?", [snapshot_id, entry["domain"], trade_date]).fetchone()
                    if existing and existing[0] != entry["slice_id"]:
                        raise AnalysisActivationError("SNAPSHOT_ENTRY_IDENTITY_CONFLICT")
                    if not existing:
                        connection.execute("insert into analysis_snapshot_entries values (?,?,?,?)", [snapshot_id, entry["domain"], trade_date, entry["slice_id"]])
                actual = connection.execute("select domain,cast(trade_date as varchar),slice_id from analysis_snapshot_entries where snapshot_id=? order by domain,trade_date", [snapshot_id]).fetchall()
                expected_entries = sorted((entry["domain"], entry["trade_date"], entry["slice_id"]) for entry in manifest["entries"])
                if actual != expected_entries:
                    raise AnalysisActivationError("SNAPSHOT_ENTRY_SET_MISMATCH")
                connection.execute("commit")
            except Exception:
                connection.execute("rollback")
                raise
        return {"snapshot_id": snapshot_id, "manifest_hash": manifest["manifest_hash"], "manifest_path": path.relative_to(self.root).as_posix(), "binding_domain": binding_domain, "status": stored[5]}

    def _event(self, connection, job_id: str, attempt: int, status: str, **details: Any) -> None:
        sequence = connection.execute("select coalesce(max(sequence),0)+1 from job_events where job_id=? and attempt=?", [job_id, attempt]).fetchone()[0]
        connection.execute("insert into job_events values (?,?,?,?,?)", [job_id, attempt, sequence, datetime.now(timezone.utc), _json({"status": status, **details})])

    def activate(self, job_id: str, *, expected_head_id: str, idempotency_key: str) -> dict[str, Any]:
        if not expected_head_id:
            raise AnalysisActivationError("EXPECTED_HEAD_REQUIRED")
        if not idempotency_key:
            raise AnalysisActivationError("IDEMPOTENCY_KEY_REQUIRED")
        prepared = self.prepare(job_id)
        manifest, snapshot_id, _, binding_domain, attempt = self._build_manifest(job_id)
        activation_identity = _hash({"job_id": job_id, "snapshot_id": snapshot_id, "expected_head_id": expected_head_id, "idempotency_key": idempotency_key})
        new_publication_id = "pub-history-" + snapshot_id.removeprefix("snapshot-")[:32]
        status, payload, _ = self._job(job_id)
        existing_activation = payload.get("activation")
        if existing_activation:
            if existing_activation.get("activation_identity") != activation_identity:
                raise AnalysisActivationError("ACTIVATION_IDENTITY_CONFLICT")
            return {**existing_activation, "reused": True}
        with self._connect() as connection:
            connection.execute("begin transaction")
            try:
                base = connection.execute("select trade_date,source_revision_id,production_version,source_manifest_sha256,source_identity_sha256,render_identity_sha256,source_path from publications where publication_id=? and status='SUCCESS'", [manifest["base_publication_id"]]).fetchone()
                head = connection.execute("select publication_id from publication_heads where trade_date=?", [base[0]]).fetchone() if base else None
                if not base:
                    raise AnalysisActivationError("PUBLICATION_NOT_FOUND")
                if not head or head[0] != expected_head_id:
                    raise AnalysisActivationError("EXPECTED_HEAD_MISMATCH")
                existing_pub = connection.execute("select source_manifest_sha256,source_identity_sha256,computation_identity_sha256 from publications where publication_id=?", [new_publication_id]).fetchone()
                if existing_pub:
                    if existing_pub[2] != manifest["manifest_hash"]:
                        raise AnalysisActivationError("PUBLICATION_IDENTITY_CONFLICT")
                else:
                    revision = int(connection.execute("select coalesce(max(revision),0)+1 from publications where trade_date=?", [base[0]]).fetchone()[0])
                    connection.execute("insert into publications values (?,?,?,?,?,?,?,?,?,?,?,?)", [new_publication_id, base[0], revision, "SUCCESS", base[1], "history-analysis-v1.0", base[3], base[4], manifest["manifest_hash"], base[5], base[6], datetime.now(timezone.utc)])
                    clone_specs = {
                        "stock_daily": "security_id,trade_date,security_name,primary_pattern,payload_json",
                        "sector_daily": "sector_id,trade_date,sector_name,sector_type,primary_pattern,display_rank,payload_json",
                        "candidate_daily": "security_id,trade_date,security_name,primary_pattern,research_priority,payload_json",
                        "market_daily": "trade_date,payload_json",
                        "structure_details": "queue_name,security_id,trade_date,payload_json",
                        "queue_memberships": "queue_name,security_id,queue_tier,source_v2_class,payload_json",
                        "unified_board": "security_id,trade_date,payload_json",
                        "queue_rankings": "security_id,payload_json",
                    }
                    for table, columns in clone_specs.items():
                        connection.execute(f"insert into {table} (publication_id,{columns}) select ?,{columns} from {table} where publication_id=?", [new_publication_id, manifest["base_publication_id"]])
                    connection.execute("insert into publication_artifacts select ?,artifact_name,source_path,file_sha256,logical_digest_version,logical_sha256,row_count,columns_json,primary_key_json from publication_artifacts where publication_id=?", [new_publication_id, manifest["base_publication_id"]])
                    relation_binding = connection.execute(
                        """
                        SELECT source_scope, observation_id, revision_no,
                               attribute_version_id, hierarchy_version
                        FROM relation_publication_bindings
                        WHERE publication_id=?
                        ORDER BY source_scope
                        LIMIT 1
                        """,
                        [manifest["base_publication_id"]],
                    ).fetchone()
                    if relation_binding:
                        connection.execute(
                            """
                            INSERT INTO relation_publication_bindings
                                (publication_id, source_scope, observation_id,
                                 revision_no, attribute_version_id, hierarchy_version)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            [new_publication_id, *relation_binding],
                        )
                    else:
                        # Historical publications still use the immutable
                        # legacy-ID bridge until their source is retired.
                        connection.execute("insert into publication_memberships select ?,membership_snapshot_id from publication_memberships where publication_id=?", [new_publication_id, manifest["base_publication_id"]])
                connection.execute("update analysis_snapshots set status='SUCCESS' where snapshot_id=?", [snapshot_id])
                connection.execute("insert into publication_analysis_snapshots values (?,?,?,?) on conflict(publication_id,domain) do nothing", [new_publication_id, binding_domain, snapshot_id, datetime.now(timezone.utc)])
                bound = connection.execute("select snapshot_id from publication_analysis_snapshots where publication_id=? and domain=?", [new_publication_id, binding_domain]).fetchone()
                if not bound or bound[0] != snapshot_id:
                    raise AnalysisActivationError("PUBLICATION_SNAPSHOT_BINDING_CONFLICT")
                connection.execute("insert into publication_heads values (?,?) on conflict(trade_date) do update set publication_id=excluded.publication_id", [base[0], new_publication_id])
                payload["activation"] = {"activation_identity": activation_identity, "publication_id": new_publication_id, "analysis_snapshot_id": snapshot_id, "manifest_hash": manifest["manifest_hash"], "status": "SUCCESS"}
                connection.execute("update jobs set payload_json=? where job_id=?", [_json(payload), job_id])
                self._event(connection, job_id, attempt, "ACTIVATED", publication_id=new_publication_id, analysis_snapshot_id=snapshot_id)
                connection.execute("commit")
            except Exception:
                connection.execute("rollback")
                raise
        return {"activation_identity": activation_identity, "publication_id": new_publication_id, "analysis_snapshot_id": snapshot_id, "manifest_hash": manifest["manifest_hash"], "status": "SUCCESS", "reused": False}
