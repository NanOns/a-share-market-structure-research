"""PostgreSQL repository boundary used during shadow reads and cutover.

The existing DuckDB repository remains the legacy/offline path until the
cutover gate passes.  This adapter intentionally exposes parameterized reads
and transaction boundaries without leaking PostgreSQL SQL into HTTP handlers.
"""
from __future__ import annotations

import os
import json
from contextlib import contextmanager
from typing import Any, Iterator, Sequence

import psycopg
from psycopg import sql

from .read_repository import PublicationReadRepository


DEFAULT_DSN = "host=127.0.0.1 port=5432 dbname=market_research user=postgres"


class PostgresRepository(PublicationReadRepository):
    def __init__(self, dsn: str | None = None, *, schema: str = "workbench", statement_timeout_ms: int = 30_000):
        self.dsn = dsn or os.environ.get("WORKBENCH_PG_DSN") or DEFAULT_DSN
        self.schema = schema
        self.statement_timeout_ms = statement_timeout_ms
        self.connection: psycopg.Connection[Any] | None = None

    def open(self) -> "PostgresRepository":
        self.connection = psycopg.connect(self.dsn)
        with self.connection.cursor() as cur:
            # SET does not accept a bind placeholder in PostgreSQL.  Use
            # set_config so the timeout remains parameterized and cannot be
            # changed by a DSN/identifier injection.
            cur.execute("select set_config('statement_timeout', %s, false)", (f"{self.statement_timeout_ms}ms",))
            cur.execute("set timezone = 'UTC'")
        self.connection.commit()
        return self

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
        self.connection = None

    def __enter__(self) -> "PostgresRepository":
        return self.open()

    def __exit__(self, *_: object) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[psycopg.Connection[Any]]:
        if self.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        try:
            yield self.connection
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def count(self, table: str) -> int:
        if self.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        with self.connection.cursor() as cur:
            cur.execute(sql.SQL("select count(*) from {}.{}").format(sql.Identifier(self.schema), sql.Identifier(table)))
            return int(cur.fetchone()[0])

    def fetch(self, query: str, params: Sequence[Any] = ()) -> list[tuple[Any, ...]]:
        if self.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        with self.connection.cursor() as cur:
            cur.execute(query, params)
            return list(cur.fetchall())

    def table_counts(self, tables: Sequence[str]) -> dict[str, int]:
        return {table: self.count(table) for table in tables}

    def research_security_names(self, publication_id: str) -> dict[str, str]:
        """Read the registered V3.3 security-name projection for one publication.

        Bundle JSON remains an immutable managed artifact; PostgreSQL only
        supplies the relational name projection used to decorate the read
        model.  The publication key prevents a name from another snapshot
        being reused.
        """
        if self.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        query = sql.SQL(
            "select security_id,security_name from {schema}.stock_daily "
            "where publication_id=%s and security_name is not null"
        ).format(schema=sql.Identifier(self.schema))
        with self.connection.cursor() as cur:
            cur.execute(query, (publication_id,))
            return {str(security_id): str(name) for security_id, name in cur.fetchall()}

    def research_v3_3_bundle(self, publication_id: str, trade_date: str) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
        """Read the immutable bundle selected by the PostgreSQL date head."""
        if self.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        schema = sql.Identifier(self.schema)
        run_query = sql.SQL(
            """select r.bundle_digest,r.research_run_id,cast(r.trade_date as text),r.publication_id,
                      r.snapshot_id,r.membership_snapshot_id,r.bundle_contract_id,r.parameter_hash,
                      r.dependency_lock_hash,r.history_basis,r.result_count,r.bundle_path,r.status
                 from {schema}.research_bundle_heads h
                 join {schema}.research_runs_v3_3 r using(bundle_digest)
                where h.publication_id=%s and cast(h.trade_date as text)=%s and r.status='COMPLETE'"""
        ).format(schema=schema)
        with self.connection.cursor() as cur:
            cur.execute(run_query, (publication_id, str(trade_date)))
            run = cur.fetchone()
            if not run:
                return None
            candidates_query = sql.SQL(
                "select result_payload from {}.research_candidates_v3_3 where bundle_digest=%s order by security_id"
            ).format(schema)
            cur.execute(candidates_query, (run[0],))
            rows = cur.fetchall()
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

    def active_research_v3_3_bundle(self) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
        """Read the bundle head for the latest publication head in PostgreSQL."""
        if self.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        schema = sql.Identifier(self.schema)
        query = sql.SQL(
            "with latest as (select publication_id,trade_date from {schema}.publication_heads order by trade_date desc limit 1) "
            "select latest.publication_id,cast(latest.trade_date as text) from latest "
            "join {schema}.research_bundle_heads b using(trade_date,publication_id)"
        ).format(schema=schema)
        with self.connection.cursor() as cur:
            cur.execute(query)
            row = cur.fetchone()
        return self.research_v3_3_bundle(str(row[0]), str(row[1])) if row else None

    def publication_heads(self, *, include_analysis: bool = False) -> dict[str, Any]:
        """Return the public publication head projection used by the API."""
        if self.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        query = sql.SQL(
            "select cast(h.trade_date as text),h.publication_id,p.revision,p.production_version "
            "from {schema}.publication_heads h join {schema}.publications p using(publication_id) "
            "where p.status='SUCCESS' and (p.production_version not like 'm4-%%' or exists "
            "(select 1 from {schema}.publication_analysis_snapshots a where a.publication_id=p.publication_id and a.domain='LOCAL_RECONSTRUCTED')) "
            "order by h.trade_date desc"
        ).format(schema=sql.Identifier(self.schema))
        with self.connection.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
        items: list[dict[str, Any]] = []
        for trade_date, publication_id, revision, production_version in rows:
            item: dict[str, Any] = {"trade_date": str(trade_date), "publication_id": str(publication_id)}
            if include_analysis:
                item.update({"revision": revision, "production_version": production_version, "analysis_capabilities": self.analysis_capabilities(str(publication_id))})
            items.append(item)
        result: dict[str, Any] = {"items": items, "latest_publication_id": items[0]["publication_id"] if items else None}
        if include_analysis:
            result["api_contract"] = "workbench-api-v2.1"
        return result

    @staticmethod
    def _json_value(value: Any, default: Any) -> Any:
        if isinstance(value, (dict, list)):
            return value
        if value in (None, ""):
            return default
        try:
            parsed = json.loads(str(value))
        except (TypeError, ValueError, json.JSONDecodeError):
            return default
        return parsed

    @staticmethod
    def _timestamp_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).replace("+00:00", "")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text

    def _analysis_bindings(self, publication_id: str) -> dict[str, dict[str, Any]]:
        query = sql.SQL(
            "select b.domain,b.snapshot_id,cast(s.cutoff_date as text),cast(s.query_start as text),s.manifest_hash,"
            "s.universe_contract,s.config_hash,s.created_at "
            "from {schema}.publication_analysis_snapshots b join {schema}.analysis_snapshots s using(snapshot_id) "
            "left join {schema}.analysis_snapshot_audit_status a on a.snapshot_id=s.snapshot_id "
            "where b.publication_id=%s and s.status='SUCCESS' and coalesce(a.audit_status,'ACTIVE') not in ('BLOCKED','PENDING_REVIEW') "
            "order by case b.domain when 'LOCAL_OBSERVED' then 0 else 1 end"
        ).format(schema=sql.Identifier(self.schema))
        with self.connection.cursor() as cur:  # type: ignore[union-attr]
            cur.execute(query, (publication_id,))
            rows = cur.fetchall()
        return {str(row[0]): {"domain": str(row[0]), "snapshot_id": str(row[1]), "analysis_snapshot_id": str(row[1]), "cutoff_date": str(row[2]), "query_start": str(row[3]), "manifest_hash": row[4], "universe_contract": row[5], "config_hash": row[6], "created_at": self._timestamp_text(row[7])} for row in rows}

    def _analysis_quality(self, snapshot_id: str) -> dict[str, Any]:
        query = sql.SQL(
            "select e.domain,cast(e.trade_date as text),s.slice_id,cast(s.trade_date as text),s.contract_id,s.input_hash,s.dependency_hash,"
            "s.logical_hash,s.row_count,s.basis_json,b.universe_basis,b.membership_snapshot_id,b.price_basis,"
            "cast(b.adjustment_as_of as text),b.source_observed_at,b.coverage,b.capabilities_json "
            "from {schema}.analysis_snapshot_entries e join {schema}.analysis_slices s on s.slice_id=e.slice_id "
            "left join {schema}.analysis_daily_basis b on b.slice_id=e.slice_id "
            "where e.snapshot_id=%s order by e.domain,e.trade_date,s.slice_id"
        ).format(schema=sql.Identifier(self.schema))
        with self.connection.cursor() as cur:  # type: ignore[union-attr]
            cur.execute(query, (snapshot_id,))
            rows = cur.fetchall()
        all_dates = sorted({str(row[1]) for row in rows})
        coverage: dict[str, dict[str, Any]] = {}
        for row in rows:
            (domain, trade_date, slice_id, slice_trade_date, contract_id, input_hash, dependency_hash,
             logical_hash, row_count, basis_json, universe_basis, membership_snapshot_id, price_basis,
             adjustment_as_of, source_observed_at, covered, capabilities_json) = row
            domain = str(domain); trade_date = str(trade_date); slice_trade_date = str(slice_trade_date)
            item = coverage.setdefault(domain, {"available_from": trade_date, "available_to": trade_date, "date_count": 0, "slice_count": 0, "row_count": 0, "contract_ids": set(), "slice_ids": [], "input_hashes": set(), "dependency_hashes": set(), "logical_hashes": set(), "missing_dates": [], "coverage_values": [], "basis_metadata_complete": True, "basis": None, "latest_slice": None, "slice_trade_date_mismatches": []})
            item["available_from"] = min(item["available_from"], trade_date); item["available_to"] = max(item["available_to"], trade_date); item["date_count"] += 1; item["row_count"] += int(row_count or 0); item["contract_ids"].add(contract_id); item["input_hashes"].add(input_hash); item["dependency_hashes"].add(dependency_hash); item["logical_hashes"].add(logical_hash)
            if slice_id not in item["slice_ids"]: item["slice_ids"].append(slice_id)
            if slice_trade_date != trade_date: item["slice_trade_date_mismatches"].append({"entry_trade_date": trade_date, "slice_trade_date": slice_trade_date, "slice_id": slice_id})
            if covered is not None: item["coverage_values"].append(float(covered))
            else: item["basis_metadata_complete"] = False
            if item["latest_slice"] is None or trade_date >= item["latest_slice"]["trade_date"]:
                item["latest_slice"] = {"slice_id": str(slice_id), "trade_date": trade_date, "slice_trade_date": slice_trade_date, "contract_id": contract_id, "input_hash": input_hash, "dependency_hash": dependency_hash, "logical_hash": logical_hash, "row_count": int(row_count or 0), "basis_json": self._json_value(basis_json, {}), "universe_basis": universe_basis, "membership_snapshot_id": membership_snapshot_id, "price_basis": price_basis, "adjustment_as_of": str(adjustment_as_of) if adjustment_as_of is not None else None, "source_observed_at": self._timestamp_text(source_observed_at), "coverage": float(covered) if covered is not None else None, "capabilities": self._json_value(capabilities_json, {})}
        for domain, item in coverage.items():
            item["missing_dates"] = [day for day in all_dates if item["available_from"] <= day <= item["available_to"] and day not in {str(row[1]) for row in rows if str(row[0]) == domain}]
            item["coverage"] = round(sum(item["coverage_values"]) / len(item["coverage_values"]), 8) if item["coverage_values"] else None
            item["contract_ids"] = sorted(item["contract_ids"]); item["input_hashes"] = sorted(item["input_hashes"]); item["dependency_hashes"] = sorted(item["dependency_hashes"]); item["logical_hashes"] = sorted(item["logical_hashes"]); item["slice_ids"] = sorted(set(item["slice_ids"]))[-10:]; item["slice_count"] = len(set(item["slice_ids"])); item.pop("coverage_values", None)
            latest = item["latest_slice"]
            latest_capabilities = latest.get("capabilities", {}) if latest else {}
            membership_metadata_ok = domain not in ("mainline", "sector_cycle", "member_state") or bool(latest and latest.get("membership_snapshot_id"))
            semantic_metadata_ok = domain != "mainline" or bool(latest and (latest.get("basis_json", {}).get("semantic_version") or latest_capabilities.get("semantic_version")))
            item["basis_metadata_complete"] = bool(item["basis_metadata_complete"] and latest and latest.get("coverage") is not None and membership_metadata_ok and semantic_metadata_ok and not item["slice_trade_date_mismatches"])
        codes: list[str] = []
        if any(item["missing_dates"] for item in coverage.values()): codes.append("SNAPSHOT_DOMAIN_DATE_GAPS")
        if any(item.get("slice_trade_date_mismatches") for item in coverage.values()): codes.append("SNAPSHOT_SLICE_TRADE_DATE_MISMATCH")
        if any(not item["basis_metadata_complete"] for item in coverage.values()): codes.append("BASIS_METADATA_INCOMPLETE")
        return {"status": "AVAILABLE" if coverage and not codes else ("PARTIAL" if coverage else "UNAVAILABLE"), "codes": codes, "field_coverage": coverage}

    def analysis_capabilities(self, publication_id: str) -> dict[str, Any]:
        if self.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        with self.connection.cursor() as cur:
            counts = {}
            for table in ("stock_daily", "sector_daily", "queue_memberships"):
                cur.execute(sql.SQL("select count(*) from {}.{} where publication_id=%s").format(sql.Identifier(self.schema), sql.Identifier(table)), (publication_id,))
                counts[table] = int(cur.fetchone()[0])
        bindings = self._analysis_bindings(publication_id)
        preferred = bindings.get("LOCAL_OBSERVED") or bindings.get("LOCAL_RECONSTRUCTED")
        quality = self._analysis_quality(preferred["snapshot_id"]) if preferred else {"field_coverage": {}, "status": "PARTIAL", "codes": ["HISTORY_ANALYSIS_NOT_BUILT"]}
        domain_capabilities = {domain: ("AVAILABLE" if value.get("date_count", 0) > 0 else "UNAVAILABLE") for domain, value in quality.get("field_coverage", {}).items()}
        return {"overview": "AVAILABLE" if counts["stock_daily"] else "UNAVAILABLE", "universe": "AVAILABLE" if counts["stock_daily"] else "UNAVAILABLE", "sector": "AVAILABLE" if counts["sector_daily"] else "UNAVAILABLE", "structure": "AVAILABLE" if counts["queue_memberships"] else "UNAVAILABLE", "history_analysis": "AVAILABLE" if bindings else "NOT_BUILT", "analysis_domains": domain_capabilities, "field_coverage": quality.get("field_coverage", {})}

    def sector_metadata(self, publication_id: str) -> list[dict[str, str]]:
        """Return the stable sector identity projection for one publication."""
        if self.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        query = sql.SQL("select sector_id,sector_name,sector_type from {}.sector_daily where publication_id=%s order by sector_id").format(sql.Identifier(self.schema))
        with self.connection.cursor() as cur:
            cur.execute(query, (publication_id,))
            return [{"sector_id": str(sector_id), "sector_name": str(sector_name or sector_id), "sector_type": str(sector_type or "LOCAL")} for sector_id, sector_name, sector_type in cur.fetchall()]

    def research_sector_state_rows(self, run_id: str, *, track: str = "ALL", query_text: str = "") -> list[tuple[Any, ...]]:
        """Read raw sector-state rows with the same filter/order as the API."""
        if self.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        clauses = ["run_id=%s"]; params: list[Any] = [run_id]
        if track == "CURRENT": clauses.append("current_eligible IS TRUE")
        elif track == "POTENTIAL": clauses.append("potential_eligible IS TRUE")
        elif track == "WEAK": clauses.append("coalesce(current_eligible,FALSE) IS FALSE AND coalesce(potential_eligible,FALSE) IS FALSE")
        if query_text:
            clauses.append("sector_id ILIKE %s"); params.append(f"%{query_text}%")
        columns = "run_id,sector_id,current_eligible,potential_eligible,potential_branch,potential_branches,current_rank,potential_rank,m1,b1,rel1,p1,q5,q20,dq5_3,b_delta3,ma20_width,ma20_delta3,early_width,amount_a,top1_positive_share,member_count,quote_valid_count,feature_valid_count,early_count,positive_count,quote_coverage,feature_coverage,risk_coverage,quality,reason_codes,evidence,input_members_hash,rank_universe_hash"
        sql_text = sql.SQL("select {} from {}.research_sector_states where {} order by coalesce(current_rank,potential_rank,999999),sector_id").format(sql.SQL(columns), sql.Identifier(self.schema), sql.SQL(" and ".join(clauses)))
        with self.connection.cursor() as cur:
            cur.execute(sql_text, params)
            return cur.fetchall()

    def research_sector_member_role_rows(self, run_id: str) -> list[tuple[Any, ...]]:
        """Read all role rows used by sector detail/member projections."""
        if self.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        query = sql.SQL("select run_id,sector_id,security_id,role,role_rank,today_rank,role_reason_codes,evidence from {}.research_sector_member_roles where run_id=%s order by sector_id,role_rank,security_id,role").format(sql.Identifier(self.schema))
        with self.connection.cursor() as cur:
            cur.execute(query, (run_id,))
            return cur.fetchall()

    def membership_entry_rows(self, snapshot_id: str) -> list[tuple[Any, ...]]:
        """Read immutable membership entries for one snapshot."""
        if self.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        query = sql.SQL("select membership_snapshot_id,sector_id,security_id,payload_json from {}.membership_entries where membership_snapshot_id=%s order by sector_id,security_id").format(sql.Identifier(self.schema))
        with self.connection.cursor() as cur:
            cur.execute(query, (snapshot_id,))
            return cur.fetchall()

    def relation_edges_for_publication(self, publication_id: str) -> list[tuple[Any, ...]]:
        """Resolve the immutable relation edges bound to a publication."""
        if self.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        query = sql.SQL(
            "select b.publication_id,b.source_scope,b.revision_no,e.sector_id,e.security_id,e.source_kind,e.from_revision,e.to_revision "
            "from {schema}.relation_publication_bindings b join {schema}.relation_edge_intervals e on e.source_scope=b.source_scope "
            "and e.from_revision<=b.revision_no and (e.to_revision is null or b.revision_no<e.to_revision) "
            "where b.publication_id=%s order by b.source_scope,e.sector_id,e.security_id,e.source_kind"
        ).format(schema=sql.Identifier(self.schema))
        with self.connection.cursor() as cur:
            cur.execute(query, (publication_id,))
            return cur.fetchall()

    def publication_source_identity(self, publication_id: str) -> tuple[str, int | None, str | None]:
        """Return the source identity needed to freeze a publication."""
        if self.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        query = sql.SQL(
            "select cast(trade_date as text),source_revision_id,source_identity_sha256 "
            "from {schema}.publications where publication_id=%s and status='SUCCESS'"
        ).format(schema=sql.Identifier(self.schema))
        with self.connection.cursor() as cur:
            cur.execute(query, (publication_id,))
            row = cur.fetchone()
        if not row:
            raise KeyError("PUBLICATION_NOT_FOUND")
        return str(row[0]), (int(row[1]) if row[1] is not None else None), (str(row[2]) if row[2] is not None else None)

    def source_bundles(self) -> list[tuple[str, Any]]:
        """Return source-bundle receipts from the relational catalog."""
        if self.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        query = sql.SQL("select source_bundle_id,payload_json from {schema}.source_bundles").format(schema=sql.Identifier(self.schema))
        with self.connection.cursor() as cur:
            cur.execute(query)
            return list(cur.fetchall())
