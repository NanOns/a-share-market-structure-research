"""Read one exact V4 publication from PG without filesystem fallback.

The reader is an opt-in candidate surface. It validates the final 001--009
schema identity, source and state bindings, required module contract, and Owner
readback in one repeatable-read, read-only transaction. It does not switch or
write the production Head.
"""
from contextlib import contextmanager
from datetime import date, datetime
import os
import re
from typing import Any, Callable, Mapping
from zoneinfo import ZoneInfo

from workbench_service.current_v4_context import canonical, digest
from .v4_publication_contract import (
    CONTRACT_ID as MODULE_CONTRACT_ID, OWNER_FAMILIES, effective_module_contract,
    required_module_keys, supported_owner_keys,
)
from .v4_source_manifest import (
    CONTRACT_ID as SOURCE_MANIFEST_CONTRACT_ID, canonical_source_rows,
    source_manifest_digest, CONTRACT_ID_R3 as SOURCE_MANIFEST_CONTRACT_ID_R3,
    source_manifest_digest_r3,
)


CONTRACT_ID = "V4_PG_PUBLICATION_READER_CANDIDATE_R2"
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_MODULE = re.compile(r"^[a-z][a-z0-9_]{0,47}$")


class PublicationReadError(ValueError):
    """A stable, fail-closed candidate-reader error."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def reader_dsn(environ: Mapping[str, str] | None = None) -> str:
    """Reuse the project's existing read configuration; reads are transaction-RO."""
    env = os.environ if environ is None else environ
    value = env.get("WORKBENCH_PG_DSN")
    if not value:
        raise PublicationReadError("PG_READ_ENV_UNAVAILABLE")
    return value


@contextmanager
def readonly_connection(*, dsn: str | None = None):
    """Open a bounded repeatable-read transaction enforced read-only by PostgreSQL."""
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
        # Driver exception strings can contain connection parameters.
        code = getattr(exc, "sqlstate", None)
        if code == "42501":
            raise PublicationReadError("PG_READ_PERMISSION_DENIED") from exc
        if code == "42P01":
            raise PublicationReadError("PUBLICATION_SCHEMA_UNAVAILABLE") from exc
        raise PublicationReadError("PG_READ_FAILED") from exc


def _as_dict(row: Any, columns: tuple[str, ...]) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, Mapping):
        return dict(row)
    return dict(zip(columns, row, strict=True))


