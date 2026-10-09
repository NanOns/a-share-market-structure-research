"""Crash-recoverable daily SDK session lock; original client remains frozen."""
from types import FunctionType,SimpleNamespace
from pathlib import Path
import json,os
from .baostock_supplemental import BaoStockClient as OriginalClient,BaoStockError
from .operational_daily_storage_v1 import exclusive_lock


def alive(pid):
    if not isinstance(pid,int) or pid<1:return True
    if os.name=='nt':
        import ctypes
        handle=ctypes.windll.kernel32.OpenProcess(0x1000,False,pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle);return True
        return ctypes.windll.kernel32.GetLastError()!=87
    try:os.kill(pid,0);return True
    except ProcessLookupError:return False
    except PermissionError:return True


class BaoStockClient(OriginalClient):
    def __enter__(self):
        root=self.budget.path.resolve().parents[2]
        self._daily_kernel=exclusive_lock(root,root/'runtime/dynamic_daily/baostock_session.lock')
        self._daily_kernel.__enter__()
        marker=self.budget.path.with_suffix(self.budget.path.suffix+'.session.lock')
        try:
            if marker.exists():
                try:record=json.loads(marker.read_bytes())
                except (ValueError,OSError):raise BaoStockError('UNOWNED_LEGACY_SESSION_LOCK_REQUIRES_REVIEW')
                if record.get('contract_id')!='DAILY_SDK_SESSION_LOCK_V1' or alive(record.get('pid')):
                    raise BaoStockError('ANOTHER_BAOSTOCK_PROCESS_ACTIVE')
                marker.unlink()
            owner=self
            class OwnedOS:
                def __getattr__(self,name):return getattr(os,name)
                def open(self,path,flags,mode=0o777):
                    if Path(path)!=marker:return os.open(path,flags,mode)
                    try:fd=os.open(path,flags,mode)
                    except FileExistsError:
                        owner._process_lock=None
                        raise BaoStockError('ANOTHER_BAOSTOCK_PROCESS_ACTIVE')
                    os.write(fd,json.dumps(dict(contract_id='DAILY_SDK_SESSION_LOCK_V1',pid=os.getpid())).encode())
                    os.fsync(fd);return fd
            original=OriginalClient.__enter__
            import builtins
            original_import=builtins.__import__
            def imports(name,globals=None,locals=None,fromlist=(),level=0):
                if name=='baostock_runtime_acceptance' and level==1:
                    from .operational_runtime_acceptance_v2 import error
                    return SimpleNamespace(runtime_acceptance_error=error)
                return original_import(name,globals,locals,fromlist,level)
            scope=dict(original.__globals__,os=OwnedOS(),__builtins__=dict(vars(builtins),__import__=imports))
            return FunctionType(original.__code__,scope)(self)
        except BaseException:
            self._daily_kernel.__exit__(None,None,None);self._daily_kernel=None
            raise

    def __exit__(self,*args):
        try:return super().__exit__(*args)
        finally:
            if self._daily_kernel:
                self._daily_kernel.__exit__(None,None,None);self._daily_kernel=None
