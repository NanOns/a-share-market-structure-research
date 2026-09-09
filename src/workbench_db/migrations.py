"""Transactional, hash-checked schema migration execution for M7B."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb


BASE_SCHEMA_VERSION = "workbench-schema-v1.0"
MIGRATION_DIR = Path(__file__).with_name("migrations")


class MigrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Migration:
    version: str
    path: Path
    dependencies: tuple[str, ...]


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class MigrationExecutor:
    """Apply migration files in dependency order inside one DB transaction."""

    DEPENDENCIES = {
        "007_history_identity": (BASE_SCHEMA_VERSION,),
        "008_technical_history": ("007_history_identity",),
        "008_technical_history_rps": ("008_technical_history",),
        "009_sector_base_history": ("008_technical_history_rps",),
        "010_historical_structure": ("009_sector_base_history",),
        "008_m8_contract_completion": ("010_historical_structure",),
        "011_m9_sector_cycle": ("008_m8_contract_completion",),
        "012_m9_member_state": ("011_m9_sector_cycle",),
        "013_m9_representative_state": ("012_m9_member_state",),
    }
    CHECK_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS schema_migration_checks (
            version VARCHAR PRIMARY KEY,
            sql_sha256 VARCHAR NOT NULL,
            dependencies JSON NOT NULL,
            previous_manifest_hash VARCHAR NOT NULL,
            applied_at TIMESTAMP NOT NULL,
            receipt_id VARCHAR NOT NULL
        )
    """

    def __init__(self, connection: duckdb.DuckDBPyConnection, migrations_dir: str | Path | None = None):
        self.connection = connection
        self.migrations_dir = Path(migrations_dir).resolve() if migrations_dir else MIGRATION_DIR

    def migrations(self) -> tuple[Migration, ...]:
        values = []
        for path in sorted(self.migrations_dir.glob("*.sql")):
            version = path.stem
            values.append(Migration(version, path, tuple(self.DEPENDENCIES.get(version, ()))))
        by_version = {migration.version: migration for migration in values}
        ordered: list[Migration] = []
        emitted: set[str] = set()
        while len(ordered) < len(values):
            ready = sorted(
                (
                    migration
                    for migration in values
                    if migration.version not in emitted
                    and all(dependency not in by_version or dependency in emitted for dependency in migration.dependencies)
                ),
                key=lambda migration: migration.version,
            )
            if not ready:
                unresolved = ",".join(sorted(set(by_version) - emitted))
                raise MigrationError(f"MIGRATION_DEPENDENCY_CYCLE:{unresolved}")
            for migration in ready:
                ordered.append(migration)
                emitted.add(migration.version)
        return tuple(ordered)

    def _tables(self) -> set[str]:
        return {row[0] for row in self.connection.execute("SHOW TABLES").fetchall()}

    def _applied(self) -> set[str]:
        return {row[0] for row in self.connection.execute("SELECT version FROM schema_migrations").fetchall()}

    def _manifest_hash(self) -> str:
        rows = self.connection.execute("SELECT version, applied_at_utc FROM schema_migrations ORDER BY version").fetchall()
        payload: list[dict[str, Any]] = [{"version": row[0], "applied_at_utc": str(row[1])} for row in rows]
        if "schema_migration_checks" in self._tables():
            checks = self.connection.execute(
                "SELECT version, sql_sha256, dependencies, previous_manifest_hash, receipt_id FROM schema_migration_checks ORDER BY version"
            ).fetchall()
            payload.append({"checks": [{"version": row[0], "sql_sha256": row[1], "dependencies": row[2], "previous_manifest_hash": row[3], "receipt_id": row[4]} for row in checks]})
        return _sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")))

    def _verify_existing(self, migration: Migration, applied: set[str]) -> None:
        if migration.version not in applied:
            return
        if "schema_migration_checks" not in self._tables():
            raise MigrationError(f"MIGRATION_CHECK_TABLE_MISSING:{migration.version}")
        row = self.connection.execute(
            "SELECT sql_sha256, dependencies FROM schema_migration_checks WHERE version=?", [migration.version]
        ).fetchone()
        if not row:
            raise MigrationError(f"MIGRATION_CHECK_MISSING:{migration.version}")
        expected_hash = _sha256(migration.path.read_text(encoding="utf-8"))
        stored_dependencies = json.loads(row[1]) if isinstance(row[1], str) else row[1]
        if row[0] != expected_hash:
            raise MigrationError(f"MIGRATION_HASH_MISMATCH:{migration.version}")
        if tuple(stored_dependencies) != migration.dependencies:
            raise MigrationError(f"MIGRATION_DEPENDENCY_MISMATCH:{migration.version}")

    def apply(self) -> dict[str, Any]:
        applied = self._applied()
        migrations = self.migrations()
        for migration in migrations:
            self._verify_existing(migration, applied)
        pending = [migration for migration in migrations if migration.version not in applied]
        if not pending:
            return {"status": "ALREADY_CURRENT", "applied": []}
        receipts = []
        current_version = pending[0].version
        try:
            self.connection.execute("BEGIN TRANSACTION")
            self.connection.execute(self.CHECK_TABLE_SQL)
            for migration in pending:
                current_version = migration.version
                missing = [dependency for dependency in migration.dependencies if dependency not in applied]
                if missing:
                    raise MigrationError(f"MIGRATION_DEPENDENCY_MISSING:{migration.version}:{','.join(missing)}")
                sql = migration.path.read_text(encoding="utf-8")
                sql_hash = _sha256(sql)
                previous_manifest_hash = self._manifest_hash()
                receipt_id = f"migration-{migration.version}-{uuid.uuid4().hex}"
                applied_at = datetime.now(timezone.utc)
                self.connection.execute(sql)
                self.connection.execute("INSERT INTO schema_migrations VALUES (?, ?)", [migration.version, applied_at])
                self.connection.execute(
                    "INSERT INTO schema_migration_checks VALUES (?, ?, ?, ?, ?, ?)",
                    [migration.version, sql_hash, json.dumps(migration.dependencies), previous_manifest_hash, applied_at, receipt_id],
                )
                applied.add(migration.version)
                receipts.append({
                    "version": migration.version,
                    "sql_sha256": sql_hash,
                    "dependencies": list(migration.dependencies),
                    "previous_manifest_hash": previous_manifest_hash,
                    "receipt_id": receipt_id,
                    "applied_at_utc": applied_at.isoformat(),
                    "backup_receipt": {"status": "REQUIRED_BEFORE_PRODUCTION_APPLICATION", "migration_version": migration.version},
                })
            self.connection.execute("COMMIT")
        except MigrationError:
            try:
                self.connection.execute("ROLLBACK")
            except Exception:
                pass
            raise
        except Exception as exc:
            try:
                self.connection.execute("ROLLBACK")
            except Exception:
                pass
            raise MigrationError(f"MIGRATION_APPLY_FAILED:{current_version}") from exc
        return {"status": "APPLIED" if receipts else "ALREADY_CURRENT", "applied": receipts}
