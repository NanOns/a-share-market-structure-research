"""One executable, serialized internal engine lifecycle, original HTTP readback."""
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import json
import socket
import threading
import time
import uuid
from .storage import atomic, resource_root, verify_resources, require_owned
from .jobs import ManagedDailyJobs

STATES = ('STOPPED','STARTING','RUNNING','QUIESCING','WAITING_SAFE_BOUNDARY','STOPPING','FAILED')


class EngineController:
    def __init__(self, root, port=28765, factory=None):
        self.root = Path(root).resolve()
        self.port = port
        self.factory = factory or self.production_factory
        self.state = 'STOPPED'
        self.reason = None
        self.operation_id = None
        self.server = self.jobs = self.http_thread = None
        self.lock = threading.RLock()
        self.operation = threading.Lock()
        self.instance_id = uuid.uuid4().hex
        self.manifest = verify_resources()
        self.last_snapshot = None
        self.cancel_stop = threading.Event()
        self.health_snapshot = dict(status='UNCONFIRMED', consecutive_failures=0, observed_at=None)

    def status(self):
        with self.lock:
            return dict(contract_id='V4_WINDOWS_PACKAGE_RUNTIME_V1', engine_state=self.state,
                        reason=self.reason, operation_id=self.operation_id, instance_id=self.instance_id,
                        pid=__import__('os').getpid(), port=self.port,
                        APP_RESOURCE_ROOT=str(resource_root()), WORKSPACE_ROOT=str(self.root),
                        BUILD_RELEASE_ID=self.manifest['build_release_id'], SOURCE_SHA=self.manifest['source_sha'],
                        RESOURCE_MANIFEST_SHA=self.manifest['resource_manifest_sha'],
                        WORKSPACE_SCHEMA_VERSION=self.manifest['workspace_schema_version'],
                        observed_at=datetime.now(timezone.utc).isoformat(),
                        capture_requirement='CAPTURE_REQUIRES_APP_RUNNING',
                        first_capture_state='UNCONFIRMED' if self.state != 'RUNNING' else 'CHECK_SOURCE_AND_SCHEDULER',
                        cached_snapshot=self.last_snapshot, engine_health=self.health_snapshot,
                        data_freshness='CHECK_ORIGINAL_V4_CONTEXT', external_acceptance='NOT_GRANTED')

    def poll_health(self):
        if self.state != 'RUNNING':
            return
        from urllib.request import urlopen
        alive = bool(self.http_thread and self.http_thread.is_alive() and self.jobs.thread and self.jobs.thread.is_alive())
        try:
            with urlopen(f'http://127.0.0.1:{self.port}/api/v4/desktop/status', timeout=2) as response:
                owner = json.loads(response.read(65536))
            alive = alive and owner.get('instance_id') == self.instance_id and not self.jobs.worker_error
        except (OSError, ValueError):
            alive = False
        with self.lock:
            failures = 0 if alive else self.health_snapshot['consecutive_failures']+1
            self.health_snapshot = dict(status='LIVE' if alive else 'UNCONFIRMED', consecutive_failures=failures,
                                        observed_at=datetime.now(timezone.utc).isoformat())
            if failures >= 3 and self.state == 'RUNNING':
                self.transition('FAILED', 'ENGINE_HEALTH_THREE_CONSECUTIVE_FAILURES')

    def transition(self, state, reason=None):
        if state not in STATES:
            raise ValueError('INVALID_ENGINE_STATE')
        with self.lock:
            self.state, self.reason = state, reason
            snapshot = self.status()
            atomic(self.root/'runtime/desktop/status.json', snapshot)
            atomic(self.root/'runtime/desktop/events'/f'{time.time_ns()}_{state}.json',
                   dict(snapshot, user=__import__('getpass').getuser()))

    def production_factory(self):
        require_owned(self.root)
        from workbench_service.core_product_server_r1 import make_product_handler
        from workbench_analysis.operational_successor_release_v1 import recover
        from workbench_analysis.operational_daily_executor_v1 import probe_source_revision
        from .source_adapter import executor
        execute_sources = executor(self.root)
        required = ['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json',
                    'config/v4_production_runtime_authority_v1.json']
        if any(not (self.root/p).is_file() for p in required):
            raise ValueError('EXISTING_VERIFIED_WORKSPACE_REQUIRED')
        # Port belongs to no other process before any recovery writes occur.
        server = ThreadingHTTPServer(('127.0.0.1', self.port), None, bind_and_activate=False)
        try:
            if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            server.server_bind()
            server.server_activate()
            self.port = server.server_port
            recover(self.root)
            jobs = ManagedDailyJobs(self.root, source_probe=probe_source_revision)
            jobs.original_executor = lambda day, mode: execute_sources(
                self.root, day, mode, cancelled=jobs.maintenance_cancelled,
                readback_url=f'http://127.0.0.1:{self.port}', progress=jobs.checkpoint)
            base = make_product_handler(self.root, jobs)
        except Exception:
            server.server_close()
            raise
        controller = self
        class Handler(base):
            def do_GET(self):
                path = urlparse(self.path).path
                if path == '/api/v4/desktop/status':
                    return self.send(200, controller.status())
                # Unbound product resources belong to this release; frozen bound
                # UI/source artifacts still resolve and verify in the workspace.
                if path.startswith('/v4/assets/'):
                    name = path.rsplit('/', 1)[-1]
                    if name in ('app.js','api.js','components.js','stock.js','replay.js','labels.js'):
                        raw = (resource_root()/'src/workbench_service/static/core-product-r1'/name).read_bytes()
                        return self.send(200, raw, 'application/javascript; charset=utf-8')
                return super().do_GET()
        server.RequestHandlerClass = Handler
        return server, jobs

    def _start(self):
        with self.lock:
            if self.state == 'RUNNING':
                return
            if self.state not in ('STOPPED','FAILED') or self.server or self.jobs:
                raise ValueError('ENGINE_RESOURCES_NOT_RELEASED')
        self.transition('STARTING')
        try:
            server, jobs = self.factory()
            self.server, self.jobs = server, jobs
            self.port = server.server_port
            self.http_thread = threading.Thread(target=server.serve_forever, name='v4-http', daemon=False)
            self.http_thread.start()
            jobs.start()
            self.transition('RUNNING')
        except Exception as exc:
            if self.jobs:
                self.jobs.close()
            if self.server:
                if self.http_thread and self.http_thread.is_alive():
                    self.server.shutdown(); self.http_thread.join()
                self.server.server_close()
            self.server = self.jobs = self.http_thread = None
            self.transition('FAILED', type(exc).__name__+':'+str(exc)[:180])
            raise

    def _stop(self):
        if self.state == 'STOPPED':
            return True
        if not self.jobs and not self.server:
            self.transition('STOPPED'); return True
        self.cancel_stop.clear()
        self.transition('QUIESCING')
        try:
            self.jobs.quiesce()
            self.transition('WAITING_SAFE_BOUNDARY')
            # HTTP is deliberately alive until the whole worker/transaction exits.
            while self.jobs.thread and self.jobs.thread.is_alive():
                self.jobs.thread.join(.2)
                with self.lock:
                    if self.cancel_stop.is_set():
                        if self.jobs.thread.is_alive():
                            self.jobs.resume_admission()
                        else:
                            self.jobs.start()
                        self.transition('RUNNING', 'MAINTENANCE_REQUEST_CANCELLED')
                        return False
            with self.lock:
                if self.cancel_stop.is_set():
                    self.jobs.start()
                    self.transition('RUNNING', 'MAINTENANCE_REQUEST_CANCELLED')
                    return False
                self.transition('STOPPING')
            try:
                self.last_snapshot = self.jobs.status()
            except (ValueError, OSError, KeyError):
                self.last_snapshot = dict(observed_at=datetime.now(timezone.utc).isoformat(), status='UNCONFIRMED')
            self.server.shutdown()
            self.http_thread.join()
            self.server.server_close()
            self.server = self.jobs = self.http_thread = None
            self.transition('STOPPED')
            return True
        except Exception as exc:
            self.transition('FAILED', type(exc).__name__+':'+str(exc)[:180])
            raise

    def perform(self, action):
        if action not in ('start','stop','restart'):
            raise ValueError('ENGINE_ACTION_NOT_ALLOWED')
        if not self.operation.acquire(blocking=False):
            raise ValueError('ENGINE_OPERATION_IN_PROGRESS')
        self.operation_id = uuid.uuid4().hex
        try:
            if action in ('stop','restart'):
                if not self._stop():
                    return self.status()
            if action in ('start','restart'):
                self._start()
            return self.status()
        finally:
            self.operation.release()

    def cancel_maintenance(self):
        with self.lock:
            if self.state != 'WAITING_SAFE_BOUNDARY':
                raise ValueError('FINAL_CLOSE_ALREADY_STARTED')
            self.cancel_stop.set()

    def settings(self, enabled=None):
        if not self.operation.acquire(blocking=False):
            raise ValueError('ENGINE_OPERATION_IN_PROGRESS')
        try:
            if self.jobs:
                return self.jobs.settings(enabled)
            # Persist settings without resuming maintenance-interrupted queues.
            class SettingsJobs(ManagedDailyJobs):
                def __init__(self, root):
                    from workbench_analysis.operational_daily_jobs_v1 import DailyJobs
                    DailyJobs.__init__(self, root)
            jobs = SettingsJobs(self.root)
            return jobs.settings(enabled)
        finally:
            self.operation.release()
