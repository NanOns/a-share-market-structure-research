"""Frozen runtime/lifecycle/transaction QA. Not a numeric daily E2E certificate."""
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import hashlib
import json
import os
import sys
import threading
from urllib.request import urlopen
from .storage import WorkspaceLease, atomic, verify_resources
from .engine import EngineController
from .jobs import ManagedDailyJobs


def run(root):
    root = Path(root).resolve()
    prefix = Path('G:/codex_tmp/test_temp').resolve()
    marker = root/'ISOLATED_PACKAGE_QA.json'
    if not root.is_relative_to(prefix) or root == prefix or not marker.is_file():
        raise ValueError('ISOLATED_PACKAGE_QA_MARKER_REQUIRED')
    if json.loads(marker.read_bytes()).get('contract_id') != 'V4_ISOLATED_PACKAGE_QA_V1':
        raise ValueError('ISOLATED_PACKAGE_QA_MARKER_INVALID')
    if (root/'data/v4/V4_DATA_ACCEPTED_HEAD.json').exists():
        raise ValueError('QA_REFUSES_ACCEPTED_WORKSPACE')
    manifest = verify_resources()
    checks = []
    def checked(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(dict(name=name, status='PASS'))
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
            raw = path.read_bytes() if path.exists() else b'{"qa":true}'
            self.send_response(200); self.end_headers(); self.wfile.write(raw)
        def log_message(self, *_):
            pass
    def factory():
        jobs = ManagedDailyJobs(root)
        jobs.settings(False)
        return ThreadingHTTPServer(('127.0.0.1',0), Handler), jobs
    controller = EngineController(root, factory=factory)
    with WorkspaceLease(root):
        try:
            WorkspaceLease(root).acquire()
        except ValueError as exc:
            checked('WHOLE_WORKSPACE_SINGLETON', str(exc)=='WORKSPACE_ALREADY_OWNED')
        else:
            raise AssertionError('DOUBLE_OWNER')
        controller.perform('start')
        original_server, original_jobs = controller.server, controller.jobs
        checked('PACKAGED_HTTP_ALIVE', urlopen(f'http://127.0.0.1:{controller.port}', timeout=3).status==200)
        controller.settings(True); controller.settings(False)
        controller.perform('restart')
        checked('RESTART_FRESH_OBJECTS', controller.server is not original_server and controller.jobs is not original_jobs and not original_jobs.thread.is_alive())
        checked('PERSISTED_AUTO_PAUSE', not controller.settings()['auto_enabled'])
        # Existing supported transaction fault-injection contract, explicitly
        # replacing numeric admission in a private scope rather than claiming it.
        from workbench_analysis import operational_successor_release_v1 as release
        from workbench_analysis.operational_owner_adapter_v1 import private_scope
        from workbench_analysis.operational_successor_v1 import digest
        from workbench_analysis.r43_owner_replay import ref
        from workbench_analysis.tdx_official_daily_source import sha256_file
        scope = private_scope(release, dict(validate=lambda *a: True, verify_policy=lambda *a: True))
        head = root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
        atomic(head, dict(accepted_trade_date='2026-10-08', simulation=True))
        before = head.read_bytes()
        archive = root/'data/v4/predecessors'/(sha256_file(head)+'.json')
        archive.parent.mkdir(parents=True, exist_ok=True); archive.write_bytes(before)
        candidate = dict(accepted_trade_date='2026-10-09', predecessor=ref(root,archive), simulation=True)
        try:
            scope['promote'](root,candidate,'0'*64,lambda _:None)
        except ValueError as exc:
            checked('CAS_STALE_REJECTED', 'STALE_OPERATIONAL' in str(exc) and head.read_bytes()==before)
        else:
            raise AssertionError('STALE_CAS_ACCEPTED')
        try:
            scope['promote'](root,candidate,sha256_file(head),lambda _:dict(status='PASS',context_token='wrong'))
        except ValueError as exc:
            checked('READBACK_FAILURE_EXACT_ROLLBACK', 'HTTP_SAME_TOKEN' in str(exc) and head.read_bytes()==before)
        else:
            raise AssertionError('BAD_TOKEN_ACCEPTED')
        def readback(value):
            current = json.loads(urlopen(f'http://127.0.0.1:{controller.port}',timeout=3).read())
            return dict(status='PASS',context_token=digest(current),accepted_trade_date=current['accepted_trade_date'])
        result = scope['promote'](root,candidate,sha256_file(head),readback)
        committed = head.read_bytes()
        release.recover(root)
        checked('COMMITTED_PRESERVED_AFTER_RECOVER', result['status']=='PUBLISHED' and head.read_bytes()==committed)
        transaction = json.loads((root/'runtime/dynamic_daily/publication_transaction.json').read_bytes())
        checked('FINAL_TRANSACTION_COMMITTED', transaction['state']=='COMMITTED')
        atomic(root/'runtime/dynamic_daily/publication_transaction.json',
               dict(state='CAS_COMPLETE_READBACK_PENDING',predecessor=candidate['predecessor'],candidate_token=digest(candidate)))
        release.recover(root)
        checked('CRASH_PENDING_RECOVERS_PREDECESSOR',head.read_bytes()==before)
        controller.perform('stop')
        checked('STOPPED_WITH_NO_THREADS',controller.state=='STOPPED' and controller.server is None)
        with original_jobs.connect() as db:
            checked('SQLITE_INTEGRITY',db.execute('PRAGMA integrity_check').fetchone()[0]=='ok')
    return dict(status='PASS', contract_id='V4_FROZEN_RUNTIME_TRANSACTION_QA_V1',
        evidence_kind='ACTUAL_FROZEN_RUNTIME_AND_LIFECYCLE_WITH_SIMULATED_NUMERIC_ADMISSION',
        frozen=bool(getattr(sys,'frozen',False)), executable=sys.executable,
        executable_sha256=hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
        python=sys.version, external_python_used=False, PATH=os.environ.get('PATH'),
        manifest=manifest, checks=checks, observed_at=datetime.now(timezone.utc).isoformat(), workspace=str(root),
        FROZEN_EXE_END_TO_END_PASS=False,
        remaining=['Actual capture/readiness/numeric derive through original admission', 'Source transient and deterministic failure recovery',
                   'Interactive tray clicks/two screen sizes', 'Actual Windows reboot/login', 'Authorized production takeover'],
        external_acceptance='NOT_GRANTED')
