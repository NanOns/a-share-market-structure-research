"""Persistent HISTORY_ANALYSIS task state for M7B-05."""
from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

import duckdb

from workbench_db import DuckDBHistoryJobRepository, HistoryJobRepository
from workbench_db.history_job_repository import HistoryJobStore
from .source_freezer import SourceFreezeError, verify_source_manifest


CONTRACT_VERSION = "history-job-state-v1.0"
JOB_KIND = "HISTORY_ANALYSIS"
TERMINAL_STATUSES = {"SUCCESS", "FAILED", "CANCELLED"}


class HistoryJobError(RuntimeError):
    pass


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _hash(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


class HistoryJobService:
    """A small persisted state machine with cooperative cancellation."""

    # MIGRATION_CONTRACT: history job state remains MIGRATE_TO_PG until its
    # queue, event, cancellation and recovery transactions pass PG rehearsal.
    def __init__(self, root: str | Path, database_path: str | Path | None = None, *, worker: Callable[[str, Mapping[str, Any]], Any] | None = None, repository: HistoryJobRepository | None = None):
        self.root = Path(root).resolve()
        self._repository = repository or DuckDBHistoryJobRepository(self.root, database_path)
        repository_path = getattr(self._repository, "database_path", None)
        self.database_path = Path(database_path).resolve() if database_path else (Path(repository_path).resolve() if repository_path else None)
        self.worker = worker
        self._threads: dict[str, threading.Thread] = {}
        self._cancel: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def _write_with_retry(self, operation: Callable[[HistoryJobStore], None]) -> None:
        """Retry short DuckDB state transitions when a cancel races with progress."""
        last_error: Exception | None = None
        for _ in range(50):
            try:
                with self._repository.transaction() as store:
                    operation(store)
                return
            except duckdb.TransactionException as exc:
                last_error = exc
                time.sleep(0.02)
        if last_error is not None:
            raise last_error

    def _manifest_for(self, publication_id: str) -> tuple[dict[str, Any], str, str]:
        with self._repository.transaction() as store:
            try:
                cutoff, source_identity = store.publication_source_identity(publication_id)
            except KeyError as exc:
                raise HistoryJobError("PUBLICATION_NOT_FOUND") from exc
        paths = sorted((self.root / "reports/upgrade_m7").glob(f"source_manifest_{str(cutoff).replace('-', '')}*.json"))
        if not paths:
            raise HistoryJobError("SOURCE_MANIFEST_NOT_FOUND")
        selected = None
        for path in paths:
            try:
                candidate = json.loads(path.read_text(encoding="utf-8"))
                if candidate.get("publication_id") != publication_id or candidate.get("cutoff_date") != cutoff:
                    continue
                if source_identity and candidate.get("source_identity_sha256") != source_identity:
                    continue
                verification = verify_source_manifest(self.root, candidate)
                if verification["status"] == "PASS":
                    selected = (candidate, path)
            except (OSError, json.JSONDecodeError, SourceFreezeError):
                continue
        if not selected:
            raise HistoryJobError("SOURCE_MANIFEST_INVALID_OR_IDENTITY_MISMATCH")
        manifest, path = selected
        return manifest, cutoff, path.relative_to(self.root).as_posix()

    def _validate_request(self, request: Mapping[str, Any]) -> tuple[dict[str, Any], str, str, str]:
        publication_id = str(request.get("base_publication_id") or "")
        if not publication_id:
            raise HistoryJobError("BASE_PUBLICATION_REQUIRED")
        basis = str(request.get("basis") or "AUTO").upper()
        if basis not in {"AUTO", "OBSERVED", "RECONSTRUCTED"}:
            raise HistoryJobError("BASIS_UNSUPPORTED")
        try:
            output_days = int(request.get("output_days", 250))
        except (TypeError, ValueError) as exc:
            raise HistoryJobError("OUTPUT_DAYS_INVALID") from exc
        if output_days < 1 or output_days > 250:
            raise HistoryJobError("OUTPUT_DAYS_OUT_OF_RANGE")
        domains = request.get("domains")
        if not isinstance(domains, list) or not domains or any(not str(value) for value in domains):
            raise HistoryJobError("DOMAINS_REQUIRED")
        idempotency_key = str(request.get("idempotency_key") or "")
        if not idempotency_key:
            raise HistoryJobError("IDEMPOTENCY_KEY_REQUIRED")
        manifest, cutoff, manifest_path = self._manifest_for(publication_id)
        if output_days > int(manifest.get("window", {}).get("output_days", 0)):
            raise HistoryJobError("SOURCE_WINDOW_TOO_SHORT")
        normalized = {"base_publication_id": publication_id, "basis": "OBSERVED" if basis == "AUTO" else basis, "output_days": output_days, "domains": sorted(set(str(value) for value in domains)), "membership_snapshot_id": request.get("membership_snapshot_id"), "contract_bundle_id": str(request.get("contract_bundle_id") or ""), "source_manifest_path": manifest_path, "source_manifest_sha256": manifest["manifest_sha256"], "slice_ids": sorted(set(str(value) for value in request.get("slice_ids", [])))}
        request_identity = _hash(normalized)
        job_key = "history-" + _hash({"request_identity": request_identity, "idempotency_key": idempotency_key})[:32]
        return normalized, request_identity, job_key, cutoff

    def _payload(self, normalized: Mapping[str, Any], request_identity: str, *, completed: list[str] | None = None, cancel_requested: bool = False) -> dict[str, Any]:
        return {"contract": CONTRACT_VERSION, "job_kind": JOB_KIND, "request_identity": request_identity, "request": dict(normalized), "planned_domains": list(normalized["domains"]), "completed_slice_ids": sorted(set(completed or [])), "cancel_requested": cancel_requested}

    def submit(self, request: Mapping[str, Any]) -> dict[str, Any]:
        normalized, request_identity, job_key, _ = self._validate_request(request)
        job_id = "job-history-" + uuid.uuid4().hex
        existing_id: str | None = None
        with self._repository.transaction() as store:
            existing = store.job_by_key(job_key)
            if existing:
                existing_id = existing["job_id"]
            else:
                payload = self._payload(normalized, request_identity)
                store.upsert_job(job_id=job_id, job_key=job_key, status="QUEUED", payload=payload)
                store.upsert_attempt(job_id=job_id, attempt=1, status="QUEUED", payload={"attempt": 1, "progress": {"stage": "QUEUED", "completed": 0, "total": len(normalized["slice_ids"])}})
                store.append_event(job_id=job_id, attempt=1, status="QUEUED", details={"job_kind": JOB_KIND, "request_identity": request_identity})
        if existing_id:
            result = self.status(existing_id)
            result["reused_submission"] = True
            return result
        self._start(job_id, 1)
        return self.status(job_id)

    def _start(self, job_id: str, attempt: int) -> None:
        with self._lock:
            thread = self._threads.get(job_id)
            if thread and thread.is_alive():
                return
            self._cancel.setdefault(job_id, threading.Event()).clear()
            thread = threading.Thread(target=self._run, args=(job_id, attempt), daemon=True, name=job_id)
            self._threads[job_id] = thread
            thread.start()

    def _load(self, job_id: str) -> tuple[str, dict[str, Any], int, dict[str, Any]]:
        with self._repository.transaction() as store:
            row = store.job(job_id)
            if not row:
                raise HistoryJobError("JOB_NOT_FOUND")
            attempt = store.latest_attempt(job_id)
        return row["status"], row["payload"], int(attempt["attempt"] if attempt else 0), attempt["payload"] if attempt else {}

    def _run(self, job_id: str, attempt: int) -> None:
        try:
            self._write_with_retry(lambda store: (store.update_job(job_id, status="RUNNING"), store.update_attempt(job_id, attempt, status="RUNNING"), store.append_event(job_id=job_id, attempt=attempt, status="RUNNING")))
            _, payload, _, _ = self._load(job_id)
            completed = set(payload.get("completed_slice_ids", []))
            units = list(payload.get("request", {}).get("slice_ids", []))
            for index, slice_id in enumerate(units, start=1):
                if self._cancel.get(job_id, threading.Event()).is_set() or self._cancel_requested(job_id):
                    self._finish(job_id, attempt, "CANCELLED", error={"code": "CANCELLED_AT_BATCH_BOUNDARY"}, completed=completed, stage="CANCELLED")
                    return
                with self._repository.transaction() as store:
                    domain = store.slice_domain(slice_id)
                if not domain:
                    raise HistoryJobError(f"SLICE_NOT_FOUND:{slice_id}")
                if domain not in payload.get("planned_domains", []):
                    raise HistoryJobError(f"SLICE_DOMAIN_NOT_PLANNED:{slice_id}")
                if slice_id not in completed:
                    if self.worker:
                        self.worker(slice_id, payload["request"])
                    completed.add(slice_id)
                    self._progress(job_id, attempt, completed, len(units), f"SLICE_{index}_SEALED")
            self._finish(job_id, attempt, "SUCCESS", completed=completed, stage="COMPLETED" if units else "PLANNED_ONLY")
        except Exception as exc:
            self._finish(job_id, attempt, "FAILED", error={"type": type(exc).__name__, "message": str(exc)}, completed=self._completed(job_id), stage="FAILED")

    def _completed(self, job_id: str) -> set[str]:
        try:
            return set(self._load(job_id)[1].get("completed_slice_ids", []))
        except HistoryJobError:
            return set()

    def _cancel_requested(self, job_id: str) -> bool:
        try:
            return bool(self._load(job_id)[1].get("cancel_requested"))
        except HistoryJobError:
            return False

    def _progress(self, job_id: str, attempt: int, completed: set[str], total: int, stage: str) -> None:
        def write_progress(store: HistoryJobStore):
            row = store.job(job_id)
            if not row:
                return
            payload = row["payload"]
            payload["completed_slice_ids"] = sorted(completed)
            progress = {"stage": stage, "completed": len(completed), "total": total, "updated_at_utc": datetime.now(timezone.utc).isoformat()}
            payload["progress"] = progress
            store.update_job(job_id, payload=payload)
            store.update_attempt(job_id, attempt, payload={"attempt": attempt, "progress": progress})
            store.append_event(job_id=job_id, attempt=attempt, status=stage, details={"completed_slice_ids": sorted(completed), "progress": progress})
        self._write_with_retry(write_progress)

    def _finish(self, job_id: str, attempt: int, status: str, *, completed: set[str], stage: str, error: dict[str, Any] | None = None) -> None:
        def write_finish(store: HistoryJobStore):
            row = store.job(job_id)
            if not row:
                return
            payload = row["payload"]
            payload["completed_slice_ids"] = sorted(completed)
            payload["progress"] = {"stage": stage, "completed": len(completed), "total": len(payload.get("request", {}).get("slice_ids", [])), "updated_at_utc": datetime.now(timezone.utc).isoformat()}
            if error:
                payload["error"] = error
            store.update_job(job_id, status=status, payload=payload)
            attempt_payload = {"attempt": attempt, "progress": payload["progress"]}
            if error:
                attempt_payload["error"] = error
            store.update_attempt(job_id, attempt, status=status, payload=attempt_payload)
            store.append_event(job_id=job_id, attempt=attempt, status=status, details={"completed_slice_ids": sorted(completed), "error": error})
        self._write_with_retry(write_finish)

    def status(self, job_id: str) -> dict[str, Any]:
        status, payload, attempt, attempt_payload = self._load(job_id)
        with self._repository.transaction() as store:
            latest_event = store.latest_event(job_id)
        return {"job_id": job_id, "job_kind": payload.get("job_kind", JOB_KIND), "status": status, "attempt": attempt, "request_identity": payload.get("request_identity"), "planned_domains": payload.get("planned_domains", []), "completed_slice_ids": payload.get("completed_slice_ids", []), "progress": payload.get("progress", attempt_payload.get("progress", {})), "error": payload.get("error", attempt_payload.get("error")), "latest_event": latest_event["payload"] if latest_event else None, "activation": payload.get("activation"), "updated_at_utc": payload.get("progress", {}).get("updated_at_utc")}

    def cancel(self, job_id: str, expected_attempt: int | None = None) -> dict[str, Any]:
        status, payload, attempt, _ = self._load(job_id)
        if expected_attempt is not None and int(expected_attempt) != attempt:
            raise HistoryJobError("ATTEMPT_MISMATCH")
        if status in TERMINAL_STATUSES:
            raise HistoryJobError("JOB_NOT_CANCELLABLE")
        def write_cancel(store: HistoryJobStore):
            payload["cancel_requested"] = True
            store.update_job(job_id, payload=payload)
            store.append_event(job_id=job_id, attempt=attempt, status="CANCEL_REQUESTED")
        self._write_with_retry(write_cancel)
        self._cancel.setdefault(job_id, threading.Event()).set()
        return self.status(job_id)

    def recover_interrupted(self, *, background: bool = False) -> list[dict[str, Any]]:
        with self._repository.transaction() as store:
            running = [job_id for job_id in store.active_history_jobs(JOB_KIND) if (store.job(job_id) or {}).get("status") == "RUNNING"]
            for job_id in running:
                attempt = store.latest_attempt(job_id)
                if not attempt:
                    continue
                store.update_job(job_id, status="INTERRUPTED")
                store.update_attempt(job_id, int(attempt["attempt"]), status="INTERRUPTED")
                store.append_event(job_id=job_id, attempt=int(attempt["attempt"]), status="INTERRUPTED")
        return [self.resume(job_id) if background else self.status(job_id) for job_id in running]

    def resume(self, job_id: str) -> dict[str, Any]:
        status, payload, _, _ = self._load(job_id)
        if status != "INTERRUPTED":
            raise HistoryJobError("JOB_NOT_INTERRUPTED")
        with self._repository.transaction() as store:
            attempt = store.next_attempt(job_id)
            payload["cancel_requested"] = False
            store.update_job(job_id, status="QUEUED", payload=payload)
            store.upsert_attempt(job_id=job_id, attempt=attempt, status="QUEUED", payload={"attempt": attempt, "progress": {"stage": "QUEUED", "completed": len(payload.get("completed_slice_ids", [])), "total": len(payload.get("request", {}).get("slice_ids", []))}})
            store.append_event(job_id=job_id, attempt=attempt, status="RESUMED")
        self._start(job_id, attempt)
        return self.status(job_id)
