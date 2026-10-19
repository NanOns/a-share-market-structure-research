"""Remove one legacy research schema only after complete v4 parity proof."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import psycopg
from psycopg import sql


TABLES = {
    "snapshot": {"objects", "aliases", "members", "metadata"},
    "series": {"objects", "aliases", "members", "metadata", "bars"},
    "journal": {"objects", "aliases", "members", "metadata", "days", "day_inputs"},
}


def cleanup(dsn: str, *, apply: bool) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.migrate_v4_single_schema_research_r1 import table_digest, central_digest

    outcomes = []
    with psycopg.connect(dsn, connect_timeout=5) as pg:
        pg.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ" + (", READ WRITE" if apply else ", READ ONLY"))
        identity = pg.execute("""SELECT current_database(),inet_server_addr()::text,
            inet_server_port(),current_user""").fetchone()
        if identity[:3] != ("market_research", "127.0.0.1/32", 5432):
            raise RuntimeError("V4_RESEARCH_CLEANUP_DATABASE_IDENTITY_MISMATCH")
        pg.execute("SET LOCAL statement_timeout='180s'")
        pg.execute("SET LOCAL lock_timeout='5s'")
        schemas = [row[0] for row in pg.execute("""SELECT nspname FROM pg_namespace
            WHERE nspname LIKE 'v4_research_%' ORDER BY nspname""").fetchall()]
        for source in schemas:
            if not re.fullmatch(r"v4_research_[a-f0-9]{24}", source):
                raise RuntimeError("V4_RESEARCH_CLEANUP_SOURCE_INVALID:" + source)
            with pg.transaction():
                pg.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                           ("V4_RESEARCH_SCHEMA_CLEANUP_R1:" + source,))
                identity_rows = pg.execute(sql.SQL("""SELECT digest,contract_id,descriptor
                    FROM {}.snapshot_identity""").format(sql.Identifier(source))).fetchall()
                if len(identity_rows) != 1:
                    raise RuntimeError("V4_RESEARCH_DESCRIPTOR_CARDINALITY:" + source)
                legacy_digest, contract_id, descriptor_text = identity_rows[0]
                raw_descriptor = descriptor_text.encode("utf-8")
                descriptor_sha = hashlib.sha256(raw_descriptor).hexdigest()
                descriptor = json.loads(descriptor_text)
                release_id = descriptor.get("release_id")
                kind = descriptor.get("content_manifest", {}).get("storage_kind")
                if (contract_id != "V4_PG_RESEARCH_SNAPSHOT_R2"
                        or descriptor.get("contract_id") != contract_id
                        or descriptor.get("schema") != source
                        or descriptor.get("logical_digest") != legacy_digest
                        or kind not in TABLES
                        or not isinstance(release_id, str)):
                    raise RuntimeError("V4_RESEARCH_DESCRIPTOR_IDENTITY_INVALID:" + source)
                expected_data_tables = set(descriptor["content_manifest"].get("tables", {}))
                if expected_data_tables != TABLES[kind]:
                    raise RuntimeError("V4_RESEARCH_DESCRIPTOR_TABLE_SET_INVALID:" + source)

                source_relations = pg.execute("""SELECT c.relname,c.relkind FROM pg_class c
                    JOIN pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname=%s ORDER BY c.relname""", (source,)).fetchall()
                relation_tables = {name for name, relkind in source_relations if relkind == "r"}
                if relation_tables != expected_data_tables | {"snapshot_identity"}:
                    raise RuntimeError("V4_RESEARCH_UNEXPECTED_RELATIONS:" + source)
                if any(kind not in ("r", "i", "S") for _name, kind in source_relations):
                    raise RuntimeError("V4_RESEARCH_UNEXPECTED_RELATION_KIND:" + source)
                routines = pg.execute("""SELECT p.proname,pg_get_function_identity_arguments(p.oid),p.prokind
                    FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                    WHERE n.nspname=%s ORDER BY p.proname""", (source,)).fetchall()
                if routines != [("reject_snapshot_mutation", "", "f")]:
                    raise RuntimeError("V4_RESEARCH_UNEXPECTED_ROUTINES:" + source)

                stored = pg.execute("""SELECT storage_kind,contract_id,t0,source_schema,legacy_digest,
                    original_descriptor,original_descriptor_sha256,sealed
                    FROM v4.research_releases WHERE release_id=%s""", (release_id,)).fetchall()
                if len(stored) != 1:
                    raise RuntimeError("V4_RESEARCH_CANONICAL_RELEASE_MISSING:" + source)
                (stored_kind, stored_contract, t0, stored_source, stored_digest,
                 stored_raw, stored_sha, sealed) = stored[0]
                if (stored_kind, stored_contract, stored_source, stored_digest, bytes(stored_raw),
                        str(stored_sha).strip(), sealed) != (
                        kind, contract_id, source, legacy_digest, raw_descriptor, descriptor_sha, True):
                    raise RuntimeError("V4_RESEARCH_ORIGINAL_DESCRIPTOR_PARITY_FAILED:" + source)
                if t0.isoformat() != descriptor.get("T0"):
                    raise RuntimeError("V4_RESEARCH_T0_PARITY_FAILED:" + source)

                source_manifest = {}
                for table in sorted(expected_data_tables):
                    source_manifest[table] = table_digest(pg, source, table, kind)
                expected_manifest = descriptor["content_manifest"]["tables"]
                for table, (count, digest) in source_manifest.items():
                    if expected_manifest[table].get("rows") != count or expected_manifest[table].get("digest") != digest:
                        raise RuntimeError("V4_RESEARCH_SOURCE_DIGEST_FAILED:" + source + "." + table)
                    relation, columns = __import__(
                        "workbench_db.v4_research_release_pg_r1", fromlist=["TABLE_RELATIONS"]
                    ).TABLE_RELATIONS[table]
                    target_count, target_digest = central_digest(pg, relation, release_id, columns, table)
                    if (count, digest) != (target_count, target_digest):
                        raise RuntimeError("V4_RESEARCH_TARGET_PARITY_FAILED:" + source + "." + table)
                receipts = pg.execute("""SELECT source_table,canonical_relation,canonical_version,
                    original_sha256,verification FROM v4.legacy_schema_migration_map
                    WHERE source_schema=%s AND legacy_identity=%s ORDER BY source_table""",
                    (source, f"{contract_id}:{release_id}:{kind}")).fetchall()
                if len(receipts) != len(expected_data_tables):
                    raise RuntimeError("V4_RESEARCH_MIGRATION_RECEIPT_COUNT_FAILED:" + source)
                for table, relation, version, source_sha, proof in receipts:
                    expected_relation = __import__(
                        "workbench_db.v4_research_release_pg_r1", fromlist=["TABLE_RELATIONS"]
                    ).TABLE_RELATIONS[table][0]
                    count, expected_sha = source_manifest[table]
                    if (table not in expected_data_tables or relation != "v4." + expected_relation
                            or version != release_id or str(source_sha).strip() != expected_sha
                            or proof.get("status") != "VERIFIED"
                            or proof.get("source_rows") != count or proof.get("target_rows") != count
                            or proof.get("source_digest") != expected_sha
                            or proof.get("target_digest") != expected_sha):
                        raise RuntimeError("V4_RESEARCH_MIGRATION_RECEIPT_INVALID:" + source)

                if apply:
                    for table in sorted(relation_tables):
                        pg.execute(sql.SQL("DROP TABLE {}.{} RESTRICT").format(
                            sql.Identifier(source), sql.Identifier(table)))
                    pg.execute(sql.SQL("DROP FUNCTION {}.reject_snapshot_mutation() RESTRICT")
                               .format(sql.Identifier(source)))
                    pg.execute(sql.SQL("DROP SCHEMA {} RESTRICT").format(sql.Identifier(source)))
                outcomes.append({"source_schema": source, "release_id": release_id,
                    "storage_kind": kind, "status": "DROP_RESTRICT_SUCCESS" if apply else "VERIFIED_CLEANUP_ELIGIBLE",
                    "tables": {table: {"rows": count, "sha256": digest}
                               for table, (count, digest) in source_manifest.items()},
                    "original_descriptor_sha256": descriptor_sha})
    return {"status": "CLEANED", "database": identity, "schemas": outcomes}


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, "src")
    from workbench_db.v4_native import configured_dsn
    print(json.dumps(cleanup(configured_dsn(), apply=args.apply), ensure_ascii=False,
                     sort_keys=True, default=str))


if __name__ == "__main__":
    main()
