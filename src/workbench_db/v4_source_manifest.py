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


CONTRACT_ID = "V4_PG_CONSUMED_SOURCE_MANIFEST_R2"
CONTRACT_VERSION = "2.0.0"
CONTRACT_ID_R3 = "V4_PG_CONSUMED_SOURCE_MANIFEST_R3"
CONTRACT_VERSION_R3 = "3.0.0"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
FIELDS = (
    "source_key", "source_revision_id", "digest", "logical_fact_id", "revision_no",
    "revision_digest", "effective_from", "effective_to", "provider_available_at",
    "observed_at", "ingested_at", "system_available_at", "tombstone",
    "source_package_id", "source_package_contract_version", "source_package_sha256",
    "source_package_page_observed_at", "source_package_target_trade_date",
    "source_package_parser_version", "source_package_accepted_scope",
)
FACT_PROOF_FIELDS = (
    "source_package_acceptance_receipt_id", "source_package_as_recorded",
    "source_package_pit_eligible", "source_package_acceptance_proof_sha256",
    "source_fact_digest", "source_fact_sha256",
    "source_fact_record_locator", "source_fact_record_count",
    "source_fact_acceptance_receipt_id",
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
                else:
                    try:
                        parsed = date.fromisoformat(value)
                    except ValueError as exc:
                        raise SourceManifestError("SOURCE_MANIFEST_DATE_INVALID") from exc
                    if parsed.isoformat() != value:
                        raise SourceManifestError("SOURCE_MANIFEST_DATE_NONCANONICAL")
                    value = parsed.isoformat()
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
        if effective_from is not None and effective_to is not None and effective_from > effective_to:
            raise SourceManifestError("SOURCE_MANIFEST_DATE_WINDOW_INVALID")
        if (not isinstance(row["source_package_id"], str) or not row["source_package_id"].strip()
                or not isinstance(row["source_package_contract_version"], str)
                or not row["source_package_contract_version"].strip()
                or not isinstance(row["source_package_parser_version"], str)
                or not row["source_package_parser_version"].strip()
                or row["source_package_accepted_scope"] != "ACCEPTED_SOURCE_PACKAGE"):
            raise SourceManifestError("SOURCE_MANIFEST_PACKAGE_AUTHORITY_INVALID")
        package_sha = row["source_package_sha256"]
        if not isinstance(package_sha, str) or not _SHA256.fullmatch(package_sha):
            raise SourceManifestError("SOURCE_MANIFEST_PACKAGE_DIGEST_INVALID")
        package_date = row["source_package_target_trade_date"]
        if isinstance(package_date, datetime):
            raise SourceManifestError("SOURCE_MANIFEST_DATE_INVALID")
        if isinstance(package_date, date):
            package_date = package_date.isoformat()
        elif isinstance(package_date, str):
            try:
                parsed_package_date = date.fromisoformat(package_date)
            except ValueError as exc:
                raise SourceManifestError("SOURCE_MANIFEST_DATE_INVALID") from exc
            if parsed_package_date.isoformat() != package_date:
                raise SourceManifestError("SOURCE_MANIFEST_DATE_NONCANONICAL")
        else:
            raise SourceManifestError("SOURCE_MANIFEST_DATE_INVALID")
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
            "source_package_id": row["source_package_id"],
            "source_package_contract_version": row["source_package_contract_version"],
            "source_package_sha256": package_sha.lower(),
            "source_package_page_observed_at": _timestamp(row["source_package_page_observed_at"]),
            "source_package_target_trade_date": package_date,
            "source_package_parser_version": row["source_package_parser_version"],
            "source_package_accepted_scope": row["source_package_accepted_scope"],
        })
    normalized.sort(key=lambda row: row["source_key"].encode("utf-8"))
    return normalized


def source_manifest_digest(rows: Sequence[Mapping[str, Any]]) -> str:
    material = json.dumps(
        canonical_source_rows(rows), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def build_source_manifest(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Producer entry point: canonicalize the complete source rows and hash them."""
    canonical_rows = canonical_source_rows(rows)
    return {
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "source_rows": canonical_rows,
        "source_manifest_sha256": source_manifest_digest(rows),
    }


def canonical_source_rows_r3(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """R3 binds the exact package/fact proof consumed by the Core Reader."""
    normalized = canonical_source_rows(rows)
    by_key = {row["source_key"]: row for row in rows}
    output = []
    for base in normalized:
        row = by_key[base["source_key"]]
        if any(field not in row for field in FACT_PROOF_FIELDS):
            raise SourceManifestError("SOURCE_MANIFEST_R3_FACT_PROOF_FIELDS_INVALID")
        receipt = row["source_package_acceptance_receipt_id"]
        fact_receipt = row["source_fact_acceptance_receipt_id"]
        if (not isinstance(receipt, str) or not receipt.strip() or fact_receipt != receipt
                or row["source_package_as_recorded"] is not True
                or row["source_package_pit_eligible"] is not True):
            raise SourceManifestError("SOURCE_MANIFEST_R3_ACCEPTANCE_PROOF_INVALID")
        for field in ("source_package_acceptance_proof_sha256", "source_fact_digest", "source_fact_sha256"):
            value = row[field]
            if not isinstance(value, str) or not _SHA256.fullmatch(value):
                raise SourceManifestError("SOURCE_MANIFEST_R3_FACT_DIGEST_INVALID")
        locator = row["source_fact_record_locator"]
        if not isinstance(locator, Mapping):
            raise SourceManifestError("SOURCE_MANIFEST_R3_FACT_LOCATOR_INVALID")
        record_count = row["source_fact_record_count"]
        if record_count is not None and (isinstance(record_count, bool) or not isinstance(record_count, int) or record_count < 0):
            raise SourceManifestError("SOURCE_MANIFEST_R3_RECORD_COUNT_INVALID")
        if (isinstance(locator.get("record_count"), bool)
                or locator.get("record_count") != record_count
                or base["source_key"] in {"tdx", "security_universe"} and (record_count is None or record_count <= 0)):
            raise SourceManifestError("SOURCE_MANIFEST_R3_RECORD_COUNT_INVALID")
        output.append({
            **base,
            "source_package_acceptance_receipt_id": receipt,
            "source_package_as_recorded": True,
            "source_package_pit_eligible": True,
            "source_package_acceptance_proof_sha256": row["source_package_acceptance_proof_sha256"].lower(),
            "source_fact_digest": row["source_fact_digest"].lower(),
            "source_fact_sha256": row["source_fact_sha256"].lower(),
            "source_fact_record_locator": dict(locator),
            "source_fact_record_count": record_count,
            "source_fact_acceptance_receipt_id": fact_receipt,
        })
    return output


def source_manifest_digest_r3(rows: Sequence[Mapping[str, Any]]) -> str:
    material = json.dumps(
        canonical_source_rows_r3(rows), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def build_source_manifest_r3(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    canonical_rows = canonical_source_rows_r3(rows)
    return {
        "contract_id": CONTRACT_ID_R3,
        "contract_version": CONTRACT_VERSION_R3,
        "source_rows": canonical_rows,
        "source_manifest_sha256": source_manifest_digest_r3(rows),
    }
