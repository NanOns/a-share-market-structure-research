"""Read-only/rollback-only performance samples required by V4.2.2 REV2 §74.

The PostgreSQL sample uses a temporary table inside a rolled-back transaction.
It never runs the daily pipeline, scanner, source overlap, or external fetches.
"""
from __future__ import annotations

from datetime import datetime, timezone
import http.client
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import time

import psutil
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

from apply_v4_phase0_schema import MIGRATIONS, VERSIONS, apply, dsn


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * fraction
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)


def database_size() -> int:
    with psycopg.connect(dsn()) as pg:
        return int(pg.execute("select pg_database_size(current_database())").fetchone()[0])


def v4_runtime_row_count() -> int:
    total = 0
    with psycopg.connect(dsn()) as pg:
        tables = [row[0] for row in pg.execute("select tablename from pg_tables where schemaname='v4'").fetchall()]
        for table in tables:
            total += int(pg.execute(sql.SQL("select count(*) from v4.{}").format(sql.Identifier(table))).fetchone()[0])
    return total


def fresh_schema_rebuild_probe() -> dict:
    """Measure a fresh schema rebuild in an isolated temporary DB, then remove only that DB."""
    base_dsn = dsn()
    params = conninfo_to_dict(base_dsn)
    target = f"v4_phase0_perf_{os.urandom(6).hex()}"
    maintenance_params = dict(params)
    maintenance_params["dbname"] = "postgres"
    maintenance_dsn = psycopg.conninfo.make_conninfo(**maintenance_params)
    rebuild_started = time.perf_counter()
    cpu_started = time.process_time()
    applied = []
    system_id = None
    before_databases = []
    created = False
    result: dict = {}
    try:
        with psycopg.connect(maintenance_dsn, autocommit=True) as maint:
            identity = maint.execute("select (select system_identifier::text from pg_control_system()), current_database()").fetchone()
            system_id = identity[0]
            before_databases = [row[0] for row in maint.execute("select datname from pg_database where datistemplate=false order by datname").fetchall()]
            if target in before_databases:
                raise RuntimeError("TEMP_DATABASE_NAME_COLLISION")
            maint.execute(sql.SQL("CREATE DATABASE {} WITH OWNER {} TEMPLATE template0 ENCODING 'UTF8' LC_COLLATE {} LC_CTYPE {}").format(
                sql.Identifier(target), sql.Identifier("postgres"), sql.Literal("Chinese (Simplified)_China.936"), sql.Literal("Chinese (Simplified)_China.936")))
            created = True

        temp_params = dict(params)
        temp_params["dbname"] = target
        temp_dsn = psycopg.conninfo.make_conninfo(**temp_params)
        for path in sorted(MIGRATIONS.glob("*.sql")):
            version = VERSIONS[path.name]
            text = path.read_text("utf-8")
            checksum = hashlib.sha256(text.encode()).hexdigest()
            with psycopg.connect(temp_dsn) as pg:
                with pg.transaction():
                    pg.execute(text)
                    pg.execute("insert into v4_meta.schema_migrations(version,checksum_sha256,applied_at,contract_id) values (%s,%s,now(),%s)", (version, checksum, version))
            applied.append({"version": version, "checksum_sha256": checksum})
        with psycopg.connect(temp_dsn) as pg:
            size_after = int(pg.execute("select pg_database_size(current_database())").fetchone()[0])
            table_count = int(pg.execute("select count(*) from pg_tables where schemaname='v4'").fetchone()[0])
            fk_count, unvalidated = pg.execute("select count(*),count(*) filter (where not convalidated) from pg_constraint where connamespace='v4'::regnamespace and contype='f'").fetchone()
            all_empty = True
            for (table,) in pg.execute("select tablename from pg_tables where schemaname='v4'").fetchall():
                if pg.execute(sql.SQL("select count(*) from v4.{}").format(sql.Identifier(table))).fetchone()[0] != 0:
                    all_empty = False
                    break
        result.update({
            "status": "FRESH_SCHEMA_REBUILD_MEASURED",
            "temporary_database": target,
            "temporary_database_removed_after_measurement": True,
            "cluster_system_identifier": system_id,
            "non_template_database_set_before": before_databases,
            "applied_migrations": applied,
            "schema_rebuild_wall_seconds": time.perf_counter() - rebuild_started,
            "schema_rebuild_process_cpu_seconds": time.process_time() - cpu_started,
            "database_size_after_schema_build_bytes": size_after,
            "v4_table_count": table_count,
            "foreign_key_count": int(fk_count),
            "unvalidated_foreign_key_count": int(unvalidated),
            "all_v4_tables_empty_after_build": all_empty,
        })
    finally:
        if created:
            with psycopg.connect(maintenance_dsn, autocommit=True) as maint:
                maint.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(target)))
                remaining = maint.execute("select 1 from pg_database where datname=%s", (target,)).fetchone()
                if remaining is not None:
                    raise RuntimeError("TEMP_DATABASE_CLEANUP_FAILED")
    with psycopg.connect(maintenance_dsn) as maint:
        after_databases = [row[0] for row in maint.execute("select datname from pg_database where datistemplate=false order by datname").fetchall()]
    if after_databases != before_databases:
        raise RuntimeError("DATABASE_SET_CHANGED_DURING_TEMP_SCHEMA_PROBE")
    result["non_template_database_set_after"] = after_databases
    return result


