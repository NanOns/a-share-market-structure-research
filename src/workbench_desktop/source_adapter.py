"""Explicit frozen IO adapter. Original accepted modules remain byte-identical."""
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import builtins
import importlib.util
from .storage import require_owned


def tdx_capture(root):
    require_owned(root)
    from workbench_analysis.operational_owner_adapter_v1 import private_scope
    from scripts import capture_dm01_a01_r3_tdx_package as capture
    from scripts import enter_source_authority_remediation_r2 as binding
    bind = private_scope(binding, dict(ROOT=Path(root)))['bind']
    # Pure fixed module call: no interpreter child, arbitrary command or second
    # writer. Existing bounded official requests and SHA checks remain intact.
    return private_scope(capture, dict(ROOT=Path(root), bind=bind))['main']()


def executor(root):
    require_owned(root)
    from workbench_analysis.operational_owner_adapter_v1 import private_scope
    from workbench_analysis import tdx_official_daily_source as tdx
    from workbench_analysis import tdx_latest_daily_source_v2 as latest
    from workbench_analysis import operational_daily_executor_v1 as daily
    from workbench_analysis.tdx_local_daily_fallback_v1 import fallback as native_fallback
    from .source_view import project
    expected = str((Path(root)/'scripts/capture_dm01_a01_r3_tdx_package.py').resolve())
    def run(command, **kwargs):
        if command != [sys.executable, '-X','utf8','-B', expected] or Path(kwargs['cwd']).resolve() != Path(root).resolve():
            raise ValueError('FROZEN_TASK_NOT_WHITELISTED')
        tdx_capture(root)
        return subprocess.CompletedProcess(command, 0, b'', b'')
    proxy = SimpleNamespace(run=run)
    tdx_scope = private_scope(tdx, dict(__file__=str(Path(root)/'src/workbench_analysis/tdx_official_daily_source.py'), subprocess=proxy))
    latest_scope = private_scope(latest, dict(__file__=str(Path(root)/'src/workbench_analysis/tdx_latest_daily_source_v2.py'),
                                            subprocess=proxy, old=SimpleNamespace(**tdx_scope)))
    def fallback(package,bars,day,daily_rows,**kwargs):
        package,bars,receipt=native_fallback(package,bars,day,daily_rows,**kwargs)
        return package,project(root,bars),receipt
    def imports(name,globals=None,locals=None,fromlist=(),level=0):
        full=importlib.util.resolve_name('.'*level+name,globals['__package__']) if level else name
        if full=='workbench_analysis.tdx_local_daily_fallback_v1' and 'fallback' in fromlist:
            return SimpleNamespace(fallback=fallback)
        return builtins.__import__(name,globals,locals,fromlist,level)
    scope = private_scope(daily, dict(tdx=SimpleNamespace(**tdx_scope),
        capture_latest_tdx_package=latest_scope['capture_latest_tdx_package'],
        extract_target_session_bars=latest_scope['extract_target_session_bars'],
        __builtins__=dict(vars(builtins),__import__=imports)))
    return scope['execute_sources']
