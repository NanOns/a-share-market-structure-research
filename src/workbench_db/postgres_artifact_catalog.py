"""Managed-root aware PostgreSQL ArtifactCatalog boundary."""
from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
from typing import Any

from psycopg import sql

from .postgres_repository import PostgresRepository


class ArtifactCatalogError(ValueError):
    pass


class PostgresArtifactCatalog:
    """Resolve files by managed root and persist only relative references."""

    CONTRACT_VERSION = "ARTIFACT_CATALOG_V1"

    def __init__(self, repository: PostgresRepository, *, root: str | Path, managed_roots: dict[str, str | Path] | None = None, forbidden_roots: tuple[str | Path, ...] = ()):
        self.repository = repository
        self.root = Path(root).resolve()
        configured = managed_roots or {"PROJECT_ROOT": self.root}
        self.managed_roots = {str(key): Path(value).resolve() for key, value in configured.items()}
        self.forbidden_roots = tuple(Path(value).resolve() for value in forbidden_roots)

    def resolve_path(self, managed_root_id: str, relative_path: str) -> Path:
        root = self.managed_roots.get(str(managed_root_id))
        if root is None:
            raise ArtifactCatalogError("MANAGED_ROOT_UNKNOWN")
        raw = str(relative_path or "")
        candidate_text = raw.replace("\\", "/")
        parsed = PurePosixPath(candidate_text)
        drive_like = len(parsed.parts[0]) == 2 and parsed.parts[0][1] == ":" if parsed.parts else False
        if not candidate_text or parsed.is_absolute() or drive_like or any(part in {"", ".", ".."} for part in parsed.parts):
            raise ArtifactCatalogError("ARTIFACT_RELATIVE_PATH_INVALID")
        candidate = (root / Path(*parsed.parts)).resolve()
        if candidate != root and root not in candidate.parents:
            raise ArtifactCatalogError("ARTIFACT_PATH_ESCAPES_MANAGED_ROOT")
        for forbidden in self.forbidden_roots:
            if candidate == forbidden or forbidden in candidate.parents:
                raise ArtifactCatalogError("ARTIFACT_PATH_FORBIDDEN_ROOT")
        current = root
        for part in parsed.parts[:-1]:
            current = current / part
            if current.is_symlink():
                raise ArtifactCatalogError("ARTIFACT_SYMLINK_TRAVERSAL")
        return candidate

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def register_file(self, *, managed_root_id: str, relative_path: str, category: str, artifact_contract: str | None, migration_class: str) -> dict[str, Any]:
        path = self.resolve_path(managed_root_id, relative_path)
        if not path.is_file():
            raise ArtifactCatalogError("ARTIFACT_NOT_AVAILABLE")
        digest = self._sha256(path)
        artifact_id = hashlib.sha256(f"{managed_root_id}|{relative_path}|{digest}".encode("utf-8")).hexdigest()
        if self.repository.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        query = sql.SQL(
            "insert into workbench_meta.artifact_catalog "
            "(artifact_id,category,managed_root_id,relative_path,sha256,size_bytes,artifact_contract,availability,migration_class,migration_source_path,discovered_at) "
            "values (%s,%s,%s,%s,%s,%s,%s,'AVAILABLE',%s,%s,now()) "
            "on conflict(artifact_id) do update set category=excluded.category,managed_root_id=excluded.managed_root_id,relative_path=excluded.relative_path,sha256=excluded.sha256,size_bytes=excluded.size_bytes,artifact_contract=excluded.artifact_contract,availability=excluded.availability,migration_class=excluded.migration_class,migration_source_path=excluded.migration_source_path,discovered_at=excluded.discovered_at"
        )
        with self.repository.connection.cursor() as cur:
            cur.execute(query, (artifact_id, category, managed_root_id, str(relative_path).replace("\\", "/"), digest, path.stat().st_size, artifact_contract, migration_class, str(path)))
        return {"artifact_id": artifact_id, "managed_root_id": managed_root_id, "relative_path": str(relative_path).replace("\\", "/"), "sha256": digest, "size_bytes": path.stat().st_size, "availability": "AVAILABLE", "contract_version": self.CONTRACT_VERSION}

    def get(self, artifact_id: str) -> dict[str, Any] | None:
        if self.repository.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        with self.repository.connection.cursor() as cur:
            cur.execute("select artifact_id,category,managed_root_id,relative_path,sha256,size_bytes,artifact_contract,availability,migration_class from workbench_meta.artifact_catalog where artifact_id=%s", (artifact_id,))
            row = cur.fetchone()
        if not row:
            return None
        return dict(zip(("artifact_id", "category", "managed_root_id", "relative_path", "sha256", "size_bytes", "artifact_contract", "availability", "migration_class"), row))


__all__ = ["ArtifactCatalogError", "PostgresArtifactCatalog"]
