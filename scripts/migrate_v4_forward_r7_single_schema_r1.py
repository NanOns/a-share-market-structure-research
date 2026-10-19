"""Migrate only the active R7 fact family into fixed v4 storage with digest proof."""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import sys

import psycopg
from psycopg import sql

ROOT_SCHEMA = "v4_forward_f17219af1df44bb8"
TARGET_SCHEMA = "v4"
NAMESPACE = "R7_ACTIVE"


def _canonical(row):
    return json.dumps(row, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest_row(hasher, row):
    raw = _canonical(row)
    hasher.update(len(raw).to_bytes(8, "big"))
    hasher.update(raw)


def _fact_rows(pg, schema):
    query = sql.SQL("""SELECT kind,fact_key,payload,payload_sha256,source_sha256,ordinal
        FROM {}.forward_facts WHERE kind LIKE 'r7\\_%' ESCAPE '\\' ORDER BY ordinal""").format(sql.Identifier(schema))
    with pg.cursor(name="forward_r7_single_schema_source") as cursor:
        cursor.itersize = 8
        cursor.execute(query)
        while batch := cursor.fetchmany(8):
            yield from batch


def _business_identity(payload):
    try:
        value = json.loads(payload)
    except (TypeError, json.JSONDecodeError):
        return None, None, None
    owner = value.get("owner_id") if isinstance(value, dict) else None
    run_id = (value.get("run_id") or value.get("source_run_id")) if isinstance(value, dict) else None
    day = (value.get("trade_date") or value.get("T0")) if isinstance(value, dict) else None
    try:
        day = date.fromisoformat(day) if isinstance(day, str) and len(day) == 10 else None
    except ValueError:
        day = None
    return owner, run_id, day


def migrate(dsn: str):
    with psycopg.connect(dsn, connect_timeout=5) as pg:
        pg.execute("SET LOCAL statement_timeout='120s'")
        pg.execute("SET LOCAL lock_timeout='5s'")
        identity = pg.execute("SELECT current_database(), inet_server_addr()::text, inet_server_port() FROM pg_stat_activity WHERE pid=pg_backend_pid()").fetchone()
        if identity[0] != "market_research" or identity[1] not in ("127.0.0.1", "127.0.0.1/32") or identity[2] != 5432:
            raise RuntimeError("V4_FORWARD_R7_DATABASE_IDENTITY_MISMATCH")
        if not pg.execute("SELECT to_regclass('v4.forward_r7_facts_r1')").fetchone()[0]:
            raise RuntimeError("V4_FORWARD_R7_SINGLE_SCHEMA_MIGRATION_050_REQUIRED")
        if not pg.execute("SELECT to_regclass(%s)", (f"{ROOT_SCHEMA}.forward_facts",)).fetchone()[0]:
            raise RuntimeError("V4_FORWARD_R7_EXACT_SOURCE_SCHEMA_MISSING")

        source_hash = hashlib.sha256()
        source_count = 0
        with pg.transaction():
            pg.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("V4_FORWARD_R7_SINGLE_SCHEMA_R1:" + ROOT_SCHEMA,))
            existing = pg.execute("SELECT row_count,source_digest,target_digest FROM v4.forward_r7_migration_r1 WHERE source_schema=%s", (ROOT_SCHEMA,)).fetchone()
            # Stable ordinal order retains the source append order for the R7 relation.
            for kind, key, payload, payload_sha, source_sha, ordinal in _fact_rows(pg, ROOT_SCHEMA):
                raw = payload.encode("utf-8") if isinstance(payload, str) else bytes(payload)
                if hashlib.sha256(raw).hexdigest() != payload_sha.strip():
                    raise RuntimeError("V4_FORWARD_R7_SOURCE_PAYLOAD_DIGEST_MISMATCH")
                row_identity = (kind, key, payload, payload_sha.strip(), source_sha, ordinal)
                _digest_row(source_hash, row_identity)
                owner, run_id, t0 = _business_identity(payload)
                pg.execute("""INSERT INTO v4.forward_r7_facts_r1
                    (origin_namespace,owner_id,run_id,t0,kind,fact_key,payload,payload_sha256,source_sha256,ordinal)
                    OVERRIDING SYSTEM VALUE VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(origin_namespace,kind,fact_key) DO NOTHING""",
                    (NAMESPACE, owner, run_id, t0, kind, key, payload, payload_sha.strip(), source_sha, ordinal))
                target = pg.execute("""SELECT origin_namespace,kind,fact_key,payload,payload_sha256,source_sha256,ordinal
                    FROM v4.forward_r7_facts_r1 WHERE origin_namespace=%s AND kind=%s AND fact_key=%s""", (NAMESPACE,kind, key)).fetchone()
                expected = (NAMESPACE, kind, key, payload, payload_sha.strip(), source_sha, ordinal)
                if target != expected:
                    raise RuntimeError("V4_FORWARD_R7_TARGET_FACT_IDENTITY_CONFLICT")
                source_count += 1

            source_digest = source_hash.hexdigest()
            target_hash = hashlib.sha256()
            target_count = 0
            with pg.cursor(name="forward_r7_single_schema_target") as cursor:
                cursor.itersize = 16
                cursor.execute("""SELECT kind,fact_key,payload,payload_sha256,source_sha256,ordinal
                    FROM v4.forward_r7_facts_r1 WHERE origin_namespace=%s ORDER BY ordinal""", (NAMESPACE,))
                for row in cursor:
                    _digest_row(target_hash, row)
                    target_count += 1
            target_digest = target_hash.hexdigest()
            if target_count != source_count or target_digest != source_digest:
                raise RuntimeError("V4_FORWARD_R7_SINGLE_SCHEMA_FULL_DIGEST_MISMATCH")
            if existing and existing != (source_count, source_digest, target_digest):
                raise RuntimeError("V4_FORWARD_R7_MIGRATION_RECEIPT_CONFLICT")
            if not existing:
                pg.execute("INSERT INTO v4.forward_r7_migration_r1(source_schema,source_table,origin_namespace,row_count,source_digest,target_digest) VALUES(%s,'forward_facts',%s,%s,%s,%s)",
                           (ROOT_SCHEMA, NAMESPACE, source_count, source_digest, target_digest))
            pg.execute("SELECT setval(pg_get_serial_sequence('v4.forward_r7_facts_r1','ordinal'),GREATEST((SELECT coalesce(max(ordinal),1) FROM v4.forward_r7_facts_r1),1),true)")
        return dict(status="MIGRATED_AND_VERIFIED", database=identity, source_schema=ROOT_SCHEMA,
                    target_schema=TARGET_SCHEMA, relation="forward_r7_facts_r1", namespace=NAMESPACE,
                    rows=source_count, source_digest=source_digest, target_digest=target_digest)


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
