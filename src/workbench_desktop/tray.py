"""Small Windows tray UI; callbacks never wait for network or safe shutdown."""
from datetime import datetime, timezone
from pathlib import Path
import ctypes
import json
import os
import sys
import threading
import time
import webbrowser
from .storage import atomic

LABELS = {'STOPPED':'引擎已停止','STARTING':'启动中','RUNNING':'引擎运行中',
          'QUIESCING':'停止新任务','WAITING_SAFE_BOUNDARY':'等待安全边界',
          'STOPPING':'正在关闭','FAILED':'需要处理'}


class DesktopTray:
    def __init__(self, controller):
        import pystray
        from PIL import Image, ImageDraw
        self.controller = controller
        self.exiting = False
        self.monitor_stop = threading.Event()
        image = Image.new('RGBA', (64,64), (18,30,45,255))
        draw = ImageDraw.Draw(image)
        draw.line([(12,46),(26,34),(35,39),(52,16)], fill=(49,199,141), width=6)
        item = pystray.MenuItem
        self.icon = pystray.Icon('DaAV4', image, '大A V4', pystray.Menu(
            item('打开 V4 研究工作台', self.open_page, enabled=lambda _:controller.state=='RUNNING', default=True),
            item('查看运行状态与最近错误', self.show_status),
            pystray.Menu.SEPARATOR,
            item('启动引擎', lambda *_:self.action('start'), enabled=lambda _:controller.state in ('STOPPED','FAILED') and not controller.operation.locked()),
            item('安全停止引擎', lambda *_:self.action('stop'), enabled=lambda _:controller.state=='RUNNING' and not controller.operation.locked()),
            item('安全重启引擎', lambda *_:self.action('restart'), enabled=lambda _:controller.state=='RUNNING' and not controller.operation.locked()),
            item('取消本次停止／重启／退出请求', lambda *_:self.cancel_maintenance(), enabled=lambda _:controller.state=='WAITING_SAFE_BOUNDARY'),
            pystray.Menu.SEPARATOR,
            item('暂停自动日更', lambda *_:self.set_auto(False), enabled=lambda _:not controller.operation.locked()),
            item('恢复自动日更', lambda *_:self.set_auto(True), enabled=lambda _:not controller.operation.locked()),
            item('打开日志目录', self.open_logs),
            item('启用登录后自动启动', lambda *_:self.autostart(True)),
            item('关闭登录后自动启动', lambda *_:self.autostart(False)),
            pystray.Menu.SEPARATOR,
            item('退出大A应用（先安全停引擎）', lambda *_:self.action('exit'), enabled=lambda _:not controller.operation.locked()),
        ))

    def notify(self, text):
        try:
            self.icon.notify(text, '大A交易')
        except Exception:
            pass

    def confirm_stop(self, action):
        text = ('停止引擎期间不执行采集，可能错过本机首次观测；补日更不能补造历史首次观测。\n'
                '当前任务会等待安全边界后停止。\n是否继续？')
        return ctypes.windll.user32.MessageBoxW(None, text, '大A交易 · 安全维护', 0x24) == 6

    def action(self, action, confirm=True):
        if action in ('stop','restart','exit') and self.controller.state == 'RUNNING' and confirm and not self.confirm_stop(action):
            return
        if self.controller.operation.locked():
            self.notify('操作正在进行，请等待安全边界。'); return
        def work():
            try:
                result = self.controller.perform('stop' if action=='exit' else action)
                self.notify(LABELS[result['engine_state']])
                if action == 'exit' and result['engine_state'] == 'STOPPED':
                    self.exiting = True
                    self.monitor_stop.set()
                    self.icon.stop()
            except Exception as exc:
                self.notify('操作未完成：'+str(exc)[:120])
        threading.Thread(target=work, name='tray-operation', daemon=False).start()

    def cancel_maintenance(self):
        try:
            self.controller.cancel_maintenance()
            self.notify('已撤销后续停止意图；等待当前安全边界并恢复准入。')
        except ValueError as exc:
            self.notify(str(exc))

    def set_auto(self, enabled):
        def work():
            try:
                self.controller.settings(enabled)
                self.notify('自动日更已恢复' if enabled else '自动日更已暂停；引擎和网页仍可用')
            except Exception as exc:
                self.notify(str(exc)[:120])
        threading.Thread(target=work, name='tray-settings', daemon=False).start()

    def open_page(self, *_):
        if self.controller.state == 'RUNNING':
            webbrowser.open(f'http://127.0.0.1:{self.controller.port}/v4')

    def show_status(self, *_):
        status = self.controller.status()
        text = ('应用已启动；引擎：'+LABELS[status['engine_state']]+'\n'
                '包版本：'+str(status['BUILD_RELEASE_ID'])+'\n'
                '工作区：'+status['WORKSPACE_ROOT']+'\n'
                '观测时间：'+status['observed_at']+'\n'
                '最近错误：'+str(status['reason'] or '无')+'\n\n'
                'CAPTURE_REQUIRES_APP_RUNNING\n真实首次观测需要电脑可用、用户登录、引擎运行及来源/调度条件满足。\n'
                '离线记录不代表实时健康；正式能力准入沿用原合同。')
        ctypes.windll.user32.MessageBoxW(None, text, '大A V4 · 运行状态', 0x40)

    def open_logs(self, *_):
        path = self.controller.root/'runtime/desktop'
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(str(path))

    def autostart(self, enabled):
        if not getattr(sys, 'frozen', False):
            self.notify('登录自启仅在安装版可用。'); return
        import winreg
        executable = str(Path(sys.executable).resolve())
        command = f'"{executable}" --workspace "{self.controller.root}" --no-browser'
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
            if enabled:
                winreg.SetValueEx(key, 'DaAV4Packaged', 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(key, 'DaAV4Packaged')
                except FileNotFoundError:
                    pass
        self.notify('登录后自启已开启；未登录、休眠或停引擎时不采集。' if enabled else '登录后自启已关闭。')

    def run(self, open_browser=True):
        def setup(icon):
            icon.visible = True
            def start():
                try:
                    self.controller.perform('start')
                    if open_browser:
                        self.open_page()
                except Exception as exc:
                    self.notify('启动失败：'+str(exc)[:120])
            threading.Thread(target=start, name='desktop-start', daemon=False).start()
        def monitor():
            waiting_since = None
            while not self.monitor_stop.wait(5):
                self.controller.poll_health()
                state = self.controller.state
                self.icon.title = '大A V4 · '+LABELS[state]
                self.icon.update_menu()
                if state == 'WAITING_SAFE_BOUNDARY':
                    waiting_since = waiting_since or time.monotonic()
                    if time.monotonic()-waiting_since >= 120:
                        self.notify('尚未到安全边界，仍在等待；不会自动强制结束。')
                        waiting_since = time.monotonic()
                else:
                    waiting_since = None
        thread = threading.Thread(target=monitor, name='tray-status', daemon=True)
        thread.start()
        try:
            self.icon.run(setup=setup)
        finally:
            self.monitor_stop.set()
            if self.controller.state != 'STOPPED':
                self.controller.perform('stop')
