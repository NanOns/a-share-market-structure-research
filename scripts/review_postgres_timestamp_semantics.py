"""Apply writer-backed timestamp semantics to the PostgreSQL workbench schema.

DuckDB stores these values without an offset because the existing writers
normalize aware datetimes to a UTC wall value before persistence.  This script
only promotes fields whose writer contract proves that behavior.  Ambiguous
source quote/evidence times remain ``timestamp`` and are recorded as pending;
they are not guessed from the machine timezone.
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

import psycopg
from psycopg import sql


# (table, column): (semantic label, evidence, transform)
UTC_FIELDS: dict[tuple[str, str], tuple[str, str, str]] = {
    ("analysis_daily_basis", "source_observed_at"): ("UTC_INSTANT", "M10/M13 writers derive source_observed_at from UTC-aware snapshot/file observation", "AT TIME ZONE UTC"),
    ("analysis_result_objects", "created_at"): ("UTC_INSTANT", "result_objects.py uses datetime.now(timezone.utc)", "AT TIME ZONE UTC"),
    ("analysis_slices", "created_at"): ("UTC_INSTANT", "slice/result writers use datetime.now(timezone.utc)", "AT TIME ZONE UTC"),
    ("analysis_snapshot_audit_status", "created_at"): ("UTC_INSTANT", "audit status is created by UTC-aware activation/audit writers", "AT TIME ZONE UTC"),
    ("analysis_snapshot_hierarchy", "bound_at"): ("UTC_INSTANT", "M10/M11/M13 bind writers use UTC-aware now", "AT TIME ZONE UTC"),
    ("analysis_snapshots", "created_at"): ("UTC_INSTANT", "analysis activation/preview writers use datetime.now(timezone.utc)", "AT TIME ZONE UTC"),
    ("limit_rule_versions", "audited_at"): ("UTC_INSTANT", "register_m8c_public_rules_preview.py writes datetime.now(timezone.utc)", "AT TIME ZONE UTC"),
    ("m8c_rule_audit_events", "audited_at"): ("UTC_INSTANT", "register_m8c_public_rules_preview.py writes datetime.now(timezone.utc)", "AT TIME ZONE UTC"),
    ("market_reference_daily", "observed_at"): ("UTC_INSTANT", "M8c source observation is file mtime tagged timezone.utc", "AT TIME ZONE UTC"),
    ("membership_snapshot_metadata", "observed_at"): ("UTC_INSTANT", "membership snapshot manifest observation is UTC-aware", "AT TIME ZONE UTC"),
    ("online_batches", "first_seen_at"): ("UTC_INSTANT", "event_store _db_timestamp normalizes aware values to UTC wall time", "AT TIME ZONE UTC"),
    ("online_batches", "observed_at"): ("UTC_INSTANT", "event_store stores received_at normalized to UTC wall time", "AT TIME ZONE UTC"),
    ("online_batches", "source_as_of"): ("UTC_INSTANT", "event_store _db_timestamp parses source_as_of and normalizes to UTC", "AT TIME ZONE UTC"),
    ("online_event_bundles", "observed_at"): ("UTC_INSTANT", "event_store received_at is UTC-normalized", "AT TIME ZONE UTC"),
    ("online_fetch_runs", "received_at"): ("UTC_INSTANT", "event_store received_at is UTC-normalized", "AT TIME ZONE UTC"),
    ("online_fetch_runs", "requested_at"): ("UTC_INSTANT", "event_store requested_at is UTC-normalized", "AT TIME ZONE UTC"),
    ("online_payloads", "created_at"): ("UTC_INSTANT", "payload lifecycle writer uses UTC-aware creation time", "AT TIME ZONE UTC"),
    ("online_pool_entries", "first_limit_time"): ("UTC_INSTANT", "event DTO parses epoch seconds and event_store normalizes to UTC", "AT TIME ZONE UTC"),
    ("online_pool_entries", "last_break_time"): ("UTC_INSTANT", "event DTO/event_store contract is UTC-normalized when present", "AT TIME ZONE UTC"),
    ("online_pool_entries", "last_limit_time"): ("UTC_INSTANT", "event DTO parses epoch seconds and event_store normalizes to UTC", "AT TIME ZONE UTC"),
    ("publication_analysis_snapshots", "bound_at"): ("UTC_INSTANT", "analysis activation/preview writers use UTC-aware now", "AT TIME ZONE UTC"),
    ("relation_observations", "observed_at"): ("UTC_INSTANT", "relation_repository _timestamp normalizes aware input to UTC wall time", "AT TIME ZONE UTC"),
    ("relation_revisions", "created_at"): ("UTC_INSTANT", "relation_repository _timestamp(None) uses UTC now", "AT TIME ZONE UTC"),
    ("research_runs", "completed_at"): ("UTC_INSTANT", "research run completion writer uses UTC-aware completion time", "AT TIME ZONE UTC"),
    ("research_runs", "created_at"): ("UTC_INSTANT", "research run creation writer uses UTC-aware creation time", "AT TIME ZONE UTC"),
    ("research_runs_v3_3", "registered_at"): ("UTC_INSTANT", "research_registry_v3_3.py uses datetime.now(timezone.utc)", "AT TIME ZONE UTC"),
    ("research_signal_outcomes", "evaluated_at"): ("UTC_INSTANT", "research_signal_evaluation.py defaults evaluated_at to UTC-aware now", "AT TIME ZONE UTC"),
    ("schema_migration_checks", "applied_at"): ("UTC_INSTANT", "migration receipt writer uses UTC-aware applied time", "AT TIME ZONE UTC"),
    ("sector_semantic_versions", "observed_at"): ("UTC_INSTANT", "semantic writer receives UTC-aware observation timestamps", "AT TIME ZONE UTC"),
    ("security_metadata_versions", "observed_at"): ("UTC_INSTANT", "M8c metadata writer uses UTC-aware source observation", "AT TIME ZONE UTC"),
    ("tdx_sector_hierarchy_versions", "created_at"): ("UTC_INSTANT", "hierarchy registration timestamps are UTC-aware", "AT TIME ZONE UTC"),
    ("tdx_sector_hierarchy_versions", "observed_at"): ("UTC_INSTANT", "hierarchy source observation is UTC-aware", "AT TIME ZONE UTC"),
}

PENDING_REASON: dict[tuple[str, str], str] = {
    ("online_quote_entries", "quote_time"): "source quote time is provider-defined and may be absent; no UTC contract proven",
    ("online_evidence", "event_time"): "external evidence has a parser contract but no production persistence writer",
    ("online_evidence", "published_at"): "external evidence has a parser contract but no production persistence writer",
    ("online_evidence", "first_seen_at"): "external evidence has a parser contract but no production persistence writer",
}


def qi(value: str) -> sql.Identifier:
    return sql.Identifier(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=None)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        raise SystemExit("Refusing to change PostgreSQL without --apply")
    dsn = args.dsn or os.environ.get("PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    now = datetime.now(timezone.utc)
    applied = 0
    pending = 0
    with psycopg.connect(dsn) as pg:
        with pg.cursor() as cur:
            cur.execute("alter table workbench_meta.timestamp_semantics_catalog add column if not exists evidence text")
            cur.execute("alter table workbench_meta.timestamp_semantics_catalog add column if not exists review_basis text")
            cur.execute("alter table workbench_meta.timestamp_semantics_catalog add column if not exists contract_version text")
        pg.commit()
        with pg.cursor() as cur:
            cur.execute("select table_name,column_name,target_type from workbench_meta.timestamp_semantics_catalog")
            existing = {(r[0], r[1]): r[2] for r in cur.fetchall()}
        for key, (semantics, evidence, transform) in UTC_FIELDS.items():
            table, column = key
            if key not in existing:
                continue
            if existing[key] != "timestamp with time zone":
                with pg.cursor() as cur:
                    cur.execute(sql.SQL("alter table workbench.{} alter column {} type timestamptz using {} at time zone 'UTC'").format(qi(table), qi(column), qi(column)))
            with pg.cursor() as cur:
                cur.execute("""update workbench_meta.timestamp_semantics_catalog set writer_semantics=%s, semantic_timezone='UTC', target_type='timestamptz', transform_rule=%s, status='APPLIED', evidence=%s, review_basis='writer-backed contract review', contract_version='PG_TIMESTAMP_SEMANTICS_V2', reviewed_at=%s where table_name=%s and column_name=%s""", (semantics, f"source TIMESTAMP interpreted as UTC wall value; promote with {transform}", evidence, now, table, column))
            pg.commit()
            applied += 1
        for key, reason in PENDING_REASON.items():
            if key not in existing:
                continue
            with pg.cursor() as cur:
                cur.execute("""update workbench_meta.timestamp_semantics_catalog set writer_semantics='UNCONFIRMED_SOURCE_TIME', semantic_timezone=null, target_type='timestamp without time zone', transform_rule='retain wall-clock type; require source contract before promotion', status='PENDING_REVIEW', evidence=%s, review_basis='explicit unresolved source-time contract', contract_version='PG_TIMESTAMP_SEMANTICS_V2', reviewed_at=%s where table_name=%s and column_name=%s""", (reason, now, key[0], key[1]))
            pg.commit()
            pending += 1
    print(f"TIMESTAMP_REVIEW_COMPLETE applied={applied} pending_explicit={pending}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
