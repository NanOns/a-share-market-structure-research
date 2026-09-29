"""Select versioned output names for reproducible V4-05 replay builds."""
from __future__ import annotations

import os
from pathlib import Path

BUILD_IDS = {"R4", "R4_1"}


def replay_build_id() -> str:
    value = os.environ.get("V4_05_BUILD_ID", "R4")
    if value not in BUILD_IDS:
        raise ValueError(f"unsupported V4_05_BUILD_ID: {value}")
    return value


def replay_report_path(root: str | Path, relative: str | Path) -> Path:
    """Map an R4 report path to its R4.1 sibling when requested by the runner."""
    relative = Path(relative)
    if replay_build_id() == "R4_1" and relative.name.startswith("V4_05_R4_"):
        relative = relative.with_name(relative.name.replace("V4_05_R4_", "V4_05_R4_1_", 1))
    return Path(root) / relative
