"""PostgreSQL-only persistence and paged reads for the R7 Forward domain."""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import statistics

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from workbench_analysis.forward_r7 import canonical_bytes, make_observation_id, sha256
from .v4_native import workspace_schema


SETTLEMENT_STATUS_STATES = (
    "SETTLED", "NO_QUOTE", "SUSPENDED", "SOURCE_GAP",
    "DUE_SOURCE_NOT_ACCEPTED", "PENDING_FUTURE_SESSION",
)


def summarize_settlement_schedule(trade_date, lane, horizon, scheduled):
    """Only validated SETTLED returns enter the return denominator."""
    settled=[item.get("settlement",{}).get("nominal_return") for item in scheduled
             if item.get("schedule_status")=="SETTLED"
             and item.get("settlement",{}).get("status")=="SETTLED"
             and item.get("settlement",{}).get("nominal_return") is not None]
    return dict(trade_date=trade_date,lane=lane,horizon_sessions=horizon,
        outcomes={state:sum(item.get("schedule_status")==state for item in scheduled)
                  for state in SETTLEMENT_STATUS_STATES},
        sample_count=len(scheduled),settled_count=len(settled),return_denominator=len(settled),
        mean_return=statistics.mean(settled) if settled else None,
        median_return=statistics.median(settled) if settled else None,
        source_observation_ids=sorted({item.get("observation_id") for item in scheduled}),
        price_basis="NOMINAL_UNADJUSTED_CLOSE")


def _configured_forward_dsn(root: Path):
    """Use the project's existing PostgreSQL setting without duplicating it."""
    for key in ("V4_NATIVE_PG_DSN", "WORKBENCH_PG_DSN"):
        if os.environ.get(key):
            return os.environ[key]
    project_root = Path(__file__).resolve().parents[2]
    for env_path in (root / "config/.env", project_root / "config/.env"):
        if not env_path.is_file():
            continue
        for raw in env_path.read_text(encoding="utf-8-sig").splitlines():
            key, sep, value = raw.partition("=")
            if sep and key.strip() in ("V4_NATIVE_PG_DSN", "WORKBENCH_PG_DSN"):
                value = value.strip().strip('"').strip("'")
                if value:
                    return value
    raise RuntimeError("EXISTING_WORKBENCH_POSTGRES_DSN_REQUIRED")


