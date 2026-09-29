"""Exercise the V4-06 append-only schema in a disposable PostgreSQL cluster."""
from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
import gzip
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MIGRATION = ROOT / "src/workbench_db/migrations/v4_postgres/013_v4_06_stock_profile_enrichments.sql"
ROLLBACK = ROOT / "src/workbench_db/migrations/v4_postgres/rollback/013_v4_06_stock_profile_enrichments.sql"
VERSION = "V4_06_STOCK_PROFILE_ENRICHMENTS_V1"
ACCEPTED_INPUT_ROOT = Path(os.environ.get("V4_06_ACCEPTED_INPUTS_ROOT", str(ROOT))).resolve()
ACCEPTED_LEDGER = ACCEPTED_INPUT_ROOT / "reports/v4_05/V4_05_R4_2_POSTGRES_REVISION_LEDGER_IDEMPOTENCY.json"
ACCEPTED_HEAD = ACCEPTED_INPUT_ROOT / "data/v4/V4_05_ACCEPTED_HEAD.json"
CORE_FACTORS = ACCEPTED_INPUT_ROOT / "reports/v4_05/staging/V4_05_R4_1_FULL_SCOPE_FACTORS.jsonl.gz"


def pg_bin() -> Path:
    candidates = [Path(os.environ[key]) for key in ("V4_POSTGRES_BIN", "PG_BIN") if os.environ.get(key)]
    candidates.extend((Path(r"E:\Postgres\bin"), Path(r"C:\Program Files\PostgreSQL\18\bin")))
    for candidate in candidates:
        if all((candidate / f"{name}.exe").is_file() for name in ("initdb", "pg_ctl", "psql")):
            return candidate
    raise FileNotFoundError("PostgreSQL 18 binaries unavailable")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def run(args: list[str], *, capture: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=capture)
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {args[0]}\n{result.stdout}\n{result.stderr}")
    return result


def _accepted_core_fixture() -> dict:
    ledger = json.loads(ACCEPTED_LEDGER.read_text(encoding="utf-8"))
    head = json.loads(ACCEPTED_HEAD.read_text(encoding="utf-8"))
    details = ledger["cases"]
    publication = ledger["actual_publication_head"]["publication_id"]
    revision_rows = details["revision_identities"]
    final = next(item for item in revision_rows if item["publication_id"] == publication)
    if (head["accepted_artifacts"]["core_profile"]["logical_digest"]
            != ledger["actual_state_head"]["logical_digest"]):
        raise AssertionError("accepted core profile and PostgreSQL state digest differ")
    with gzip.open(CORE_FACTORS, "rt", encoding="utf-8") as stream:
        first_factor = json.loads(stream.readline())
    return {
        "publication_id": publication, "namespace_id": details["model_namespace_id"],
        "model_contract_id": details["model_contract_id"], "publication_lineage_id": details["publication_lineage_id"],
        "market_calendar_id": details["market_calendar_id"], "state_head_id": ledger["actual_state_head"]["state_head_id"],
        "core_logical_digest": ledger["actual_state_head"]["logical_digest"],
        "final_revision": final, "revision_rows": revision_rows,
        "security_id": first_factor["security_id"], "source_security_key": first_factor["source_security_key"],
        "trade_date": head["target_trade_date"],
    }