def pg_rollback_probe(row_count: int = 1000) -> dict:
    process = psutil.Process()
    probe_wall_started = time.perf_counter()
    rss_before = process.memory_info().rss
    cpu_before = time.process_time()
    size_before = database_size()
    rows = [(i, f"payload-{i:06d}") for i in range(row_count)]
    conn = psycopg.connect(dsn())
    write_started = time.perf_counter()
    read_elapsed = None
    write_elapsed = None
    roundtrip_elapsed = None
    try:
        conn.execute("BEGIN")
        conn.execute("CREATE TEMP TABLE v4_phase0_perf_probe (id integer primary key, payload text) ON COMMIT DROP")
        write_started = time.perf_counter()
        conn.cursor().executemany("INSERT INTO v4_phase0_perf_probe(id,payload) VALUES (%s,%s)", rows)
        write_elapsed = time.perf_counter() - write_started
        read_started = time.perf_counter()
        count, payload_bytes = conn.execute("SELECT count(*), sum(octet_length(payload)) FROM v4_phase0_perf_probe").fetchone()
        read_elapsed = time.perf_counter() - read_started
        roundtrip_elapsed = write_elapsed + read_elapsed
        if count != row_count:
            raise RuntimeError("PERF_PROBE_ROW_COUNT_MISMATCH")
    finally:
        conn.rollback()
        conn.close()
    size_after = database_size()
    memory = process.memory_info()
    probe_wall_elapsed = time.perf_counter() - probe_wall_started
    probe_cpu_elapsed = time.process_time() - cpu_before
    return {
        "scope": "synthetic 1000-row temporary-table transaction; rolled back",
        "rows_written": row_count,
        "payload_bytes_read": int(payload_bytes),
        "postgres_write_seconds": write_elapsed,
        "postgres_read_seconds": read_elapsed,
        "postgres_write_read_seconds": roundtrip_elapsed,
        "probe_wall_seconds_including_db_size_checks": probe_wall_elapsed,
        "process_cpu_seconds": probe_cpu_elapsed,
        "process_cpu_percent_one_core": 100.0 * probe_cpu_elapsed / max(probe_wall_elapsed, 1e-9),
        "process_rss_before_bytes": rss_before,
        "process_rss_after_bytes": memory.rss,
        "process_peak_working_set_bytes": getattr(memory, "peak_wset", None),
        "database_size_before_bytes": size_before,
        "database_size_after_bytes": size_after,
        "database_size_growth_bytes": size_after - size_before,
    }


