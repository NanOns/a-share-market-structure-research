"""Replay V4-06 R1/R2 migrations and rollback in a disposable PostgreSQL 18 cluster."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile

import psycopg
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_v4_06_migration_acceptance import _accepted_core_fixture, _insert_publication, pg_bin
from scripts.run_v4_05_r4_1_postgres_ledger import migration_receipt

MIGRATION_013 = ROOT / "src/workbench_db/migrations/v4_postgres/013_v4_06_stock_profile_enrichments.sql"
MIGRATION_014 = ROOT / "src/workbench_db/migrations/v4_postgres/014_v4_06_turnover_contract_semantics_r2.sql"
ROLLBACK_014 = ROOT / "src/workbench_db/migrations/v4_postgres/rollback/014_v4_06_turnover_contract_semantics_r2.sql"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _run(args: list[str]) -> subprocess.CompletedProcess:
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {args[0]}\n{result.stdout}\n{result.stderr}")
    return result


def _manifest(pg: psycopg.Connection, publication: str, revision: int, *, strict: int, soft: int) -> None:
    pg.execute(
        """insert into v4.supplemental_enrichment_manifests(
             publication_id,enrichment_revision,provider,source_contract_id,field_map_version,parameter_digest,
             observed_at,ingested_at,provider_asof,security_count,strict_bound_count,soft_bound_count,
             unavailable_count,source_revision_set_digest,logical_digest)
           values (%s,%s,'BAOSTOCK','BAOSTOCK_SUPPLEMENTAL_SOURCE_V1','BAOSTOCK_FIELD_MAP_V1.1',%s,
                   '2026-09-29T00:00:00Z','2026-09-29T00:00:01Z','2026-09-28',1,%s,%s,0,%s,%s)""",
        (publication, revision, "c" * 64, strict, soft, "d" * 64, "f" * 64),
    )


def _insert_semantic_row(pg: psycopg.Connection, publication: str, security: str, revision: int,
                         *, percentile: float, state: str, alias: str) -> None:
    note = {
        "contract_id": "SUPPLEMENTAL_EXTENSION_NOTE_V1", "contract_version": "1.0.0",
        "producer": "V4_06_SUPPLEMENTAL_ENRICHMENT", "produced_at_utc": "2026-09-29T00:00:00Z",
        "source_revision_id": f"R2_PG_FIXTURE:{revision}", "source_digest": "1" * 64,
        "state": "UNKNOWN_DATA", "reason_codes": ["CORE_EXTENSION_FACT_UNAVAILABLE"], "core_extension_fact": None,
        "supplemental_observation": {"turnover_state": state, "turnover_pct60": percentile,
                                     "relationship": "SIDE_BY_SIDE_ANNOTATION_ONLY"},
        "core_effect": "NONE", "prewatch_effect": "NONE", "base_seed_eligibility_effect": "NONE",
        "maturity_effect": "NONE", "focus_activation_effect": "NONE",
    }
    pg.execute(
        """insert into v4.stock_profile_enrichments(
             publication_id,security_id,enrichment_revision,provider,trade_date,query_identity,source_contract_id,
             source_contract_version,field_map_version,raw_source_value,raw_source_unit,turnover_rate,
             turnover_ma5,turnover_median20,turnover_ratio20,turnover_pct5,turnover_pct20,turnover_pct60,
             turnover_delta3,turnover_state,turnover_context,supplemental_participation_context,
             supplemental_extension_note,provider_asof,binding_quality,quality_codes,source_revision_id,
             source_digest,created_at)
           values (%s,%s,%s,'BAOSTOCK','2026-09-28',%s,'BAOSTOCK_SUPPLEMENTAL_SOURCE_V1','1.1.0',
             'BAOSTOCK_FIELD_MAP_V1.1','1.25','PERCENT_POINTS',0.0125,0.01,0.01,1.25,%s,%s,%s,0,
             %s,%s,%s,%s,'2026-09-28','BOUND_STRICT','[]'::jsonb,%s,%s,'2026-09-29T00:00:00Z')""",
        (publication, security, revision,
         Jsonb({"provider_code": "sh.600000", "frequency": "d", "start_date": "2026-09-28",
                "end_date": "2026-09-28", "adjustflag": "3"}),
         percentile, percentile, percentile, state, alias,
         Jsonb({"contract_id": "TURNOVER_CONTEXT_V1", "contract_version": "2.0.0", "effect": "NONE"}),
         Jsonb(note), f"R2_PG_FIXTURE:{revision}", "1" * 64),
    )


def run_acceptance() -> dict:
    started = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    binary = pg_bin()
    root = Path(tempfile.mkdtemp(prefix="v4_06_r2_pg_")).resolve()
    data, log = root / "data", root / "postgres.log"
    port = _free_port()
    started_server = False
    receipt: dict = {
        "contract_id": "V4_06_R2_SCHEMA_MIGRATION_ACCEPTANCE_V1", "status": "FAIL",
        "started_at_utc": started, "production_connection_used": False,
        "migration_013_sha256": sha256(MIGRATION_013.read_bytes()).hexdigest(),
        "migration_014_sha256": sha256(MIGRATION_014.read_bytes()).hexdigest(),
        "checks": {}, "cleanup": {"attempted": False, "succeeded": False},
        "isolated_connection_identity": {"host": "127.0.0.1", "port": port, "cluster_root": "TEMP_PATH_REDACTED"},
    }
    try:
        _run([str(binary / "initdb.exe"), "-D", str(data), "-U", "postgres", "--encoding=UTF8",
              "--no-locale", "--auth-local=trust", "--auth-host=trust", "--no-sync"])
        pg_version = _run([str(binary / "psql.exe"), "--version"]).stdout.strip()
        server = subprocess.run([str(binary / "pg_ctl.exe"), "-D", str(data), "-l", str(log), "-o",
                                 f"-h 127.0.0.1 -p {port} -c listen_addresses=127.0.0.1", "-w", "start"],
                                cwd=ROOT, text=True, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=45)
        if server.returncode:
            raise RuntimeError("temporary PostgreSQL failed to start; see isolated postgresql.log")
        started_server = True
        dsn = f"host=127.0.0.1 port={port} dbname=postgres user=postgres connect_timeout=10"
        with psycopg.connect(dsn) as pg:
            info = pg.execute("select current_database(),current_user,inet_server_addr()::text,inet_server_port(),current_setting('server_version'),pg_is_in_recovery()").fetchone()
            if info[0] != "postgres" or info[1] != "postgres" or str(info[2]).split("/", 1)[0] != "127.0.0.1" or info[5]:
                raise AssertionError(f"isolated database identity mismatch: {info!r}")
            receipt["postgres_version"] = pg_version
            receipt["isolated_connection_identity"].update({"database": info[0], "user": info[1],
                "server_address": info[2], "server_port": info[3], "server_version": info[4], "in_recovery": info[5]})
            base = migration_receipt(pg)
            pg.execute(MIGRATION_013.read_text(encoding="utf-8"))
            checksum_013 = sha256(MIGRATION_013.read_bytes()).hexdigest()
            pg.execute("insert into v4_meta.schema_migrations(version,checksum_sha256,applied_at,contract_id) values (%s,%s,now(),%s)",
                       ("V4_06_STOCK_PROFILE_ENRICHMENTS_V1", checksum_013, "V4_06_STOCK_PROFILE_ENRICHMENTS_V1"))
            pg.execute(MIGRATION_014.read_text(encoding="utf-8"))
            checksum_014 = sha256(MIGRATION_014.read_bytes()).hexdigest()
            pg.execute("insert into v4_meta.schema_migrations(version,checksum_sha256,applied_at,contract_id) values (%s,%s,now(),%s)",
                       ("V4_06_TURNOVER_CONTRACT_SEMANTICS_R2", checksum_014, "V4_06_TURNOVER_CONTRACT_SEMANTICS_R2"))

            pg.execute("SAVEPOINT v4_06_r2_rollback_probe")
            try:
                pg.execute(ROLLBACK_014.read_text(encoding="utf-8"))
                has_note = pg.execute("select exists(select 1 from information_schema.columns where table_schema='v4' and table_name='stock_profile_enrichments' and column_name='supplemental_extension_note')").fetchone()[0]
                pct_def = pg.execute("select pg_get_constraintdef(oid) from pg_constraint where conname='stock_profile_enrichments_turnover_pct60_check'").fetchone()[0]
                if has_note or "turnover_pct60" not in pct_def or "<=" not in pct_def or "1" not in pct_def:
                    raise AssertionError("014 rollback did not restore isolated 013 schema")
            finally:
                pg.execute("ROLLBACK TO SAVEPOINT v4_06_r2_rollback_probe")
                pg.execute("RELEASE SAVEPOINT v4_06_r2_rollback_probe")

            core = _accepted_core_fixture()
            publication, _, head_before = _insert_publication(pg, core)
            _manifest(pg, publication, 1, strict=1, soft=0)
            _insert_semantic_row(pg, publication, core["security_id"], 1, percentile=100.0,
                                 state="EXTREME", alias="EXTREME")
            stored = pg.execute("select turnover_pct60,turnover_state,turnover_context from v4.stock_profile_enrichments where publication_id=%s and enrichment_revision=1", (publication,)).fetchone()
            if stored != (100.0, "EXTREME", "EXTREME"):
                raise AssertionError(f"R2 percentile/state did not persist: {stored!r}")

            range_rejected = alias_rejected = False
            for revision, percentile, state, alias, expected in (
                (2, 101.0, "EXTREME", "EXTREME", "range"),
                (3, 99.0, "EXTREME", "HIGH", "alias"),
            ):
                _manifest(pg, publication, revision, strict=1, soft=0)
                pg.execute(f"SAVEPOINT v4_06_r2_probe_{expected}")
                try:
                    _insert_semantic_row(pg, publication, core["security_id"], revision,
                                         percentile=percentile, state=state, alias=alias)
                except psycopg.errors.CheckViolation:
                    if expected == "range":
                        range_rejected = True
                    else:
                        alias_rejected = True
                finally:
                    pg.execute(f"ROLLBACK TO SAVEPOINT v4_06_r2_probe_{expected}")
                    pg.execute(f"RELEASE SAVEPOINT v4_06_r2_probe_{expected}")
            head_row = pg.execute("select trade_date::text,model_namespace_id,publication_id,state_head_id,state_logical_digest from v4.publication_heads where publication_id=%s", (publication,)).fetchone()
            head_after = {"trade_date": head_row[0], "model_namespace_id": head_row[1], "publication_id": head_row[2],
                          "state_head_id": head_row[3], "state_logical_digest": head_row[4]}
            if not range_rejected or not alias_rejected or head_before != head_after:
                raise AssertionError("R2 schema rejection or Core isolation failed")
            receipt["base_migrations"] = base
            receipt["checks"] = {
                "migration_013_preserved": checksum_013 == "6aa326f725ad98179b112be6b6f34346c5fbc70d69c4798d2259f01d3c3337e1",
                "migration_014_applied": True, "migration_014_sha256": checksum_014,
                "rollback_014_isolated": "PASS", "percentile_100_persisted": stored[0] == 100.0,
                "percentile_101_rejected": range_rejected, "turnover_context_alias_mismatch_rejected": alias_rejected,
                "accepted_core_publication_id": publication, "accepted_core_digest": core["core_logical_digest"],
                "core_publication_head_before": head_before, "core_publication_head_after": head_after,
                "core_publication_head_unchanged": head_before == head_after,
                "fixture_rows_are_synthetic": True,
            }
            receipt["status"] = "PASS"
    except Exception as exc:
        receipt["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        cleanup = {"attempted": True, "server_stopped": not started_server, "cluster_removed": False}
        if started_server:
            stopped = subprocess.run([str(binary / "pg_ctl.exe"), "-D", str(data), "-m", "immediate", "-w", "stop"],
                                     cwd=ROOT, text=True, capture_output=True)
            cleanup["server_stopped"] = stopped.returncode == 0
            if stopped.returncode:
                cleanup["stop_error"] = stopped.stderr[-2000:]
        try:
            shutil.rmtree(root)
            cleanup["cluster_removed"] = not root.exists()
        except OSError as exc:
            cleanup["cleanup_error"] = str(exc)
        cleanup["succeeded"] = cleanup["server_stopped"] and cleanup["cluster_removed"]
        receipt["cleanup"] = cleanup
        if not cleanup["succeeded"]:
            receipt["status"] = "FAIL"
        receipt["finished_at_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return receipt


if __name__ == "__main__":
    result = run_acceptance()
    output = ROOT / "reports/v4_06/V4_06_R2_SCHEMA_MIGRATION_RECEIPT.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if result.get("status") != "PASS":
        raise SystemExit(1)