def _insert_publication(pg: psycopg.Connection, core: dict) -> tuple[str, str, dict]:
    namespace = core["namespace_id"]
    publication = core["publication_id"]
    lineage = core["publication_lineage_id"]
    calendar = core["market_calendar_id"]
    pg.execute(
        "insert into v4.model_namespaces(namespace_id,model_contract_id,execution_mode,namespace) values (%s,%s,'SHADOW',%s)",
        (namespace, core["model_contract_id"], namespace),
    )
    pg.execute(
        "insert into v4.market_calendar_sessions(market_calendar_id,session_no,trade_date,calendar_digest) values (%s,%s,%s,%s)",
        (calendar, date.fromisoformat(core["trade_date"]).toordinal(), core["trade_date"], "e" * 64),
    )
    for item in core["revision_rows"]:
        pg.execute(
            """insert into v4.publications(
                 publication_id,publication_lineage_id,trade_date,market_calendar_id,revision_no,status,model_namespace_id,
                 core_revision,source_manifest_sha256,computation_identity_sha256,same_day_revision_parent_id,
                 prior_session_publication_id,prior_session_state_logical_digest,prior_session_state_head,
                 prior_session_gap_reason,accepted_at)
               values (%s,%s,%s,%s,%s,'ACCEPTED',%s,%s,%s,%s,%s,null,null,null,'INITIAL_BOUNDARY',now())""",
            (item["publication_id"], lineage, core["trade_date"], calendar, item["revision_no"], namespace,
             item["core_revision"], item["source_manifest_sha256"], item["computation_identity_sha256"],
             item["same_day_revision_parent_id"]),
        )
    pg.execute(
        "insert into v4.state_heads(namespace_id,state_head_id,publication_id,logical_digest) values (%s,%s,%s,%s)",
        (namespace, core["state_head_id"], publication, core["core_logical_digest"]),
    )
    pg.execute(
        """insert into v4.publication_heads(trade_date,model_namespace_id,publication_id,state_head_id,state_logical_digest)
           values (%s,%s,%s,%s,%s)""",
        (core["trade_date"], namespace, publication, core["state_head_id"], core["core_logical_digest"]),
    )
    head = pg.execute(
        "select trade_date::text,model_namespace_id,publication_id,state_head_id,state_logical_digest from v4.publication_heads where publication_id=%s",
        (publication,),
    ).fetchone()
    return publication, namespace, {"trade_date": head[0], "model_namespace_id": head[1],
                                    "publication_id": head[2], "state_head_id": head[3],
                                    "state_logical_digest": head[4]}


def _manifest(pg: psycopg.Connection, publication: str, revision: int) -> None:
    pg.execute(
        """insert into v4.supplemental_enrichment_manifests(
            publication_id,enrichment_revision,provider,source_contract_id,field_map_version,parameter_digest,
            observed_at,ingested_at,provider_asof,security_count,strict_bound_count,soft_bound_count,
            unavailable_count,source_revision_set_digest,logical_digest)
           values (%s,%s,'BAOSTOCK','BAOSTOCK_SUPPLEMENTAL_SOURCE_V1','BAOSTOCK_FIELD_MAP_V1.1',%s,
                   '2026-09-29T00:00:00Z','2026-09-29T00:00:01Z','2026-09-28',1,0,1,0,%s,%s)""",
        (publication, revision, "c" * 64, "d" * 64, "f" * 64),
    )


def _append_with_writer(pg: psycopg.Connection, publication: str, revision: int, core_security_id: str) -> None:
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from workbench_analysis.baostock_supplemental import normalize_row
    from workbench_analysis.v4_06_supplemental import (
        PostgresSupplementalWriter, build_supplemental_row, make_manifest,
    )
    source = normalize_row("sh.600000", {
        "date": "2026-09-28", "code": "sh.600000", "close": "10.0", "volume": "1200",
        "amount": "12000.0", "turn": "1.25", "tradestatus": "1", "isST": "0",
    })
    row = build_supplemental_row(
        publication_id=publication, security_id=core_security_id, enrichment_revision=revision,
        trade_date="2026-09-28",
        query_identity={"provider_code": "sh.600000", "frequency": "d",
                        "start_date": "2026-09-28", "end_date": "2026-09-28", "adjustflag": "3"},
        binding_quality="BOUND_SOFT", source=source,
        source_revision_id=f"BAOSTOCK:ISOLATED_FIXTURE:{revision}:{core_security_id}", source_digest=source.source_digest,
        turnover_context=None, created_at="2026-09-29T00:00:00Z", provider_asof="2026-09-28",
        binding_quality_codes=("TOLERANCE_UNACCEPTED",),
    )
    manifest = make_manifest(
        publication_id=publication, enrichment_revision=revision, provider="BAOSTOCK",
        source_contract_id="BAOSTOCK_SUPPLEMENTAL_SOURCE_V1", field_map_version="BAOSTOCK_FIELD_MAP_V1.1",
        parameter_digest="c" * 64, observed_at="2026-09-29T00:00:00Z",
        ingested_at="2026-09-29T00:00:01Z", provider_asof="2026-09-28", rows=[row],
    )
    PostgresSupplementalWriter.append_revision(pg, manifest, [row])


