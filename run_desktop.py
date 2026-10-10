"""Packaged entry: fixed task dispatch precedes any tray/worker initialization."""
from pathlib import Path
import argparse
import multiprocessing
import os
import sys

if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).resolve().parent/'src'))


def main():
    os.environ.update(TMP='G:/codex_tmp', TEMP='G:/codex_tmp', TMPDIR='G:/codex_tmp')
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    Path('G:/codex_tmp').mkdir(parents=True, exist_ok=True)
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', default='G:/codex work/大A交易')
    parser.add_argument('--port', type=int, default=28765)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--task', choices=('inspect-package','qa-e2e','qa-daily-replay'))
    parser.add_argument('--report')
    args = parser.parse_args()
    from workbench_desktop.storage import atomic, verify_resources, WorkspaceLease, g_path
    if getattr(sys, 'frozen', False):
        from workbench_desktop.storage import resource_root
        git_dir = resource_root()/'git/bin'
        if not (git_dir/'git.exe').is_file():
            raise ValueError('BUNDLED_GIT_READER_MISSING')
        os.environ['PATH'] = str(git_dir)+os.pathsep+str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32')
    if args.task:
        if not args.report:
            parser.error('--report is required for a task')
        try:
            if args.task == 'inspect-package':
                result = dict(status='PASS', frozen=bool(getattr(sys,'frozen',False)), manifest=verify_resources())
            elif args.task == 'qa-daily-replay':
                from workbench_desktop.qa_daily import run
                result = run(g_path(args.workspace))
            else:
                from workbench_desktop.qa import run
                result = run(g_path(args.workspace))
        except Exception as exc:
            import traceback
            result = dict(status='FAIL',reason=str(exc),traceback=traceback.format_exc(),
                          executable=sys.executable,frozen=bool(getattr(sys,'frozen',False)))
        atomic(args.report, result)
        return 0 if result['status'] == 'PASS' else 2
    root = g_path(args.workspace)
    try:
        with WorkspaceLease(root):
            from workbench_desktop.engine import EngineController
            from workbench_desktop.tray import DesktopTray
            DesktopTray(EngineController(root, args.port)).run(open_browser=not args.no_browser)
        return 0
    except Exception as exc:
        import ctypes
        if str(exc) == 'WORKSPACE_ALREADY_OWNED':
            from workbench_desktop.storage import verified_existing_owner
            try:
                owner = verified_existing_owner(root)
                status = __import__('json').loads((root/'runtime/desktop/status.json').read_bytes())
                ctypes.windll.user32.MessageBoxW(None,
                    '已核验已有实例，请使用现有托盘。\n引擎：'+status['engine_state']+'\n版本：'+owner['build_release_id']+
                    '\n引擎已停止时需由现有托盘手动启动。', '大A交易 · 已有实例', 0x40)
                return 0
            except (OSError, ValueError, KeyError):
                pass
        ctypes.windll.user32.MessageBoxW(None, '无法启动：'+str(exc)+'\n请检查工作区、已有实例或日志；不会终止未知进程。', '大A交易', 0x10)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
