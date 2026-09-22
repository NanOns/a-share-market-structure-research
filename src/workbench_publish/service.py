"""M4 one-click background publication with transactional recovery."""
from __future__ import annotations

import hashlib
import json
import threading
import pyarrow as pa
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from workbench_db import (
    DuckDBPublicationRepositoryFactory,
    DuckDBPublicationStatusReader,
    PublicationRepositoryFactory,
    PublicationStatusReader,
)
from workbench_input import verify_source_bundle
from workbench_service.legacy_relation_import import LEGACY_SOURCE_SCOPE
from workbench_service.relation_repository import RelationRepository

CONTRACT_VERSION = "m4-one-click-publication-contract-v1.1"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _hash(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


class SimulatedCrash(RuntimeError):
    """Fault-injection exception used by recovery acceptance tests."""


@dataclass(frozen=True)
class PublicationRequest:
    trade_date: date
    source_bundle_id: str
    economic_model_id: str
    computation_contract_id: str
    release_id: str | None = None
    stocks: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    sectors: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    candidates: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    structures: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    queue_memberships: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    unified_board: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    queue_rankings: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    memberships: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    observations: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    outcomes: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    @property
    def job_key(self) -> str:
        # Display-only changes intentionally do not participate.
        return _hash({"trade_date": self.trade_date.isoformat(), "source_bundle_id": self.source_bundle_id,
                      "economic_model_id": self.economic_model_id,
                      "computation_contract_id": self.computation_contract_id})

    @property
    def publication_id(self) -> str:
        return self.release_id or "pub-" + self.job_key[:32]

    def persisted(self, *, include_results: bool=True) -> dict[str, Any]:
        return {"trade_date":self.trade_date.isoformat(),"source_bundle_id":self.source_bundle_id,"economic_model_id":self.economic_model_id,"computation_contract_id":self.computation_contract_id,"release_id":self.release_id,
                **({name:list(getattr(self,name)) for name in ("stocks","sectors","candidates","structures","queue_memberships","unified_board","queue_rankings","memberships","observations","outcomes")} if include_results else {})}

    @classmethod
    def restore(cls, value: dict[str, Any]) -> "PublicationRequest":
        return cls(trade_date=date.fromisoformat(value["trade_date"]),source_bundle_id=value["source_bundle_id"],economic_model_id=value["economic_model_id"],computation_contract_id=value["computation_contract_id"],release_id=value.get("release_id"),
                   **{name:tuple(value.get(name,[])) for name in ("stocks","sectors","candidates","structures","queue_memberships","unified_board","queue_rankings","memberships","observations","outcomes")})


class OneClickPublisher:
    # MIGRATION_CONTRACT: publisher remains MIGRATE_TO_PG until a PostgreSQL
    # repository factory and status reader pass the publication rehearsal.
    def __init__(
        self,
        root: str | Path,
        database_path: str | Path | None = None,
        bundle_verifier: Callable[[Path],dict[str,Any]]=verify_source_bundle,
        *,
        repository_factory: PublicationRepositoryFactory | None = None,
        status_reader: PublicationStatusReader | None = None,
    ):
        self.root = Path(root).resolve()
        self._repository_factory = repository_factory or DuckDBPublicationRepositoryFactory(self.root, database_path)
        self.database_path = Path(database_path).resolve() if database_path else self._repository_factory.database_path
        self._status_reader = status_reader or DuckDBPublicationStatusReader(self.root, self.database_path)
        self._threads: dict[str, threading.Thread] = {}
        self._progress: dict[str, dict[str, Any]] = {}
        self.bundle_verifier=bundle_verifier

    @contextmanager
    def _open_repository(self, *, timeout_seconds: float = 15.0):
        """Open the configured repository through the backend boundary."""
        with self._repository_factory.open(timeout_seconds=timeout_seconds) as repository:
            yield repository

    def _event(self, con, job_id: str, attempt: int, status: str, **details: Any) -> None:
        seq = con.execute("SELECT coalesce(max(sequence),0)+1 FROM job_events WHERE job_id=? AND attempt=?", [job_id, attempt]).fetchone()[0]
        con.execute("INSERT INTO job_events VALUES (?, ?, ?, ?, ?)", [job_id, attempt, seq, datetime.now(timezone.utc), _json({"status": status, **details})])

    @staticmethod
    def _write_relation_binding(
        con,
        publication_id: str,
        trade_date: date,
        source_bundle_id: str,
        memberships: tuple[dict[str, Any], ...],
    ) -> dict[str, Any] | None:
        if not memberships:
            return None
        existing = con.execute(
            "SELECT observation_id, revision_no, attribute_version_id, hierarchy_version FROM relation_publication_bindings WHERE publication_id=? AND source_scope=?",
            [publication_id, LEGACY_SOURCE_SCOPE],
        ).fetchone()
        if existing:
            return {
                "status": "EXISTING",
                "observation_id": str(existing[0]),
                "revision_no": int(existing[1]),
                "attribute_version_id": existing[2],
                "hierarchy_version": existing[3],
            }

        def source_kind(row: dict[str, Any]) -> str | None:
            source = str(row.get("source") or "").strip().lower()
            if source == "tdxhy.cfg:derived_parent":
                return None
            if source in {"tdxhy.cfg", "infoharbor_block.dat"} or not source:
                return "DIRECT"
            return "LEGACY_EXPLICIT"

        edges = []
        attributes = {}
        for row in memberships:
            kind = source_kind(row)
            if kind is not None:
                edges.append({"sector_id": row.get("sector_id"), "security_id": row.get("security_id"), "source_kind": kind})
            sector_id = str(row.get("sector_id") or "").strip()
            if sector_id:
                attributes[sector_id] = {
                    "sector_id": sector_id,
                    "name": row.get("sector_name") or sector_id,
                    "type": row.get("sector_type") or sector_id.split(":", 1)[0].upper(),
                    "role": row.get("sector_role"),
                    "semantic_bucket": row.get("semantic_bucket"),
                }
        if not edges:
            raise ValueError("PUBLICATION_RELATION_SOURCE_EMPTY")
        observation_id = f"relation-publication-observation-{publication_id}"
        recorded = RelationRepository(con).record_observation(
            source_scope=LEGACY_SOURCE_SCOPE,
            edges=edges,
            attributes=tuple(attributes.values()),
            observed_at=datetime.now(timezone.utc),
            source_effective_date=trade_date,
            source_file_hashes={"source_bundle_id": source_bundle_id, "membership_rows": len(memberships)},
            observation_id=observation_id,
            manage_transaction=False,
        )
        if recorded["status"] not in {"UPDATED", "UNCHANGED"}:
            raise ValueError(f"PUBLICATION_RELATION_NOT_READY:{recorded['status']}")
        con.execute(
            """
            INSERT INTO relation_publication_bindings
                (publication_id, source_scope, observation_id, revision_no,
                 attribute_version_id, hierarchy_version)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                publication_id,
                LEGACY_SOURCE_SCOPE,
                observation_id,
                recorded["revision_no"],
                recorded.get("attribute_version_id"),
                None,
            ],
        )
        return {
            "status": recorded["status"],
            "observation_id": observation_id,
            "revision_no": recorded["revision_no"],
            "attribute_version_id": recorded.get("attribute_version_id"),
            "hierarchy_version": None,
        }

    @staticmethod
    def _bulk(con, name: str, table: str, columns: list[str], rows: list[dict[str,Any]]) -> None:
        if not rows:return
        batch=pa.Table.from_pylist(rows);con.register(name,batch)
        try:
            select=",".join(f"{column}::JSON" if column=="payload_json" else column for column in columns)
            con.execute(f"INSERT INTO {table} ({','.join(columns)}) SELECT {select} FROM {name}")
        finally:con.unregister(name)

    def submit(self, request: PublicationRequest, compute: Callable[[PublicationRequest], PublicationRequest] | None = None) -> str:
        job_id = "job-" + request.job_key[:32]
        # Avoid contending for the single-writer database while this process is
        # already computing exactly the same immutable request.
        active=self._threads.get(job_id)
        if active and active.is_alive():
            return job_id
        with self._open_repository() as repo:
            con = repo.connection
            assert con is not None
            row = con.execute("SELECT job_id,status FROM jobs WHERE job_key=?", [request.job_key]).fetchone()
            if row and row[1] in ("SUCCESS", "QUEUED", "RUNNING"):
                return row[0]
            con.execute("INSERT INTO jobs VALUES (?, ?, 'QUEUED', ?) ON CONFLICT(job_key) DO UPDATE SET status='QUEUED',payload_json=excluded.payload_json", [job_id, request.job_key, _json({"contract": CONTRACT_VERSION, "publication_id": request.publication_id,"request":request.persisted()})])
        self._progress[job_id]={"status":"QUEUED"}
        thread = threading.Thread(target=self.run, args=(request, compute), daemon=True, name=job_id)
        self._threads[job_id] = thread
        thread.start()
        return job_id

    def wait(self, job_id: str, timeout: float = 30) -> dict[str, Any]:
        thread = self._threads.get(job_id)
        if thread:
            thread.join(timeout)
        return self.status(job_id)

    def status(self, job_id: str) -> dict[str, Any]:
        cached=self._progress.get(job_id)
        if cached and cached.get("status") in ("QUEUED","COMPUTING","COMMITTING"):
            return {"job_id":job_id,"status":"RUNNING" if cached["status"]!="QUEUED" else "QUEUED","details":{},"progress":cached,"updated_at_utc":cached.get("updated_at_utc")}
        if cached and cached.get("status") in ("SUCCESS", "FAILED"):
            return {"job_id": job_id, "status": cached["status"], "publication_id": cached.get("publication_id"),
                    "details": {}, "progress": cached, "updated_at_utc": cached.get("updated_at_utc")}
        # Status is a read path and must stay backend-neutral for the PG cutover.
        return self._status_reader.read(job_id)

    def recover_interrupted(self, compute: Callable[[PublicationRequest], PublicationRequest] | None=None, *, background: bool=False) -> list[dict[str, Any]]:
        with self._open_repository() as repo:
            rows=repo.connection.execute("SELECT job_id,payload_json FROM jobs WHERE status IN ('QUEUED','RUNNING','INTERRUPTED') ORDER BY job_id").fetchall()
            repo.connection.execute("UPDATE jobs SET status='INTERRUPTED' WHERE status='RUNNING'")
            repo.connection.execute("UPDATE job_attempts SET status='INTERRUPTED' WHERE status='RUNNING'")
        results=[]
        for job_id,payload in rows:
            request=PublicationRequest.restore(json.loads(payload)["request"])
            if background:
                thread=threading.Thread(target=self.run,args=(request,compute),daemon=True,name=job_id)
                self._threads[job_id]=thread; thread.start()
                results.append({"job_id":job_id,"status":"QUEUED","recovered":True})
            else:
                results.append(self.run(request,compute))
        return results

    def run(self, request: PublicationRequest, compute: Callable[[PublicationRequest], PublicationRequest] | None = None,
            crash_at: str | None = None) -> dict[str, Any]:
        job_id = "job-" + request.job_key[:32]
        self._progress[job_id]={"status":"COMPUTING","updated_at_utc":datetime.now(timezone.utc).isoformat()}
        # Recover a commit whose acknowledgement was lost.
        with self._open_repository() as repo:
            con = repo.connection
            existing = con.execute("SELECT status FROM publications WHERE publication_id=?", [request.publication_id]).fetchone()
            if existing and existing[0] == "SUCCESS":
                with repo.transaction() as tx:
                    tx.execute("UPDATE jobs SET status='SUCCESS' WHERE job_id=?", [job_id])
                self._progress[job_id]={"status":"SUCCESS","publication_id":request.publication_id,"updated_at_utc":datetime.now(timezone.utc).isoformat()}
                return {"job_id": job_id, "publication_id": request.publication_id, "status": "SUCCESS", "recovered": True}
            attempt = int(con.execute("SELECT coalesce(max(attempt),0)+1 FROM job_attempts WHERE job_id=?", [job_id]).fetchone()[0])
            con.execute("INSERT INTO jobs VALUES (?, ?, 'RUNNING', ?) ON CONFLICT(job_key) DO UPDATE SET status='RUNNING',payload_json=excluded.payload_json", [job_id, request.job_key, _json({"contract": CONTRACT_VERSION, "publication_id": request.publication_id,"request":request.persisted()})])
            con.execute("INSERT INTO job_attempts VALUES (?, ?, 'RUNNING', ?)", [job_id, attempt, _json({"started_at_utc": datetime.now(timezone.utc)})])
            self._event(con, job_id, attempt, "COMPUTING")
        try:
            bundle_path=self.root/"data/source_bundles"/request.source_bundle_id/"source_bundle.json"
            verified=self.bundle_verifier(bundle_path)
            if verified["source_bundle_id"]!=request.source_bundle_id: raise ValueError("SOURCE_BUNDLE_IDENTITY_MISMATCH")
            prepared = compute(request) if compute else request
            self._validate(request, prepared)
            publication_id=prepared.publication_id
            self._progress[job_id]={"status":"COMMITTING","publication_id":publication_id,"updated_at_utc":datetime.now(timezone.utc).isoformat()}
            with self._open_repository() as repo:
                attempt=int(repo.connection.execute("SELECT max(attempt) FROM job_attempts WHERE job_id=?",[job_id]).fetchone()[0])
                self._event(repo.connection,job_id,attempt,"COMMITTING",publication_id=publication_id)
            if crash_at == "before_commit":
                raise SimulatedCrash("CRASH_BEFORE_COMMIT")
            with self._open_repository() as repo:
                with repo.transaction() as con:
                    already=con.execute("SELECT status FROM publications WHERE publication_id=?",[publication_id]).fetchone()
                    if already and already[0]=="SUCCESS":
                        if prepared.memberships:
                            self._write_relation_binding(con,publication_id,request.trade_date,request.source_bundle_id,prepared.memberships)
                        con.execute("UPDATE job_attempts SET status='SUCCESS' WHERE job_id=? AND attempt=?", [job_id, attempt])
                        con.execute("UPDATE jobs SET status='SUCCESS',payload_json=? WHERE job_id=?",[_json({"contract":CONTRACT_VERSION,"publication_id":publication_id,"request":prepared.persisted(include_results=False)}),job_id])
                        self._event(con, job_id, attempt, "COMMITTED", publication_id=publication_id)
                        return {"job_id":job_id,"publication_id":publication_id,"status":"SUCCESS","recovered":True}
                    revision = int(con.execute("SELECT coalesce(max(revision),0)+1 FROM publications WHERE trade_date=?", [request.trade_date]).fetchone()[0])
                    con.execute("INSERT INTO publications VALUES (?, ?, ?, 'SUCCESS', NULL, ?, ?, ?, ?, NULL, ?, ?)",
                                [publication_id, request.trade_date, revision, CONTRACT_VERSION, request.source_bundle_id,
                                 request.economic_model_id, request.computation_contract_id, str(self.root / "data/source_bundles" / request.source_bundle_id), datetime.now(timezone.utc)])
                    self._bulk(con,"_m4_stocks","stock_daily",["publication_id","security_id","trade_date","security_name","primary_pattern","payload_json"],[{"publication_id":publication_id,"security_id":r["security_id"],"trade_date":request.trade_date,"security_name":r.get("security_name"),"primary_pattern":r.get("primary_pattern"),"payload_json":_json(r)} for r in prepared.stocks])
                    self._bulk(con,"_m4_sectors","sector_daily",["publication_id","sector_id","trade_date","sector_name","sector_type","primary_pattern","display_rank","payload_json"],[{"publication_id":publication_id,"sector_id":r["sector_id"],"trade_date":request.trade_date,"sector_name":r.get("sector_name"),"sector_type":r.get("sector_type"),"primary_pattern":r.get("primary_pattern"),"display_rank":float(r["display_rank"]) if r.get("display_rank") not in (None,"") else None,"payload_json":_json(r)} for r in prepared.sectors])
                    self._bulk(con,"_m4_candidates","candidate_daily",["publication_id","security_id","trade_date","security_name","primary_pattern","research_priority","payload_json"],[{"publication_id":publication_id,"security_id":r["security_id"],"trade_date":request.trade_date,"security_name":r.get("security_name"),"primary_pattern":r.get("primary_pattern"),"research_priority":r.get("research_priority"),"payload_json":_json(r)} for r in prepared.candidates])
                    self._bulk(con,"_m4_structures","structure_details",["publication_id","queue_name","security_id","trade_date","payload_json"],[{"publication_id":publication_id,"queue_name":r["queue_name"],"security_id":r["security_id"],"trade_date":request.trade_date,"payload_json":_json(r)} for r in prepared.structures])
                    self._bulk(con,"_m4_queue_members","queue_memberships",["publication_id","queue_name","security_id","queue_tier","source_v2_class","payload_json"],[{"publication_id":publication_id,"queue_name":r["queue_name"],"security_id":r["security_id"],"queue_tier":r["queue_tier"],"source_v2_class":r.get("source_v2_class"),"payload_json":_json(r)} for r in prepared.queue_memberships])
                    self._bulk(con,"_m4_board","unified_board",["publication_id","security_id","trade_date","payload_json"],[{"publication_id":publication_id,"security_id":r["security_id"],"trade_date":request.trade_date,"payload_json":_json(r)} for r in prepared.unified_board])
                    self._bulk(con,"_m4_rankings","queue_rankings",["publication_id","security_id","payload_json"],[{"publication_id":publication_id,"security_id":r["security_id"],"payload_json":_json(r)} for r in prepared.queue_rankings])
                    if prepared.memberships:
                        self._write_relation_binding(con,publication_id,request.trade_date,request.source_bundle_id,prepared.memberships)
                    self._bulk(con,"_m4_observations","observations",["observation_id","publication_id","payload_json"],[{"observation_id":r.get("observation_id") or _hash({"publication_id":publication_id,**r}),"publication_id":publication_id,"payload_json":_json(r)} for r in prepared.observations])
                    for row in prepared.outcomes:
                        bound=con.execute("SELECT 1 FROM observations WHERE observation_id=?",[row["observation_id"]]).fetchone()
                        if not bound: raise ValueError("OUTCOME_OBSERVATION_MISSING")
                        key=[row["observation_id"], row["horizon"], row["target_revision"]]
                        payload=_json(row)
                        existing_outcome=con.execute("SELECT payload_json FROM outcomes WHERE observation_id=? AND horizon=? AND target_revision=?",key).fetchone()
                        if existing_outcome and str(existing_outcome[0])!=payload:
                            raise ValueError("OUTCOME_IDENTITY_CONFLICT")
                        if not existing_outcome:
                            con.execute("INSERT INTO outcomes VALUES (?, ?, ?, ?)", [*key, payload])
                    con.execute("INSERT INTO publication_heads VALUES (?, ?) ON CONFLICT(trade_date) DO UPDATE SET publication_id=excluded.publication_id", [request.trade_date, publication_id])
                    con.execute("UPDATE job_attempts SET status='SUCCESS' WHERE job_id=? AND attempt=?", [job_id, attempt])
                    con.execute("UPDATE jobs SET status='SUCCESS',payload_json=? WHERE job_id=?", [_json({"contract":CONTRACT_VERSION,"publication_id":publication_id,"request":prepared.persisted(include_results=False)}),job_id])
                    self._event(con, job_id, attempt, "COMMITTED", publication_id=publication_id)
            if crash_at == "after_commit":
                raise SimulatedCrash("CRASH_AFTER_COMMIT")
            self._progress[job_id]={"status":"SUCCESS","publication_id":publication_id,"updated_at_utc":datetime.now(timezone.utc).isoformat()}
            return {"job_id": job_id, "publication_id": publication_id, "status": "SUCCESS", "recovered": False}
        except SimulatedCrash:
            if crash_at == "before_commit":
                with self._open_repository() as repo:
                    repo.connection.execute("UPDATE job_attempts SET status='INTERRUPTED' WHERE job_id=? AND attempt=?", [job_id, attempt])
                    repo.connection.execute("UPDATE jobs SET status='INTERRUPTED' WHERE job_id=?", [job_id])
            raise
        except Exception as exc:
            self._progress[job_id]={"status":"FAILED","error":str(exc),"updated_at_utc":datetime.now(timezone.utc).isoformat()}
            with self._open_repository() as repo:
                repo.connection.execute("UPDATE job_attempts SET status='FAILED', payload_json=? WHERE job_id=? AND attempt=?", [_json({"error": type(exc).__name__, "message": str(exc)}), job_id, attempt])
                repo.connection.execute("UPDATE jobs SET status='FAILED' WHERE job_id=?", [job_id])
                self._event(repo.connection, job_id, attempt, "FAILED", error=f"{type(exc).__name__}: {exc}")
            raise

    @staticmethod
    def _validate(original: PublicationRequest, prepared: PublicationRequest) -> None:
        if prepared.job_key != original.job_key:
            raise ValueError("COMPUTE_IDENTITY_CHANGED")
        ids = [row.get("security_id") for row in prepared.stocks]
        if any(not value for value in ids) or len(ids) != len(set(ids)):
            raise ValueError("INVALID_OR_DUPLICATE_SECURITY_ID")
        observation_ids = [row.get("observation_id") or _hash({"publication_id": original.publication_id, **row}) for row in prepared.observations]
        if len(observation_ids) != len(set(observation_ids)):
            raise ValueError("DUPLICATE_OBSERVATION_ID")
        for rows,key in ((prepared.sectors,"sector_id"),(prepared.candidates,"security_id"),(prepared.unified_board,"security_id"),(prepared.queue_rankings,"security_id")):
            values=[row.get(key) for row in rows]
            if any(not x for x in values) or len(values)!=len(set(values)): raise ValueError("INVALID_OR_DUPLICATE_RESULT_KEY")
