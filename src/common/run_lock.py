"""Single-writer lock for the daily production entrypoint."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import sys
import time
from typing import Any


class ActiveRunLock(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pid_alive(pid: Any) -> bool:
    try:
        pid = int(pid)
        if pid <= 0:
            return False
        if sys.platform == "win32":
            # os.kill(pid, 0) is not a harmless existence probe on Windows:
            # CPython delegates non-console signals to TerminateProcess.  Use
            # a query-only process handle so lock inspection cannot kill the
            # active production writer (or the test runner itself).
            import ctypes
            from ctypes import wintypes

            process_query_limited_information = 0x1000
            still_active = 259
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
            kernel32.GetExitCodeProcess.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
            kernel32.CloseHandle.restype = wintypes.BOOL

            handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
            if not handle:
                return False
            try:
                exit_code = wintypes.DWORD()
                return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))) and exit_code.value == still_active
            finally:
                kernel32.CloseHandle(handle)
        os.kill(pid, 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


class RunLock:
    def __init__(self, path: str | Path, *, run_id: str, stale_after_seconds: int = 24 * 60 * 60):
        self.path = Path(path)
        self.run_id = run_id
        self.stale_after_seconds = stale_after_seconds
        self.acquired = False
        self.last_decision: dict[str, Any] | None = None

    def acquire(self) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"pid": os.getpid(), "run_id": self.run_id, "started_at": _now(), "host": socket.gethostname()}
        encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        while True:
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                try:
                    os.write(fd, encoded)
                    os.fsync(fd)
                finally:
                    os.close(fd)
                self.acquired = True
                return payload
            except FileExistsError:
                existing = self._read_existing()
                if self._is_active(existing):
                    self.last_decision = {
                        "decision": "REJECT_ACTIVE",
                        "owner": existing,
                    }
                    raise ActiveRunLock(f"ACTIVE_RUN_LOCK:{existing.get('run_id', 'unknown')}")
                # Recovery is only allowed for a lock that is both old enough
                # and demonstrably not owned by a live process.
                try:
                    age = time.time() - self.path.stat().st_mtime
                except FileNotFoundError:
                    continue
                if age < self.stale_after_seconds:
                    self.last_decision = {
                        "decision": "REJECT_RECENT_UNVERIFIED",
                        "owner": existing,
                        "age_seconds": age,
                    }
                    raise ActiveRunLock("UNVERIFIED_RECENT_RUN_LOCK")
                self.last_decision = {
                    "decision": "RECOVER_STALE",
                    "owner": existing,
                    "age_seconds": age,
                }
                try:
                    # The stale decision is made only after confirming the
                    # recorded owner is not alive and the file is old enough.
                    # Reuse the existing inode on Windows: delete/rename of a
                    # pytest- or antivirus-observed lock path can block, while
                    # an exclusive truncate-and-rewrite keeps recovery bounded.
                    fd = os.open(self.path, os.O_WRONLY | os.O_TRUNC)
                    try:
                        os.write(fd, encoded)
                        os.fsync(fd)
                    finally:
                        os.close(fd)
                    self.acquired = True
                    return payload
                except FileNotFoundError:
                    continue

    def _read_existing(self) -> dict[str, Any]:
        try:
            value = json.loads(self.path.read_text("utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _is_active(existing: dict[str, Any]) -> bool:
        return _pid_alive(existing.get("pid"))

    def release(self) -> None:
        if not self.acquired:
            return
        try:
            current = self._read_existing()
            if current.get("run_id") == self.run_id and current.get("pid") == os.getpid():
                self.path.unlink(missing_ok=True)
        finally:
            self.acquired = False

    def __enter__(self) -> "RunLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
