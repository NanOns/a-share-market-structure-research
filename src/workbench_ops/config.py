from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb  # compatibility export for existing failure-injection tests
from workbench_db.config_store import ConfigVersionStore, DuckDBConfigVersionStore


class ConfigValidationError(ValueError):
    pass


class ConfigConflict(ValueError):
    pass


DEFAULT = {
    "version": "m5-operations-config-v1",
    "retention_successful_days": 3,
    "query_page_size": 50,
    "download_timeout_seconds": 120,
    "download_retry_count": 2,
    "cpu_budget": 1,
    "memory_budget_mb": 2048,
    "temp_space_budget_mb": 4096,
    "managed_write_roots": ["data", "reports", "runtime"],
    "database_path": "data/database/market_research.duckdb",
    "backup_root": "data/backups",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else root / path).resolve()


def _is_root(path: Path) -> bool:
    return path == path.parent or (path.drive and str(path).rstrip("\\/") == path.drive.rstrip("\\/"))


class OperationsConfig:
    """Versioned M5 config with explicit validation before it can take effect."""

    def __init__(self, root: str | Path, database_path: str | Path | None = None, *, version_store: ConfigVersionStore | None = None):
        self.root = Path(root).resolve()
        self.database_path = Path(database_path).resolve() if database_path else self.root / "data/database/market_research.duckdb"
        self.version_store = version_store or DuckDBConfigVersionStore(self.database_path)
        self.local_path = self.root / "runtime/operations_config.json"
        self._apply_lock = threading.Lock()

    def current(self) -> dict[str, Any]:
        if not self.local_path.is_file():
            return {"revision": None, "config": dict(DEFAULT)}
        value = json.loads(self.local_path.read_text(encoding="utf-8"))
        return {"revision": value["revision"], "config": value["config"]}

    def validate(self, draft: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(draft, dict):
            raise ConfigValidationError("CONFIG_MUST_BE_OBJECT")
        unknown = set(draft) - set(DEFAULT)
        if unknown:
            raise ConfigValidationError("CONFIG_UNKNOWN_KEYS:" + ",".join(sorted(unknown)))
        config = {**DEFAULT, **draft}
        for key in ("retention_successful_days", "query_page_size", "download_timeout_seconds", "download_retry_count", "cpu_budget", "memory_budget_mb", "temp_space_budget_mb"):
            if not isinstance(config[key], int) or isinstance(config[key], bool) or config[key] < 1:
                raise ConfigValidationError("CONFIG_POSITIVE_INTEGER_REQUIRED:" + key)
        if config["retention_successful_days"] < 3:
            raise ConfigValidationError("CONFIG_RETENTION_MINIMUM_THREE_DAYS")
        roots = config["managed_write_roots"]
        if not isinstance(roots, list) or not roots or not all(isinstance(x, str) and x for x in roots):
            raise ConfigValidationError("CONFIG_MANAGED_ROOTS_INVALID")
        tdx_root = _resolve(self.root, self._tdx_root())
        resolved = []
        for raw in roots + [config["backup_root"], config["database_path"]]:
            path = _resolve(self.root, raw)
            if _is_root(path):
                raise ConfigValidationError("CONFIG_PROTECTED_ROOT:" + str(path))
            if path == self.root:
                raise ConfigValidationError("CONFIG_WORKSPACE_ROOT_FORBIDDEN")
            if path == tdx_root or tdx_root in path.parents:
                raise ConfigValidationError("CONFIG_TDX_WRITE_FORBIDDEN:" + str(path))
            if path.is_symlink():
                raise ConfigValidationError("CONFIG_SYMLINK_FORBIDDEN:" + str(path))
            resolved.append(path)
        if len(set(resolved[:-1])) != len(resolved[:-1]):
            raise ConfigValidationError("CONFIG_DUPLICATE_MANAGED_ROOT")
        return {"valid": True, "config": config, "resolved_managed_write_roots": [str(x) for x in resolved[:-2]], "resolved_backup_root": str(resolved[-2]), "resolved_database_path": str(resolved[-1])}

    def apply(self, draft: dict[str, Any], *, expected_revision: str | None) -> dict[str, Any]:
        with self._apply_lock:
            before = self.current()
            if before["revision"] != expected_revision:
                raise ConfigConflict("CONFIG_REVISION_CONFLICT")
            report = self.validate(draft)
            config = report["config"]
            revision = "cfg-" + hashlib.sha256(_canonical(config).encode()).hexdigest()[:24]
            payload = {"revision": revision, "config": config, "validation": report, "applied_at_utc": datetime.now(timezone.utc).isoformat()}
            self.local_path.parent.mkdir(parents=True, exist_ok=True)
            previous_bytes = self.local_path.read_bytes() if self.local_path.is_file() else None
            previous = self.local_path.with_name("operations_config.previous.json")
            temp = self.local_path.with_name(self.local_path.name + "." + uuid.uuid4().hex + ".tmp")
            try:
                temp.write_text(_canonical(payload), encoding="utf-8")
                os.replace(temp, self.local_path)
                self.version_store.put(revision, _canonical(payload))
            except Exception:
                if previous_bytes is None:
                    self.local_path.unlink(missing_ok=True)
                else:
                    rollback = self.local_path.with_name(self.local_path.name + "." + uuid.uuid4().hex + ".rollback")
                    rollback.write_bytes(previous_bytes)
                    os.replace(rollback, self.local_path)
                raise
            finally:
                temp.unlink(missing_ok=True)
            if previous_bytes is not None:
                previous.write_bytes(previous_bytes)
            return {"revision": revision, "config": config, "validation": report}

    def history(self) -> dict[str, Any]:
        return {"items": self.version_store.list()}

    def _tdx_root(self) -> str:
        # The configured immutable source is intentionally read without writing it.
        paths = self.root / "config/paths.yaml"
        text = paths.read_text(encoding="utf-8") if paths.is_file() else ""
        for line in text.splitlines():
            if line.strip().startswith("root:"):
                return line.split(":", 1)[1].strip().strip("\"'")
        return "D:/new_tdx"