def _iso_date(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as exc:
            raise PublicationReadError("INVALID_TRADE_DATE") from exc
    raise PublicationReadError("INVALID_TRADE_DATE")


def _row_dicts(cursor, columns):
    return [_as_dict(row, columns) for row in cursor.fetchall()]


class PgPublicationReader:
    """Candidate-only reader bound to the versioned seven-endpoint contract."""

    def __init__(
        self,
        *,
        connection_factory: Callable[[], Any] | None = None,
        expected_database_identity: Mapping[str, Any] | None = None,
        owner_readers: Mapping[str, Callable[[Any, Mapping[str, Any]], Any]] | None = None,
        workspace_root: str | None = None,
    ):
        self.connection_factory = connection_factory or readonly_connection
        self.expected_database_identity = dict(expected_database_identity or {})
        self.workspace_root = workspace_root
        if owner_readers is None:
            from .v4_publication_owners import default_owner_readers
            owner_readers = default_owner_readers()
        self.owner_readers = dict(owner_readers)

    @staticmethod
    def startup_head_tuple(*, connection_factory: Callable[[], Any] | None = None) -> dict[str, Any]:
        """Attest the current accepted PG Head set and contracts in one snapshot.

        Startup uses the tuple twice around module loading to detect an authority
        change without consulting JSON Head files or runtime acceptance files.
        """
        factory = connection_factory or readonly_connection
        with factory() as pg:
            try:
                pg.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                pg.execute("SET LOCAL statement_timeout='30s'")
                pg.execute("SET LOCAL lock_timeout='5s'")
            except Exception as exc:
                raise PublicationReadError("PG_READ_TRANSACTION_NOT_READ_ONLY") from exc
            from .v4_native import attest_read_role
            attest_read_role(pg, "v4")
            identity = PgPublicationReader._read_database_identity(pg)
            cursor = pg.execute(
                """WITH ranked AS (
                       SELECT p.publication_id,p.revision_no,p.trade_date,p.model_namespace_id,
                              p.status,p.accepted_at,p.core_revision,p.source_manifest_sha256,
                              p.computation_identity_sha256,
                              p.publication_lineage_id,p.same_day_revision_parent_id,
                              p.prior_session_publication_id,p.prior_session_state_head,
                              p.prior_session_state_logical_digest,p.prior_session_gap_reason,
                              p.contract_bindings,h.state_head_id,h.state_logical_digest,
                              sh.logical_digest AS verified_state_digest,
                              row_number() OVER (PARTITION BY h.model_namespace_id
                                ORDER BY h.trade_date DESC,p.revision_no DESC,p.publication_id) AS rn
                         FROM v4.publication_heads AS h
                         JOIN v4.publications AS p ON p.publication_id=h.publication_id
                         LEFT JOIN v4.state_heads AS sh
                           ON sh.namespace_id=h.model_namespace_id
                          AND sh.state_head_id=h.state_head_id
                          AND sh.publication_id=h.publication_id
                          AND sh.logical_digest=h.state_logical_digest
                        WHERE p.status='ACCEPTED' AND p.accepted_at IS NOT NULL
                     )
                     SELECT publication_id,revision_no,trade_date,model_namespace_id,status,accepted_at,
                            core_revision,source_manifest_sha256,computation_identity_sha256,
                            publication_lineage_id,same_day_revision_parent_id,
                            prior_session_publication_id,prior_session_state_head,
                            prior_session_state_logical_digest,prior_session_gap_reason,contract_bindings,
                            state_head_id,state_logical_digest,verified_state_digest
                       FROM ranked WHERE rn=1 ORDER BY model_namespace_id"""
            )
            columns = (
                "publication_id","revision_no","trade_date","model_namespace_id","status","accepted_at",
                "core_revision","source_manifest_sha256",
                "computation_identity_sha256","publication_lineage_id","same_day_revision_parent_id",
                "prior_session_publication_id","prior_session_state_head","prior_session_state_logical_digest",
                "prior_session_gap_reason","contract_bindings","state_head_id","state_logical_digest",
                "verified_state_digest",
            )
            heads = _row_dicts(cursor, columns)
            if not heads:
                raise PublicationReadError("NO_ACCEPTED_PUBLICATION_HEAD")
            try:
                from workbench_analysis.contract_registry_pg_v1 import load_publication_contracts
            except ImportError as exc:
                raise PublicationReadError("CONTRACT_REGISTRY_UNAVAILABLE") from exc
            contract_rows = []
            for head in heads:
                day = _iso_date(head["trade_date"])
                PgPublicationReader._validate_publication(head, day, head["model_namespace_id"])
                try:
                    contracts = load_publication_contracts(
                        pg, head["publication_id"], int(head["revision_no"]), head.get("contract_bindings")
                    )
                except Exception as exc:
                    code = getattr(exc, "code", None)
                    raise PublicationReadError(str(code or "PUBLICATION_CONTRACT_BINDING_INVALID")) from exc
                contract_rows.append(dict(
                    publication_id=head["publication_id"], revision_no=int(head["revision_no"]),
                    trade_date=day, model_namespace_id=head["model_namespace_id"],
                    contracts_digest=digest(canonical(contracts)),
                ))
            return dict(contract_id="V4_STARTUP_PG_HEAD_ATTESTATION_R1",
                database_identity=identity, heads=[dict(
                    publication_id=row["publication_id"],revision_no=int(row["revision_no"]),
                    trade_date=_iso_date(row["trade_date"]),model_namespace_id=row["model_namespace_id"],
                    source_manifest_sha256=row["source_manifest_sha256"],state_head_id=row["state_head_id"],
                    state_logical_digest=row["state_logical_digest"],verified_state_digest=row["verified_state_digest"],
                ) for row in heads], contracts=contract_rows)

    def read_context(
        self,
        *,
        trade_date: str,
        model_namespace_id: str,
        expected_publication: tuple[str, int] | None = None,
        expected_context_token: str | None = None,
        resolve_payloads: bool = True,
    ) -> dict[str, Any]:
        target_date = _iso_date(trade_date)
        if not isinstance(model_namespace_id, str) or not model_namespace_id.strip():
            raise PublicationReadError("PUBLICATION_SELECTOR_REQUIRED")
        modules = required_module_keys()
        with self.connection_factory() as pg:
            try:
                pg.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                pg.execute("SET LOCAL statement_timeout='30s'")
                pg.execute("SET LOCAL lock_timeout='5s'")
            except Exception as exc:
                raise PublicationReadError("PG_READ_TRANSACTION_NOT_READ_ONLY") from exc

            try:
                head_cursor = pg.execute(
                    """SELECT p.publication_id, p.revision_no, p.trade_date,
                              p.model_namespace_id, p.status, p.accepted_at,
                              p.core_revision, p.source_manifest_sha256, p.source_manifest_contract_id,
                              p.computation_identity_sha256, p.publication_lineage_id,
                              p.same_day_revision_parent_id, p.prior_session_publication_id,
                              p.prior_session_state_head, p.prior_session_state_logical_digest,
                              p.prior_session_gap_reason, h.state_head_id,
                              h.state_logical_digest, sh.logical_digest AS verified_state_digest,
                              p.contract_bindings
                       FROM v4.publication_heads AS h
                       JOIN v4.publications AS p ON p.publication_id=h.publication_id
                       LEFT JOIN v4.state_heads AS sh
                         ON sh.namespace_id=h.model_namespace_id
                        AND sh.state_head_id=h.state_head_id
                        AND sh.publication_id=h.publication_id
                        AND sh.logical_digest=h.state_logical_digest
                       WHERE h.trade_date=%s AND h.model_namespace_id=%s""",
                    (target_date, model_namespace_id),
                )
            except Exception as exc:
                self._map_schema_error(exc, "PUBLICATION_SCHEMA_UNAVAILABLE")
                raise
            pub_columns = (
                "publication_id", "revision_no", "trade_date", "model_namespace_id",
                "status", "accepted_at", "core_revision", "source_manifest_sha256", "source_manifest_contract_id",
                "computation_identity_sha256", "publication_lineage_id",
                "same_day_revision_parent_id", "prior_session_publication_id",
                "prior_session_state_head", "prior_session_state_logical_digest",
                "prior_session_gap_reason", "state_head_id", "state_logical_digest",
                "verified_state_digest",
                "contract_bindings",
            )
            publication = _as_dict(head_cursor.fetchone(), pub_columns)
            if publication is None:
                raise PublicationReadError("NO_ACCEPTED_PUBLICATION")
            self._validate_publication(publication, target_date, model_namespace_id)
            if expected_publication is not None and (
                publication["publication_id"], int(publication["revision_no"])
            ) != (expected_publication[0], int(expected_publication[1])):
                raise PublicationReadError("PUBLICATION_IDENTITY_MISMATCH")

            identity = self._read_database_identity(pg)
            if not {"database", "database_oid", "host", "port"}.issubset(self.expected_database_identity):
                raise PublicationReadError("PG_DATABASE_IDENTITY_REQUIRED")
            if identity != self.expected_database_identity:
                raise PublicationReadError("PG_DATABASE_IDENTITY_MISMATCH")
            try:
                role = self._attest_read_role(pg)
            except PublicationReadError:
                raise
            except Exception as exc:
                self._map_schema_error(exc, "MODULE_RESULT_BINDING_SCHEMA_UNAVAILABLE")
                if getattr(exc, "sqlstate", None) == "42501":
                    raise PublicationReadError("PG_READ_PERMISSION_DENIED") from exc
                raise PublicationReadError("PG_READER_ROLE_ATTESTATION_FAILED") from exc

            # Contract bytes and their approval event share this transaction snapshot
            # with the selected Head, source bindings, and Owner descriptors.  Older
            # accepted publications with no reconciled contract map remain readable
            # only through their explicit legacy path; this candidate surface fails
            # closed instead of silently consulting filesystem contracts.
            try:
                from workbench_analysis.contract_registry_pg_v1 import (
                    ContractRegistryError,
                    load_publication_contracts,
                )
                registered_contracts = load_publication_contracts(
                    pg,
                    publication["publication_id"],
                    int(publication["revision_no"]),
                    publication.get("contract_bindings"),
                )
            except ContractRegistryError as exc:
                raise PublicationReadError(str(exc)) from exc

            workspace_owner_mapping = None
            if self.workspace_root is not None:
                mapping_contract = registered_contracts.get("V4_PG_WORKSPACE_OWNER_MAPPING_REGISTRY_R1")
                if mapping_contract is not None:
                    try:
                        from .v4_workspace_owner_mapping_r1 import resolve_workspace_owner_mapping_document
                        workspace_owner_mapping = resolve_workspace_owner_mapping_document(
                            root=self.workspace_root, trade_date=target_date,
                            selected_model_namespace_id=model_namespace_id,
                            registry=mapping_contract.parsed_json,
                        )
                    except ValueError as exc:
                        raise PublicationReadError(str(exc)) from exc

            parent = self._read_same_day_parent(pg, publication)
            sources = self._read_sources(pg, publication)
            manifest_status, recomputed_manifest_digest = self._verify_source_manifest(publication, sources)
            page_data = self._read_page_data(pg, publication, sources)
            bindings = self._read_module_bindings(pg, publication, identity)
            missing = sorted(set(modules) - set(bindings))
            if missing:
                raise PublicationReadError("MODULE_RESULT_UNBOUND")
            extras = sorted(set(bindings) - set(supported_owner_keys()))
            if extras:
                raise PublicationReadError("MODULE_NOT_IN_EFFECTIVE_CONTRACT")

            payloads = {}
            readback_complete = False
            if resolve_payloads:
                for module in sorted(bindings):
                    resolver = self.owner_readers.get(module)
                    if resolver is None:
                        raise PublicationReadError("MODULE_OWNER_READER_UNAVAILABLE")
                    resolved = resolver(pg, bindings[module])
                    self._validate_owner_readback(resolved, bindings[module])
                    payloads[module] = resolved.get("payload")
                readback_complete = True

            selected = {
                module: {key: value for key, value in row.items() if key != "module_key"}
                for module, row in sorted(bindings.items())
            }
            binding_rows = [{"module_key": module, **selected[module]} for module in sorted(selected)]
            source_rows = canonical_source_rows(sources)
            context = {
                "contract_id": CONTRACT_ID,
                "module_contract": effective_module_contract(),
                "candidate_only": True,
                "readback_complete": readback_complete,
                "read_mode": "OWNER_READBACK" if readback_complete else "METADATA_ONLY_UNVERIFIED",
                "reader_role_attested": True,
                "trade_date": target_date,
                "model_namespace_id": model_namespace_id,
                "publication_id": publication["publication_id"],
                "revision_no": int(publication["revision_no"]),
                "contracts": {
                    contract_id: {
                        "version": contract.version,
                        "raw_sha256": contract.raw_sha256,
                        "content_format": contract.content_format,
                        "schema_version": contract.schema_version,
                        "namespace": contract.namespace,
                        "publication_id": contract.publication_id,
                        "trade_date": contract.trade_date,
                        "accepted_at": contract.accepted_at.isoformat()
                        if hasattr(contract.accepted_at, "isoformat") else str(contract.accepted_at),
                        "approved_by": contract.approved_by,
                        "approval_ref": contract.approval_ref,
                        "approval_source_revision": contract.approval_source_revision,
                        "approval_occurred_at": contract.approval_occurred_at.isoformat()
                        if hasattr(contract.approval_occurred_at, "isoformat") else str(contract.approval_occurred_at),
                        "approval_recorded_at": contract.approval_recorded_at.isoformat()
                        if hasattr(contract.approval_recorded_at, "isoformat") else str(contract.approval_recorded_at),
                        "approval_source_sha256": contract.approval_source_sha256,
                    }
                    for contract_id, contract in sorted(registered_contracts.items())
                },
                "workspace_owner_mapping": workspace_owner_mapping,
                "publication_status": publication["status"],
                "accepted_at": publication["accepted_at"].isoformat()
                if hasattr(publication["accepted_at"], "isoformat") else str(publication["accepted_at"]),
                "core_revision": int(publication["core_revision"]),
                "publication_lineage_id": publication["publication_lineage_id"],
                "same_day_revision_parent_id": publication["same_day_revision_parent_id"],
                "state_head_id": publication["state_head_id"],
                "state_logical_digest": publication["state_logical_digest"],
                "prior_session_publication_id": publication["prior_session_publication_id"],
                "prior_session_state_head": publication["prior_session_state_head"],
                "prior_session_state_logical_digest": publication["prior_session_state_logical_digest"],
                "prior_session_gap_reason": publication["prior_session_gap_reason"],
                "source_manifest_sha256": str(publication["source_manifest_sha256"]).strip(),
                "computation_identity_sha256": str(publication["computation_identity_sha256"]).strip(),
                "source_bindings": source_rows,
                "source_bindings_digest": digest(canonical(source_rows)),
                "source_manifest_contract_id": publication.get("source_manifest_contract_id"),
                "source_manifest_rehash_status": manifest_status,
                "source_manifest_recomputed_sha256": recomputed_manifest_digest,
                "database_identity": identity,
                "reader_role": role,
                "same_day_parent": parent,
                "page_data": page_data,
                "module_results": selected,
                "module_results_digest": digest(canonical(binding_rows)),
                "module_requirements": {module: "CAPABILITY_OPTIONAL" for module in supported_owner_keys()},
            }
            context["context_token"] = "pg-candidate-" + digest(canonical(context))
            if expected_context_token is not None and context["context_token"] != expected_context_token:
                raise PublicationReadError("STALE_CONTEXT_REQUIRES_REFRESH")
            if resolve_payloads:
                context["module_payloads"] = payloads
            return context

    @staticmethod
    def _map_schema_error(exc, default):
        if getattr(exc, "sqlstate", None) in {"42P01", "42703"}:
            raise PublicationReadError(default) from exc

    @staticmethod
    def _read_database_identity(pg):
        cursor = pg.execute(
            """SELECT current_database(),
                      (SELECT oid FROM pg_database WHERE datname=current_database()),
                      inet_server_addr()::text, inet_server_port()"""
        )
        row = cursor.fetchone()
        if row is None:
            raise PublicationReadError("PG_DATABASE_IDENTITY_UNAVAILABLE")
        return {"database": row[0], "database_oid": row[1], "host": row[2], "port": row[3]}

    @staticmethod
    def _attest_read_role(pg):
        cursor = pg.execute(
            """SELECT current_user, r.rolsuper, r.rolbypassrls,
                      r.rolcreaterole, r.rolcreatedb, r.rolreplication,
                      has_schema_privilege(current_user, 'v4', 'CREATE'),
                      (has_table_privilege(current_user, 'v4.publications', 'INSERT') OR has_table_privilege(current_user, 'v4.publications', 'UPDATE') OR has_table_privilege(current_user, 'v4.publications', 'DELETE') OR has_table_privilege(current_user, 'v4.publications', 'TRUNCATE')),
                      (has_table_privilege(current_user, 'v4.publication_heads', 'INSERT') OR has_table_privilege(current_user, 'v4.publication_heads', 'UPDATE') OR has_table_privilege(current_user, 'v4.publication_heads', 'DELETE') OR has_table_privilege(current_user, 'v4.publication_heads', 'TRUNCATE')),
                      (has_table_privilege(current_user, 'v4.publication_consumed_sources', 'INSERT') OR has_table_privilege(current_user, 'v4.publication_consumed_sources', 'UPDATE') OR has_table_privilege(current_user, 'v4.publication_consumed_sources', 'DELETE') OR has_table_privilege(current_user, 'v4.publication_consumed_sources', 'TRUNCATE')),
                      (has_table_privilege(current_user, 'v4.publication_module_results', 'INSERT') OR has_table_privilege(current_user, 'v4.publication_module_results', 'UPDATE') OR has_table_privilege(current_user, 'v4.publication_module_results', 'DELETE') OR has_table_privilege(current_user, 'v4.publication_module_results', 'TRUNCATE')),
                      (has_table_privilege(current_user, 'v4.contract_versions', 'INSERT') OR has_table_privilege(current_user, 'v4.contract_versions', 'UPDATE') OR has_table_privilege(current_user, 'v4.contract_versions', 'DELETE') OR has_table_privilege(current_user, 'v4.contract_versions', 'TRUNCATE')),
                      (has_table_privilege(current_user, 'v4.contract_approval_events', 'INSERT') OR has_table_privilege(current_user, 'v4.contract_approval_events', 'UPDATE') OR has_table_privilege(current_user, 'v4.contract_approval_events', 'DELETE') OR has_table_privilege(current_user, 'v4.contract_approval_events', 'TRUNCATE')),
                      EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                               WHERE n.nspname='v4' AND c.relkind='S'
                                 AND (has_sequence_privilege(current_user,c.oid,'USAGE')
                                   OR has_sequence_privilege(current_user,c.oid,'UPDATE')))
                 FROM pg_roles r WHERE r.rolname=current_user"""
        )
        row = cursor.fetchone()
        if row is None:
            raise PublicationReadError("PG_READER_ROLE_UNAVAILABLE")
        if any(bool(value) for value in row[1:]):
            raise PublicationReadError("PG_READER_ROLE_HAS_WRITE_PRIVILEGES")
        return {"role_capability_check": "NO_SUPERUSER_NO_BYPASS_NO_CHECKED_WRITE_PRIVILEGES"}

    @staticmethod
    def _validate_publication(row, target_date, namespace):
        if row["status"] != "ACCEPTED" or row["accepted_at"] is None:
            raise PublicationReadError("PUBLICATION_HEAD_TARGET_INVALID")
        if _iso_date(row["trade_date"]) != target_date or row["model_namespace_id"] != namespace:
            raise PublicationReadError("PUBLICATION_DATE_OR_NAMESPACE_MISMATCH")
        if isinstance(row.get("revision_no"), bool) or int(row.get("revision_no", 0)) <= 0:
            raise PublicationReadError("PUBLICATION_REVISION_NO_INVALID")
        for key in ("source_manifest_sha256", "computation_identity_sha256", "state_logical_digest"):
            if not _DIGEST.fullmatch(str(row.get(key) or "").strip()):
                raise PublicationReadError("PUBLICATION_IDENTITY_DIGEST_INVALID")
        if row.get("verified_state_digest") is None or str(row["verified_state_digest"]).strip() != str(row["state_logical_digest"]).strip():
            raise PublicationReadError("PUBLICATION_STATE_HEAD_INVALID")
        if not isinstance(row.get("publication_lineage_id"), str) or not row["publication_lineage_id"].strip():
            raise PublicationReadError("PUBLICATION_LINEAGE_INVALID")
        if not isinstance(row.get("state_head_id"), str) or not row["state_head_id"].strip():
            raise PublicationReadError("PUBLICATION_STATE_HEAD_INVALID")
        if row.get("prior_session_publication_id") is None:
            if row.get("prior_session_state_head") is not None or row.get("prior_session_state_logical_digest") is not None or not row.get("prior_session_gap_reason"):
                raise PublicationReadError("PRIOR_SESSION_IDENTITY_INVALID")
        elif row.get("prior_session_state_head") is None or not _DIGEST.fullmatch(str(row.get("prior_session_state_logical_digest") or "").strip()) or row.get("prior_session_gap_reason") is not None:
            raise PublicationReadError("PRIOR_SESSION_IDENTITY_INVALID")

    @staticmethod
    def _verify_source_manifest(publication, rows):
        contract_id = publication.get("source_manifest_contract_id")
        if contract_id not in {SOURCE_MANIFEST_CONTRACT_ID, SOURCE_MANIFEST_CONTRACT_ID_R3}:
            raise PublicationReadError("SOURCE_MANIFEST_CONTRACT_UNSUPPORTED")
        try:
            actual = (source_manifest_digest_r3(rows) if contract_id == SOURCE_MANIFEST_CONTRACT_ID_R3
                      else source_manifest_digest(rows))
        except Exception as exc:
            raise PublicationReadError("SOURCE_MANIFEST_REHASH_FAILED") from exc
        expected = str(publication.get("source_manifest_sha256") or "").strip().lower()
        if not _DIGEST.fullmatch(expected) or actual != expected:
            raise PublicationReadError("SOURCE_MANIFEST_REHASH_MISMATCH")
        return "REHASH_PASS", actual

    @staticmethod
    def _read_page_data(pg, publication, source_rows):
        """Read only page facts with a verifiable publication/source binding."""
        publication_id = publication["publication_id"]
        target_date = date.fromisoformat(_iso_date(publication["trade_date"]))
        try:
            event_rows = _row_dicts(pg.execute(
                """SELECT logical_event_id,observation_revision,status,payload
                     FROM (
                         SELECT logical_event_id,observation_revision,status,payload,
                                row_number() OVER (
                                    PARTITION BY logical_event_id
                                    ORDER BY observation_revision DESC
                                ) AS event_rank
                           FROM v4.event_observations
                          WHERE publication_id=%s AND publication_revision=%s
                     ) latest
                    WHERE event_rank=1 AND status='ACTIVE'
                    ORDER BY logical_event_id COLLATE \"C\"
                    LIMIT 50001""",
                (publication_id, int(publication["revision_no"])),
            ), ("logical_event_id", "observation_revision", "status", "payload"))
            source_ids = sorted({row["source_revision_id"] for row in source_rows})
            lifecycle_rows = []
            if source_ids:
                lifecycle_rows = _row_dicts(pg.execute(
                    """SELECT security_id,security_type,board,listed_from,listed_to,
                              st_state,trade_status,effective_from,effective_to,
                              observed_at,ingested_at,system_available_at,
                              source_revision_id,source_identity,quality
                         FROM v4.security_lifecycle_facts
                        WHERE source_revision_id=ANY(%s)
                          AND effective_from<=%s
                          AND (effective_to IS NULL OR effective_to>=%s)
                        ORDER BY security_id COLLATE \"C\",effective_from,source_revision_id
                        LIMIT 50001""",
                    (source_ids, target_date, target_date),
                ), ("security_id", "security_type", "board", "listed_from", "listed_to",
                    "st_state", "trade_status", "effective_from", "effective_to",
                    "observed_at", "ingested_at", "system_available_at",
                    "source_revision_id", "source_identity", "quality"))
            core_rows, core_status = PgPublicationReader._read_core_result_rows(
                pg, publication, source_ids,
            )
            membership_rows, membership_status = PgPublicationReader._read_sector_membership_rows(
                pg, publication, source_rows, source_ids,
            )
        except PublicationReadError:
            raise
        except Exception as exc:
            PgPublicationReader._map_schema_error(exc, "PAGE_RELATION_SCHEMA_UNAVAILABLE")
            raise PublicationReadError("PAGE_RELATION_READ_FAILED") from exc
        if len(event_rows) > 50000 or len(lifecycle_rows) > 50000:
            raise PublicationReadError("PAGE_RELATION_ROW_LIMIT_EXCEEDED")
        for row in event_rows:
            if (not isinstance(row.get("logical_event_id"), str) or not row["logical_event_id"]
                    or isinstance(row.get("observation_revision"), bool)
                    or int(row.get("observation_revision", 0)) < 1
                    or row.get("status") != "ACTIVE" or not isinstance(row.get("payload"), Mapping)):
                raise PublicationReadError("EVENT_OBSERVATION_IDENTITY_INVALID")
            event_date = row["payload"].get("trade_date")
            if event_date is not None and _iso_date(event_date) != target_date.isoformat():
                raise PublicationReadError("EVENT_TRADE_DATE_MISMATCH")
        bound_source_ids = {row["source_revision_id"] for row in source_rows}
        for row in lifecycle_rows:
            if row.get("source_revision_id") not in bound_source_ids:
                raise PublicationReadError("LIFECYCLE_SOURCE_NOT_PUBLICATION_BOUND")
            if (not isinstance(row.get("quality"), str) or not row["quality"].strip()
                    or not isinstance(row.get("security_id"), str) or not row["security_id"].strip()
                    or not isinstance(row.get("source_revision_id"), str)):
                raise PublicationReadError("LIFECYCLE_ROW_QUALITY_OR_IDENTITY_MISSING")
            if row.get("listed_from") is not None and row.get("listed_to") is not None and row["listed_to"] < row["listed_from"]:
                raise PublicationReadError("LIFECYCLE_LISTING_DATE_WINDOW_INVALID")
        def json_row(row):
            return {key: value.isoformat() if hasattr(value, "isoformat") else value for key, value in row.items()}
        return {
            "publication_id": publication_id,
            "trade_date": target_date.isoformat(),
            "summary_events": [json_row(row) for row in event_rows],
            "entity_lifecycle": [json_row(row) for row in lifecycle_rows],
            "daily_core_rows": [json_row(row) for row in core_rows],
            "daily_core_status": core_status,
            "sector_membership_rows": [json_row(row) for row in membership_rows],
            "sector_membership_status": membership_status,
            "uncovered": {
                "entity_prices": None if core_status == "VERIFIED" else core_status,
                "identity_names": "NO_V4_PUBLICATION_BOUND_IDENTITY_NAME_RELATION",
                "replay": "NO_V4_PUBLICATION_BOUND_REPLAY_RELATION",
                "sector_membership": None if membership_status == "VERIFIED" else membership_status,
                "cohort": "NO_V4_PUBLICATION_BOUND_COHORT_RELATION",
                "settlement": "NO_V4_PUBLICATION_BOUND_SETTLEMENT_RELATION",
            },
        }

    @staticmethod
    def _read_core_result_rows(pg, publication, bound_source_ids):
        """Read R6 Core rows only when their immutable result is bound to this exact publication."""
        publication_id = publication["publication_id"]
        revision = int(publication["revision_no"])
        target = _iso_date(publication["trade_date"])
        try:
            snapshot_cursor = pg.execute(
                """SELECT trade_date,result_contract_id,source_manifest_sha256,result_sha256,row_count,
                          producer_contract_id,producer_sha256,producer_receipt_sha256
                     FROM v4.daily_core_result_snapshots
                    WHERE publication_id=%s AND publication_revision=%s""",
                (publication_id, revision),
            )
            snapshot = snapshot_cursor.fetchone()
            if snapshot is None:
                return [], "NO_PUBLICATION_BOUND_CORE_RESULT"
            if (snapshot[0].isoformat() != target
                    or snapshot[1] != "V4_DAILY_CORE_RESULT_BINDING_R6"
                    or str(snapshot[2]).strip() != str(publication["source_manifest_sha256"]).strip()):
                raise PublicationReadError("CORE_RESULT_PUBLICATION_IDENTITY_MISMATCH")
            cursor = pg.execute(
                """SELECT trade_date,security_id,security_type,trade_status,open,high,low,close,
                          volume,amount,turnover_rate,turnover_status,ma5,ma20,ma60,history_status,
                          price_basis,source_revision_id,profile_payload,quality_status,row_sha256
                     FROM v4.daily_core_result_rows
                    WHERE publication_id=%s AND publication_revision=%s
                    ORDER BY security_id COLLATE "C"
                    LIMIT 20001""",
                (publication_id, revision),
            )
            columns = ("trade_date", "security_id", "security_type", "trade_status", "open", "high", "low", "close",
                       "volume", "amount", "turnover_rate", "turnover_status", "ma5", "ma20", "ma60", "history_status",
                       "price_basis", "source_revision_id", "profile_payload", "quality_status", "row_sha256")
            rows = _row_dicts(cursor, columns)
        except PublicationReadError:
            raise
        except Exception as exc:
            if getattr(exc, "sqlstate", None) == "42P01":
                return [], "CORE_RESULT_RELATION_UNAVAILABLE"
            PgPublicationReader._map_schema_error(exc, "CORE_RESULT_RELATION_UNAVAILABLE")
            raise PublicationReadError("CORE_RESULT_READ_FAILED") from exc
        if len(rows) > 20000:
            raise PublicationReadError("CORE_RESULT_ROW_LIMIT_EXCEEDED")
        if len(rows) != int(snapshot[4]) or not rows:
            raise PublicationReadError("CORE_RESULT_ROW_COUNT_MISMATCH")
        from .v4_daily_core_result_r6 import _sha
        verified = []
        for row in rows:
            if (_iso_date(row["trade_date"]) != target
                    or row["price_basis"] != "TDX_GBBQ_UNCHANGED"
                    or row["source_revision_id"] not in bound_source_ids):
                raise PublicationReadError("CORE_RESULT_ROW_SOURCE_OR_T0_MISMATCH")
            row_sha = str(row.pop("row_sha256")).strip()
            row["trade_date"] = target
            if _sha(row) != row_sha:
                raise PublicationReadError("CORE_RESULT_ROW_DIGEST_MISMATCH")
            row["row_sha256"] = row_sha
            verified.append(row)
        verified.sort(key=lambda row: str(row["security_id"]).encode("utf-8"))
        result_material = {
            "contract_id": "V4_DAILY_CORE_RESULT_BINDING_R6", "contract_version": "1.0.0",
            "publication_id": publication_id, "publication_revision": revision,
            "trade_date": target, "source_manifest_sha256": str(snapshot[2]).strip(),
            "producer_contract_id": snapshot[5], "producer_sha256": str(snapshot[6]).strip(),
            "producer_receipt_sha256": str(snapshot[7]).strip(), "rows": verified,
        }
        if _sha(result_material) != str(snapshot[3]).strip():
            raise PublicationReadError("CORE_RESULT_AGGREGATE_DIGEST_MISMATCH")
        return verified, "VERIFIED"

    @staticmethod
    def _read_sector_membership_rows(pg, publication, source_rows, bound_source_ids):
        """Read dated membership only where the snapshot source revision is consumed by this publication."""
        if not bound_source_ids:
            return [], "NO_PUBLICATION_BOUND_SECTOR_MEMBERSHIP_RELATION"
        target = _iso_date(publication["trade_date"])
        source_digest_by_id = {
            str(row["source_revision_id"]): str(row["digest"]).strip()
            for row in source_rows
        }
        try:
            cursor = pg.execute(
                """SELECT f.membership_fact_id,f.snapshot_id,f.source_revision_id,f.sector_id,
                          f.sector_code,f.sector_name,f.sector_type,f.source_security_key,f.security_id,
                          f.identity_status,f.target_trade_date,f.membership_asof_date,f.membership_basis,
                          f.membership_quality,f.pit_observed,f.historical_backtest_safe,
                          s.source_digest,s.row_count,s.membership_quality,s.pit_observed
                     FROM v4.sector_membership_facts f
                     JOIN v4.sector_membership_snapshots s ON s.snapshot_id=f.snapshot_id
                    WHERE f.source_revision_id=ANY(%s) AND f.target_trade_date=%s
                    ORDER BY f.sector_id COLLATE "C",f.source_security_key COLLATE "C"
                    LIMIT 50001""",
                (bound_source_ids, target),
            )
            columns = (
                "membership_fact_id", "snapshot_id", "source_revision_id", "sector_id", "sector_code",
                "sector_name", "sector_type", "source_security_key", "security_id", "identity_status",
                "target_trade_date", "membership_asof_date", "membership_basis", "membership_quality",
                "pit_observed", "historical_backtest_safe", "snapshot_source_digest", "snapshot_row_count",
                "snapshot_quality", "snapshot_pit_observed",
            )
            rows = _row_dicts(cursor, columns)
        except Exception as exc:
            if getattr(exc, "sqlstate", None) == "42P01":
                return [], "SECTOR_MEMBERSHIP_RELATION_UNAVAILABLE"
            PgPublicationReader._map_schema_error(exc, "PAGE_RELATION_SCHEMA_UNAVAILABLE")
            raise PublicationReadError("SECTOR_MEMBERSHIP_READ_FAILED") from exc
        if len(rows) > 50000:
            raise PublicationReadError("SECTOR_MEMBERSHIP_ROW_LIMIT_EXCEEDED")
        if not rows:
            return [], "NO_PUBLICATION_BOUND_SECTOR_MEMBERSHIP_ROWS"
        by_snapshot = {}
        for row in rows:
            target_date = _iso_date(row["target_trade_date"])
            source_id = row["source_revision_id"]
            if (target_date != target or source_id not in bound_source_ids
                    or source_digest_by_id.get(source_id) != str(row["snapshot_source_digest"]).strip()
                    or not isinstance(row.get("sector_id"), str) or not row["sector_id"].strip()
                    or not isinstance(row.get("sector_name"), str) or not row["sector_name"].strip()
                    or row.get("sector_type") not in {"INDUSTRY", "THEME", "STYLE", "UNKNOWN"}
                    or row.get("membership_basis") not in {
                        "PIT_OBSERVED", "CURRENT_TDX_MEMBERSHIP", "CURRENT_MEMBERSHIP_REPLAY", "DERIVED_PARENT_MEMBERSHIP",
                    }
                    or not isinstance(row.get("membership_quality"), str) or not row["membership_quality"].strip()
                    or row.get("identity_status") not in {"MAPPED", "UNKNOWN"}
                    or (row.get("identity_status") == "MAPPED" and not row.get("security_id"))
                    or (row.get("identity_status") == "UNKNOWN" and row.get("security_id") is not None)):
                raise PublicationReadError("SECTOR_MEMBERSHIP_PUBLICATION_BINDING_INVALID")
            pit = row.get("membership_basis") == "PIT_OBSERVED"
            if (bool(row.get("pit_observed")) != pit
                    or bool(row.get("snapshot_pit_observed")) != pit
                    or bool(row.get("historical_backtest_safe")) and not pit
                    or bool(row.get("historical_backtest_safe"))
                       and (row.get("membership_quality") != "PIT_OBSERVED_ACCEPTED" or row.get("identity_status") != "MAPPED")
                    or pit and row.get("membership_asof_date") is None
                    or row.get("snapshot_quality") != row.get("membership_quality")):
                raise PublicationReadError("SECTOR_MEMBERSHIP_PIT_OR_QUALITY_INVALID")
            by_snapshot.setdefault(row["snapshot_id"], []).append(row)
        for snapshot_rows in by_snapshot.values():
            if any(int(row["snapshot_row_count"]) != len(snapshot_rows) for row in snapshot_rows):
                raise PublicationReadError("SECTOR_MEMBERSHIP_SNAPSHOT_ROW_COUNT_MISMATCH")
        if len(by_snapshot) != 1:
            raise PublicationReadError("MULTIPLE_SECTOR_MEMBERSHIP_SNAPSHOTS_FOR_PUBLICATION")
        return rows, "VERIFIED"

    @staticmethod
    def _read_same_day_parent(pg, publication):
        parent_id = publication.get("same_day_revision_parent_id")
        revision_no = int(publication["revision_no"])
        if parent_id is None:
            if revision_no != 1:
                raise PublicationReadError("SAME_DAY_REVISION_PARENT_MISSING")
            return None
        cursor = pg.execute(
            """SELECT publication_id, model_namespace_id, trade_date,
                      publication_lineage_id, revision_no
                 FROM v4.publications WHERE publication_id=%s""",
            (parent_id,),
        )
        parent = _as_dict(cursor.fetchone(), (
            "publication_id", "model_namespace_id", "trade_date", "publication_lineage_id", "revision_no",
        ))
        if (parent is None or parent["model_namespace_id"] != publication["model_namespace_id"]
                or _iso_date(parent["trade_date"]) != _iso_date(publication["trade_date"])
                or parent["publication_lineage_id"] != publication["publication_lineage_id"]
                or int(parent["revision_no"]) + 1 != revision_no):
            raise PublicationReadError("SAME_DAY_REVISION_PARENT_INVALID")
        return {"publication_id": parent_id, "revision_no": int(parent["revision_no"])}

    @staticmethod
    def _read_sources(pg, publication):
        contract_id = publication.get("source_manifest_contract_id")
        if contract_id == SOURCE_MANIFEST_CONTRACT_ID_R3:
            query = """SELECT cs.source_key, cs.source_revision_id, cs.digest,
                      sr.logical_fact_id, sr.revision_no, sr.digest AS revision_digest,
                      sr.effective_from, sr.effective_to, sr.provider_available_at,
                      sr.observed_at, sr.ingested_at, sr.system_available_at, sr.tombstone,
                      sp.package_id AS source_package_id,
                      sp.contract_version AS source_package_contract_version,
                      sp.package_sha256 AS source_package_sha256,
                      sp.page_observed_at AS source_package_page_observed_at,
                      sp.target_trade_date AS source_package_target_trade_date,
                      sp.parser_version AS source_package_parser_version,
                      sp.accepted_scope AS source_package_accepted_scope,
                      sp.manifest AS source_package_manifest,
                      f.acceptance_receipt_id AS source_fact_acceptance_receipt_id,
                      f.fact_digest AS source_fact_digest,f.source_fact_sha256,
                      f.record_locator AS source_fact_record_locator,f.record_count AS source_fact_record_count
                 FROM v4.publication_consumed_sources cs
                 JOIN v4.source_revisions sr ON sr.source_revision_id=cs.source_revision_id
                 JOIN v4.source_packages sp ON sp.package_id=sr.source_package_id
                 JOIN v4.source_package_facts f
                   ON f.package_id=sr.source_package_id
                  AND f.source_key=sr.source_package_source_key
                  AND f.logical_fact_id=sr.logical_fact_id
                  AND f.fact_digest=sr.source_fact_digest
                WHERE cs.publication_id=%s
                ORDER BY convert_to(cs.source_key, 'UTF8')"""
            columns = (
                "source_key", "source_revision_id", "digest", "logical_fact_id", "revision_no",
                "revision_digest", "effective_from", "effective_to", "provider_available_at",
                "observed_at", "ingested_at", "system_available_at", "tombstone",
                "source_package_id", "source_package_contract_version", "source_package_sha256",
                "source_package_page_observed_at", "source_package_target_trade_date",
                "source_package_parser_version", "source_package_accepted_scope", "source_package_manifest",
                "source_fact_acceptance_receipt_id", "source_fact_digest", "source_fact_sha256",
                "source_fact_record_locator", "source_fact_record_count",
            )
        else:
            query = """SELECT cs.source_key, cs.source_revision_id, cs.digest,
                      sr.logical_fact_id, sr.revision_no, sr.digest AS revision_digest,
                      sr.effective_from, sr.effective_to, sr.provider_available_at,
                      sr.observed_at, sr.ingested_at, sr.system_available_at, sr.tombstone,
                      sp.package_id AS source_package_id,
                      sp.contract_version AS source_package_contract_version,
                      sp.package_sha256 AS source_package_sha256,
                      sp.page_observed_at AS source_package_page_observed_at,
                      sp.target_trade_date AS source_package_target_trade_date,
                      sp.parser_version AS source_package_parser_version,
                      sp.accepted_scope AS source_package_accepted_scope
                 FROM v4.publication_consumed_sources cs
                 JOIN v4.source_revisions sr ON sr.source_revision_id=cs.source_revision_id
                 LEFT JOIN v4.source_packages sp ON sp.package_id=sr.source_package_id
                WHERE cs.publication_id=%s
                ORDER BY convert_to(cs.source_key, 'UTF8')"""
            columns = (
                "source_key", "source_revision_id", "digest", "logical_fact_id", "revision_no",
                "revision_digest", "effective_from", "effective_to", "provider_available_at",
                "observed_at", "ingested_at", "system_available_at", "tombstone",
                "source_package_id", "source_package_contract_version", "source_package_sha256",
                "source_package_page_observed_at", "source_package_target_trade_date",
                "source_package_parser_version", "source_package_accepted_scope",
            )
        cursor = pg.execute(
            query,
            (publication["publication_id"],),
        )
        rows = _row_dicts(cursor, columns)
        if not rows:
            raise PublicationReadError("PUBLICATION_SOURCE_SET_EMPTY")
        accepted_at = publication["accepted_at"]
        target = date.fromisoformat(_iso_date(publication["trade_date"]))
        seen = set()
        for row in rows:
            if row["source_key"] in seen:
                raise PublicationReadError("DUPLICATE_PUBLICATION_SOURCE_KEY")
            seen.add(row["source_key"])
            if (row.get("source_package_accepted_scope") != "ACCEPTED_SOURCE_PACKAGE"
                    or row.get("source_package_id") is None):
                raise PublicationReadError("SOURCE_PACKAGE_NOT_ACCEPTED_OR_UNBOUND")
            if _iso_date(row.get("source_package_target_trade_date")) != target.isoformat():
                raise PublicationReadError("SOURCE_PACKAGE_T0_MISMATCH")
            page_observed_at = row.get("source_package_page_observed_at")
            if not isinstance(page_observed_at, datetime) or page_observed_at.tzinfo is None:
                raise PublicationReadError("SOURCE_PACKAGE_OBSERVATION_CLOCK_MISSING")
            if page_observed_at.astimezone(ZoneInfo("Asia/Shanghai")).date() < target:
                raise PublicationReadError("FUTURE_TRADE_DATE_WITHOUT_SAME_DAY_SOURCE_OBSERVATION")
            if page_observed_at > accepted_at:
                raise PublicationReadError("SOURCE_PACKAGE_OBSERVED_AFTER_PUBLICATION_ACCEPTANCE")
            if not _DIGEST.fullmatch(str(row["digest"]).strip()) or str(row["digest"]).strip() != str(row["revision_digest"]).strip():
                raise PublicationReadError("PUBLICATION_SOURCE_DIGEST_MISMATCH")
            if row["tombstone"] is True:
                raise PublicationReadError("PUBLICATION_SOURCE_TOMBSTONED")
            start = row["effective_from"]
            end = row["effective_to"]
            if start is not None and start > target or end is not None and end < target:
                raise PublicationReadError("PUBLICATION_SOURCE_OUTSIDE_T0_WINDOW")
            clocks = [row["observed_at"], row["ingested_at"], row["system_available_at"]]
            if any(value is None or value > accepted_at for value in clocks):
                raise PublicationReadError("PUBLICATION_SOURCE_AVAILABLE_AFTER_ACCEPTANCE")
            if row["provider_available_at"] is not None and row["provider_available_at"] > accepted_at:
                raise PublicationReadError("PUBLICATION_SOURCE_PROVIDER_TIME_AFTER_ACCEPTANCE")
            if contract_id == SOURCE_MANIFEST_CONTRACT_ID_R3:
                manifest = row.get("source_package_manifest")
                try:
                    from .v4_daily_source_ingest_r6 import verify_source_package_manifest_authority
                    proof = verify_source_package_manifest_authority(manifest)
                except (TypeError, ValueError) as exc:
                    raise PublicationReadError("SOURCE_PACKAGE_INDEPENDENT_ACCEPTANCE_INVALID") from exc
                if (manifest.get("AS_RECORDED") is not True or manifest.get("PIT_ELIGIBLE") is not True
                        or row["source_fact_acceptance_receipt_id"] != manifest.get("acceptance_receipt_id")):
                    raise PublicationReadError("SOURCE_PACKAGE_ACCEPTANCE_PROOF_INVALID")
                bindings = manifest.get("source_fact_bindings")
                expected_fact = next((item for item in bindings if isinstance(item, dict)
                                      and item.get("source_key") == row["source_key"]), None) if isinstance(bindings, list) else None
                if (not isinstance(expected_fact, dict)
                        or expected_fact.get("fact_digest") != row["source_fact_digest"]
                        or expected_fact.get("source_fact_sha256") != row["source_fact_sha256"]
                        or expected_fact.get("record_locator") != row["source_fact_record_locator"]
                        or expected_fact.get("record_count") != row["source_fact_record_count"]
                        or expected_fact.get("acceptance_receipt_id") != row["source_fact_acceptance_receipt_id"]):
                    raise PublicationReadError("SOURCE_PACKAGE_FACT_MANIFEST_MISMATCH")
                row.update({
                    "source_package_acceptance_receipt_id": manifest["acceptance_receipt_id"],
                    "source_package_as_recorded": manifest["AS_RECORDED"],
                    "source_package_pit_eligible": manifest["PIT_ELIGIBLE"],
                    "source_package_acceptance_proof_sha256": proof["receipt_sha256"],
                    "source_fact_digest": row["source_fact_digest"],
                    "source_fact_sha256": row["source_fact_sha256"],
                    "source_fact_record_locator": row["source_fact_record_locator"],
                    "source_fact_record_count": row["source_fact_record_count"],
                    "source_fact_acceptance_receipt_id": row["source_fact_acceptance_receipt_id"],
                })
        return rows

    @staticmethod
    def _read_module_bindings(pg, publication, database_identity):
        try:
            cursor = pg.execute(
                """SELECT module_key, module_contract_id, database_identity,
                      owner_schema, owner_relation, owner_version_token,
                      owner_trade_date, owner_contract_id, result_digest,
                      row_count, quality_status, as_recorded, pit_eligible
                 FROM v4.publication_module_results
                WHERE publication_id=%s
                ORDER BY module_key""",
                (publication["publication_id"],),
            )
        except Exception as exc:
            PgPublicationReader._map_schema_error(exc, "MODULE_RESULT_BINDING_SCHEMA_UNAVAILABLE")
            raise PublicationReadError("MODULE_RESULT_BINDING_READ_FAILED") from exc
        columns = (
            "module_key", "module_contract_id", "database_identity", "owner_schema",
            "owner_relation", "owner_version_token", "owner_trade_date", "owner_contract_id",
            "result_digest", "row_count", "quality_status", "as_recorded", "pit_eligible",
        )
        bindings = {}
        for row in _row_dicts(cursor, columns):
            module = row["module_key"]
            if not isinstance(module, str) or not _MODULE.fullmatch(module):
                raise PublicationReadError("INVALID_MODULE_KEY")
            if module in bindings:
                raise PublicationReadError("DUPLICATE_MODULE_RESULT_BINDING")
            if module not in OWNER_FAMILIES:
                raise PublicationReadError("MODULE_NOT_IN_EFFECTIVE_CONTRACT")
            if row["module_contract_id"] != MODULE_CONTRACT_ID:
                raise PublicationReadError("MODULE_CONTRACT_ID_MISMATCH")
            family_contract = OWNER_FAMILIES[module]
            if (row["owner_contract_id"] != family_contract["owner_contract_id"]
                    or row["owner_relation"] != family_contract["relation"]):
                raise PublicationReadError("OWNER_FAMILY_CONTRACT_MISMATCH")
            for key in ("owner_schema", "owner_relation"):
                if not isinstance(row.get(key), str) or not _IDENTIFIER.fullmatch(row[key]):
                    raise PublicationReadError("INVALID_OWNER_LOCATOR")
            for key in ("owner_version_token", "owner_contract_id", "quality_status"):
                if not isinstance(row.get(key), str) or not row[key].strip():
                    raise PublicationReadError("OWNER_IDENTITY_INCOMPLETE")
            if not isinstance(row.get("database_identity"), Mapping) or dict(row["database_identity"]) != dict(database_identity):
                raise PublicationReadError("PG_DATABASE_IDENTITY_MISMATCH")
            if not _DIGEST.fullmatch(str(row.get("result_digest", ""))):
                raise PublicationReadError("MODULE_RESULT_DIGEST_INVALID")
            count = row.get("row_count")
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise PublicationReadError("MODULE_RESULT_ROW_COUNT_INVALID")
            if row.get("as_recorded") not in (True, False) or row.get("pit_eligible") not in (True, False):
                raise PublicationReadError("OWNER_QUALIFICATION_INVALID")
            if _iso_date(row.get("owner_trade_date")) != _iso_date(publication["trade_date"]):
                raise PublicationReadError("OWNER_T0_MISMATCH")
            row["owner_trade_date"] = _iso_date(row["owner_trade_date"])
            row["row_count"] = count
            bindings[module] = row
        return bindings

    @staticmethod
    def _validate_owner_readback(resolved, binding):
        if not isinstance(resolved, Mapping):
            raise PublicationReadError("OWNER_READBACK_IDENTITY_MISSING")
        identity_keys = (
            "database_identity", "owner_schema", "owner_relation", "owner_version_token",
            "owner_trade_date", "owner_contract_id", "result_digest", "row_count",
        )
        if any(key not in resolved for key in identity_keys):
            raise PublicationReadError("OWNER_READBACK_IDENTITY_MISSING")
        actual, expected = dict(resolved), {key: binding[key] for key in identity_keys}
        if isinstance(actual.get("database_identity"), Mapping):
            actual["database_identity"] = dict(actual["database_identity"])
        if isinstance(expected.get("database_identity"), Mapping):
            expected["database_identity"] = dict(expected["database_identity"])
        actual["owner_trade_date"] = _iso_date(actual["owner_trade_date"])
        expected["owner_trade_date"] = _iso_date(expected["owner_trade_date"])
        try:
            actual["row_count"] = int(actual["row_count"])
            expected["row_count"] = int(expected["row_count"])
        except (TypeError, ValueError) as exc:
            raise PublicationReadError("OWNER_READBACK_IDENTITY_MISMATCH") from exc
        if any(actual[key] != expected[key] for key in identity_keys):
            raise PublicationReadError("OWNER_READBACK_IDENTITY_MISMATCH")
        if "payload" not in resolved:
            raise PublicationReadError("OWNER_READBACK_PAYLOAD_MISSING")