class ForwardR7Store:
    contract_id = "V4_FORWARD_PG_READ_WRITE_R7_R1"

    def __init__(self, root: str | Path, *, dsn: str | None = None):
        self.root = Path(root).resolve()
        self.dsn = dsn or _configured_forward_dsn(self.root)
        self.schema = self._resolve_existing_schema()
        self._generic_facts = True

    def _resolve_existing_schema(self):
        """Bind to the existing Forward facts namespace for this accepted Head.

        R7 deliberately reuses the current ``forward_facts`` table. It must not
        create a schema or infer an empty target when the expected namespace is
        absent. The accepted core fact date uniquely binds the live workspace.
        """
        target_date = None
        head_path = self.root / "data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json"
        if head_path.is_file():
            try:
                target_date = json.loads(head_path.read_bytes()).get("accepted_trade_date")
            except (OSError, ValueError, TypeError):
                target_date = None
        with psycopg.connect(self.dsn, connect_timeout=5) as pg:
            candidates = pg.execute("""SELECT s.schema_name
                FROM information_schema.schemata s
                JOIN information_schema.tables t ON t.table_schema=s.schema_name
                WHERE s.schema_name LIKE 'v4_forward_%' AND t.table_name='forward_facts'
                ORDER BY s.schema_name""").fetchall()
            matches = []
            for (schema,) in candidates:
                if target_date:
                    exists = pg.execute(sql.SQL("""SELECT 1 FROM {}.forward_facts
                        WHERE kind='core' AND fact_key LIKE %s LIMIT 1""").format(
                            sql.Identifier(schema)), (f"%_{target_date}_core",)).fetchone()
                    if exists:
                        matches.append(schema)
            if len(matches) == 1:
                return matches[0]
            expected = workspace_schema(self.root, "forward")
            if any(row[0] == expected for row in candidates):
                return expected
            if not target_date and len(candidates) == 1:
                return candidates[0][0]
        raise RuntimeError("EXISTING_FORWARD_FACTS_NAMESPACE_NOT_UNIQUELY_BOUND")

    def _connect(self):
        return psycopg.connect(self.dsn, connect_timeout=5)

    @staticmethod
    def _stable_hash(value):
        """Hash immutable research facts while preserving first-write audit clocks."""
        def strip_clock(item):
            if isinstance(item, dict):
                return {k: strip_clock(v) for k, v in item.items()
                        if k not in {"captured_at", "observed_at", "frozen_at", "settlement_at"}}
            if isinstance(item, list):
                return [strip_clock(v) for v in item]
            return item
        return sha256(strip_clock(value))

    def record_failure(self, *, stage: str, trade_date: str | None, current_head_date: str | None,
                       run_id: str, attempt: int, error_code: str, payload: dict | None = None):
        failure = dict(stage=stage, trade_date=trade_date, current_head_date=current_head_date,
                       run_id=run_id, attempt=attempt, error_code=error_code,
                       payload=payload or {}, recorded_at=datetime.now(timezone.utc).isoformat())
        with self._connect() as pg:
            digest = self._stable_hash(failure)
            self._append_fact(pg, "r7_pipeline_run", run_id, dict(status="FAILED", **failure), digest)
        return dict(status="FAILED_RECORDED", run_id=run_id, attempt=attempt, error_code=error_code)


    def verify_existing_storage(self):
        with self._connect() as pg:
            present = pg.execute("""SELECT 1 FROM information_schema.tables
                WHERE table_schema=%s AND table_name='forward_facts' AND table_type='BASE TABLE'""",
                (self.schema,)).fetchone()
            if not present:
                raise RuntimeError("EXISTING_FORWARD_FACTS_TABLE_REQUIRED_NO_MIGRATION")
        return dict(status="REUSED_EXISTING_PG_FACTS", schema=self.schema, table="forward_facts")

    def _append_fact(self, pg, kind: str, fact_key: str, payload: dict,
                     source_sha256: str | None = None):
        """Append one immutable R7 fact using the existing table's contract."""
        raw = canonical_bytes(payload).decode("utf-8")
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        pg.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",
                   ("v4-forward-facts:" + self.schema,))
        pg.execute(sql.SQL("""INSERT INTO {}.forward_facts
            (kind,fact_key,payload,payload_sha256,source_sha256)
            VALUES (%s,%s,%s,%s,%s) ON CONFLICT(kind,fact_key) DO NOTHING""").format(
                sql.Identifier(self.schema)), (kind, fact_key, raw, digest, source_sha256))
        saved = pg.execute(sql.SQL("""SELECT payload_sha256 FROM {}.forward_facts
            WHERE kind=%s AND fact_key=%s""").format(sql.Identifier(self.schema)),
            (kind, fact_key)).fetchone()
        if not saved or saved[0].strip() != digest:
            raise ValueError("FORWARD_R7_IMMUTABLE_FACT_CONFLICT")
        return digest

    def _read_facts(self, kind: str):
        with self._connect() as pg:
            pg.execute("SET TRANSACTION READ ONLY")
            rows = pg.execute(sql.SQL("""SELECT fact_key,payload FROM {}.forward_facts
                WHERE kind=%s ORDER BY ordinal""").format(sql.Identifier(self.schema)), (kind,)).fetchall()
        return [(key, json.loads(payload)) for key, payload in rows]

    def _daily_facts(self):
        return [value for _, value in self._read_facts("r7_daily_universe")]

    def _settlement_facts(self):
        return [value for _, value in self._read_facts("r7_settlement_schedule")]

    @staticmethod
    def _insert_immutable(pg, table, columns, values, identity_where, identity_values,
                          digest, *, revision=1):
        placeholders = sql.SQL(",").join(sql.Placeholder() for _ in columns)
        statement = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT DO NOTHING").format(
            sql.Identifier(table), sql.SQL(",").join(map(sql.Identifier, columns)), placeholders)
        pg.execute(statement, values)
        existing = pg.execute(sql.SQL("SELECT content_sha256 FROM {} WHERE {} FOR SHARE").format(
            sql.Identifier(table), identity_where), identity_values).fetchone()
        if existing is None:
            raise RuntimeError("FORWARD_R7_IMMUTABLE_INSERT_READBACK_MISSING")
        if existing[0].strip() != digest:
            raise ValueError("FORWARD_R7_IMMUTABLE_CONTENT_CHANGED_NEW_REVISION_REQUIRED")

    def register_definitions(self, definitions: dict, definitions_sha256: str):
        with self._connect() as pg:
            for rule in definitions["rules"]:
                row = dict(contract_id=definitions["contract_id"], version=definitions["version"],
                           effective_from=definitions["effective_from"], scope=definitions["scope"], rule=rule,
                           definitions_sha256=definitions_sha256)
                key = f"{rule['rule_id']}:{rule['rule_version']}"
                self._append_fact(pg, "r7_signal_definition", key, row, definitions_sha256)
        return dict(status="READY", rule_count=len(definitions["rules"]), definition_sha256=definitions_sha256)


    def publish_day(self, *, trade_date: str, rows: list[dict], lane: str,
                    run_id: str, revision: int = 1, first_available_at: str | None = None,
                    source_run: dict | None = None, settlement_rows: list[dict] | None = None):
        """Atomically persist the complete denominator and advance its read pointer."""
        if lane not in ("LIVE_OOS", "RETROSPECTIVE_RESEARCH", "LATE_OBSERVED_NOT_PIT"):
            raise ValueError("FORWARD_R7_EVIDENCE_LANE_INVALID")
        if not rows:
            raise ValueError("EMPTY_UNIVERSE_CANNOT_BE_PUBLISHED_AS_A_COMPLETED_READ")
        return self._publish_day_facts(trade_date=trade_date, rows=rows, lane=lane,
            run_id=run_id, revision=revision, first_available_at=first_available_at,
            source_run=source_run, settlement_rows=settlement_rows or [])

    def _publish_day_facts(self, *, trade_date, rows, lane, run_id, revision,
                           first_available_at, source_run, settlement_rows):
        existing = [item for item in self._daily_facts() if item.get("trade_date") == trade_date]
        body_rows = [{**row, "evidence_lane": lane, "revision": revision} for row in rows]
        digest = self._stable_hash(dict(trade_date=trade_date, lane=lane, rows=body_rows))
        already_published = False
        if existing:
            old = existing[0]
            if old.get("stable_sha256") != digest:
                raise ValueError("FORWARD_R7_IMMUTABLE_REVISION_CONFLICT")
            already_published = True
        summary_groups = {}
        for row in rows:
            key = (row["rule_id"], row["rule_version"], row["entity_type"])
            group = summary_groups.setdefault(key, dict(entity_type=key[2], universe_count=0,
                match_count=0, no_match_count=0, unknown_count=0))
            group["universe_count"] += 1
            group["match_count" if row["status"] == "MATCH" else
                  "no_match_count" if row["status"] == "NO_MATCH" else "unknown_count"] += 1
        bundle = dict(trade_date=trade_date, lane=lane, revision=revision, rows=body_rows,
            first_available_at=first_available_at,
            source_run=source_run or {}, groups={"/".join(k): v for k, v in summary_groups.items()},
            stable_sha256=digest, captured_at=datetime.now(timezone.utc).isoformat())
        with self._connect() as pg:
            if not already_published:
                self._append_fact(pg, "r7_daily_universe", trade_date, bundle,
                                   self._stable_hash((source_run or {}).get("source_hashes", {})))
            settlement_digest = self._stable_hash(settlement_rows)
            prior_settlement = [item for item in self._settlement_facts()
                                if item.get("trade_date") == trade_date]
            if not any(item.get("stable_sha256") == settlement_digest for item in prior_settlement):
                self._append_fact(pg, "r7_settlement_schedule", f"{trade_date}:{settlement_digest}",
                    dict(trade_date=trade_date, lane=lane, revision=revision,
                         items=settlement_rows, stable_sha256=settlement_digest, source_run=source_run or {}),
                    self._stable_hash((source_run or {}).get("source_hashes", {})))
            self._append_fact(pg, "r7_aggregate_stats", trade_date,
                dict(trade_date=trade_date, lane=lane, groups=bundle["groups"],
                     stable_sha256=digest), digest)
            for horizon in (1, 3, 5):
                scheduled = [item for item in settlement_rows if item.get("horizon_sessions") == horizon]
                summary = summarize_settlement_schedule(trade_date,lane,horizon,scheduled)
                summary_digest = self._stable_hash(summary)
                self._append_fact(pg, "r7_settlement_aggregate",
                    f"{trade_date}:{horizon}:{summary_digest}", summary, summary_digest)
            self._append_fact(pg, "r7_pipeline_run", run_id,
                dict(run_id=run_id, stage="PUBLISH", trade_date=trade_date, status="PASS",
                     counts={"universe_rows": len(rows), "lane": lane},
                     source_run=source_run or {}, recorded_at=bundle["captured_at"]), digest)
            prior = self._latest_publish_index(pg)
            if not prior or prior.get("trade_date", "") < trade_date:
                generation = int(prior.get("generation", 0)) + 1 if prior else 1
                self._append_fact(pg, "r7_publish_index", f"{generation:020d}",
                    dict(index_name="daily_universe", generation=generation, trade_date=trade_date,
                         payload_sha256=digest, source_run_id=run_id,
                         published_at=datetime.now(timezone.utc).isoformat()), digest)
                status = "PUBLISHED"
            elif prior.get("trade_date") == trade_date:
                if prior.get("payload_sha256") != digest:
                    raise ValueError("FORWARD_R7_PUBLISH_POINTER_CONFLICT")
                generation, status = prior["generation"], "PUBLISHED_IDEMPOTENT"
            else:
                generation, status = prior["generation"], "PUBLISHED_HISTORICAL"
        if already_published and status == "PUBLISHED_IDEMPOTENT":
            status = "PUBLISHED_IDEMPOTENT"
        return dict(status=status, trade_date=trade_date, lane=lane, rows=len(rows),
                    groups=bundle["groups"], payload_sha256=digest, generation=generation)

    def _latest_publish_index(self, pg=None):
        own = pg is None
        conn = pg or self._connect()
        try:
            row = conn.execute(sql.SQL("""SELECT payload FROM {}.forward_facts
                WHERE kind='r7_publish_index' ORDER BY ordinal DESC LIMIT 1""").format(
                    sql.Identifier(self.schema))).fetchone()
            return json.loads(row[0]) if row else {}
        finally:
            if own:
                conn.close()


    def read_universe(self, *, lane: str | None = None, trade_date: str | None = None,
                      rule: str | None = None, status: str | None = None,
                      limit: int = 30, offset: int = 0):
        if not 1 <= limit <= 200 or not 0 <= offset <= 1_000_000:
            raise ValueError("INVALID_QUERY_BOUND")
        items = [row for bundle in self._daily_facts() for row in bundle.get("rows", [])
                 if (not lane or row.get("evidence_lane") == lane)
                 and (not trade_date or row.get("T0") == trade_date)
                 and (not rule or row.get("rule_id") == rule)
                 and (not status or row.get("status") == status)]
        items.sort(key=lambda row: (row.get("T0", ""), row.get("rule_id", ""),
                                    row.get("entity_id", "")), reverse=True)
        total = len(items)
        page = items[offset:offset + limit]
        return dict(status="READY" if total else "EMPTY_VALID", items=page,
                    total=total, offset=offset, limit=limit, has_next=offset + len(page) < total)


    def read_counts(self):
        bundles = self._daily_facts()
        rows = [row for bundle in bundles for row in bundle.get("rows", [])]
        grouped = {}
        for row in rows:
            lane = row.get("evidence_lane")
            info = grouped.setdefault(lane, dict(count=0, match=0, no_match=0, unknown=0, latest_t0=""))
            info["count"] += 1
            info["match"] += row.get("status") == "MATCH"
            info["no_match"] += row.get("status") == "NO_MATCH"
            info["unknown"] += row.get("status") == "UNKNOWN"
            info["latest_t0"] = max(info["latest_t0"], row.get("T0", ""))
        pointer = self._latest_publish_index()
        if not pointer:
            return dict(status="DATA_MISSING", historical=None, live=None, published_generation=None)
        return dict(status="READY", historical=grouped.get("RETROSPECTIVE_RESEARCH"),
            live=grouped.get("LIVE_OOS"), late=grouped.get("LATE_OBSERVED_NOT_PIT"),
            published_generation=pointer.get("generation"), published_t0=pointer.get("trade_date"),
            payload_sha256=pointer.get("payload_sha256"), source_run_id=pointer.get("source_run_id"),
            published_at=pointer.get("published_at"))


    def read_audit_dates(self, *, limit: int = 100, offset: int = 0):
        if not 1 <= limit <= 200 or not 0 <= offset <= 1_000_000:
            raise ValueError("INVALID_QUERY_BOUND")
        by_date = {}
        for bundle in self._daily_facts():
            day = bundle.get("trade_date")
            groups = by_date.setdefault(day, {})
            for row in bundle.get("rows", []):
                key = (row.get("rule_id"), row.get("rule_version"), row.get("entity_type"))
                group = groups.setdefault(key, dict(rule_id=key[0], rule_version=key[1],
                    entity_type=key[2], universe_count=0, match_count=0, no_match_count=0,
                    unknown_count=0, live_count=0, historical_count=0))
                group["universe_count"] += 1
                group["match_count"] += row.get("status") == "MATCH"
                group["no_match_count"] += row.get("status") == "NO_MATCH"
                group["unknown_count"] += row.get("status") == "UNKNOWN"
                group["live_count"] += row.get("evidence_lane") == "LIVE_OOS"
                group["historical_count"] += row.get("evidence_lane") == "RETROSPECTIVE_RESEARCH"
        dates = sorted(by_date, reverse=True)
        page = dates[offset:offset + limit]
        return dict(status="READY" if dates else "EMPTY_VALID",
            items=[dict(trade_date=day, groups=sorted(by_date[day].values(), key=lambda x:x["rule_id"])) for day in page],
            total=len(dates), limit=limit, offset=offset, has_next=offset + len(page) < len(dates))


    def read_settlement(self, *, lane: str | None = None, trade_date: str | None = None,
                        horizon: int | None = None, status: str | None = None,
                        limit: int = 30, offset: int = 0):
        if not 1 <= limit <= 200 or not 0 <= offset <= 1_000_000:
            raise ValueError("INVALID_QUERY_BOUND")
        observations = {make_observation_id(row): row for bundle in self._daily_facts()
                        for row in bundle.get("rows", [])}
        items, counts = [], {}
        latest_schedule = {}
        for bundle in self._settlement_facts():
            for schedule in bundle.get("items", []):
                latest_schedule[(schedule.get("observation_id"), schedule.get("horizon_sessions"))] = (bundle, schedule)
        for bundle, schedule in latest_schedule.values():
            row = observations.get(schedule.get("observation_id"))
            if not row:
                continue
            state = schedule.get("schedule_status", "PENDING")
            h = schedule.get("horizon_sessions")
            lane_value, day = row.get("evidence_lane"), row.get("T0")
            counts[(lane_value, h, state)] = counts.get((lane_value, h, state), 0) + 1
            if (lane and lane != lane_value) or (trade_date and trade_date != day) or (horizon and horizon != h) or (status and status != state):
                continue
            outcome = schedule.get("settlement", {})
            items.append(dict(observation_id=schedule.get("observation_id"), revision=row.get("revision",1),
                trade_date=day, rule_id=row.get("rule_id"), rule_version=row.get("rule_version"),
                entity_type=row.get("entity_type"), entity_id=row.get("entity_id"), lane=lane_value,
                horizon_sessions=h, due_date=schedule.get("due_date"), status=state,
                reason=schedule.get("reason"), t0_close=outcome.get("T0_close"),
                due_close=outcome.get("due_close"), nominal_return=outcome.get("nominal_return"),
                price_basis=outcome.get("price_basis"), settlement_at=outcome.get("settlement_at"),
                payload=outcome or None))
        items.sort(key=lambda x:(x.get("trade_date", ""), x.get("due_date") or "",
                                 x.get("horizon_sessions") or 0, x.get("entity_id", "")), reverse=True)
        total = len(items); page = items[offset:offset + limit]
        return dict(status="READY" if total else "EMPTY_VALID", total=total, offset=offset,
            limit=limit, has_next=offset+len(page)<total, items=page,
            counts=[dict(lane=k[0],horizon_sessions=k[1],status=k[2],count=v) for k,v in sorted(counts.items())])


    def publish_fep_projection(self, projection: dict):
        projection_id = self._stable_hash(projection)
        digest = self._stable_hash(projection)
        source = projection.get("source_hashes", {})
        with self._connect() as pg:
            self._append_fact(pg, "r7_fep_projection", projection_id,
                              dict(projection_id=projection_id, payload=projection),
                              self._stable_hash(source))
        return dict(status="PUBLISHED",projection_id=projection_id,content_sha256=digest)


    def read_fep_projections(self):
        rows = [item.get("payload", {}) for _, item in self._read_facts("r7_fep_projection")]
        rows.sort(key=lambda row:(row.get("asof") or "", row.get("model_version") or ""), reverse=True)
        return dict(status="READY" if rows else "EMPTY_VALID",items=rows,total=len(rows))


    def read_matured_count(self):
        latest = {}
        for bundle in self._settlement_facts():
            for schedule in bundle.get("items", []):
                latest[(schedule.get("observation_id"), schedule.get("horizon_sessions"))] = schedule
        return sum(schedule.get("schedule_status") == "SETTLED"
                   and schedule.get("settlement", {}).get("status") == "SETTLED"
                   for schedule in latest.values())
