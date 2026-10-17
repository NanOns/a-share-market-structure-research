"""Read immutable V4 contracts pinned by the canonical PG publication.

Callers must invoke this helper inside the same repeatable-read, read-only
transaction used for their other publication/Owner reads. There is deliberately
no filesystem fallback when the draft registry is absent or incomplete.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any


class ContractRegistryError(RuntimeError):
    pass


@dataclass(frozen=True)
class RegisteredContract:
    contract_id: str
    version: str
    raw_sha256: str
    content_format: str
    schema_version: str
    namespace: str
    raw_content: bytes
    parsed_json: Any | None = None
    publication_id: str = ""
    trade_date: str = ""
    accepted_at: Any = None
    database_identity: tuple[str, str] = ("", "")


def _mapping(value: Any, code: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError) as exc:
            raise ContractRegistryError(code) from exc
        if isinstance(parsed, dict):
            return parsed
    raise ContractRegistryError(code)


def load_publication_contract(cursor: Any, publication_id: str, contract_id: str) -> RegisteredContract:
    """Load exact approved bytes selected by one canonical publication.

    ``cursor`` must be attached to a read-only repeatable-read transaction.
    This function intentionally does not begin, commit, or change that scope.
    """
    if not publication_id or not contract_id:
        raise ContractRegistryError("V4_CONTRACT_LOOKUP_ID_REQUIRED")
    try:
        cursor.execute(
            """SELECT current_database(), current_user,
                      current_setting('transaction_isolation'),
                      current_setting('transaction_read_only')"""
        )
        session = cursor.fetchone()
        if (not session or len(session) < 4 or not session[0] or not session[1]
                or str(session[2]).lower() != "repeatable read"
                or str(session[3]).lower() not in ("on", "true", "1")):
            raise ContractRegistryError("V4_PG_READONLY_REPEATABLE_READ_REQUIRED")
        cursor.execute(
            """SELECT p.contract_bindings, n.namespace, p.status, p.accepted_at,
                      p.trade_date
                 FROM v4.publications p
                 JOIN v4.model_namespaces n ON n.namespace_id=p.model_namespace_id
                WHERE p.publication_id=%s""",
            (publication_id,),
        )
        publication = cursor.fetchone()
    except Exception as exc:
        # Missing migration/schema is a closed failure, not a signal to open a file.
        if isinstance(exc, ContractRegistryError):
            raise
        raise ContractRegistryError("V4_PG_CONTRACT_BINDING_UNAVAILABLE") from exc
    if not publication:
        raise ContractRegistryError("V4_PUBLICATION_NOT_FOUND")
    if len(publication) < 5 or publication[2] != "ACCEPTED" or publication[3] is None:
        raise ContractRegistryError("V4_PUBLICATION_NOT_ACCEPTED")
    bindings = _mapping(publication[0], "V4_PUBLICATION_CONTRACT_BINDINGS_INVALID")
    namespace = str(publication[1] or "")
    accepted_at = publication[3]
    binding = bindings.get(contract_id)
    if not isinstance(binding, dict):
        raise ContractRegistryError("V4_PUBLICATION_CONTRACT_NOT_BOUND")
    version = str(binding.get("version") or "")
    digest = str(binding.get("raw_sha256") or "")
    if not version or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ContractRegistryError("V4_PUBLICATION_CONTRACT_BINDING_INVALID")
    try:
        cursor.execute(
            """SELECT raw_content, raw_sha256, content_format, schema_version,
                      namespace, status, approved_by, approved_at
                 FROM v4.contract_versions
                WHERE contract_id=%s AND version=%s AND approved_at <= %s""",
            (contract_id, version, accepted_at),
        )
        row = cursor.fetchone()
    except Exception as exc:
        raise ContractRegistryError("V4_PG_CONTRACT_REGISTRY_UNAVAILABLE") from exc
    if not row:
        raise ContractRegistryError("V4_PG_CONTRACT_VERSION_NOT_FOUND")
    raw, stored_digest, content_format, schema_version, contract_namespace, status, approved_by, approved_at = row
    raw = bytes(raw)
    actual = hashlib.sha256(raw).hexdigest()
    if (status != "APPROVED" or not approved_by or approved_at is None
            or str(stored_digest) != digest or actual != digest):
        raise ContractRegistryError("V4_PG_CONTRACT_APPROVAL_OR_DIGEST_INVALID")
    if str(contract_namespace) != namespace:
        raise ContractRegistryError("V4_PG_CONTRACT_NAMESPACE_MISMATCH")
    parsed_json = None
    fmt = str(content_format).upper()
    if fmt == "JSON":
        try:
            parsed_json = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise ContractRegistryError("V4_PG_CONTRACT_JSON_INVALID") from exc
    elif fmt == "XML":
        upper = raw.upper()
        if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
            raise ContractRegistryError("V4_PG_CONTRACT_XML_DTD_FORBIDDEN")
    elif fmt != "TEXT":
        raise ContractRegistryError("V4_PG_CONTRACT_FORMAT_UNSUPPORTED")
    return RegisteredContract(contract_id, version, digest, fmt, str(schema_version),
                              namespace, raw, parsed_json, publication_id,
                              str(publication[4]), publication[3],
                              (str(session[0]), str(session[1])))
