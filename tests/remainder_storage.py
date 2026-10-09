"""Explicit user-authorized G-only disposable roots; original guard stays intact."""
from pathlib import Path

ALLOWED = {Path('G:/codex_tmp/test_temp').resolve()}


def configure(base):
    from tests import runtime_isolation
    root = Path(base).resolve()
    if root not in ALLOWED:
        raise ValueError('UNREGISTERED_DISPOSABLE_STORAGE_ROOT')
    runtime_isolation.DISPOSABLE_BASE = root
    return root
