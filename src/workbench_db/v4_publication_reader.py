"""Read one accepted V4 publication and its exact module bindings from PG.

This is an opt-in candidate reader. It never reads the filesystem and it does
not replace ``CurrentAcceptedV4Reader``. Owner payload resolution is delegated
to per-module callbacks so a locator stored in PostgreSQL is never treated as
an executable SQL identifier.
"""
from contextlib import contextmanager
from datetime import date
import os
import re
from typing import Any, Callable, Mapping

from workbench_service.current_v4_context import canonical, digest


CONTRACT_ID = "V4_PG_PUBLICATION_READER_CANDIDATE_R1"
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_MODULE = re.compile(r"^[a-z][a-z0-9_]{0,47}$")


class PublicationReadError(ValueError):
    """A stable, fail-closed candidate-reader error."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def reader_dsn(environ: Mapping[str, str] | None = None) -> str:
    """Return a configured read DSN without ever falling back to a writer DSN."""
    env = os.environ if environ is None else environ
    value = env.get("V4_NATIVE_PG_READER_DSN") or env.get("WORKBENCH_PG_DSN")
    if not value:
        raise PublicationReadError("PG_READ_ENV_UNAVAILABLE")
    return value


@contextmanager
def readonly_connection(*, dsn: str | None = None):
    """Open a bounded, repeatable-read, read-only transaction."""
    resolved = dsn or reader_dsn()
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - depends on runtime packaging
        raise PublicationReadError("PG_DRIVER_UNAVAILABLE") from exc
    try:
        with psycopg.connect(resolved, connect_timeout=5) as pg:
            pg.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            pg.execute("SET LOCAL statement_timeout='30s'")
            pg.execute("SET LOCAL lock_timeout='5s'")
            yield pg
    except PublicationReadError:
        raise
    except Exception as exc:
        # Do not surface exception strings: drivers may include connection data.
        code = getattr(exc, "sqlstate", None)
        if code == "42501":
            raise PublicationReadError("PG_READ_PERMISSION_DENIED") from exc
        if code == "42P01":
            raise PublicationReadError("MODULE_RESULT_BINDING_SCHEMA_UNAVAILABLE") from exc
        raise PublicationReadError("PG_READ_FAILED") from exc


def _as_dict(row: Any, columns: tuple[str, ...]) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, Mapping):
        return dict(row)
    return dict(zip(columns, row, strict=True))


def _requirement_status(value: Any) -> str:
    if isinstance(value, str):
        status = value
    elif isinstance(value, Mapping):
        status = value.get("requiredness")
    else:
        status = None
    if status not in {"REQUIRED", "OPTIONAL", "UNKNOWN"}:
        raise PublicationReadError("MODULE_REQUIREDNESS_UNKNOWN")
    return status


def _iso_date(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as exc:
            raise PublicationReadError("INVALID_TRADE_DATE") from exc
    raise PublicationReadError("INVALID_TRADE_DATE")


class PgPublicationReader:
    """Candidate reader for one caller-selected date and model namespace.

    ``required_modules`` must come from an effective V4 module contract. The
    reader intentionally refuses to infer requiredness from row presence.
    Owner callbacks, when supplied, must use fixed per-module SQL and verify
    the returned owner identity against the binding in the same transaction.
    """

    def __init__(
        self,
        *,
        connection_factory: Callable[[], Any] | None = None,
        expected_database_identity: Mapping[str, Any] | None = None,
        owner_readers: Mapping[str, Callable[[Any, Mapping[str, Any]], Any]] | None = None,
    ):
        self.connection_factory = connection_factory or readonly_connection
        self.expected_database_identity = dict(expected_database_identity or {})
        self.owner_readers = dict(owner_readers or {})

    def read_context(
        self,
        *,
        trade_date: str,
        model_namespace_id: str,
        required_modules: Mapping[str, Any],
        expected_publication: tuple[str, int] | None = None,
        expected_context_token: str | None = None,
        resolve_payloads: bool = False,
    ) -> dict[str, Any]:
        target_date = _iso_date(trade_date)
        if not isinstance(model_namespace_id, str) or not model_namespace_id.strip():
            raise PublicationReadError("PUBLICATION_SELECTOR_REQUIRED")
        if not isinstance(required_modules, Mapping) or not required_modules:
            raise PublicationReadError("MODULE_REQUIREDNESS_UNKNOWN")
        requirements = {}
        for module, value in required_modules.items():
            if not isinstance(module, str) or not _MODULE.fullmatch(module):
                raise PublicationReadError("INVALID_MODULE_KEY")
            requirements[module] = _requirement_status(value)
        if any(status == "UNKNOWN" for status in requirements.values()):
            raise PublicationReadError("MODULE_REQUIREDNESS_UNKNOWN")

        with self.connection_factory() as pg:
            try:
                head_cursor = pg.execute(
                    """SELECT p.publication_id, p.revision, p.trade_date,
                          p.model_namespace_id, p.status, p.accepted_at,
                          p.core_revision, p.source_manifest_sha256,
                          p.computation_identity_sha256
                   FROM v4.publication_heads AS h
                   JOIN v4.publications AS p
                     ON p.publication_id=h.publication_id
                    AND p.revision=h.revision
                   WHERE h.trade_date=%s AND h.model_namespace_id=%s""",
                    (target_date, model_namespace_id),
                )
            except Exception as exc:
                if getattr(exc, "sqlstate", None) == "42P01":
                    raise PublicationReadError("PUBLICATION_SCHEMA_UNAVAILABLE") from exc
                raise
            publication = _as_dict(
                head_cursor.fetchone(),
                (
                    "publication_id", "revision", "trade_date",
                    "model_namespace_id", "status", "accepted_at",
                    "core_revision", "source_manifest_sha256",
                    "computation_identity_sha256",
                ),
            )
            if publication is None:
                raise PublicationReadError("NO_ACCEPTED_PUBLICATION")
            if publication["status"] != "ACCEPTED" or publication["accepted_at"] is None:
                raise PublicationReadError("PUBLICATION_HEAD_TARGET_INVALID")
            if _iso_date(publication["trade_date"]) != target_date:
                raise PublicationReadError("PUBLICATION_DATE_MISMATCH")
            if expected_publication is not None and (
                publication["publication_id"], int(publication["revision"])
            ) != (expected_publication[0], int(expected_publication[1])):
                raise PublicationReadError("PUBLICATION_IDENTITY_MISMATCH")

            # Check cluster identity only after confirming a Head exists. A
            # missing Head remains an explicit, useful candidate result.
            identity_keys = {"database", "database_oid", "host", "port"}
            if not identity_keys.issubset(self.expected_database_identity):
                raise PublicationReadError("PG_DATABASE_IDENTITY_REQUIRED")
            identity_cursor = pg.execute(
                """SELECT current_database(),
                          (SELECT oid FROM pg_database WHERE datname=current_database()),
                          inet_server_addr()::text, inet_server_port()"""
            )
            identity_row = identity_cursor.fetchone()
            if identity_row is None:
                raise PublicationReadError("PG_DATABASE_IDENTITY_UNAVAILABLE")
            identity = {
                "database": identity_row[0], "database_oid": identity_row[1],
                "host": identity_row[2], "port": identity_row[3],
            }
            if identity != self.expected_database_identity:
                raise PublicationReadError("PG_DATABASE_IDENTITY_MISMATCH")

            try:
                binding_cursor = pg.execute(
                    """SELECT module_key, database_identity,
                          owner_schema, owner_relation, owner_version_token,
                          owner_trade_date, owner_contract_id, result_digest,
                          row_count, quality_status, as_recorded, pit_eligible
                   FROM v4.publication_module_results
                   WHERE publication_id=%s AND revision=%s
                   ORDER BY module_key""",
                    (publication["publication_id"], publication["revision"]),
                )
            except Exception as exc:
                if getattr(exc, "sqlstate", None) == "42P01":
                    raise PublicationReadError("MODULE_RESULT_BINDING_SCHEMA_UNAVAILABLE") from exc
                raise
            binding_columns = (
                "module_key", "database_identity",
                "owner_schema", "owner_relation", "owner_version_token",
                "owner_trade_date", "owner_contract_id", "result_digest",
                "row_count", "quality_status", "as_recorded", "pit_eligible",
            )
            bindings: dict[str, dict[str, Any]] = {}
            for raw in binding_cursor.fetchall():
                row = _as_dict(raw, binding_columns)
                module = row["module_key"]
                self._validate_binding(row, module, publication, identity)
                if module in bindings:
                    raise PublicationReadError("DUPLICATE_MODULE_RESULT_BINDING")
                bindings[module] = row

            missing = sorted(
                module for module, requiredness in requirements.items()
                if requiredness == "REQUIRED" and module not in bindings
            )
            if missing:
                raise PublicationReadError("MODULE_RESULT_UNBOUND")

            payloads = {}
            if resolve_payloads:
                for module, binding in bindings.items():
                    resolver = self.owner_readers.get(module)
                    if resolver is None:
                        if requirements.get(module) == "REQUIRED":
                            raise PublicationReadError("MODULE_OWNER_READER_UNAVAILABLE")
                        continue
                    resolved = resolver(pg, binding)
                    self._validate_owner_readback(resolved, binding)
                    payloads[module] = resolved.get("payload")

            selected = {
                module: {
                    "database_identity": row["database_identity"],
                    "owner_schema": row["owner_schema"],
                    "owner_relation": row["owner_relation"],
                    "owner_version_token": row["owner_version_token"],
                    "owner_trade_date": _iso_date(row["owner_trade_date"]),
                    "owner_contract_id": row["owner_contract_id"],
                    "result_digest": row["result_digest"],
                    "row_count": int(row["row_count"]),
                    "quality_status": row["quality_status"],
                    "as_recorded": bool(row["as_recorded"]),
                    "pit_eligible": bool(row["pit_eligible"]),
                }
                for module, row in sorted(bindings.items())
            }
            module_result_rows = [
                {"module_key": module, **selected[module]}
                for module in sorted(selected)
            ]
            context = {
                "contract_id": CONTRACT_ID,
                "candidate_only": True,
                "trade_date": target_date,
                "model_namespace_id": model_namespace_id,
                "publication_id": publication["publication_id"],
                "revision": int(publication["revision"]),
                "publication_status": publication["status"],
                "accepted_at": publication["accepted_at"].isoformat()
                if hasattr(publication["accepted_at"], "isoformat")
                else str(publication["accepted_at"]),
                "core_revision": int(publication["core_revision"]),
                "source_manifest_sha256": str(publication["source_manifest_sha256"]).strip(),
                "computation_identity_sha256": str(publication["computation_identity_sha256"]).strip(),
                "database_identity": identity,
                "module_results": selected,
                "module_results_digest": digest(canonical(module_result_rows)),
                "module_requirements": requirements,
            }
            context["context_token"] = "pg-candidate-" + digest(canonical(context))
            if expected_context_token is not None and context["context_token"] != expected_context_token:
                raise PublicationReadError("STALE_CONTEXT_REQUIRES_REFRESH")
            if payloads:
                context["module_payloads"] = payloads
            return context

    @staticmethod
    def _validate_binding(row, module, publication, database_identity):
        if not isinstance(module, str) or not _MODULE.fullmatch(module):
            raise PublicationReadError("INVALID_MODULE_KEY")
        for key in ("owner_schema", "owner_relation"):
            if not isinstance(row.get(key), str) or not _IDENTIFIER.fullmatch(row[key]):
                raise PublicationReadError("INVALID_OWNER_LOCATOR")
        for key in ("owner_version_token", "owner_contract_id", "quality_status"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise PublicationReadError("OWNER_IDENTITY_INCOMPLETE")
        if not isinstance(row.get("database_identity"), Mapping):
            raise PublicationReadError("PG_DATABASE_IDENTITY_MISSING")
        if dict(row["database_identity"]) != dict(database_identity):
            raise PublicationReadError("PG_DATABASE_IDENTITY_MISMATCH")
        if not _DIGEST.fullmatch(str(row.get("result_digest", ""))):
            raise PublicationReadError("MODULE_RESULT_DIGEST_INVALID")
        try:
            row_count = int(row.get("row_count", -1))
        except (TypeError, ValueError) as exc:
            raise PublicationReadError("MODULE_RESULT_ROW_COUNT_INVALID") from exc
        if isinstance(row.get("row_count"), bool) or row_count < 0:
            raise PublicationReadError("MODULE_RESULT_ROW_COUNT_INVALID")
        _iso_date(row.get("owner_trade_date"))
        if row.get("as_recorded") not in (True, False) or row.get("pit_eligible") not in (True, False):
            raise PublicationReadError("OWNER_QUALIFICATION_INVALID")
        if publication["model_namespace_id"] == "":
            raise PublicationReadError("PUBLICATION_NAMESPACE_INVALID")

    @staticmethod
    def _validate_owner_readback(resolved, binding):
        if not isinstance(resolved, Mapping):
            raise PublicationReadError("OWNER_READBACK_IDENTITY_MISSING")
        identity_keys = (
            "database_identity", "owner_schema",
            "owner_relation", "owner_version_token", "owner_trade_date",
            "owner_contract_id", "result_digest", "row_count",
        )
        if any(key not in resolved for key in identity_keys):
            raise PublicationReadError("OWNER_READBACK_IDENTITY_MISSING")
        expected = {key: binding[key] for key in identity_keys}
        actual = dict(resolved)
        if "database_identity" in actual and isinstance(actual["database_identity"], Mapping):
            actual["database_identity"] = dict(actual["database_identity"])
        if "database_identity" in expected and isinstance(expected["database_identity"], Mapping):
            expected["database_identity"] = dict(expected["database_identity"])
        if "owner_trade_date" in actual:
            actual["owner_trade_date"] = _iso_date(actual["owner_trade_date"])
        expected["owner_trade_date"] = _iso_date(expected["owner_trade_date"])
        try:
            actual["row_count"] = int(actual["row_count"])
            expected["row_count"] = int(expected["row_count"])
        except (TypeError, ValueError) as exc:
            raise PublicationReadError("OWNER_READBACK_IDENTITY_MISMATCH") from exc
        if any(actual[key] != expected[key] for key in identity_keys):
            raise PublicationReadError("OWNER_READBACK_IDENTITY_MISMATCH")
