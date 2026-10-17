"""Resolve configured market-data paths without implicit drive fallbacks.

Precedence is explicit argument, environment, then ``config/paths.yaml``.
Callers can log :func:`configured_path_source` without exposing credentials.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


PATH_SETTINGS: dict[str, tuple[str, str]] = {
    "tdx.source_root": ("tdx", "source_root"),
    "tdx.daily_download_root": ("tdx", "daily_download_root"),
    "tdx.snapshot_root": ("tdx", "snapshot_root"),
    "baostock.download_root": ("baostock", "download_root"),
    "baostock.cache_root": ("baostock", "cache_root"),
    "ingest.temp_root": ("ingest", "temp_root"),
}
PATH_ENV: dict[str, str] = {
    "tdx.source_root": "TDX_ROOT",
    "tdx.daily_download_root": "TDX_DAILY_DOWNLOAD_ROOT",
    "tdx.snapshot_root": "TDX_SNAPSHOT_ROOT",
    "baostock.download_root": "BAOSTOCK_DOWNLOAD_ROOT",
    "baostock.cache_root": "BAOSTOCK_CACHE_ROOT",
    "ingest.temp_root": "V4_INGEST_TEMP_ROOT",
}


def _yaml_path_values(path: Path) -> dict[str, str]:
    """Read the small, scalar-only path map without a YAML runtime dependency."""
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    section: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith((" ", "\t")) and line.rstrip().endswith(":"):
            section = line.rstrip()[:-1].strip()
            continue
        match = re.match(r"^\s+([A-Za-z0-9_]+):\s*(.*?)\s*$", line)
        if not match or section is None:
            continue
        raw = match.group(2).split(" #", 1)[0].strip()
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
            raw = raw[1:-1]
        values[f"{section}.{match.group(1)}"] = raw
    # Keep the historic key as a read-only compatibility alias.
    if values.get("tdx.root") and not values.get("tdx.source_root"):
        values["tdx.source_root"] = values["tdx.root"]
    return values


def configured_path_source(project_root: str | Path, setting: str, *, explicit: str | Path | None = None) -> str:
    if setting not in PATH_SETTINGS:
        raise KeyError(f"UNKNOWN_PATH_SETTING:{setting}")
    if explicit is not None and str(explicit).strip():
        return "EXPLICIT_ARGUMENT"
    if os.environ.get(PATH_ENV[setting], "").strip():
        return "ENVIRONMENT:" + PATH_ENV[setting]
    return "CONFIG:config/paths.yaml" if _yaml_path_values(Path(project_root) / "config/paths.yaml").get(setting) else "UNCONFIGURED"


def resolve_configured_path(
    project_root: str | Path,
    setting: str,
    *,
    explicit: str | Path | None = None,
    required: bool = True,
) -> Path | None:
    """Resolve one path using explicit > environment > central YAML precedence."""
    if setting not in PATH_SETTINGS:
        raise KeyError(f"UNKNOWN_PATH_SETTING:{setting}")
    value: Any = explicit
    if value is None or not str(value).strip():
        value = os.environ.get(PATH_ENV[setting])
    if value is None or not str(value).strip():
        value = _yaml_path_values(Path(project_root) / "config/paths.yaml").get(setting)
    if value is None or not str(value).strip():
        if required:
            raise FileNotFoundError(f"PATH_NOT_CONFIGURED:{setting}:{PATH_ENV[setting]}")
        return None
    candidate = Path(str(value)).expanduser()
    if not candidate.is_absolute():
        candidate = Path(project_root) / candidate
    return candidate.resolve()


def resolve_tdx_root(project_root: str | Path, explicit: str | Path | None = None) -> Path:
    """Return the configured TDX source root; never bake in a drive letter."""
    try:
        return resolve_configured_path(project_root, "tdx.source_root", explicit=explicit)  # type: ignore[return-value]
    except FileNotFoundError as exc:
        raise FileNotFoundError("TDX_ROOT_NOT_CONFIGURED") from exc


def resolve_tdx_daily_download_root(project_root: str | Path, explicit: str | Path | None = None) -> Path:
    return resolve_configured_path(project_root, "tdx.daily_download_root", explicit=explicit)  # type: ignore[return-value]


def resolve_tdx_snapshot_root(project_root: str | Path, explicit: str | Path | None = None) -> Path:
    return resolve_configured_path(project_root, "tdx.snapshot_root", explicit=explicit)  # type: ignore[return-value]


def resolve_baostock_download_root(project_root: str | Path, explicit: str | Path | None = None) -> Path:
    return resolve_configured_path(project_root, "baostock.download_root", explicit=explicit)  # type: ignore[return-value]


def resolve_baostock_cache_root(project_root: str | Path, explicit: str | Path | None = None) -> Path:
    return resolve_configured_path(project_root, "baostock.cache_root", explicit=explicit)  # type: ignore[return-value]


def resolve_ingest_temp_root(project_root: str | Path, explicit: str | Path | None = None) -> Path:
    return resolve_configured_path(project_root, "ingest.temp_root", explicit=explicit)  # type: ignore[return-value]
