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
    approved_by: str = ""
    approval_ref: str = ""
    approval_source_revision: str = ""
    approval_occurred_at: Any = None
    approval_recorded_at: Any = None
    approval_source_sha256: str = ""


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


def _fetchone(cursor: Any, statement: str, params: tuple[Any, ...] = ()):
    result = cursor.execute(statement, params)
    fetch = getattr(result, "fetchone", None)
    if callable(fetch):
        return fetch()
    return cursor.fetchone()


def load_publication_contract(
    cursor: Any,
    publication_id: str,
    contract_id: str,
    *,
    publication_revision: int | None = None,
) -> RegisteredContract:
    """Load exact approved bytes selected by one canonical publication.

    ``cursor`` must be attached to a read-only repeatable-read transaction.
    This function intentionally does not begin, commit, or change that scope.
    """
    if not publication_id or not contract_id:
        raise ContractRegistryError("V4_CONTRACT_LOOKUP_ID_REQUIRED")
    if publication_revision is not None and (
        isinstance(publication_revision, bool) or int(publication_revision) <= 0
    ):
        raise ContractRegistryError("V4_PUBLICATION_REVISION_INVALID")
    try:
        session = _fetchone(cursor,
            """SELECT current_database(), current_user,
                      current_setting('transaction_isolation'),
                      current_setting('transaction_read_only')"""
        )
        if (not session or len(session) < 4 or not session[0] or not session[1]
                or str(session[2]).lower() != "repeatable read"
                or str(session[3]).lower() not in ("on", "true", "1")):
            raise ContractRegistryError("V4_PG_READONLY_REPEATABLE_READ_REQUIRED")
        publication_sql = """SELECT p.contract_bindings, n.namespace, p.status, p.accepted_at,
                      p.trade_date
                 FROM v4.publications p
                 JOIN v4.model_namespaces n ON n.namespace_id=p.model_namespace_id
                WHERE p.publication_id=%s"""
        publication_params = (publication_id,)
        if publication_revision is not None:
            publication_sql += " AND p.revision_no=%s"
            publication_params += (publication_revision,)
        publication = _fetchone(cursor, publication_sql, publication_params)
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
        row = _fetchone(cursor,
            """SELECT c.raw_content, c.raw_sha256, c.content_format, c.schema_version,
                      c.namespace, c.source_revision, a.action, a.authorized_by,
                      a.authorization_ref, a.occurred_at, a.source_revision,
                      a.source_sha256, a.recorded_at
                 FROM v4.contract_versions c
                 JOIN LATERAL (
                      SELECT e.action, e.authorized_by, e.authorization_ref,
                             e.occurred_at, e.source_revision, e.source_sha256,
                             e.recorded_at
                        FROM v4.contract_approval_events e
                       WHERE e.contract_id=c.contract_id
                         AND e.version=c.version
                         AND e.raw_sha256=c.raw_sha256
                         AND e.occurred_at <= %s
                         AND e.recorded_at <= %s
                       ORDER BY e.occurred_at DESC, e.recorded_at DESC, e.event_id DESC
                       LIMIT 1
                 ) a ON true
                WHERE c.contract_id=%s AND c.version=%s AND c.raw_sha256=%s""",
            (accepted_at, accepted_at, contract_id, version, digest),
        )
    except Exception as exc:
        raise ContractRegistryError("V4_PG_CONTRACT_REGISTRY_UNAVAILABLE") from exc
    if not row:
        raise ContractRegistryError("V4_PG_CONTRACT_VERSION_NOT_FOUND")
    (raw, stored_digest, content_format, schema_version, contract_namespace,
     source_revision, action, approved_by, approval_ref, approved_at,
     approval_source_revision, approval_source_digest, approval_recorded_at) = row
    raw = bytes(raw)
    actual = hashlib.sha256(raw).hexdigest()
    if (action != "APPROVED" or not str(approved_by or "").strip()
            or not str(approval_ref or "").strip()
            or approved_at is None or approval_recorded_at is None
            or not source_revision or not approval_source_revision
            or str(approval_source_revision) != str(source_revision)
            or str(approval_source_digest) != digest
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
                              (str(session[0]), str(session[1])), str(approved_by),
                              str(approval_ref), str(approval_source_revision),
                              approved_at, approval_recorded_at, str(approval_source_digest))


def load_publication_contracts(
    cursor: Any,
    publication_id: str,
    publication_revision: int,
    bindings: Any,
) -> dict[str, RegisteredContract]:
    """Resolve every exact contract pinned by one accepted publication."""
    normalized = _mapping(bindings, "V4_PUBLICATION_CONTRACT_BINDINGS_INVALID")
    if not normalized:
        raise ContractRegistryError("V4_PUBLICATION_CONTRACT_BINDINGS_REQUIRED")
    if (not publication_id or isinstance(publication_revision, bool)
            or not isinstance(publication_revision, int) or publication_revision <= 0):
        raise ContractRegistryError("V4_PUBLICATION_REVISION_INVALID")
    try:
        session = _fetchone(cursor,
            """SELECT current_setting('transaction_isolation'),
                      current_setting('transaction_read_only')""")
        if (not session or len(session) < 2
                or str(session[0]).lower() != "repeatable read"
                or str(session[1]).lower() not in ("on", "true", "1")):
            raise ContractRegistryError("V4_PG_READONLY_REPEATABLE_READ_REQUIRED")
        publication = _fetchone(cursor,
            """SELECT p.contract_bindings
                 FROM v4.publications p
                WHERE p.publication_id=%s AND p.revision_no=%s
                  AND p.status='ACCEPTED' AND p.accepted_at IS NOT NULL""",
            (publication_id, publication_revision),
        )
    except ContractRegistryError:
        raise
    except Exception as exc:
        raise ContractRegistryError("V4_PG_CONTRACT_BINDING_UNAVAILABLE") from exc
    if not publication:
        raise ContractRegistryError("V4_PUBLICATION_NOT_FOUND")
    stored_bindings = _mapping(publication[0], "V4_PUBLICATION_CONTRACT_BINDINGS_INVALID")
    if normalized != stored_bindings:
        raise ContractRegistryError("V4_PUBLICATION_CONTRACT_BINDINGS_MISMATCH")
    result = {}
    for contract_id in sorted(normalized):
        result[contract_id] = load_publication_contract(
            cursor,
            publication_id,
            contract_id,
            publication_revision=publication_revision,
        )
    return result
