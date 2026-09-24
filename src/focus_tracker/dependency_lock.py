"""Verify the versioned Focus runtime dependency lock before publication."""
from __future__ import annotations

import json
import sys
from importlib.metadata import version
from pathlib import Path

from .contracts import digest


CONTRACT_ID = "FOCUS_DEPENDENCY_LOCK_V1"


def verify_dependency_lock(path: Path) -> str:
    payload = json.loads(path.read_text("utf-8"))
    if payload.get("contract_id") != CONTRACT_ID:
        raise ValueError("unknown Focus dependency lock")
    if payload.get("python") != ".".join(map(str, sys.version_info[:3])):
        raise ValueError("Focus Python runtime differs from lock")
    packages = payload.get("packages")
    if not isinstance(packages, dict) or not packages:
        raise ValueError("Focus dependency lock lacks packages")
    for name, expected in packages.items():
        if version(name) != expected:
            raise ValueError(f"Focus dependency differs from lock: {name}")
    return digest(payload)
