"""Lifecycle extension around the unchanged accepted daily-job contract."""
import sqlite3
import threading
from workbench_analysis.operational_daily_jobs_v1 import DailyJobs


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


class ManagedDailyJobs(DailyJobs):
    def __init__(self, root, executor=None, **kwargs):
        self.admission = threading.RLock()
        self.busy = threading.Event()
        self.original_executor = executor
        super().__init__(root, executor=self.execute, **kwargs)
        # Maintenance is recorded using the existing INTERRUPTED recovery state.
        # User CANCELLED/CANCEL_REQUESTED records are deliberately not touched.
        with self.connect() as db:
            ids = [r[0] for r in db.execute("SELECT job_id FROM update_jobs WHERE status='INTERRUPTED' AND error='MAINTENANCE_INTERRUPTED'")]
            for job in ids:
                db.execute("UPDATE update_jobs SET status='QUEUED',error=NULL,finished_at=NULL WHERE job_id=?", (job,))
                db.execute("UPDATE update_job_days SET state='QUEUED',next_retry_at=NULL WHERE job_id=? AND state='INTERRUPTED'", (job,))
                self.event(db, job, 'RECOVERY', 'MAINTENANCE_RESUMED', {})

    def connect(self):
        db = sqlite3.connect(self.path, timeout=5, factory=ClosingConnection)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA synchronous=FULL')
        return db

    def quiesce(self):
        with self.admission:
            self.stop.set()

    def resume_admission(self):
        with self.admission:
            if not self.thread or not self.thread.is_alive():
                raise ValueError('WORKER_RECREATE_REQUIRED')
            self.stop.clear()

    def enqueue(self, *args, **kwargs):
        with self.admission:
            if self.stop.is_set():
                raise ValueError('MAINTENANCE_QUIESCING')
            return super().enqueue(*args, **kwargs)

    def retry(self, *args, **kwargs):
        with self.admission:
            if self.stop.is_set():
                raise ValueError('MAINTENANCE_QUIESCING')
            return super().retry(*args, **kwargs)

    def dispatch(self, *args, **kwargs):
        with self.admission:
            if self.stop.is_set():
                return
            return super().dispatch(*args, **kwargs)

    def tick(self):
        with self.admission:
            if self.stop.is_set():
                return
            self.busy.set()
        try:
            return super().tick()
        finally:
            self.active_job_id = None
            self.busy.clear()

    def maintenance_cancelled(self):
        return self.stop.is_set() or self.publication_cancelled()

    def execute(self, day, mode):
        if self.stop.is_set() and not self.publication_cancelled():
            return dict(status='INTERRUPTED', reason='MAINTENANCE_INTERRUPTED')
        result = self.original_executor(day, mode) if self.original_executor else dict(status='QA_BLOCKED', reason='EXECUTOR_NOT_CONFIGURED')
        if result['status'] == 'CANCELLED' and self.stop.is_set() and not self.publication_cancelled():
            result = dict(result, status='INTERRUPTED', reason='MAINTENANCE_INTERRUPTED')
        return result

    def start(self):
        if self.thread and self.thread.is_alive():
            raise ValueError('WORKER_ALREADY_RUNNING')
        self.stop.clear()
        def loop():
            while not self.stop.is_set():
                try:
                    self.tick(); self.worker_error = None
                except Exception as exc:
                    self.worker_error = 'WORKER_'+type(exc).__name__
                self.stop.wait(15)
        self.thread = threading.Thread(target=loop, name='managed-daily-worker', daemon=False)
        self.thread.start()

    def close(self, timeout=None):
        self.quiesce()
        if self.thread:
            self.thread.join(timeout)
            if self.thread.is_alive():
                raise TimeoutError('WAITING_SAFE_BOUNDARY')
