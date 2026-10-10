"""Actual Windows tray backend with deterministic programmatic menu actions."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import sys
import threading
import time
from .storage import WorkspaceLease,verify_resources
from .engine import EngineController
from .jobs import ManagedDailyJobs
from .tray import DesktopTray


def run(root):
    root=Path(root).resolve()
    prefix=Path('G:/codex_tmp/test_temp').resolve()
    marker=json.loads((root/'ISOLATED_PACKAGE_QA.json').read_bytes())
    if root==prefix or not root.is_relative_to(prefix) or marker.get('contract_id')!='V4_ISOLATED_PACKAGE_QA_V1':
        raise ValueError('ISOLATED_TRAY_QA_REQUIRED')
    if (root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').exists():
        raise ValueError('TRAY_QA_REFUSES_OPERATIONAL_HEAD')
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            raw=json.dumps(controller.status()).encode()
            self.send_response(200);self.end_headers();self.wfile.write(raw)
        def log_message(self,*_):pass
    def factory():
        jobs=ManagedDailyJobs(root);jobs.settings(False)
        return ThreadingHTTPServer(('127.0.0.1',0),Handler),jobs
    controller=EngineController(root,factory=factory)
    tray=DesktopTray(controller)
    checks=[];errors=[]
    def wait(state):
        deadline=time.monotonic()+12
        while time.monotonic()<deadline:
            if controller.state==state and not controller.operation.locked():return
            time.sleep(.05)
        raise ValueError('TRAY_STATE_TIMEOUT_'+state)
    def check(name,condition):
        if not condition:raise AssertionError(name)
        checks.append(dict(name=name,status='PASS'))
    def wait_auto(enabled):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            try:
                if controller.settings()['auto_enabled']==enabled:return
            except ValueError:
                pass
            time.sleep(.05)
        raise ValueError('AUTO_SETTING_TIMEOUT')
    def actions():
        try:
            wait('RUNNING')
            check('NATIVE_TRAY_VISIBLE',tray.icon.visible and bool(tray.icon._hwnd))
            check('MENU_START_STOP_RESTART_PRESENT',all(any(label in item.text for item in tray.icon.menu) for label in ['启动引擎','安全停止引擎','安全重启引擎']))
            tray.set_auto(True)
            wait_auto(True)
            tray.set_auto(False)
            wait_auto(False)
            check('TRAY_PAUSE_RESUME_PERSISTENCE',not controller.settings()['auto_enabled'])
            tray.action('stop',confirm=False);wait('STOPPED')
            check('TRAY_REMAINS_AFTER_ENGINE_STOP',tray.icon.visible)
            try:WorkspaceLease(root).acquire()
            except ValueError as exc:check('STOPPED_TRAY_RETAINS_LIFETIME_LOCK',str(exc)=='WORKSPACE_ALREADY_OWNED')
            else:raise AssertionError('SECOND_OWNER_ADMITTED')
            tray.action('start',confirm=False);wait('RUNNING')
            old_jobs=controller.jobs
            tray.action('restart',confirm=False)
            deadline=time.monotonic()+12
            while controller.jobs is old_jobs and time.monotonic()<deadline:time.sleep(.05)
            wait('RUNNING')
            check('TRAY_RESTART_RECREATES_WORKER',controller.jobs is not old_jobs and not old_jobs.thread.is_alive())
            tray.session_query(0,0);tray.session_end(0,0)
            check('SESSION_CANCEL_NOTIFICATION_RECORDED',json.loads((root/'runtime/desktop/session_end.json').read_bytes())['event']=='SESSION_END_CANCELLED')
            tray.action('exit',confirm=False)
        except Exception as exc:
            errors.append(str(exc))
            tray.action('exit',confirm=False)
    with WorkspaceLease(root):
        thread=threading.Thread(target=actions,name='qa-native-tray-actions',daemon=False)
        thread.start();tray.run(open_browser=False);thread.join(15)
        check('EXIT_CLOSES_ENGINE_AND_TRAY',controller.state=='STOPPED' and not tray.icon.visible and not thread.is_alive())
    return dict(status='FAIL' if errors else 'PASS',errors=errors,checks=checks,
        contract_id='V4_NATIVE_WINDOWS_TRAY_FUNCTIONAL_QA_V1',frozen=bool(getattr(sys,'frozen',False)),
        executable=sys.executable,manifest=verify_resources(),
        evidence_kind='ACTUAL_WIN32_TRAY_PROGRAMMATIC_ACTIONS_WITH_SIMULATED_HTTP_EXECUTOR',
        physical_mouse_clicks_verified=False,physical_screen_sizes_verified=False,
        actual_windows_reboot_verified=False,external_acceptance='NOT_GRANTED')
