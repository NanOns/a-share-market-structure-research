"""Migrate three classified Forward sources into fixed v4 rows in resumable batches."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

SOURCES = (
    "v4_forward_9c3fd7df8af41138",  # period raw/adjusted chunks
    "v4_forward_d49f600857001503",  # two dated owner bundles
    "v4_forward_f17219af1df44bb8",  # seven dated modules; R7 rows have their own fixed table
)
BATCH_ROWS = 32


def _row_hash(hasher, row):
    raw = json.dumps(row, ensure_ascii=False, separators=(",", ":"), allow_nan=False, default=str).encode()
    hasher.update(len(raw).to_bytes(8, "big"))
    hasher.update(raw)


def _r7_count(pg, source):
    if source != "v4_forward_f17219af1df44bb8":
        return 0
    count = pg.execute(sql.SQL("SELECT count(*) FROM {}.forward_facts WHERE kind LIKE 'r7\\_%' ESCAPE '\\'").format(sql.Identifier(source))).fetchone()[0]
    receipt = pg.execute("SELECT row_count,source_digest,target_digest FROM v4.forward_r7_migration_r1 WHERE source_schema=%s", (source,)).fetchone()
    if not receipt or receipt[0] != count or receipt[1] != receipt[2]:
        raise RuntimeError("V4_FORWARD_REMAINDER_R7_RECEIPT_NOT_EXACT")
    target_count = pg.execute("SELECT count(*) FROM v4.forward_r7_facts_r1 WHERE origin_namespace='R7_ACTIVE'").fetchone()[0]
    if target_count < count:
        raise RuntimeError("V4_FORWARD_REMAINDER_R7_TARGET_INCOMPLETE")
    return count


def migrate_source(pg, source):
    namespace = "LEGACY:" + source
    pg.execute("SELECT pg_advisory_lock(hashtextextended(%s,0))", ("V4_FORWARD_REMAINDER_BATCH_R1:" + source,))
    source_size = pg.execute("SELECT pg_total_relation_size(%s::regclass)", (source + ".forward_facts",)).fetchone()[0]
    r7_rows = _r7_count(pg, source)
    before_target = pg.execute("SELECT pg_total_relation_size('v4.forward_facts'::regclass)").fetchone()[0]
    started = time.monotonic()
    source_rows = pg.execute(sql.SQL("SELECT count(*) FROM {}.forward_facts").format(sql.Identifier(source))).fetchone()[0]
    expected_rows = source_rows - r7_rows
    mapped_existing = pg.execute("SELECT count(*) FROM v4.forward_schema_migration_map_r1 WHERE source_schema=%s AND workspace_namespace=%s AND verification->>'status'='VERIFIED'", (source, namespace)).fetchone()[0]
    target_existing = pg.execute("SELECT count(*) FROM v4.forward_facts WHERE workspace_namespace=%s", (namespace,)).fetchone()[0]
    if mapped_existing == expected_rows and target_existing == expected_rows:
        source_hash = hashlib.sha256()
        target_hash = hashlib.sha256()
        query = sql.SQL("""SELECT s.kind,s.fact_key,s.payload_sha256,s.source_sha256,s.ordinal,
            m.workspace_namespace,m.payload_sha256,m.target_sha256,m.verification,
            t.payload_sha256,t.source_sha256
            FROM {}.forward_facts s
            LEFT JOIN v4.forward_schema_migration_map_r1 m
              ON m.source_schema=%s AND m.kind=s.kind AND m.fact_key=s.fact_key
            LEFT JOIN v4.forward_facts t
              ON t.workspace_namespace=m.workspace_namespace AND t.kind=s.kind AND t.fact_key=s.fact_key
            ORDER BY s.ordinal""").format(sql.Identifier(source))
        verified = 0
        for kind, key, raw_sha, source_sha, ordinal, mapped_ns, mapped_sha, target_sha, proof, target_raw_sha, target_source_sha in pg.execute(query, (source,)):
            if source == "v4_forward_f17219af1df44bb8" and kind.startswith("r7_"):
                continue
            sha = raw_sha.strip()
            locator = (kind, key, sha, source_sha, ordinal)
            if (mapped_ns, mapped_sha.strip() if mapped_sha else None, target_sha.strip() if target_sha else None,
                    proof.get("status") if proof else None, proof.get("source_ordinal") if proof else None,
                    target_raw_sha, target_source_sha) != (namespace, sha, sha, "VERIFIED", ordinal, sha, source_sha):
                raise RuntimeError("V4_FORWARD_REMAINDER_EXISTING_MAP_TARGET_MISMATCH:" + source + ":" + kind + ":" + key)
            _row_hash(source_hash, locator)
            _row_hash(target_hash, locator)
            verified += 1
        if verified != expected_rows or source_hash.digest() != target_hash.digest():
            raise RuntimeError("V4_FORWARD_REMAINDER_EXISTING_FULL_DIGEST_MISMATCH:" + source)
        source_digest = source_hash.hexdigest()
        receipt = dict(contract_id="V4_FORWARD_PG_FACT_STORE_R1", workspace_namespace=namespace,
            originals=[], original_files_unchanged=True, source_schema=source,
            source_relation="forward_facts", source_rows=verified, excluded_r7_rows=r7_rows,
            source_digest=source_digest, target_digest=source_digest, verification="EXACT_ROW_DIGESTS_R1")
        with pg.transaction():
            prior = pg.execute("SELECT receipt FROM v4.forward_migration_r1 WHERE workspace_namespace=%s", (namespace,)).fetchone()
            if prior and prior[0] != receipt:
                raise RuntimeError("V4_FORWARD_REMAINDER_NAMESPACE_RECEIPT_CONFLICT:" + source)
            if not prior:
                pg.execute("INSERT INTO v4.forward_migration_r1(workspace_namespace,receipt) VALUES(%s,%s)", (namespace, Jsonb(receipt)))
        target_size = pg.execute("SELECT pg_total_relation_size('v4.forward_facts'::regclass)").fetchone()[0]
        pg.execute("SELECT pg_advisory_unlock(hashtextextended(%s,0))", ("V4_FORWARD_REMAINDER_BATCH_R1:" + source,))
        return dict(source_schema=source, target_schema="v4", target_table="forward_facts", namespace=namespace,
            source_rows=source_rows, migrated_rows=verified, excluded_rows=r7_rows,
            source_relation_bytes=source_size, target_relation_bytes_before=before_target,
            target_relation_bytes_after=target_size, elapsed_seconds=round(time.monotonic() - started, 3),
            source_digest=source_digest, target_digest=source_digest, status="MIGRATED_AND_VERIFIED")
    source_hash = hashlib.sha256()
    target_hash = hashlib.sha256()
    migrated_rows = 0
    excluded_rows = 0
    last_ordinal = 0

    # Recompute deterministic source/target receipts on every resume. Payload bytes are
    # read for SHA verification, while all durable writes commit in bounded row batches.
    batch_rows = 1 if source in {"v4_forward_d49f600857001503", "v4_forward_f17219af1df44bb8"} else BATCH_ROWS
    while True:
        batch = pg.execute(sql.SQL("SELECT kind,fact_key,payload,payload_sha256,source_sha256,ordinal FROM {}.forward_facts WHERE ordinal>%s ORDER BY ordinal LIMIT %s").format(sql.Identifier(source)), (last_ordinal, batch_rows)).fetchall()
        if not batch:
            break
        batch_last_ordinal = batch[-1][5]
        last_ordinal = batch_last_ordinal
        pending = []
        for kind, key, payload, payload_sha, source_sha, ordinal in batch:
            payload_sha = payload_sha.strip()
            if hashlib.sha256(payload.encode("utf-8")).hexdigest() != payload_sha:
                raise RuntimeError("V4_FORWARD_REMAINDER_SOURCE_DIGEST_MISMATCH:" + source + ":" + kind + ":" + key)
            if source == "v4_forward_f17219af1df44bb8" and kind.startswith("r7_"):
                excluded_rows += 1
                continue
            locator = (kind, key, payload_sha, source_sha, ordinal)
            _row_hash(source_hash, locator)
            pending.append((kind, key, payload, payload_sha, source_sha, ordinal))

        if pending:
            with pg.transaction():
                for kind, key, payload, payload_sha, source_sha, ordinal in pending:
                    mapped = pg.execute("""SELECT workspace_namespace,payload_sha256,target_sha256,verification
                        FROM v4.forward_schema_migration_map_r1 WHERE source_schema=%s AND kind=%s AND fact_key=%s""",
                        (source, kind, key)).fetchone()
                    if mapped and ((mapped[0], mapped[1].strip(), mapped[2].strip()) != (namespace, payload_sha, payload_sha)
                                   or mapped[3].get("status") != "VERIFIED"
                                   or mapped[3].get("source_ordinal") != ordinal):
                        raise RuntimeError("V4_FORWARD_REMAINDER_MAP_CONFLICT:" + source + ":" + kind + ":" + key)
                    target = pg.execute("""SELECT payload_sha256,source_sha256 FROM v4.forward_facts
                        WHERE workspace_namespace=%s AND kind=%s AND fact_key=%s""",
                        (namespace, kind, key)).fetchone()
                    if target is None:
                        pg.execute("""INSERT INTO v4.forward_facts
                            (workspace_namespace,kind,fact_key,payload,payload_sha256,source_sha256)
                            VALUES(%s,%s,%s,%s,%s,%s)""",
                            (namespace, kind, key, payload, payload_sha, source_sha))
                        target = (payload_sha, source_sha)
                    if target != (payload_sha, source_sha):
                        raise RuntimeError("V4_FORWARD_REMAINDER_TARGET_CONFLICT:" + source + ":" + kind + ":" + key)
                    if not mapped:
                        proof = Jsonb(dict(status="VERIFIED", source_ordinal=ordinal,
                            source_payload_sha256=payload_sha, target_payload_sha256=target[0],
                            exact_payload_identity=True, namespace=namespace))
                        pg.execute("""INSERT INTO v4.forward_schema_migration_map_r1
                            (source_schema,workspace_namespace,kind,fact_key,payload_sha256,source_sha256,target_sha256,verification)
                            VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
                            (source, namespace, kind, key, payload_sha, source_sha, payload_sha, proof))
                    locator = (kind, key, payload_sha, source_sha, ordinal)
                    _row_hash(target_hash, locator)
                    migrated_rows += 1

    if excluded_rows != r7_rows:
        raise RuntimeError("V4_FORWARD_REMAINDER_R7_SCOPE_CARDINALITY_MISMATCH")
    source_digest = source_hash.hexdigest()
    target_digest = target_hash.hexdigest()
    if source_digest != target_digest:
        raise RuntimeError("V4_FORWARD_REMAINDER_BATCH_FULL_DIGEST_MISMATCH:" + source)
    mapped_count = pg.execute("""SELECT count(*) FROM v4.forward_schema_migration_map_r1
        WHERE source_schema=%s AND workspace_namespace=%s AND verification->>'status'='VERIFIED'""",
        (source, namespace)).fetchone()[0]
    if mapped_count != migrated_rows:
        raise RuntimeError("V4_FORWARD_REMAINDER_MAP_CARDINALITY_MISMATCH:" + source)
    receipt = dict(contract_id="V4_FORWARD_PG_FACT_STORE_R1", workspace_namespace=namespace,
        originals=[], original_files_unchanged=True, source_schema=source,
        source_relation="forward_facts", source_rows=migrated_rows, excluded_r7_rows=excluded_rows,
        source_digest=source_digest, target_digest=target_digest, verification="EXACT_ROW_DIGESTS_R1")
    with pg.transaction():
        prior = pg.execute("SELECT receipt FROM v4.forward_migration_r1 WHERE workspace_namespace=%s", (namespace,)).fetchone()
        if prior and prior[0] != receipt:
            raise RuntimeError("V4_FORWARD_REMAINDER_NAMESPACE_RECEIPT_CONFLICT:" + source)
        if not prior:
            pg.execute("INSERT INTO v4.forward_migration_r1(workspace_namespace,receipt) VALUES(%s,%s)", (namespace, Jsonb(receipt)))
    target_size = pg.execute("SELECT pg_total_relation_size('v4.forward_facts'::regclass)").fetchone()[0]
    pg.execute("SELECT pg_advisory_unlock(hashtextextended(%s,0))", ("V4_FORWARD_REMAINDER_BATCH_R1:" + source,))
    return dict(source_schema=source, target_schema="v4", target_table="forward_facts", namespace=namespace,
        source_rows=migrated_rows + excluded_rows, migrated_rows=migrated_rows, excluded_rows=excluded_rows,
        source_relation_bytes=source_size, target_relation_bytes_before=before_target,
        target_relation_bytes_after=target_size, elapsed_seconds=round(time.monotonic() - started, 3),
        last_ordinal=last_ordinal, source_digest=source_digest, target_digest=target_digest,
        status="MIGRATED_AND_VERIFIED")


def migrate(dsn):
    results = []
    with psycopg.connect(dsn, connect_timeout=5, autocommit=True) as pg:
        identity = pg.execute("SELECT current_database(),inet_server_addr()::text,inet_server_port() FROM pg_stat_activity WHERE pid=pg_backend_pid()").fetchone()
        if identity != ("market_research", "127.0.0.1/32", 5432):
            raise RuntimeError("V4_FORWARD_REMAINDER_DATABASE_IDENTITY_MISMATCH")
        pg.execute("SET statement_timeout='120s'")
        pg.execute("SET lock_timeout='5s'")
        for source in SOURCES:
            exists = pg.execute("SELECT to_regclass(%s)", (source + ".forward_facts",)).fetchone()[0]
            if not exists:
                raise RuntimeError("V4_FORWARD_REMAINDER_SOURCE_MISSING:" + source)
            results.append(migrate_source(pg, source))
    return dict(status="MIGRATED_AND_VERIFIED", database=identity, results=results)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        raise SystemExit("Refusing database writes without --apply")
    sys.path.insert(0, "src")
    from workbench_db.v4_native import configured_dsn
    print(json.dumps(migrate(configured_dsn()), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
