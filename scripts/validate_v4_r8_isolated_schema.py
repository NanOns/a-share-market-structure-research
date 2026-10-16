"""Apply V4 migrations 001-039 only to a pre-provisioned isolated PG database.

This utility never provisions or starts PostgreSQL and never resolves
WORKBENCH_PG_DSN/V4_NATIVE_PG_DSN. It is intentionally not an application
migration command. Before use, the operator must independently authorize an
isolated database and set both explicit environment variables documented in
the module's --help output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
MIGRATION_DIR = ROOT / "src/workbench_db/migrations/v4_postgres"
ACK_VALUE = "I_AUTHORIZE_V4_R8_ISOLATED_SCHEMA_DDL"
PORT_BLOCKLIST = {5432, 28765, 28766}


def migration_version(path: Path) -> str:
    # Match the existing canonical IDs where defined. Other filenames receive
    # deterministic test-only IDs; this runner is not the production ledger.
    from scripts.apply_v4_phase0_schema import VERSIONS

    return VERSIONS.get(path.name, "V4_R8_ISOLATED_" + path.stem.upper())


def migrations() -> list[tuple[Path, str, str]]:
    result = []
    for path in sorted(MIGRATION_DIR.glob("*.sql")):
        raw = path.read_bytes()
        result.append((path, migration_version(path), hashlib.sha256(raw).hexdigest()))
    if not result or result[-1][0].name != "039_tdx_package_row_count_authority_r1.sql":
        raise RuntimeError("V4_R8_MIGRATION_SET_INCOMPLETE")
    return result


def _target_from_environment():
    from psycopg.conninfo import conninfo_to_dict

    if os.environ.get("V4_R8_ISOLATED_PG_ACK") != ACK_VALUE:
        raise RuntimeError("EXPLICIT_ISOLATED_DDL_ACK_REQUIRED")
    dsn = os.environ.get("V4_R8_ISOLATED_PG_DSN", "").strip()
    if not dsn:
        raise RuntimeError("V4_R8_ISOLATED_PG_DSN_REQUIRED")
    info = conninfo_to_dict(dsn)
    host = info.get("host", "")
    port = int(info.get("port", "5432"))
    dbname = info.get("dbname", "")
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("ISOLATED_DATABASE_MUST_BE_LOOPBACK")
    if port in PORT_BLOCKLIST:
        raise RuntimeError("DATABASE_PORT_BLOCKED_FOR_ISOLATED_DDL")
    if not dbname.startswith("v4_r8_validation_") or dbname == "market_research":
        raise RuntimeError("ISOLATED_DATABASE_NAME_REQUIRED")
    return dsn, dbname, port


def _assert_target(pg, expected_db: str, expected_port: int) -> dict:
    identity = pg.execute(
        """SELECT current_database(), inet_server_addr()::text,
                  inet_server_port(), current_setting('transaction_read_only'),
                  current_user, r.rolsuper
             FROM pg_roles r WHERE r.rolname=current_user"""
    ).fetchone()
    db, addr, port, read_only, role, is_superuser = identity
    if (db != expected_db or db == "market_research" or port != expected_port
            or addr not in {"127.0.0.1", "::1"} or read_only != "off" or not is_superuser):
        raise RuntimeError("ISOLATED_DATABASE_IDENTITY_OR_WRITE_MODE_MISMATCH")
    return {"database": db, "server_addr": addr, "port": port, "role": role,
            "transaction_read_only": read_only, "role_is_superuser": is_superuser}


def _assert_empty_or_replayable(pg) -> None:
    schemas = pg.execute(
        "SELECT schema_name FROM information_schema.schemata "
        "WHERE schema_name IN ('v4','v4_meta') ORDER BY schema_name"
    ).fetchall()
    if schemas not in ([], [("v4",), ("v4_meta",)]):
        raise RuntimeError("ISOLATED_SCHEMA_PARTIAL_STATE")
    if schemas:
        exists = pg.execute(
            "SELECT to_regclass('v4_meta.schema_migrations')"
        ).fetchone()[0]
        if exists is None:
            raise RuntimeError("ISOLATED_SCHEMA_LEDGER_MISSING")


def apply_and_verify(pg) -> dict:
    files = migrations()
    applied, skipped = [], []
    # A single transaction makes a failed full-chain build leave no partial
    # V4 schema behind. This function must only be called after identity checks.
    with pg.transaction():
        _assert_empty_or_replayable(pg)
        for path, version, checksum in files:
            ledger = pg.execute("SELECT checksum_sha256 FROM v4_meta.schema_migrations WHERE version=%s",
                                (version,)).fetchone() if pg.execute(
                                    "SELECT to_regclass('v4_meta.schema_migrations')"
                                ).fetchone()[0] else None
            if ledger:
                if ledger[0].strip() != checksum:
                    raise RuntimeError("MIGRATION_LEDGER_CHECKSUM_CONFLICT:" + version)
                skipped.append(version)
                continue
            pg.execute(path.read_text(encoding="utf-8"))
            pg.execute(
                "INSERT INTO v4_meta.schema_migrations(version,checksum_sha256,applied_at,contract_id) "
                "VALUES (%s,%s,clock_timestamp(),%s)",
                (version, checksum, version),
            )
            applied.append(version)

        required = {
            "v4.source_revisions": {"source_package_id", "source_package_source_key", "source_fact_digest"},
            "v4.publications": {"revision_no", "source_manifest_contract_id"},
            "v4.publication_consumed_sources": {"publication_id", "source_key", "source_revision_id", "digest"},
            "v4.daily_core_result_snapshots": {"publication_id", "publication_revision", "trade_date", "result_sha256"},
            "v4.daily_core_result_rows": {"publication_id", "publication_revision", "security_id", "source_revision_id"},
        }
        for relation, columns in required.items():
            schema, table = relation.split(".")
            actual = {row[0] for row in pg.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s",
                (schema, table),
            ).fetchall()}
            if not columns <= actual:
                raise RuntimeError("REQUIRED_SCHEMA_COLUMNS_MISSING:" + relation)
        trigger_rows = pg.execute(
            """SELECT tgname, condeferrable, condeferred
                 FROM pg_trigger t JOIN pg_constraint c ON c.oid=t.tgconstraint
                WHERE NOT t.tgisinternal AND tgname IN (
                    'accepted_package_requires_fact_set',
                    'daily_core_result_snapshot_rowset_guard',
                    'accepted_publication_requires_core_result')
                ORDER BY tgname"""
        ).fetchall()
        if len(trigger_rows) != 3 or any(not deferred or not initially_deferred
                                         for _, deferred, initially_deferred in trigger_rows):
            raise RuntimeError("DEFERRED_CONSTRAINT_TRIGGER_CATALOG_MISMATCH")
        ledger_rows = pg.execute(
            "SELECT version,checksum_sha256 FROM v4_meta.schema_migrations ORDER BY version"
        ).fetchall()
        wanted = {version: checksum for _, version, checksum in files}
        actual = {version: checksum.strip() for version, checksum in ledger_rows}
        if (len(actual) != len(wanted)
                or any(actual.get(version) != checksum for version, checksum in wanted.items())):
            raise RuntimeError("MIGRATION_LEDGER_READBACK_MISMATCH")
    return {"status": "DDL_CHAIN_VERIFIED", "migration_file_count": len(files),
            "applied": applied, "already_applied": skipped,
            "deferred_constraint_triggers": trigger_rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true", help="list the ordered migration set; performs no database access")
    parser.add_argument("--apply", action="store_true", help="apply 001-037 to the explicitly acknowledged isolated database")
    args = parser.parse_args()
    if args.plan == args.apply:
        parser.error("choose exactly one of --plan or --apply")
    if args.plan:
        print(json.dumps([{"file": path.name, "version": version, "sha256": checksum}
                          for path, version, checksum in migrations()], indent=2))
        return 0

    dsn, dbname, port = _target_from_environment()
    import psycopg

    with psycopg.connect(dsn) as pg:
        identity = _assert_target(pg, dbname, port)
        result = apply_and_verify(pg)
    print(json.dumps({"identity": identity, **result}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
