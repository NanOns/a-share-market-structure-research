"""Move the last legacy Forward relation in-place into a fixed v4 archive table.

This preserves the exact already-ingested PG rows without importing additional
historical source files or activating them as SourceIngress bindings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys

import psycopg
from psycopg import sql

SOURCE = "v4_forward_213e535c50ad7135"
FACTS = "forward_facts"
ARCHIVE = "forward_legacy_evidence_r1"
SOURCE_RECEIPT = "forward_migration"
ARCHIVE_RECEIPT = "forward_legacy_migration_r1"
ARCHIVE_NAMESPACE = "LEGACY_ARCHIVE:" + SOURCE

INDEX_RENAMES = {
    "ix_historical_source_id_r1": "ix_forward_legacy_evidence_source_id_r1",
    "ix_historical_source_path_sha_r1": "ix_forward_legacy_evidence_path_sha_r1",
}


def _row_digest(pg, relation: str) -> str:
    hasher = hashlib.sha256()
    query = sql.SQL("SELECT kind,fact_key,payload_sha256,source_sha256,ordinal FROM {}.{}").format(
        sql.Identifier("v4"), sql.Identifier(relation)
    )
    with pg.cursor(name="forward_legacy_archive_metadata_r1") as cursor:
        cursor.itersize = 256
        cursor.execute(query)
        for kind, key, payload_sha, source_sha, ordinal in cursor:
            row = (kind, key, payload_sha.strip(), source_sha, ordinal)
            raw = json.dumps(row, ensure_ascii=False, separators=(",", ":"), allow_nan=False, default=str).encode()
            hasher.update(len(raw).to_bytes(8, "big"))
            hasher.update(raw)
    return hasher.hexdigest()


def _source_digest(pg) -> str:
    hasher = hashlib.sha256()
    query = sql.SQL("SELECT kind,fact_key,payload_sha256,source_sha256,ordinal FROM {}.{}").format(
        sql.Identifier(SOURCE), sql.Identifier(FACTS)
    )
    with pg.cursor(name="forward_legacy_source_metadata_r1") as cursor:
        cursor.itersize = 256
        cursor.execute(query)
        for kind, key, payload_sha, source_sha, ordinal in cursor:
            row = (kind, key, payload_sha.strip(), source_sha, ordinal)
            raw = json.dumps(row, ensure_ascii=False, separators=(",", ":"), allow_nan=False, default=str).encode()
            hasher.update(len(raw).to_bytes(8, "big"))
            hasher.update(raw)
    return hasher.hexdigest()


def _catalog_snapshot(pg, schema: str, table: str) -> dict:
    relation = pg.execute(
        """SELECT c.oid::bigint,pg_total_relation_size(c.oid)::bigint,pg_relation_size(c.oid)::bigint
           FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname=%s AND c.relname=%s AND c.relkind='r'""",
        (schema, table),
    ).fetchone()
    if not relation:
        raise RuntimeError("V4_FORWARD_ARCHIVE_RELATION_MISSING:" + schema + "." + table)
    count = pg.execute(sql.SQL("SELECT count(*) FROM {}.{}").format(sql.Identifier(schema), sql.Identifier(table))).fetchone()[0]
    return dict(oid=relation[0], total_bytes=relation[1], main_bytes=relation[2], row_count=count)


def archive(dsn: str, *, apply: bool) -> dict:
    with psycopg.connect(dsn, connect_timeout=5, autocommit=True) as pg:
        identity = pg.execute(
            "SELECT current_database(),inet_server_addr()::text,inet_server_port(),current_user"
        ).fetchone()
        if identity[:3] != ("market_research", "127.0.0.1/32", 5432):
            raise RuntimeError("V4_FORWARD_ARCHIVE_DATABASE_IDENTITY_MISMATCH")
        pg.execute("SET statement_timeout='180s'")
        pg.execute("SET lock_timeout='5s'")
        pg.execute("SELECT pg_advisory_lock(hashtextextended(%s,0))", ("V4_FORWARD_LEGACY_ARCHIVE_R1",))
        try:
            with pg.transaction():
                pg.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ" + (", READ WRITE" if apply else ", READ ONLY"))
                schemas = pg.execute(
                    "SELECT nspname FROM pg_namespace WHERE left(nspname,3)='v4_' ORDER BY nspname"
                ).fetchall()
                if schemas != [(SOURCE,)]:
                    raise RuntimeError("V4_FORWARD_ARCHIVE_UNEXPECTED_LEGACY_SCHEMAS:" + repr(schemas))
                tables = {row[0] for row in pg.execute("SELECT tablename FROM pg_tables WHERE schemaname=%s", (SOURCE,))}
                if tables != {FACTS, SOURCE_RECEIPT}:
                    raise RuntimeError("V4_FORWARD_ARCHIVE_TABLE_SET_MISMATCH:" + repr(tables))
                routines = pg.execute(
                    """SELECT p.proname,pg_get_function_identity_arguments(p.oid),p.prokind
                       FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                       WHERE n.nspname=%s ORDER BY 1""",
                    (SOURCE,),
                ).fetchall()
                if routines != [("reject_forward_fact_mutation", "", "f")]:
                    raise RuntimeError("V4_FORWARD_ARCHIVE_ROUTINE_SET_MISMATCH:" + repr(routines))
                triggers = pg.execute(
                    """SELECT t.tgname,pg_get_triggerdef(t.oid)
                       FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
                       JOIN pg_namespace n ON n.oid=c.relnamespace
                       WHERE n.nspname=%s AND NOT t.tgisinternal ORDER BY t.tgname""",
                    (SOURCE,),
                ).fetchall()
                if len(triggers) != 1 or triggers[0][0] != "forward_append_only":
                    raise RuntimeError("V4_FORWARD_ARCHIVE_TRIGGER_SET_MISMATCH:" + repr(triggers))
                source_catalog = _catalog_snapshot(pg, SOURCE, FACTS)
                source_receipt_catalog = _catalog_snapshot(pg, SOURCE, SOURCE_RECEIPT)
                source_digest = _source_digest(pg)
                mapped = pg.execute(
                    """SELECT count(*),count(*) FILTER(WHERE m.verification->>'status'='VERIFIED'),
                              count(*) FILTER(WHERE t.fact_key IS NULL OR t.payload_sha256<>m.payload_sha256
                                  OR t.source_sha256 IS DISTINCT FROM m.source_sha256)
                       FROM v4.forward_schema_migration_map_r1 m
                       LEFT JOIN v4.forward_facts t ON t.workspace_namespace=m.workspace_namespace
                         AND t.kind=m.kind AND t.fact_key=m.fact_key
                       WHERE m.source_schema=%s""",
                    (SOURCE,),
                ).fetchone()
                if mapped[0] != 390 or mapped[1] != mapped[0] or mapped[2] != 0:
                    raise RuntimeError("V4_FORWARD_ARCHIVE_ACTIVE_MAP_MISMATCH:" + repr(mapped))
                external_dependencies = pg.execute(
                    """SELECT count(*) FROM pg_depend d
                       JOIN pg_class refc ON refc.oid=d.refobjid
                       JOIN pg_namespace refn ON refn.oid=refc.relnamespace
                       JOIN pg_class depc ON depc.oid=d.objid
                       JOIN pg_namespace depn ON depn.oid=depc.relnamespace
                       WHERE refn.nspname=%s AND depn.nspname NOT IN (%s,'pg_catalog','information_schema','pg_toast')
                         AND d.deptype NOT IN ('i','a')""",
                    (SOURCE, SOURCE),
                ).fetchone()[0]
                if external_dependencies:
                    raise RuntimeError("V4_FORWARD_ARCHIVE_EXTERNAL_DEPENDENCIES:" + str(external_dependencies))
                live_queries = pg.execute(
                    """SELECT count(*) FROM pg_stat_activity WHERE datname=current_database()
                         AND pid<>pg_backend_pid() AND query ILIKE %s""",
                    ("%" + SOURCE + "%",),
                ).fetchone()[0]
                if live_queries:
                    raise RuntimeError("V4_FORWARD_ARCHIVE_LIVE_SCHEMA_QUERIES:" + str(live_queries))
                target_names = [
                    ("v4", ARCHIVE), ("v4", ARCHIVE_RECEIPT),
                    ("v4", "forward_legacy_evidence_r1_ordinal_seq"),
                    ("v4", "forward_legacy_evidence_r1_pkey"),
                    ("v4", "forward_legacy_evidence_r1_ordinal_key"),
                    ("v4", "ix_forward_legacy_evidence_source_id_r1"),
                    ("v4", "ix_forward_legacy_evidence_path_sha_r1"),
                    ("v4", "forward_legacy_migration_r1_pkey"),
                ]
                for schema, name in target_names:
                    if pg.execute("SELECT to_regclass(%s)", (schema + "." + name,)).fetchone()[0]:
                        raise RuntimeError("V4_FORWARD_ARCHIVE_TARGET_NAME_EXISTS:" + schema + "." + name)
                if pg.execute(
                    "SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='v4' AND p.proname='reject_forward_legacy_evidence_mutation_r1'"
                ).fetchone():
                    raise RuntimeError("V4_FORWARD_ARCHIVE_TARGET_ROUTINE_EXISTS")
                if not apply:
                    return dict(status="VERIFY_ONLY", database=identity, source_schema=SOURCE,
                        source_relation=source_catalog, source_receipt=source_receipt_catalog,
                        source_metadata_digest=source_digest, exact_active_map_rows=mapped[0],
                        external_dependencies=external_dependencies, live_queries=live_queries,
                        target_schema="v4", target_relation=ARCHIVE,
                        handling="IN_PLACE_ARCHIVE; NO_HISTORICAL_FILE_BINDINGS_IMPORTED")

                pg.execute(sql.SQL("ALTER TABLE {}.forward_facts RENAME CONSTRAINT forward_facts_pkey TO forward_legacy_evidence_r1_pkey").format(sql.Identifier(SOURCE)))
                pg.execute(sql.SQL("ALTER TABLE {}.forward_facts RENAME CONSTRAINT forward_facts_ordinal_key TO forward_legacy_evidence_r1_ordinal_key").format(sql.Identifier(SOURCE)))
                pg.execute(sql.SQL("ALTER INDEX {}.ix_historical_source_id_r1 RENAME TO ix_forward_legacy_evidence_source_id_r1").format(sql.Identifier(SOURCE)))
                pg.execute(sql.SQL("ALTER INDEX {}.ix_historical_source_path_sha_r1 RENAME TO ix_forward_legacy_evidence_path_sha_r1").format(sql.Identifier(SOURCE)))
                pg.execute(sql.SQL("ALTER TABLE {}.forward_migration RENAME CONSTRAINT forward_migration_pkey TO forward_legacy_migration_r1_pkey").format(sql.Identifier(SOURCE)))
                pg.execute(sql.SQL("ALTER SEQUENCE {}.forward_facts_ordinal_seq RENAME TO forward_legacy_evidence_r1_ordinal_seq").format(sql.Identifier(SOURCE)))
                pg.execute(sql.SQL("ALTER TABLE {}.forward_facts ADD COLUMN origin_schema text NOT NULL DEFAULT {}").format(
                    sql.Identifier(SOURCE), sql.Literal(SOURCE)))
                pg.execute(sql.SQL("ALTER FUNCTION {}.reject_forward_fact_mutation() SET SCHEMA v4").format(sql.Identifier(SOURCE)))
                pg.execute("ALTER FUNCTION v4.reject_forward_fact_mutation() RENAME TO reject_forward_legacy_evidence_mutation_r1")
                pg.execute(sql.SQL("ALTER TABLE {}.forward_facts RENAME TO {}").format(sql.Identifier(SOURCE), sql.Identifier(ARCHIVE)))
                pg.execute(sql.SQL("ALTER TABLE {}.{} SET SCHEMA v4").format(sql.Identifier(SOURCE), sql.Identifier(ARCHIVE)))
                pg.execute(sql.SQL("ALTER TABLE {}.forward_migration RENAME TO {}").format(sql.Identifier(SOURCE), sql.Identifier(ARCHIVE_RECEIPT)))
                pg.execute(sql.SQL("ALTER TABLE {}.{} SET SCHEMA v4").format(sql.Identifier(SOURCE), sql.Identifier(ARCHIVE_RECEIPT)))
                pg.execute(sql.SQL("COMMENT ON TABLE v4.{} IS {}").format(
                    sql.Identifier(ARCHIVE), sql.Literal(
                        "Immutable, in-place preservation of the last legacy Forward fact relation. Audit only; not a SourceIngress binding or runtime Forward store."
                    )))
                target_catalog = _catalog_snapshot(pg, "v4", ARCHIVE)
                target_digest = _row_digest(pg, ARCHIVE)
                if (target_catalog["oid"] != source_catalog["oid"]
                        or target_catalog["row_count"] != source_catalog["row_count"]
                        or target_catalog["total_bytes"] != source_catalog["total_bytes"]
                        or target_digest != source_digest):
                    raise RuntimeError("V4_FORWARD_ARCHIVE_IN_PLACE_IDENTITY_MISMATCH")
                pg.execute(sql.SQL("DROP SCHEMA {} RESTRICT").format(sql.Identifier(SOURCE)))
                post_schemas = pg.execute(
                    "SELECT nspname FROM pg_namespace WHERE left(nspname,3)='v4_' ORDER BY nspname"
                ).fetchall()
                if post_schemas:
                    raise RuntimeError("V4_FORWARD_ARCHIVE_LEGACY_SCHEMA_REMAINS:" + repr(post_schemas))
                receipt = dict(
                    migration_id="V4_FORWARD_LEGACY_EVIDENCE_ARCHIVE_R1",
                    source_schema=SOURCE,
                    source_table=FACTS,
                    source_relation_oid=source_catalog["oid"],
                    target_schema="v4",
                    target_relation=ARCHIVE,
                    target_relation_oid=target_catalog["oid"],
                    source_rows=source_catalog["row_count"],
                    target_rows=target_catalog["row_count"],
                    source_total_bytes=source_catalog["total_bytes"],
                    target_total_bytes=target_catalog["total_bytes"],
                    source_metadata_digest=source_digest,
                    target_metadata_digest=target_digest,
                    exact_active_map_rows=mapped[0],
                    excluded_historical_binding_rows_not_imported=True,
                    payload_bytes_copied=0,
                    verification="SAME_RELATION_OID_BYTES_ROWCOUNT_AND_METADATA_DIGEST",
                    status="IN_PLACE_ARCHIVE_AND_SCHEMA_RETIRED_RESTRICT",
                )
                pg.execute("INSERT INTO v4.forward_migration_r1(workspace_namespace,receipt) VALUES(%s,%s)",
                           (ARCHIVE_NAMESPACE, json.dumps(receipt)))
                return dict(status="ARCHIVED_AND_SCHEMA_RETIRED", database=identity,
                    source_schema=SOURCE, target_relation="v4." + ARCHIVE,
                    relation_oid=target_catalog["oid"], rows=target_catalog["row_count"],
                    total_bytes=target_catalog["total_bytes"], metadata_digest=target_digest,
                    payload_bytes_copied=0, active_map_rows=mapped[0], drop_schema="DROP_RESTRICT_SUCCESS")
        finally:
            pg.execute("SELECT pg_advisory_unlock(hashtextextended(%s,0))", ("V4_FORWARD_LEGACY_ARCHIVE_R1",))


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, "src")
    from workbench_db.v4_native import configured_dsn, configured_reader_dsn
    dsn = configured_dsn() if args.apply else configured_reader_dsn()
    print(json.dumps(archive(dsn, apply=args.apply), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