def _row(pg: psycopg.Connection, publication: str, revision: int, security_id: str = "SEC-001") -> None:
    pg.execute(
        """insert into v4.stock_profile_enrichments(
            publication_id,security_id,enrichment_revision,provider,trade_date,query_identity,source_contract_id,
            source_contract_version,field_map_version,raw_source_value,raw_source_unit,turnover_rate,
            turnover_state,turnover_context,supplemental_participation_context,provider_asof,binding_quality,
            quality_codes,source_revision_id,source_digest)
           values (%s,%s,%s,'BAOSTOCK','2026-09-28',%s,'BAOSTOCK_SUPPLEMENTAL_SOURCE_V1','1.1.0',
                   'BAOSTOCK_FIELD_MAP_V1.1','1.25','PERCENT_POINTS',0.0125,'BOUND_SOFT','UNKNOWN',
                   '{"effect":"NONE"}'::jsonb,'2026-09-28','BOUND_SOFT','["DIAGNOSTIC_ONLY"]'::jsonb,
                   %s,%s)""",
        (publication, security_id, revision, json.dumps({"provider_code":"sh.600000","frequency":"d",
         "start_date":"2026-09-28","end_date":"2026-09-28","adjustflag":"3"}),
         f"BAOSTOCK:{revision}:{security_id}", "1" * 64),
    )


def exercise(pg: psycopg.Connection) -> dict:
    migrations = {row[0] for row in pg.execute("select version from v4_meta.schema_migrations").fetchall()}
    if VERSION not in migrations:
        sql = MIGRATION.read_text(encoding="utf-8")
        checksum = sha256(sql.encode("utf-8")).hexdigest()
        with pg.transaction():
            pg.execute(sql)
            pg.execute(
                "insert into v4_meta.schema_migrations(version,checksum_sha256,applied_at,contract_id) values (%s,%s,now(),%s)",
                (VERSION, checksum, VERSION),
            )
    checksum = sha256(MIGRATION.read_bytes()).hexdigest()
    if pg.execute("select checksum_sha256 from v4_meta.schema_migrations where version=%s", (VERSION,)).fetchone()[0].strip() != checksum:
        raise AssertionError("V4-06 migration checksum mismatch")

    # Verify the checked-in rollback only against an empty, disposable schema,
    # then roll back the rollback transaction so the write/immutability probes
    # can run against the same isolated schema.
    pg.execute("SAVEPOINT v4_06_rollback_probe")
    try:
        pg.execute(ROLLBACK.read_text(encoding="utf-8"))
        dropped = pg.execute("select to_regclass('v4.stock_profile_enrichments') is null and to_regclass('v4.supplemental_enrichment_manifests') is null").fetchone()[0]
    finally:
        pg.execute("ROLLBACK TO SAVEPOINT v4_06_rollback_probe")
        pg.execute("RELEASE SAVEPOINT v4_06_rollback_probe")
    if not dropped:
        raise AssertionError("isolated rollback did not remove V4-06 tables")

    core = _accepted_core_fixture()
    publication, _, head_before = _insert_publication(pg, core)
    _append_with_writer(pg, publication, 1, core["security_id"])
    duplicate_rejected = False
    try:
        with pg.transaction():
            _row(pg, publication, 1, core["security_id"])
    except psycopg.errors.UniqueViolation:
        duplicate_rejected = True
    if not duplicate_rejected:
        raise AssertionError("duplicate supplemental row identity was accepted")
    update_rejected = delete_rejected = False
    for statement, name in (
        ("update v4.stock_profile_enrichments set turnover_rate=0 where publication_id=%s", "update"),
        ("delete from v4.stock_profile_enrichments where publication_id=%s", "delete"),
    ):
        try:
            with pg.transaction():
                pg.execute(statement, (publication,))
        except psycopg.Error as exc:
            if exc.sqlstate != "P0001":
                raise
            if name == "update":
                update_rejected = True
            else:
                delete_rejected = True
    if not update_rejected or not delete_rejected:
        raise AssertionError("append-only mutation guard did not reject update/delete")
    _append_with_writer(pg, publication, 2, core["security_id"])
    head_after_row = pg.execute(
        "select trade_date::text,model_namespace_id,publication_id,state_head_id,state_logical_digest from v4.publication_heads where publication_id=%s",
        (publication,),
    ).fetchone()
    head_after = {"trade_date": head_after_row[0], "model_namespace_id": head_after_row[1],
                  "publication_id": head_after_row[2], "state_head_id": head_after_row[3],
                  "state_logical_digest": head_after_row[4]}
    revisions = pg.execute(
        "select enrichment_revision,count(*) from v4.stock_profile_enrichments where publication_id=%s group by enrichment_revision order by enrichment_revision",
        (publication,),
    ).fetchall()
    manifest_count = pg.execute("select count(*) from v4.supplemental_enrichment_manifests where publication_id=%s", (publication,)).fetchone()[0]
    if head_before != head_after or revisions != [(1, 1), (2, 1)] or manifest_count != 2:
        raise AssertionError("supplemental revisions changed Core head or failed append-only identity")
    return {
        "migration_version": VERSION,
        "migration_sha256": checksum,
        "isolated_rollback": "PASS",
        "duplicate_identity_rejected": duplicate_rejected,
        "update_rejected": update_rejected,
        "delete_rejected": delete_rejected,
        "same_publication_revisions": [{"revision": row[0], "rows": row[1]} for row in revisions],
        "manifest_count": manifest_count,
        "accepted_core_publication_id": publication,
        "accepted_core_profile_logical_digest": core["core_logical_digest"],
        "core_publication_head_before": head_before,
        "core_publication_head_after": head_after,
        "core_publication_head_unchanged": head_before == head_after,
        "isolated_fixture_source_is_synthetic": True,
        "production_connection_used": False,
    }


