"""Atomic catalog registration for sealed V3 source bundles.

The input files themselves remain immutable artifacts outside the database.
This module only records their identity and metadata in the workbench catalog;
it never copies, removes, or rewrites a source file.
"""

from __future__ import annotations

import json
import hashlib
from typing import Any, Iterable, Mapping


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _source_file_payload(
    descriptor: Mapping[str, Any],
    *,
    bundle_id: str,
    metadata_snapshot_id: str,
    existing: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a stable file row while retaining all bundle references."""

    payload = dict(descriptor)
    payload.update(
        {
            "source_bundle_id": bundle_id,
            "metadata_snapshot_id": metadata_snapshot_id,
        }
    )
    if existing:
        for key in ("size", "sha256"):
            if existing.get(key) != payload.get(key):
                raise ValueError(f"SOURCE_FILE_IDENTITY_CONFLICT:{key}")
        bundle_ids = set(existing.get("source_bundle_ids") or [])
        old_bundle_id = existing.get("source_bundle_id")
        if old_bundle_id:
            bundle_ids.add(str(old_bundle_id))
        bundle_ids.add(bundle_id)
        metadata_ids = set(existing.get("metadata_snapshot_ids") or [])
        old_metadata_id = existing.get("metadata_snapshot_id")
        if old_metadata_id:
            metadata_ids.add(str(old_metadata_id))
        metadata_ids.add(metadata_snapshot_id)
        payload["source_bundle_id"] = sorted(bundle_ids)[0]
        payload["source_bundle_ids"] = sorted(bundle_ids)
        payload["metadata_snapshot_id"] = sorted(metadata_ids)[0]
        payload["metadata_snapshot_ids"] = sorted(metadata_ids)
    return payload


def _validate_sealed_bundle(bundle: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    value = dict(bundle)
    bundle_id = str(value.get("source_bundle_id") or "")
    unsigned = dict(value)
    unsigned.pop("source_bundle_id", None)
    expected_id = hashlib.sha256(_json(unsigned).encode("utf-8")).hexdigest()
    if (
        not bundle_id
        or bundle_id != expected_id
        or value.get("contract") != "source-bundle-v1.0"
        or value.get("read_only") is not True
    ):
        raise ValueError("SOURCE_BUNDLE_IDENTITY_INVALID")
    package = value.get("package")
    metadata = value.get("metadata")
    if not isinstance(package, Mapping) or not isinstance(metadata, Mapping):
        raise ValueError("SOURCE_BUNDLE_PACKAGE_METADATA_REQUIRED")
    package_id = str(package.get("sha256") or "")
    metadata_id = str(metadata.get("metadata_snapshot_id") or "")
    files = metadata.get("files")
    if len(package_id) != 64 or not metadata_id or not isinstance(files, Mapping):
        raise ValueError("SOURCE_BUNDLE_CATALOG_IDENTITY_REQUIRED")
    for relative_path, descriptor in files.items():
        if (
            not isinstance(relative_path, str)
            or not relative_path
            or not isinstance(descriptor, Mapping)
            or not isinstance(descriptor.get("size"), int)
            or descriptor.get("size") < 0
            or not isinstance(descriptor.get("sha256"), str)
            or len(descriptor["sha256"]) != 64
        ):
            raise ValueError(f"SOURCE_FILE_DESCRIPTOR_INVALID:{relative_path}")
    return value, dict(package), dict(metadata)


def register_source_bundle_catalog(
    connection: Any,
    *,
    bundle: Mapping[str, Any],
    package: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> dict[str, int | str]:
    """Register one sealed bundle, package, and metadata-file manifest.

    The operation is idempotent by the existing catalog keys.  Callers should
    invoke it in the same transaction as the publication/input acceptance so a
    successful bundle cannot leave ``source_files`` empty for future runs.
    """

    bundle_id = str(bundle.get("source_bundle_id") or "")
    package_id = str(package.get("sha256") or "")
    metadata_id = str(metadata.get("metadata_snapshot_id") or "")
    files = metadata.get("files") or {}
    if not bundle_id or not package_id or not metadata_id or not isinstance(files, Mapping):
        raise ValueError("SOURCE_CATALOG_IDENTITY_REQUIRED")
    connection.execute(
        "INSERT INTO source_packages VALUES (?, ?) ON CONFLICT DO UPDATE SET payload_json=excluded.payload_json",
        [package_id, _json(dict(package))],
    )
    file_count = 0
    for relative_path, descriptor in sorted(files.items(), key=lambda item: str(item[0])):
        catalog_path = str(relative_path)
        if not isinstance(descriptor, Mapping):
            raise ValueError(f"SOURCE_FILE_DESCRIPTOR_INVALID:{relative_path}")
        existing_row = connection.execute(
            "SELECT payload_json FROM source_files WHERE source_package_id=? AND relative_path=?",
            [package_id, catalog_path],
        ).fetchone()
        existing = json.loads(existing_row[0]) if existing_row else None
        if existing and any(existing.get(key) != descriptor.get(key) for key in ("size", "sha256")):
            catalog_path = f"{metadata_id}/{relative_path}"
            versioned_row = connection.execute(
                "SELECT payload_json FROM source_files WHERE source_package_id=? AND relative_path=?",
                [package_id, catalog_path],
            ).fetchone()
            existing = json.loads(versioned_row[0]) if versioned_row else None
        payload = _source_file_payload(
            {**dict(descriptor), "relative_path": str(relative_path), "catalog_relative_path": catalog_path},
            bundle_id=bundle_id,
            metadata_snapshot_id=metadata_id,
            existing=existing,
        )
        connection.execute(
            "INSERT INTO source_files VALUES (?, ?, ?) ON CONFLICT(source_package_id, relative_path) DO UPDATE SET payload_json=excluded.payload_json",
            [package_id, catalog_path, _json(payload)],
        )
        file_count += 1
    connection.execute(
        "INSERT INTO metadata_snapshots VALUES (?, ?) ON CONFLICT DO UPDATE SET payload_json=excluded.payload_json",
        [metadata_id, _json(dict(metadata))],
    )
    connection.execute(
        "INSERT INTO source_bundles VALUES (?, ?) ON CONFLICT DO UPDATE SET payload_json=excluded.payload_json",
        [bundle_id, _json(dict(bundle))],
    )
    return {"source_bundle_id": bundle_id, "source_package_id": package_id, "source_file_count": file_count}


def backfill_source_file_catalog(connection: Any, *, bundles: Iterable[Mapping[str, Any]]) -> dict[str, int | str]:
    """Atomically reconcile source-file rows for already sealed V3 bundles.

    This is deliberately narrower than bundle registration: it requires the
    bundle/package/metadata identities to already exist in their catalogs and
    only fills the missing ``source_files`` manifest rows.  Any invalid or
    conflicting input aborts the whole transaction before a partial catalog
    can be committed.
    """

    validated = [_validate_sealed_bundle(bundle) for bundle in bundles]
    if not validated:
        raise ValueError("SOURCE_BUNDLE_CATALOG_INPUT_EMPTY")
    bundle_ids = {value[0]["source_bundle_id"] for value in validated}
    package_ids = {str(value[1]["sha256"]) for value in validated}
    with connection.cursor() as cursor:
        catalog_bundle_ids = {str(row[0]) for row in cursor.execute("SELECT source_bundle_id FROM source_bundles").fetchall()}
        missing_bundles = sorted(bundle_ids - catalog_bundle_ids)
        if missing_bundles:
            raise ValueError("SOURCE_BUNDLE_CATALOG_MISSING:" + ",".join(missing_bundles))
        catalog_package_ids = {str(row[0]) for row in cursor.execute("SELECT source_package_id FROM source_packages").fetchall()}
        missing_packages = sorted(package_ids - catalog_package_ids)
        if missing_packages:
            raise ValueError("SOURCE_PACKAGE_CATALOG_MISSING:" + ",".join(missing_packages))

        grouped: dict[tuple[str, str], dict[str, Any]] = {}
        for bundle, package, metadata in validated:
            package_id = str(package["sha256"])
            metadata_id = str(metadata["metadata_snapshot_id"])
            for relative_path, descriptor in sorted((metadata.get("files") or {}).items()):
                key = (package_id, str(relative_path))
                current = grouped.get(key)
                if current is None:
                    grouped[key] = {
                        "descriptor": {**dict(descriptor), "relative_path": str(relative_path)},
                        "bundle_ids": {str(bundle["source_bundle_id"])},
                        "metadata_ids": {metadata_id},
                    }
                    continue
                if current["descriptor"].get("size") != descriptor.get("size") or current["descriptor"].get("sha256") != descriptor.get("sha256"):
                    raise ValueError(f"SOURCE_FILE_IDENTITY_CONFLICT:{package_id}:{relative_path}")
                current["bundle_ids"].add(str(bundle["source_bundle_id"]))
                current["metadata_ids"].add(metadata_id)

        inserted = 0
        updated = 0
        cursor.execute("BEGIN")
        try:
            for (package_id, relative_path), item in sorted(grouped.items()):
                row = cursor.execute(
                    "SELECT payload_json FROM source_files WHERE source_package_id=? AND relative_path=?",
                    [package_id, relative_path],
                ).fetchone()
                existing = json.loads(row[0]) if row else None
                payload = dict(item["descriptor"])
                bundle_ids_for_row = set(item["bundle_ids"])
                metadata_ids_for_row = set(item["metadata_ids"])
                if existing:
                    if existing.get("size") != payload.get("size") or existing.get("sha256") != payload.get("sha256"):
                        raise ValueError(f"SOURCE_FILE_IDENTITY_CONFLICT:{package_id}:{relative_path}")
                    bundle_ids_for_row.update(existing.get("source_bundle_ids") or [])
                    if existing.get("source_bundle_id"):
                        bundle_ids_for_row.add(str(existing["source_bundle_id"]))
                    metadata_ids_for_row.update(existing.get("metadata_snapshot_ids") or [])
                    if existing.get("metadata_snapshot_id"):
                        metadata_ids_for_row.add(str(existing["metadata_snapshot_id"]))
                payload.update(
                    {
                        "source_bundle_id": sorted(bundle_ids_for_row)[0],
                        "source_bundle_ids": sorted(bundle_ids_for_row),
                        "metadata_snapshot_id": sorted(metadata_ids_for_row)[0],
                        "metadata_snapshot_ids": sorted(metadata_ids_for_row),
                    }
                )
                if existing is None:
                    cursor.execute(
                        "INSERT INTO source_files VALUES (?, ?, ?)",
                        [package_id, relative_path, _json(payload)],
                    )
                    inserted += 1
                elif _json(existing) != _json(payload):
                    cursor.execute(
                        "UPDATE source_files SET payload_json=? WHERE source_package_id=? AND relative_path=?",
                        [_json(payload), package_id, relative_path],
                    )
                    updated += 1
            cursor.execute("COMMIT")
        except Exception:
            cursor.execute("ROLLBACK")
            raise
    return {
        "contract_version": "v3-p04-03-source-file-catalog-reconcile-v1.0",
        "bundle_count": len(bundle_ids),
        "package_count": len(package_ids),
        "source_file_rows": len(grouped),
        "inserted_rows": inserted,
        "updated_rows": updated,
        "mutation_executed": bool(inserted or updated),
    }


__all__ = ["backfill_source_file_catalog", "register_source_bundle_catalog"]
