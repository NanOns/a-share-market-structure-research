"""Atomic catalog registration for sealed V3 source bundles.

The input files themselves remain immutable artifacts outside the database.
This module only records their identity and metadata in the workbench catalog;
it never copies, removes, or rewrites a source file.
"""

from __future__ import annotations

import json
from typing import Any, Mapping


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


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
        if not isinstance(descriptor, Mapping):
            raise ValueError(f"SOURCE_FILE_DESCRIPTOR_INVALID:{relative_path}")
        payload = {
            **dict(descriptor),
            "source_bundle_id": bundle_id,
            "metadata_snapshot_id": metadata_id,
            "relative_path": str(relative_path),
        }
        connection.execute(
            "INSERT INTO source_files VALUES (?, ?, ?) ON CONFLICT(source_package_id, relative_path) DO UPDATE SET payload_json=excluded.payload_json",
            [package_id, str(relative_path), _json(payload)],
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


__all__ = ["register_source_bundle_catalog"]