def local_http_probe(base_url: str = "http://127.0.0.1:8765", samples: int = 30) -> dict:
    from urllib.parse import urlsplit

    parsed = urlsplit(base_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=0.5):
            pass
    except OSError:
        return {"status": "NOT_AVAILABLE", "reason": "READ_ONLY_LOCAL_WORKBENCH_API_NOT_LISTENING", "base_url": base_url}
    if parsed.scheme != "http":
        return {"status": "NOT_MEASURED", "reason": "HTTPS_API_PROBE_NOT_CONFIGURED", "base_url": base_url}

    result = {"status": "MEASURED_LEGACY_REFERENCE_ONLY", "base_url": base_url, "samples": samples, "endpoints": {}}
    for name, path in (("api_field_catalog", "/api/metadata/field-catalog"), ("homepage", "/")):
        latencies: list[float] = []
        payload_bytes = None
        response_status = None
        for _ in range(samples):
            conn = http.client.HTTPConnection(host, port, timeout=3)
            started = time.perf_counter()
            try:
                conn.request("GET", path, headers={"Accept": "application/json,text/html"})
                response = conn.getresponse()
                body = response.read()
                latency = time.perf_counter() - started
                if response_status is None:
                    response_status = response.status
                    payload_bytes = len(body)
                if response.status < 200 or response.status >= 400:
                    return {"status": "PARTIAL", "reason": f"HTTP_{response.status}", "base_url": base_url, "endpoint": path}
                latencies.append(latency)
            finally:
                conn.close()
        result["endpoints"][name] = {
            "path": path,
            "http_status": response_status,
            "p50_ms": percentile(latencies, 0.50) * 1000,
            "p95_ms": percentile(latencies, 0.95) * 1000,
            "payload_bytes": payload_bytes,
            "cache_state": "WARM_LOCAL_PROCESS_CACHE_NOT_CONTROLLED",
        }
    return result


def main() -> None:
    process = psutil.Process()
    started = time.perf_counter()
    cpu_started = time.process_time()
    schema_apply = apply()
    migration_check_seconds = time.perf_counter() - started
    cpu_seconds = time.process_time() - cpu_started
    rebuild = fresh_schema_rebuild_probe()
    sample = pg_rollback_probe()
    current = process.memory_info()
    report = {
        "contract_id": "V4_PHASE0_PERFORMANCE_BASELINE_R2",
        "governing_contract": "DA-MSR-V4.2.2-CODEX-REV2 §74",
        "measurement_boundary": "No daily pipeline/scanner run, no external request, no source overlap rerun; DB write probe rolled back.",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "hardware": {"logical_cpu_count": psutil.cpu_count(), "physical_memory_bytes": psutil.virtual_memory().total, "platform": __import__("platform").platform()},
        "dataset_identity": {"database": "market_research", "database_size_before_probe_bytes": sample["database_size_before_bytes"], "database_size_after_probe_bytes": sample["database_size_after_bytes"], "v4_runtime_row_count": v4_runtime_row_count()},
        "schema_migration_ledger_check": {"status": schema_apply["status"], "elapsed_seconds": migration_check_seconds, "process_cpu_seconds": cpu_seconds, "migrations": schema_apply["migrations"], "note": "this measures version/hash verification and transaction setup, not a fresh-database rebuild"},
        "fresh_schema_rebuild": rebuild,
        "postgres_write_read_probe": sample,
        "legacy_api_ui_reference": local_http_probe(os.environ.get("V4_PHASE0_LOCAL_API", "http://127.0.0.1:8765")),
        "phase0_test_suite_metrics": {"status": "RECORDED_SEPARATELY_FROM_TEST_RECEIPT", "process_rss_bytes_after_probe": current.rss, "process_peak_working_set_bytes": getattr(current, "peak_wset", None)},
        "not_implemented_or_not_measured": {
            "daily_pipeline_wall_time": "NOT_IMPLEMENTED_FOR_V4",
            "factor_compute_time": "NOT_IMPLEMENTED_FOR_V4",
            "sector_stage_time": "NOT_IMPLEMENTED_FOR_V4",
            "radar_build_time": "NOT_IMPLEMENTED_FOR_V4",
            "focus_time": "NOT_IMPLEMENTED_FOR_V4",
            "v4_full_api_and_homepage": "NOT_IMPLEMENTED_FOR_V4",
            "00D_overlap_runtime": "NOT_MEASURED_R2_PROHIBITS_RERUN",
        },
        "claims": "Measurements are diagnostic samples only; no SLA, benchmark coverage threshold, quote-age threshold, or storage-layout decision is inferred.",
    }
    path = Path("reports/v4_phase0/V4_PHASE0_PERFORMANCE_BASELINE_R2.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    print(json.dumps({"status": "RECORDED", "report": str(path.resolve()), "api_status": report["legacy_api_ui_reference"]["status"], "db_probe": sample}, ensure_ascii=False))


if __name__ == "__main__":
    main()
