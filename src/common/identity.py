"""Versioned source, computation and render identity helpers."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import sys
from pathlib import Path
from typing import Any, Iterable

SOURCE_IDENTITY_VERSION = "source-identity-v1.0"
COMPUTATION_IDENTITY_VERSION = "computation-identity-v1.0"
RENDER_IDENTITY_VERSION = "render-identity-v1.0"


def _hash_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def hash_file(path: str | Path) -> str:
    return _hash_bytes(Path(path).read_bytes())


def _file_hashes(root: Path, relatives: Iterable[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for relative in relatives:
        path = root / relative
        if path.exists() and path.is_file():
            result[relative.replace("\\", "/")] = hash_file(path)
    return result


def source_identity(source_fingerprint: dict[str, Any]) -> dict[str, Any]:
    """Wrap the existing production source fingerprint as a formal identity."""
    components = source_fingerprint.get("source_fingerprint_components", {})
    payload = {
        "version": SOURCE_IDENTITY_VERSION,
        "fingerprint_version": source_fingerprint.get("source_fingerprint_version"),
        "source_fingerprint": source_fingerprint.get("source_fingerprint"),
        "components": components,
    }
    payload["sha256"] = _hash_bytes(_canonical(payload))
    return payload


def computation_identity(root: str | Path, *, active_config_paths: Iterable[str] | None = None) -> dict[str, Any]:
    root = Path(root)
    code_paths = [
        "src/phase1_runner.py", "src/phase2_runner.py", "src/phase3_runner.py",
        "src/phase4_runner.py", "src/phase5_runner.py", "src/factors/engine.py",
        "src/factors/registry.py", "src/normalize/phase1.py", "src/common/snapshot_reader.py",
        "src/common/input_snapshot.py", "src/sector/phase2.py", "src/scanner/sector_scanner.py",
        "src/scanner/stock_scanner.py", "src/candidates/research_priority.py",
        "src/adjustment/tdx_adjustment.py", "src/tdx/gbbq_reader.py",
        "src/tdx/security_master.py", "src/sector/roles.py", "src/common/identity.py",
        "docs/FACTOR_CONTRACT_V1.md", "docs/SYNTHETIC_SECTOR_FACTOR_CONTRACT_V1.md",
        "docs/SECTOR_SCANNER_CONTRACT_V1.md", "docs/STOCK_SCANNER_CONTRACT_V1.md",
        "docs/CANDIDATE_POOL_CONTRACT_V1.md", "docs/RESEARCH_PRIORITY_CONTRACT_V1.md",
        "docs/INPUT_SNAPSHOT_CONTRACT_V1.md", "docs/DATA_STATE_SEMANTICS_CONTRACT_V1.md",
        "docs/SECTOR_STATISTICAL_VALIDITY_CONTRACT_V1.md",
    ]
    configs = list(active_config_paths or (
        "config/adjustment.yaml", "config/factors.yaml", "config/research_priority.yaml",
        "config/sector_config.yaml", "config/sector_roles.yaml", "config/sector_scanner.yaml",
        "config/stock_scanner.yaml", "config/trading_calendar.yaml", "config/universe.yaml",
    ))
    files = _file_hashes(root, [*code_paths, *configs])
    environment = {
        "python_version": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "executable": Path(sys.executable).name,
        "dependencies": {
            name: importlib.metadata.version(name)
            for name in ("numpy", "pandas", "pyarrow", "pytest", "PyYAML")
            if _package_available(name)
        },
    }
    value = {"version": COMPUTATION_IDENTITY_VERSION, "files": files, "environment": environment}
    value["sha256"] = _hash_bytes(_canonical(value))
    return value


def render_identity(root: str | Path) -> dict[str, Any]:
    root = Path(root)
    files = _file_hashes(root, [
        "run_daily.py", "src/common/paths.py", "src/production/daily.py", "src/production/dashboard.py", "src/production/release.py",
        "docs/DAILY_PRODUCTION_CONTRACT_V1.md",
    ])
    value = {"version": RENDER_IDENTITY_VERSION, "files": files, "csv_schema_version": "report-csv-schema-v1.0"}
    value["sha256"] = _hash_bytes(_canonical(value))
    return value


def identity_changed(previous: dict[str, Any] | None, current: dict[str, Any]) -> bool:
    return (previous or {}).get("sha256") != current.get("sha256")


def _package_available(name: str) -> bool:
    try:
        importlib.metadata.version(name)
        return True
    except importlib.metadata.PackageNotFoundError:
        return False
