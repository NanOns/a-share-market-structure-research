import ctypes
import threading
from types import SimpleNamespace
import pytest
from workbench_desktop.tray import DesktopTray


def tray():
    obj=object.__new__(DesktopTray)
    obj.status_dialog_lock=threading.Lock();obj.action_request_lock=threading.Lock()
    obj.monitor_stop=threading.Event();obj.exiting=False;obj.notices=[]
    obj.notify=obj.notices.append
    obj.controller=SimpleNamespace(state='RUNNING',operation=threading.Lock(),status=lambda:dict(auto_daily_enabled=False,engine_state='RUNNING',BUILD_RELEASE_ID='test',WORKSPACE_ROOT='G:/codex_tmp/test_temp/tray',observed_at='test',reason=None))
    return obj

@pytest.mark.parametrize('reply,accepted',[(2,False),(7,False),(6,True)])
def test_confirmation_close_cancel_and_no_never_accept(monkeypatch,reply,accepted):
    calls=[]
    def message(*args):calls.append(args);return reply
    monkeypatch.setattr(ctypes,'windll',SimpleNamespace(user32=SimpleNamespace(MessageBoxW=message)))
    assert tray().confirm_stop('stop') is accepted
    assert calls[0][3]&15 == 3  # YESNOCANCEL enables title-bar close and Escape.


def test_status_dialog_returns_immediately_and_does_not_stack(monkeypatch):
    entered=threading.Event();close=threading.Event();calls=[]
    def message(*args):calls.append(threading.get_ident());entered.set();assert close.wait(3);return 1
    monkeypatch.setattr(ctypes,'windll',SimpleNamespace(user32=SimpleNamespace(MessageBoxW=message)))
    obj=tray();caller=threading.get_ident();obj.show_status()
    try:
        assert entered.wait(2)
        obj.show_status();assert len(calls)==1 and calls[0]!=caller
    finally:close.set()
    assert obj.status_dialog_lock.acquire(timeout=2);obj.status_dialog_lock.release()
    entered.clear();obj.show_status();assert entered.wait(2)
    assert obj.status_dialog_lock.acquire(timeout=2);obj.status_dialog_lock.release()


def test_confirmation_cancel_keeps_engine_and_allows_next_request():
    entered=threading.Event();close=threading.Event();performed=[]
    obj=tray();obj.controller.perform=performed.append
    def confirm(_):entered.set();assert close.wait(3);return False
    obj.confirm_stop=confirm
    obj.action('exit')
    try:
        assert entered.wait(2)
        obj.action('stop');assert obj.action_request_lock.locked()
    finally:close.set()
    assert obj.action_request_lock.acquire(timeout=2);obj.action_request_lock.release()
    assert performed==[] and not obj.exiting and obj.controller.state=='RUNNING'


def test_status_fetch_error_releases_dialog_slot():
    obj=tray()
    def fail():raise RuntimeError('STATUS_UNAVAILABLE')
    obj.controller.status=fail;obj.show_status()
    assert obj.status_dialog_lock.acquire(timeout=2);obj.status_dialog_lock.release()
    assert obj.notices and 'STATUS_UNAVAILABLE' in obj.notices[0]
