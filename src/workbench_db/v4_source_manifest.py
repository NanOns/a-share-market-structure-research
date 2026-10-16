"""Canonical source-set digest contract for new V4 PG publications.

Legacy publication rows have no source-manifest contract marker and must not
be reinterpreted with this serialization.  Only rows explicitly tagged with
``CONTRACT_ID`` can be rehashed by this module.
"""
from datetime import date, datetime, timezone
import hashlib
import json
import re
from typing import Any, Mapping, Sequence


CONTRACT_ID = "V4_PG_CONSUMED_SOURCE_MANIFEST_R1"
CONTRACT_VERSION = "1.0.0"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
FIELDS = (
    "source_key", "source_revision_id", "digest", "logical_fact_id", "revision_no",
    "revision_digest", "effective_from", "effective_to", "provider_available_at",
    "observed_at", "ingested_at", "system_available_at", "tombstone",
)


class SourceManifestError(ValueError):
    pass


def _timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise SourceManifestError("SOURCE_MANIFEST_TIMESTAMP_MUST_BE_AWARE")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical_source_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
        raise SourceManifestError("SOURCE_MANIFEST_ROWS_REQUIRED")
    normalized = []
    seen = set()
    for row in rows:
        if not isinstance(row, Mapping) or any(key not in row for key in FIELDS):
            raise SourceManifestError("SOURCE_MANIFEST_ROW_FIELDS_INVALID")
        key = row["source_key"]
        if not isinstance(key, str) or not key or key in seen:
            raise SourceManifestError("SOURCE_MANIFEST_SOURCE_KEY_INVALID")
        seen.add(key)
        for name in ("source_revision_id", "logical_fact_id"):
            if not isinstance(row[name], str) or not row[name].strip():
                raise SourceManifestError("SOURCE_MANIFEST_IDENTITY_INVALID")
        for name in ("digest", "revision_digest"):
            if not isinstance(row[name], str) or not _SHA256.fullmatch(row[name]):
                raise SourceManifestError("SOURCE_MANIFEST_DIGEST_INVALID")
        for name in ("effective_from", "effective_to"):
            value = row[name]
            if value is not None:
                if isinstance(value, datetime):
                    raise SourceManifestError("SOURCE_MANIFEST_DATE_INVALID")
                if isinstance(value, date):
                    value = value.isoformat()
                elif not isinstance(value, str):
                    raise SourceManifestError("SOURCE_MANIFEST_DATE_INVALID")
                row_value = value
            else:
                row_value = None
            if name == "effective_from":
                effective_from = row_value
            else:
                effective_to = row_value
        revision_no = row["revision_no"]
        if isinstance(revision_no, bool) or not isinstance(revision_no, int) or revision_no < 1:
            raise SourceManifestError("SOURCE_MANIFEST_REVISION_INVALID")
        if not isinstance(row["tombstone"], bool):
            raise SourceManifestError("SOURCE_MANIFEST_TOMBSTONE_INVALID")
        normalized.append({
            "source_key": key,
            "source_revision_id": str(row["source_revision_id"]),
            "digest": str(row["digest"]).strip().lower(),
            "logical_fact_id": str(row["logical_fact_id"]),
            "revision_no": revision_no,
            "revision_digest": str(row["revision_digest"]).strip().lower(),
            "effective_from": effective_from,
            "effective_to": effective_to,
            "provider_available_at": _timestamp(row["provider_available_at"]),
            "observed_at": _timestamp(row["observed_at"]),
            "ingested_at": _timestamp(row["ingested_at"]),
            "system_available_at": _timestamp(row["system_available_at"]),
            "tombstone": row["tombstone"],
        })
    normalized.sort(key=lambda row: row["source_key"].encode("utf-8"))
    return normalized


def source_manifest_digest(rows: Sequence[Mapping[str, Any]]) -> str:
    material = json.dumps(
        canonical_source_rows(rows), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()
