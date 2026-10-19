"""Remove only the verified, fully copied V4 migration-ledger schema."""
from __future__ import annotations

import argparse
import sys

import psycopg


def cleanup(dsn: str) -> dict:
    with psycopg.connect(dsn, connect_timeout=5) as pg:
        identity = pg.execute("""SELECT current_database(), inet_server_addr()::text,
            inet_server_port(), current_user""").fetchone()
        if identity[:3] != ("market_research", "127.0.0.1/32", 5432):
            raise RuntimeError("V4_META_CLEANUP_DATABASE_IDENTITY_MISMATCH")
        pg.execute("SET LOCAL statement_timeout='10s'")
        pg.execute("SET LOCAL lock_timeout='3s'")
        with pg.transaction():
            if not pg.execute("SELECT to_regnamespace('v4_meta')").fetchone()[0]:
                return {"status": "ALREADY_ABSENT", "database": identity}
            objects = pg.execute("""SELECT c.relname,c.relkind
                FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='v4_meta' ORDER BY c.relname""").fetchall()
            if objects != [("schema_migrations", "r"), ("schema_migrations_pkey", "i")]:
                raise RuntimeError("V4_META_CLEANUP_UNEXPECTED_OBJECTS")
            old_count = pg.execute("SELECT count(*) FROM v4_meta.schema_migrations").fetchone()[0]
            new_count = pg.execute("SELECT count(*) FROM v4.schema_migrations").fetchone()[0]
            mismatch = pg.execute("""SELECT count(*) FROM v4_meta.schema_migrations old
                LEFT JOIN v4.schema_migrations new USING(version)
                WHERE new.version IS NULL OR new.checksum_sha256<>old.checksum_sha256
                   OR new.contract_id<>old.contract_id OR new.applied_at<>old.applied_at""").fetchone()[0]
            if mismatch or new_count < old_count:
                raise RuntimeError("V4_META_CLEANUP_LEDGER_PARITY_FAILED")
            pg.execute("DROP TABLE v4_meta.schema_migrations")
            pg.execute("DROP SCHEMA v4_meta RESTRICT")
            if pg.execute("SELECT to_regnamespace('v4_meta')").fetchone()[0]:
                raise RuntimeError("V4_META_CLEANUP_SCHEMA_REMAINS")
            return {"status": "DROPPED_RESTRICT_AFTER_LEDGER_PARITY", "database": identity,
                    "source_rows": old_count, "canonical_rows": new_count,
                    "schema_objects_before": objects}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        raise SystemExit("Refusing database writes without --apply")
    sys.path.insert(0, "src")
    from workbench_db.v4_native import configured_dsn
    import json
    print(json.dumps(cleanup(configured_dsn()), ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
