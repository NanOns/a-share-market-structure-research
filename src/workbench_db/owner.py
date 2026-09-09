"""Exclusive process ownership for the DuckDB file."""
from __future__ import annotations

import os
from pathlib import Path
from typing import BinaryIO


class DatabaseOwnerBusy(RuntimeError):
    pass


class DatabaseOwner:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path).resolve()
        self.lock_path = self.database_path.with_suffix(self.database_path.suffix + ".owner.lock")
        self._handle: BinaryIO | None = None

    def acquire(self) -> "DatabaseOwner":
        if self._handle is not None:
            return self
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.lock_path.open("a+b")
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:  # pragma: no cover
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            handle.close()
            raise DatabaseOwnerBusy(f"DATABASE_OWNER_BUSY:{self.database_path}") from exc
        self._handle = handle
        return self

    def release(self) -> None:
        if self._handle is None:
            return
        self._handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:  # pragma: no cover
            import fcntl
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        self._handle.close()
        self._handle = None

    def __enter__(self) -> "DatabaseOwner":
        return self.acquire()

    def __exit__(self, *_: object) -> None:
        self.release()
