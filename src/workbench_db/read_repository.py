"""Backend-neutral read repository boundary for pre-cutover projections."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Protocol

import duckdb


class PublicationReadRepository(Protocol):
    """Stable read contract shared by DuckDB and PostgreSQL adapters."""

    def publication_heads(self, *, include_analysis: bool = False) -> dict[str, Any]: ...

    def research_security_names(self, publication_id: str) -> dict[str, str]: ...

    def research_v3_3_bundle(self, publication_id: str, trade_date: str) -> tuple[dict[str, Any], list[dict[str, Any]]] | None: ...

    def sector_metadata(self, publication_id: str) -> list[dict[str, str]]: ...

    def relation_edges_for_publication(self, publication_id: str) -> list[tuple[Any, ...]]: ...

    def publication_source_identity(self, publication_id: str) -> tuple[str, int | None, str | None]: ...

    def source_bundles(self) -> list[tuple[str, Any]]: ...


class DuckDBReadRepository:
    """Read-only implementation used for shadow comparisons and rollback."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path).resolve()
        self.connection: duckdb.DuckDBPyConnection | None = None

    def open(self) -> "DuckDBReadRepository":
        self.connection = duckdb.connect(str(self.database_path), read_only=True)
        return self

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
        self.connection = None

    def __enter__(self) -> "DuckDBReadRepository":
        return self.open()

    def __exit__(self, *_: object) -> None:
        self.close()

    @contextmanager
    def _cursor(self) -> Iterator[duckdb.DuckDBPyConnection]:
        if self.connection is not None:
            yield self.connection
            return
        # Lazy per-call sessions keep the compatibility reader from holding
        # a process-wide DuckDB handle while writers or the cutover provider
        # are active.  The explicit context-manager path remains available for
        # batched shadow reads.
        with duckdb.connect(str(self.database_path), read_only=True) as transient:
            yield transient

    def publication_heads(self, *, include_analysis: bool = False) -> dict[str, Any]:
        with self._cursor() as con:
            rows = con.execute(
                """select cast(h.trade_date as varchar),h.publication_id
                   from publication_heads h join publications p using(publication_id)
                  where p.status='SUCCESS'
                    and (p.production_version not like 'm4-%' or exists (
                        select 1 from publication_analysis_snapshots a
                         where a.publication_id=p.publication_id and a.domain='LOCAL_RECONSTRUCTED'))
                  order by h.trade_date desc"""
            ).fetchall()
        items = [{"trade_date": str(day), "publication_id": str(publication_id)} for day, publication_id in rows]
        if include_analysis:
            # Analysis enrichment is intentionally owned by the PG adapter in
            # the current shadow stage; callers must compare the basic head
            # projection before enabling the nested capability contract.
            for item in items:
                item["analysis_capabilities"] = None
        return {"items": items, "latest_publication_id": items[0]["publication_id"] if items else None}

    def research_security_names(self, publication_id: str) -> dict[str, str]:
        with self._cursor() as con:
            rows = con.execute(
                "select security_id,security_name from stock_daily where publication_id=? and security_name is not null",
                [publication_id],
            ).fetchall()
        return {str(security_id): str(name) for security_id, name in rows}

    def research_v3_3_bundle(self, publication_id: str, trade_date: str) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
        with self._cursor() as con:
            run = con.execute(
                """select bundle_digest,research_run_id,cast(trade_date as varchar),publication_id,
                          snapshot_id,membership_snapshot_id,bundle_contract_id,parameter_hash,
                          dependency_lock_hash,history_basis,result_count,bundle_path,status
                     from research_runs_v3_3
                    where publication_id=? and cast(trade_date as varchar)=? and status='COMPLETE'
                    order by registered_at desc limit 1""",
                [publication_id, str(trade_date)],
            ).fetchone()
            if not run:
                return None
            rows = con.execute(
                "select result_payload from research_candidates_v3_3 where bundle_digest=? order by security_id",
                [run[0]],
            ).fetchall()
        if int(run[10]) != len(rows):
            return None
        results: list[dict[str, Any]] = []
        for (payload,) in rows:
            value = json.loads(str(payload)) if not isinstance(payload, (dict, list)) else payload
            if not isinstance(value, dict):
                return None
            results.append(value)
        identity = {
            "research_run_id": str(run[1]), "trade_date": str(run[2]), "publication_id": str(run[3]),
            "snapshot_id": str(run[4]), "membership_snapshot_id": str(run[5]),
            "parameter_hash": str(run[7]), "dependency_lock_hash": str(run[8]), "history_basis": str(run[9]),
        }
        active = {"contract_id": str(run[6]), "bundle_path": str(run[11]), "output_digest": str(run[0]), "identity": identity}
        return active, results

    def sector_metadata(self, publication_id: str) -> list[dict[str, str]]:
        with self._cursor() as con:
            rows = con.execute(
                "select sector_id,sector_name,sector_type from sector_daily where publication_id=? order by sector_id",
                [publication_id],
            ).fetchall()
        return [{"sector_id": str(sector_id), "sector_name": str(name or sector_id), "sector_type": str(kind or "LOCAL")} for sector_id, name, kind in rows]

    def relation_edges_for_publication(self, publication_id: str) -> list[tuple[Any, ...]]:
        with self._cursor() as con:
            return con.execute(
                """select b.publication_id,b.source_scope,b.revision_no,e.sector_id,e.security_id,e.source_kind,e.from_revision,e.to_revision
                     from relation_publication_bindings b join relation_edge_intervals e on e.source_scope=b.source_scope
                      and e.from_revision<=b.revision_no and (e.to_revision is null or b.revision_no<e.to_revision)
                    where b.publication_id=? order by b.source_scope,e.sector_id,e.security_id,e.source_kind""",
                [publication_id],
            ).fetchall()

    def publication_source_identity(self, publication_id: str) -> tuple[str, int | None, str | None]:
        with self._cursor() as con:
            row = con.execute(
                "select cast(trade_date as varchar),source_revision_id,source_identity_sha256 "
                "from publications where publication_id=? and status='SUCCESS'",
                [publication_id],
            ).fetchone()
        if not row:
            raise KeyError("PUBLICATION_NOT_FOUND")
        return str(row[0]), (int(row[1]) if row[1] is not None else None), (str(row[2]) if row[2] is not None else None)

    def source_bundles(self) -> list[tuple[str, Any]]:
        with self._cursor() as con:
            return list(con.execute("select source_bundle_id,payload_json from source_bundles").fetchall())


__all__ = ["DuckDBReadRepository", "PublicationReadRepository"]