def run_acceptance() -> dict:
    started_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    bin_dir = pg_bin()
    root = Path(tempfile.mkdtemp(prefix="v4_06_pg_")).resolve()
    data, log = root / "data", root / "postgres.log"
    port = free_port()
    process_started = False
    receipt: dict = {"contract_id": "V4_06_POSTGRES_MIGRATION_ACCEPTANCE_V1", "status": "FAIL",
                     "started_at_utc": started_at,
                     "postgres_bin": str(bin_dir), "production_connection_used": False,
                     "isolated_connection_identity": {"host": "127.0.0.1", "port": port,
                                                       "cluster_root": "TEMP_PATH_REDACTED"},
                     "checks": {}, "cleanup": {"attempted": False, "succeeded": False}}
    try:
        print("V4_06_MIGRATION_INITDB", flush=True)
        run([str(bin_dir / "initdb.exe"), "-D", str(data), "-U", "postgres", "--encoding=UTF8",
             "--no-locale", "--auth-local=trust", "--auth-host=trust", "--no-sync"])
        receipt["postgres_version"] = run([str(bin_dir / "psql.exe"), "--version"]).stdout.strip()
        print(f"V4_06_MIGRATION_STARTING:{port}", flush=True)
        started = subprocess.run([str(bin_dir / "pg_ctl.exe"), "-D", str(data), "-l", str(log), "-o",
                                  f"-h 127.0.0.1 -p {port} -c listen_addresses=127.0.0.1", "-w", "start"],
                                 cwd=ROOT, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 timeout=45)
        if started.returncode:
            raise RuntimeError(started.stderr or "temporary PostgreSQL failed to start")
        process_started = True
        print(f"V4_06_MIGRATION_STARTED:{port}", flush=True)
        dsn = f"host=127.0.0.1 port={port} dbname=postgres user=postgres connect_timeout=10"
        with psycopg.connect(dsn) as pg:
            print("V4_06_MIGRATION_CONNECTED", flush=True)
            info = pg.execute("select current_database(),current_user,inet_server_addr()::text,inet_server_port(),current_setting('server_version'),pg_is_in_recovery()").fetchone()
            if info[0] != "postgres" or info[1] != "postgres" or str(info[2]).split("/", 1)[0] != "127.0.0.1" or info[5]:
                raise AssertionError(f"isolated database identity mismatch: {info!r}")
            receipt["isolated_connection_identity"].update({"database": info[0], "user": info[1],
                "server_address": info[2], "server_port": info[3], "postgres_version": info[4], "in_recovery": info[5]})
            from scripts.run_v4_05_r4_1_postgres_ledger import migration_receipt
            print("V4_06_MIGRATION_APPLYING_BASE", flush=True)
            receipt["base_migrations"] = migration_receipt(pg)
            base_tables = pg.execute("select table_name from information_schema.tables where table_schema='v4' order by table_name").fetchall()
            print(f"V4_06_BASE_TABLES:{[row[0] for row in base_tables]}", flush=True)
            print("V4_06_MIGRATION_APPLYING_STAGE", flush=True)
            receipt["checks"] = exercise(pg)
            print("V4_06_MIGRATION_STAGE_APPLIED", flush=True)
        receipt["status"] = "PASS"
    except Exception as exc:
        receipt["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        cleanup = {"attempted": True, "server_stopped": not process_started, "cluster_removed": False}
        if process_started:
            stopped = subprocess.run([str(bin_dir / "pg_ctl.exe"), "-D", str(data), "-m", "immediate", "-w", "stop"],
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
    receipt = run_acceptance()
    output = ROOT / "reports/v4_06/V4_06_SCHEMA_MIGRATION_RECEIPT.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
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
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    if receipt.get("status") != "PASS":
        raise SystemExit(1)
