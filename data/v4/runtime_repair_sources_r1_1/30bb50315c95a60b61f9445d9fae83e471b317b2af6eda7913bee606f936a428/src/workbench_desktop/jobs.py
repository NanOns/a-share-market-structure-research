"""Lifecycle extension around the unchanged accepted daily-job contract."""
import threading
from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobs


class ManagedDailyJobs(DailyJobs):
    def __init__(self, root, executor=None, **kwargs):
        self.admission = threading.RLock()
        self.busy = threading.Event()
        self.original_executor = executor
        super().__init__(root, executor=self.execute, **kwargs)
        # Maintenance is recorded using the existing INTERRUPTED recovery state.
        # User CANCELLED/CANCEL_REQUESTED records are deliberately not touched.
        with self.worker_lock(), self.connect() as db:
            ids = [r[0] for r in db.execute("SELECT job_id FROM update_jobs WHERE status='INTERRUPTED' AND error='MAINTENANCE_INTERRUPTED'")]
            for job in ids:
                db.execute("UPDATE update_jobs SET status='QUEUED',error=NULL,finished_at=NULL WHERE job_id=?", (job,))
                db.execute("UPDATE update_job_days SET state='QUEUED',next_retry_at=NULL WHERE job_id=? AND state='INTERRUPTED'", (job,))
                self.event(db, job, 'RECOVERY', 'MAINTENANCE_RESUMED', {})

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


class ProcessDailyJobs(DailyJobs):
    """PG control facade; all capture and CPU work belongs to a child process."""
    def __init__(self,root,readback_url,**kwargs):
        super().__init__(root,**kwargs)
        self.readback_url=readback_url;self.process=None
        self.admission=threading.RLock()

    def command(self):
        import sys
        from pathlib import Path
        args=['--daily-worker','--workspace',str(self.root),'--readback-url',self.readback_url]
        if getattr(sys,'frozen',False):return [sys.executable,*args]
        return [sys.executable,str(Path(__file__).resolve().parents[2]/'run_desktop.py'),*args]

    def start(self):
        import os,subprocess
        if self.thread and self.thread.is_alive():raise ValueError('WORKER_ALREADY_RUNNING')
        self.stop.clear()
        env=dict(os.environ,TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp',PYTHONDONTWRITEBYTECODE='1')
        self.process=subprocess.Popen(self.command(),stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,text=True,env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        process=self.process
        def monitor():
            code=process.wait()
            if code and not self.stop.is_set():self.worker_error='DAILY_WORKER_EXIT_'+str(code)
        self.thread=threading.Thread(target=monitor,name='daily-worker-process-monitor',daemon=False)
        self.thread.start()

    def control(self,message):
        if self.process and self.process.poll() is None:
            try:self.process.stdin.write(message+'\n');self.process.stdin.flush()
            except (OSError,ValueError):pass

    def quiesce(self):
        with self.admission:self.stop.set();self.control('QUIESCE')

    def resume_admission(self):
        with self.admission:
            if not self.thread or not self.thread.is_alive():raise ValueError('WORKER_RECREATE_REQUIRED')
            self.control('RESUME');self.stop.clear()

    def enqueue(self,*args,**kwargs):
        with self.admission:
            if self.stop.is_set():raise ValueError('MAINTENANCE_QUIESCING')
            return super().enqueue(*args,**kwargs)

    def retry(self,*args,**kwargs):
        with self.admission:
            if self.stop.is_set():raise ValueError('MAINTENANCE_QUIESCING')
            return super().retry(*args,**kwargs)

    def close(self,timeout=None):
        self.quiesce()
        if self.thread:
            self.thread.join(timeout)
            if self.thread.is_alive():raise TimeoutError('WAITING_SAFE_BOUNDARY')
        if self.process and self.process.stdin:self.process.stdin.close()


def run_daily_worker(root,readback_url):
    """No tray, HTTP socket, or WorkspaceLease; PG lock is writer authority."""
    import sys
    from .source_adapter import executor
    from workbench_analysis.operational_daily_executor_v1 import probe_source_revision
    jobs=ManagedDailyJobs(root,source_probe=probe_source_revision)
    execute=executor(root,producer_worker=True)
    jobs.original_executor=lambda day,mode:execute(root,day,mode,cancelled=jobs.maintenance_cancelled,
        readback_url=readback_url,progress=jobs.checkpoint)
    stream=sys.stdin
    if stream is None:
        # PyInstaller windowed executables set sys.stdin=None even with a
        # redirected Win32 pipe. Recover only that inherited standard handle.
        import ctypes,msvcrt,os
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetStdHandle.restype=ctypes.c_void_p
        handle=kernel.GetStdHandle(-10)
        if not handle or handle==ctypes.c_void_p(-1).value:
            raise RuntimeError('DAILY_WORKER_CONTROL_PIPE_REQUIRED')
        stream=os.fdopen(msvcrt.open_osfhandle(handle,os.O_RDONLY),'r',encoding='utf-8')
    def listen():
        for line in stream:
            if line.strip()=='QUIESCE':jobs.quiesce()
            elif line.strip()=='RESUME':
                if jobs.thread and jobs.thread.is_alive():jobs.resume_admission()
        # Parent exit closes its pipe; finish safely, never kill publication.
        jobs.quiesce()
    jobs.start()
    threading.Thread(target=listen,name='daily-worker-control',daemon=True).start()
    while jobs.thread.is_alive():
        jobs.thread.join(2)
        if jobs.active_job_id:
            try:
                with jobs.connect() as db:
                    db.execute('UPDATE update_job_progress SET heartbeat_at=clock_timestamp() WHERE job_id=?',(jobs.active_job_id,))
            except Exception as exc:
                jobs.worker_error='HEARTBEAT_'+type(exc).__name__
    return 0
