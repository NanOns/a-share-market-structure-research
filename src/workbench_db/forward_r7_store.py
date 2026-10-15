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

from workbench_analysis.forward_r7 import (canonical_bytes, legacy_observation_id,
    make_observation_id, sha256, compute_nominal_settlement)
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

    def _read_day_facts(self, kind: str, trade_date: str, lane: str | None = None):
        """Use append-only fact-key prefixes to bound date-scoped reads in PG."""
        def prefix_clause(prefix):
            if not prefix.endswith(":"):
                raise ValueError("FORWARD_FACT_KEY_PREFIX_INVALID")
            return "(fact_key >= %s AND fact_key < %s)", [prefix, prefix[:-1] + ";"]
        with self._connect() as pg:
            pg.execute("SET TRANSACTION READ ONLY")
            if kind == "r7_daily_universe":
                if lane:
                    clause, params = prefix_clause(f"v2:{trade_date}:{lane}:")
                    clauses = [clause]
                    if lane == "RETROSPECTIVE_RESEARCH":
                        clauses.append("fact_key=%s"); params.append(trade_date)
                else:
                    clause, params = prefix_clause(f"v2:{trade_date}:")
                    clauses = ["fact_key=%s", clause]
                    params = [trade_date, *params]
                query = sql.SQL("SELECT fact_key,payload FROM {}.forward_facts WHERE kind=%s AND ({}) ORDER BY ordinal").format(
                    sql.Identifier(self.schema), sql.SQL(" OR ").join(sql.SQL(x) for x in clauses))
                rows = pg.execute(query, [kind, *params]).fetchall()
            else:
                clause, prefix_params = prefix_clause(f"v2:{trade_date}:{lane}:" if lane else f"v2:{trade_date}:")
                legacy_clause, legacy_params = prefix_clause(f"{trade_date}:")
                advance_clause, advance_params = prefix_clause("v2:advance:")
                clauses = [f"({clause} OR {legacy_clause} OR ({advance_clause} AND payload::jsonb->>'trade_date'=%s))"]
                params = [*prefix_params, *legacy_params, *advance_params, trade_date]
                if lane:
                    clauses.append("(payload::jsonb->>'lane'=%s OR (payload::jsonb->>'identity_contract' IS NULL AND %s='RETROSPECTIVE_RESEARCH'))")
                    params.extend([lane, lane])
                query = sql.SQL("SELECT fact_key,payload FROM {}.forward_facts WHERE kind=%s AND {} ORDER BY ordinal").format(
                    sql.Identifier(self.schema), sql.SQL(" AND ").join(sql.SQL(x) for x in clauses))
                rows = pg.execute(query, [kind, *params]).fetchall()
        return [(key, json.loads(payload)) for key, payload in rows]

    def _daily_facts(self, trade_date: str | None = None, lane: str | None = None):
        source = (self._read_facts("r7_daily_universe") if trade_date is None
                  else self._read_day_facts("r7_daily_universe", trade_date, lane))
        bundles = []
        for key, value in source:
            item = dict(value)
            if not item.get("identity_contract"):
                # R7 had one date-wide identity. Preserve every old row as Lane H.
                item["identity_contract"] = "V4_FORWARD_OBSERVATION_ID_R1_LEGACY_LANE_H"
                item["lane"] = "RETROSPECTIVE_RESEARCH"
                item["revision"] = 1
                item["capture_revision"] = 1
                for row in item.get("rows", []):
                    row["evidence_lane"] = "RETROSPECTIVE_RESEARCH"
                    row["evidence_class"] = "RETROSPECTIVE_RESEARCH"
                    row["capture_revision"] = 1
                    row.setdefault("revision", 1)
                    row.setdefault("legacy_observation_id", legacy_observation_id(row))
            bundles.append(item)
        return bundles

    def _settlement_facts(self, trade_date: str | None = None, lane: str | None = None):
        result = []
        source = (self._read_facts("r7_settlement_schedule") if trade_date is None
                  else self._read_day_facts("r7_settlement_schedule", trade_date, lane))
        for _, value in source:
            item = dict(value)
            if not item.get("identity_contract"):
                item["lane"] = "RETROSPECTIVE_RESEARCH"
                item["identity_contract"] = "V4_FORWARD_SETTLEMENT_R1_LEGACY_LANE_H"
            result.append(item)
        return result

    def _latest_daily_aggregates(self):
        latest = {}
        for _, payload in self._read_facts("r7_aggregate_stats"):
            day = payload.get("trade_date")
            lane = payload.get("lane") or "RETROSPECTIVE_RESEARCH"
            key = (day, lane)
            revision = int(payload.get("revision", 1))
            if key not in latest or revision >= latest[key][0]:
                latest[key] = (revision, payload)
        return latest

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
        source_hashes = (source_run or {}).get("source_hashes", {})
        source_digest = sha256(source_hashes)
        body_rows = []
        observation_id_map = {}
        for row in rows:
            prior_identity = row.get("id") or make_observation_id(row)
            body = {**row, "evidence_lane": lane, "revision": revision,
                    "capture_revision": revision, "source_digest": row.get("source_digest") or source_digest}
            body["id"] = make_observation_id(body)
            observation_id_map[prior_identity] = body["id"]
            body_rows.append(body)
        settlement_rows = [{**item,
            "observation_id": observation_id_map.get(item.get("observation_id"), item.get("observation_id")),
            "capture_revision": revision, "settlement_revision": item.get("settlement_revision", 1)}
            for item in settlement_rows]
        digest = self._stable_hash(dict(trade_date=trade_date, lane=lane, revision=revision,
                                        source_digest=source_digest, rows=body_rows))
        existing = [item for item in self._daily_facts()
                    if item.get("trade_date") == trade_date and item.get("lane") == lane]
        for old in existing:
            if old.get("identity_contract") == "V4_FORWARD_OBSERVATION_ID_R1_LEGACY_LANE_H":
                continue
            old_revision = int(old.get("capture_revision", old.get("revision", 1)))
            if old_revision == revision and old.get("stable_sha256") != digest:
                raise ValueError("FORWARD_R7_IMMUTABLE_CONTENT_CHANGED_NEW_REVISION_REQUIRED")
            if old_revision == revision and old.get("stable_sha256") == digest:
                already_published = True
                break
        else:
            already_published = False
        versioned_existing = [item for item in existing if item.get("identity_contract") == "V4_FORWARD_OBSERVATION_ID_R2"]
        if not already_published and versioned_existing:
            max_revision = max(int(item.get("capture_revision", item.get("revision", 1))) for item in versioned_existing)
            if revision <= max_revision:
                raise ValueError("FORWARD_R7_REVISION_MUST_INCREASE")
        summary_groups = {}
        for row in rows:
            key = (row["rule_id"], row["rule_version"], row["entity_type"])
            group = summary_groups.setdefault(key, dict(entity_type=key[2], universe_count=0,
                match_count=0, no_match_count=0, unknown_count=0))
            group["universe_count"] += 1
            group["match_count" if row["status"] == "MATCH" else
                  "no_match_count" if row["status"] == "NO_MATCH" else "unknown_count"] += 1
        bundle = dict(identity_contract="V4_FORWARD_OBSERVATION_ID_R2", trade_date=trade_date,
            lane=lane, revision=revision, capture_revision=revision, source_digest=source_digest, rows=body_rows,
            first_available_at=first_available_at,
            source_run=source_run or {}, groups={"/".join(k): v for k, v in summary_groups.items()},
            stable_sha256=digest, captured_at=datetime.now(timezone.utc).isoformat())
        with self._connect() as pg:
            if not already_published:
                daily_key = f"v2:{trade_date}:{lane}:r{revision}:{source_digest}:{digest}"
                self._append_fact(pg, "r7_daily_universe", daily_key, bundle, source_digest)
            settlement_digest = self._stable_hash(settlement_rows)
            prior_settlement = [item for item in self._settlement_facts()
                                if item.get("trade_date") == trade_date and item.get("lane") == lane]
            same_capture = [item for item in prior_settlement
                            if item.get("identity_contract") == "V4_FORWARD_SETTLEMENT_R2"
                            and int(item.get("capture_revision", item.get("revision", 1))) == revision]
            if same_capture and not any(item.get("stable_sha256") == settlement_digest for item in same_capture):
                raise ValueError("FORWARD_R7_SETTLEMENT_CHANGED_USE_APPEND_REVISION")
            if not any(item.get("stable_sha256") == settlement_digest for item in same_capture):
                self._append_fact(pg, "r7_settlement_schedule", f"v2:{trade_date}:{lane}:r{revision}:{settlement_digest}",
                    dict(identity_contract="V4_FORWARD_SETTLEMENT_R2", trade_date=trade_date, lane=lane, revision=revision,
                         capture_revision=revision, items=settlement_rows, stable_sha256=settlement_digest, source_run=source_run or {}),
                    self._stable_hash((source_run or {}).get("source_hashes", {})))
            self._append_fact(pg, "r7_aggregate_stats", f"v2:{trade_date}:{lane}:r{revision}:{digest}",
                dict(trade_date=trade_date, lane=lane, revision=revision, groups=bundle["groups"],
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
            prior = self._latest_publish_index(pg, lane=lane, include_legacy=False)
            if (not prior or prior.get("trade_date", "") < trade_date
                    or (prior.get("trade_date") == trade_date and prior.get("payload_sha256") != digest)):
                generation = int(prior.get("generation", 0)) + 1 if prior else 1
                self._append_fact(pg, "r7_publish_index", f"v2:{lane}:{generation:020d}",
                    dict(index_name="daily_universe", identity_contract="V4_FORWARD_PUBLISH_INDEX_R2",
                         lane=lane, generation=generation, trade_date=trade_date,
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

    def _latest_publish_index(self, pg=None, *, lane=None, include_legacy=True):
        own = pg is None
        conn = pg or self._connect()
        try:
            rows = conn.execute(sql.SQL("""SELECT payload FROM {}.forward_facts
                WHERE kind='r7_publish_index' ORDER BY ordinal DESC""").format(
                    sql.Identifier(self.schema))).fetchall()
            decoded = [json.loads(payload) for (payload,) in rows]
            for value in decoded:
                value_lane = value.get("lane") or "RETROSPECTIVE_RESEARCH"
                if (lane is None or value_lane == lane) and value.get("identity_contract") == "V4_FORWARD_PUBLISH_INDEX_R2":
                    return value
            if include_legacy:
                for value in decoded:
                    value_lane = value.get("lane") or "RETROSPECTIVE_RESEARCH"
                    if (lane is None or value_lane == lane) and not value.get("identity_contract"):
                        return value
            return {}
        finally:
            if own:
                conn.close()


    def read_universe(self, *, lane: str | None = None, trade_date: str | None = None,
                      rule: str | None = None, status: str | None = None,
                      limit: int = 30, offset: int = 0, revision: int | None = None):
        if not 1 <= limit <= 200 or not 0 <= offset <= 1_000_000:
            raise ValueError("INVALID_QUERY_BOUND")
        candidates = [row for bundle in self._daily_facts() for row in bundle.get("rows", [])
                 if (not lane or row.get("evidence_lane") == lane)
                 and (not trade_date or row.get("T0") == trade_date)
                 and (revision is None or int(row.get("capture_revision", row.get("revision", 1))) == revision)
                 and (not rule or row.get("rule_id") == rule)
                 and (not status or row.get("status") == status)]
        latest = {}
        for row in candidates:
            key = (row.get("T0"), row.get("evidence_lane"), row.get("rule_id"),
                   row.get("rule_version"), row.get("entity_id"))
            current = latest.get(key)
            if current is None or int(row.get("capture_revision", row.get("revision", 1))) >= int(current.get("capture_revision", current.get("revision", 1))):
                latest[key] = row
        items = list(latest.values())
        items.sort(key=lambda row: (row.get("T0", ""), row.get("rule_id", ""),
                                    row.get("entity_id", "")), reverse=True)
        total = len(items)
        page = items[offset:offset + limit]
        return dict(status="READY" if total else "EMPTY_VALID", items=page,
                    total=total, offset=offset, limit=limit, has_next=offset + len(page) < total)


    def read_counts(self):
        grouped = {}
        if hasattr(self, "schema"):
            for (day, lane), (_, payload) in self._latest_daily_aggregates().items():
                info = grouped.setdefault(lane, dict(count=0, match=0, no_match=0, unknown=0, latest_t0=""))
                info["latest_t0"] = max(info["latest_t0"], day or "")
                for aggregate in payload.get("groups", {}).values():
                    info["count"] += int(aggregate.get("universe_count", 0))
                    info["match"] += int(aggregate.get("match_count", 0))
                    info["no_match"] += int(aggregate.get("no_match_count", 0))
                    info["unknown"] += int(aggregate.get("unknown_count", 0))
        else:
            latest = {}
            for bundle in self._daily_facts():
                for row in bundle.get("rows", []):
                    key = (row.get("T0"), row.get("evidence_lane"), row.get("rule_id"), row.get("rule_version"), row.get("entity_id"))
                    current = latest.get(key)
                    if current is None or int(row.get("capture_revision", row.get("revision", 1))) >= int(current.get("capture_revision", current.get("revision", 1))):
                        latest[key] = row
            for row in latest.values():
                lane = row.get("evidence_lane")
                info = grouped.setdefault(lane, dict(count=0, match=0, no_match=0, unknown=0, latest_t0=""))
                info["count"] += 1
                info["match"] += row.get("status") == "MATCH"
                info["no_match"] += row.get("status") == "NO_MATCH"
                info["unknown"] += row.get("status") == "UNKNOWN"
                info["latest_t0"] = max(info["latest_t0"], row.get("T0", ""))
        pointer = self._latest_publish_index(lane="LIVE_OOS") or self._latest_publish_index(lane="RETROSPECTIVE_RESEARCH") or self._latest_publish_index()
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
        if hasattr(self, "schema"):
            for (day, lane), (_, payload) in self._latest_daily_aggregates().items():
                groups = by_date.setdefault(day, {})
                for key_text, counts in payload.get("groups", {}).items():
                    entity_type = key_text.split("/")[-1]
                    key = (key_text.split("/")[0], key_text.split("/")[1] if "/" in key_text else "1.0.0", entity_type)
                    group = groups.setdefault(key, dict(rule_id=key[0],rule_version=key[1],entity_type=key[2],
                        universe_count=0,match_count=0,no_match_count=0,unknown_count=0,live_count=0,historical_count=0))
                    for field in ("universe_count","match_count","no_match_count","unknown_count"):
                        group[field] += int(counts.get(field,0))
                    group["live_count"] += int(counts.get("universe_count",0)) if lane=="LIVE_OOS" else 0
                    group["historical_count"] += int(counts.get("universe_count",0)) if lane=="RETROSPECTIVE_RESEARCH" else 0
        else:
            latest = {}
            for bundle in self._daily_facts():
                for row in bundle.get("rows", []):
                    identity=(row.get("T0"),row.get("evidence_lane"),row.get("rule_id"),row.get("rule_version"),row.get("entity_id"))
                    revision=int(row.get("capture_revision",row.get("revision",1)))
                    if identity not in latest or revision>=latest[identity][0]: latest[identity]=(revision,row)
            for _, row in latest.values():
                day=row.get("T0");groups=by_date.setdefault(day,{})
                key=(row.get("rule_id"),row.get("rule_version"),row.get("entity_type"))
                group=groups.setdefault(key,dict(rule_id=key[0],rule_version=key[1],entity_type=key[2],universe_count=0,
                    match_count=0,no_match_count=0,unknown_count=0,live_count=0,historical_count=0))
                group["universe_count"]+=1;group["match_count"]+=row.get("status")=="MATCH"
                group["no_match_count"]+=row.get("status")=="NO_MATCH";group["unknown_count"]+=row.get("status")=="UNKNOWN"
                group["live_count"]+=row.get("evidence_lane")=="LIVE_OOS"
                group["historical_count"]+=row.get("evidence_lane")=="RETROSPECTIVE_RESEARCH"
        dates = sorted(by_date, reverse=True)
        page = dates[offset:offset + limit]
        return dict(status="READY" if dates else "EMPTY_VALID",
            items=[dict(trade_date=day, groups=sorted(by_date[day].values(), key=lambda x:x["rule_id"])) for day in page],
            total=len(dates), limit=limit, offset=offset, has_next=offset + len(page) < len(dates))


    def read_settlement(self, *, lane: str | None = None, trade_date: str | None = None,
                        horizon: int | None = None, status: str | None = None,
                        limit: int = 30, offset: int = 0, revision: int | None = None,
                        settlement_revision: int | None = None):
        if not 1 <= limit <= 200 or not 0 <= offset <= 1_000_000:
            raise ValueError("INVALID_QUERY_BOUND")
        latest_observations = {}
        for bundle in self._daily_facts(trade_date=trade_date, lane=lane):
            for row in bundle.get("rows", []):
                if revision is not None and int(row.get("capture_revision", row.get("revision", 1))) != revision:
                    continue
                identity = (row.get("T0"), row.get("evidence_lane"), row.get("rule_id"),
                            row.get("rule_version"), row.get("entity_id"))
                current = latest_observations.get(identity)
                row_revision = int(row.get("capture_revision", row.get("revision", 1)))
                if current is None or row_revision >= current[0]:
                    latest_observations[identity] = (row_revision, row, bundle)
        observations = {}
        for _, row, bundle in latest_observations.values():
            observations[make_observation_id(row)] = row
            if bundle.get("identity_contract") == "V4_FORWARD_OBSERVATION_ID_R1_LEGACY_LANE_H":
                observations[legacy_observation_id(row)] = row
        items, counts = [], {}
        latest_schedule = {}
        for bundle in self._settlement_facts(trade_date=trade_date, lane=lane):
            for schedule in bundle.get("items", []):
                key = (bundle.get("lane", "RETROSPECTIVE_RESEARCH"), schedule.get("observation_id"),
                       schedule.get("horizon_sessions"))
                old = latest_schedule.get(key)
                current_revision = int(schedule.get("settlement_revision", bundle.get("revision", 1)))
                if settlement_revision is not None and current_revision != settlement_revision:
                    continue
                if old is None or current_revision >= old[2]:
                    latest_schedule[key] = (bundle, schedule, current_revision)
        aggregate_values = {}
        for bundle, schedule, settlement_revision in latest_schedule.values():
            row = observations.get(schedule.get("observation_id"))
            if not row:
                continue
            state = schedule.get("schedule_status", "PENDING")
            h = schedule.get("horizon_sessions")
            lane_value, day = row.get("evidence_lane"), row.get("T0")
            if ((lane and lane != lane_value) or (trade_date and trade_date != day)
                    or (horizon and horizon != h) or (status and status != state)):
                continue
            counts[(lane_value, h, state)] = counts.get((lane_value, h, state), 0) + 1
            aggregate_values.setdefault((lane_value, h), []).append(schedule)
            outcome = schedule.get("settlement", {})
            items.append(dict(observation_id=schedule.get("observation_id"), revision=row.get("capture_revision",row.get("revision",1)),
                settlement_revision=settlement_revision,
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
        aggregates=[]
        for (aggregate_lane, aggregate_horizon), scheduled in sorted(aggregate_values.items()):
            settled_returns=[x.get("settlement",{}).get("nominal_return") for x in scheduled
                if x.get("schedule_status")=="SETTLED" and x.get("settlement",{}).get("status")=="SETTLED"
                and x.get("settlement",{}).get("nominal_return") is not None]
            aggregates.append(dict(lane=aggregate_lane,horizon_sessions=aggregate_horizon,
                sample_count=len(scheduled),settled_count=len(settled_returns),
                return_denominator=len(settled_returns),
                mean_return=statistics.mean(settled_returns) if settled_returns else None,
                median_return=statistics.median(settled_returns) if settled_returns else None,
                price_basis="NOMINAL_UNADJUSTED_CLOSE",corporate_action_adjustment="NOT_APPLIED"))
        return dict(status="READY" if total else "EMPTY_VALID", total=total, offset=offset,
            limit=limit, has_next=offset+len(page)<total, items=page,
            counts=[dict(lane=k[0],horizon_sessions=k[1],status=k[2],count=v) for k,v in sorted(counts.items())],
            aggregates=aggregates)


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
        if hasattr(self, "schema"):
            snapshots={}; base={}; has_per_observation_revision=False
            for ordinal,(_,payload) in enumerate(self._read_facts("r7_settlement_aggregate")):
                lane=payload.get("lane") or "RETROSPECTIVE_RESEARCH"
                horizon=payload.get("horizon_sessions")
                asof=payload.get("asof_trade_date")
                if asof:
                    key=(lane,horizon)
                    if key not in snapshots or (asof,ordinal)>snapshots[key][0]:
                        snapshots[key]=((asof,ordinal),int(payload.get("settled_count",0)))
                else:
                    key=(payload.get("trade_date"),lane,horizon)
                    if key not in base or ordinal>=base[key][0]:
                        base[key]=(ordinal,int(payload.get("settled_count",0)))
                    has_per_observation_revision |= payload.get("identity_contract") == "V4_FORWARD_SETTLEMENT_AGGREGATE_R2"
            if has_per_observation_revision:
                return sum(count for _,count in base.values())
            grouped={(lane,horizon) for _,lane,horizon in base}|set(snapshots)
            return sum(snapshots[(lane,horizon)][1] if (lane,horizon) in snapshots else
                       sum(count for (_,item_lane,item_h),(_,count) in base.items()
                           if item_lane==lane and item_h==horizon)
                       for lane,horizon in grouped)
        latest_observations = {}
        for bundle in self._daily_facts():
            for row in bundle.get("rows", []):
                identity = (row.get("T0"), row.get("evidence_lane"), row.get("rule_id"),
                            row.get("rule_version"), row.get("entity_id"))
                revision = int(row.get("capture_revision", row.get("revision", 1)))
                if identity not in latest_observations or revision >= latest_observations[identity][0]:
                    latest_observations[identity] = (revision, row, bundle)
        valid_ids = set()
        for _, row, bundle in latest_observations.values():
            valid_ids.add(make_observation_id(row))
            if bundle.get("identity_contract") == "V4_FORWARD_OBSERVATION_ID_R1_LEGACY_LANE_H":
                valid_ids.add(legacy_observation_id(row))
        latest = {}
        for bundle in self._settlement_facts():
            for schedule in bundle.get("items", []):
                if schedule.get("observation_id") not in valid_ids:
                    continue
                key = (bundle.get("lane", "RETROSPECTIVE_RESEARCH"), schedule.get("observation_id"), schedule.get("horizon_sessions"))
                revision = int(schedule.get("settlement_revision", bundle.get("revision", 1)))
                if key not in latest or revision >= latest[key][0]:
                    latest[key] = (revision, schedule)
        return sum(schedule.get("schedule_status") == "SETTLED"
                   and schedule.get("settlement", {}).get("status") == "SETTLED"
                   for _, schedule in latest.values())

    def pending_due_dates(self, *, accepted_source_dates: set[str]):
        """Return accepted due sessions whose latest schedule still needs settlement."""
        accepted = set(accepted_source_dates)
        latest = {}
        for bundle in self._settlement_facts():
            for schedule in bundle.get("items", []):
                key = (bundle.get("lane", "RETROSPECTIVE_RESEARCH"), schedule.get("observation_id"), schedule.get("horizon_sessions"))
                revision = int(schedule.get("settlement_revision", bundle.get("revision", 1)))
                if key not in latest or revision >= latest[key][0]:
                    latest[key] = (revision, schedule)
        return sorted({schedule.get("due_date") for _, schedule in latest.values()
                       if schedule.get("due_date") in accepted
                       and schedule.get("schedule_status") in (
                           "DUE_SOURCE_NOT_ACCEPTED", "SOURCE_GAP", "PENDING_FUTURE_SESSION")})

    def advance_due_settlements(self, *, accepted_trade_date: str, prices_by_date: dict,
                                source_digest: str, accepted_source_dates: set[str] | None = None,
                                source_digests_by_date: dict[str, str] | None = None):
        """Append accepted-session settlement revisions for genuinely due observations."""
        accepted = set(accepted_source_dates or {accepted_trade_date})
        if accepted_trade_date not in accepted:
            raise ValueError("FORWARD_R7_SETTLEMENT_ADVANCE_DATE_NOT_ACCEPTED")
        observations = []
        for bundle in self._daily_facts():
            for row in bundle.get("rows", []):
                if row.get("entity_type") != "STOCK" or row.get("status") != "MATCH":
                    continue
                observations.append((bundle, row, make_observation_id(row)))
        latest = {}
        for bundle in self._settlement_facts():
            for schedule in bundle.get("items", []):
                key = (bundle.get("lane", "RETROSPECTIVE_RESEARCH"), schedule.get("observation_id"), schedule.get("horizon_sessions"))
                revision = int(schedule.get("settlement_revision", bundle.get("revision", 1)))
                if key not in latest or revision >= latest[key][0]:
                    latest[key] = (revision, bundle, schedule)
        appended = []
        for bundle, row, observation_id in observations:
            lane = row.get("evidence_lane", bundle.get("lane", "RETROSPECTIVE_RESEARCH"))
            for (row_lane, schedule_id, horizon), (revision, old_bundle, old) in latest.items():
                if row_lane != lane or schedule_id not in (observation_id, legacy_observation_id(row)):
                    continue
                due_day = old.get("due_date")
                if due_day not in accepted or due_day > accepted_trade_date or old.get("schedule_status") not in (
                        "DUE_SOURCE_NOT_ACCEPTED", "SOURCE_GAP", "PENDING_FUTURE_SESSION"):
                    continue
                current_prices = prices_by_date.get(due_day, {})
                due_source_digest = (source_digests_by_date or {}).get(due_day, source_digest)
                if old.get("source_digest") == due_source_digest:
                    continue
                t0_close = (row.get("values") or {}).get("close")
                materialized_prices = dict(prices_by_date)
                materialized_prices.setdefault(row.get("T0"), {})
                if row.get("entity_id") not in materialized_prices[row.get("T0")]:
                    materialized_prices[row.get("T0")][row.get("entity_id")] = dict(close=t0_close)
                if due_day not in accepted:
                    result = dict(status="DUE_SOURCE_NOT_ACCEPTED", reason="DUE_SESSION_NOT_IN_ACCEPTED_HEAD", due_date=due_day)
                else:
                    result = compute_nominal_settlement(observation=row, due_date=due_day,
                        prices_by_date=materialized_prices, settlement_at=datetime.now(timezone.utc).isoformat(),
                        due_source_accepted=True)
                status = result.get("status", "SOURCE_GAP")
                updated = dict(observation_id=schedule_id, horizon_sessions=horizon,
                    due_date=due_day, schedule_status=status, reason=result.get("reason"),
                    settlement=result, settlement_revision=revision + 1,
                    source_digest=due_source_digest, price_basis="NOMINAL_UNADJUSTED_CLOSE")
                appended.append((lane, row.get("T0"), updated, revision + 1))
        if not appended:
            return dict(status="NO_DUE_SETTLEMENTS", accepted_trade_date=accepted_trade_date, appended=0)
        by_lane = {}
        latest_schedule_rows = {(key[0], key[1], key[2]): value[2] for key, value in latest.items()}
        observation_dates = {}
        for bundle, row, observation_id in observations:
            lane = row.get("evidence_lane", bundle.get("lane", "RETROSPECTIVE_RESEARCH"))
            observation_dates[(lane, observation_id)] = row.get("T0")
            observation_dates[(lane, legacy_observation_id(row))] = row.get("T0")
        for lane, t0, item, revision in appended:
            by_lane.setdefault((lane, t0, revision), []).append(item)
            latest_schedule_rows[(lane, item["observation_id"], item["horizon_sessions"])] = item
        run_id = sha256(["SETTLEMENT_ADVANCE_R1", accepted_trade_date, source_digest,
                         datetime.now(timezone.utc).isoformat()])
        try:
            with self._connect() as pg:
                for (lane, t0, revision), items in by_lane.items():
                    digest = self._stable_hash(items)
                    item_source_digest = items[0].get("source_digest", source_digest)
                    key = f"v2:{t0}:{lane}:advance:{accepted_trade_date}:r{revision}:{item_source_digest}:{digest}"
                    self._append_fact(pg, "r7_settlement_schedule", key,
                        dict(identity_contract="V4_FORWARD_SETTLEMENT_R2", trade_date=t0,
                             accepted_trade_date=accepted_trade_date, lane=lane, revision=revision,
                             capture_revision=revision, items=items, stable_sha256=digest,
                             source_digest=item_source_digest,
                             price_basis="NOMINAL_UNADJUSTED_CLOSE", corporate_action_adjustment="NOT_APPLIED"),
                        item_source_digest)
                changed_groups={(lane,t0,item.get("horizon_sessions")) for lane,t0,item,_ in appended}
                aggregate_groups = {}
                for (lane, observation_id, horizon), schedule in latest_schedule_rows.items():
                    t0=observation_dates.get((lane,observation_id))
                    if (lane,t0,horizon) in changed_groups:
                        aggregate_groups.setdefault((lane,t0,horizon), []).append(schedule)
                for (lane,t0,horizon), schedules in aggregate_groups.items():
                    summary = summarize_settlement_schedule(t0,lane,horizon,schedules)
                    summary.update(identity_contract="V4_FORWARD_SETTLEMENT_AGGREGATE_R2",
                        settlement_revision=max(int(x.get("settlement_revision",1)) for x in schedules),
                        price_basis="NOMINAL_UNADJUSTED_CLOSE",corporate_action_adjustment="NOT_APPLIED")
                    summary_digest = self._stable_hash(summary)
                    self._append_fact(pg,"r7_settlement_aggregate",
                        f"v2:{t0}:{lane}:{horizon}:r{summary['settlement_revision']}:{summary_digest}",
                        summary,summary_digest)
                self._append_fact(pg, "r7_pipeline_run", run_id,
                    dict(run_id=run_id, stage="SETTLEMENT_ADVANCE", trade_date=accepted_trade_date,
                         status="PASS", counts={"appended":len(appended)}, source_digest=source_digest,
                         recorded_at=datetime.now(timezone.utc).isoformat()), source_digest)
        except Exception as exc:
            self.record_failure(stage="SETTLEMENT_ADVANCE", trade_date=accepted_trade_date,
                current_head_date=accepted_trade_date, run_id=run_id + ":FAILED", attempt=1,
                error_code=type(exc).__name__ + ":" + str(exc),
                payload={"source_digest":source_digest,"retryable":True,"due_dates":sorted({x[2].get("due_date") for x in appended})})
            return dict(status="RETRY_REQUIRED", accepted_trade_date=accepted_trade_date,
                        appended=0, error_code=type(exc).__name__)
        return dict(status="APPENDED", accepted_trade_date=accepted_trade_date,
                    appended=len(appended), source_digest=source_digest,
                    outcomes={state:sum(item[2]["schedule_status"] == state for item in appended)
                              for state in SETTLEMENT_STATUS_STATES})
