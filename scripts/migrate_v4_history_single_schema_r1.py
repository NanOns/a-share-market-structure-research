"""Move the three inventoried dated-history schemas into fixed v4 tables."""
from __future__ import annotations

import argparse
import json
import sys

import psycopg
from psycopg import sql

SOURCES = (
    "v4_history_80ef60f40eca6e6d",
    "v4_history_64d0f9c30983a3ac",
    "v4_history_dbe184da961f97b8",
)


def migrate(dsn):
    sys.path.insert(0, "src")
    from workbench_db.v4_history_pg_r1 import DDL

    results = []
    with psycopg.connect(dsn, connect_timeout=5) as pg:
        identity = pg.execute("SELECT current_database(),inet_server_addr()::text,inet_server_port() FROM pg_stat_activity WHERE pid=pg_backend_pid()").fetchone()
        if identity[0] != "market_research" or identity[1] not in ("127.0.0.1", "127.0.0.1/32") or identity[2] != 5432:
            raise RuntimeError("V4_HISTORY_DATABASE_IDENTITY_MISMATCH")
        pg.execute("SET LOCAL statement_timeout='120s'")
        pg.execute("SET LOCAL lock_timeout='5s'")
        pg.execute(DDL)
        for source in SOURCES:
            if not pg.execute("SELECT to_regclass(%s)", (f"{source}.history_versions",)).fetchone()[0]:
                raise RuntimeError("V4_HISTORY_EXACT_SOURCE_VERSION_TABLE_MISSING:" + source)
            if not pg.execute("SELECT to_regclass(%s)", (f"{source}.history",)).fetchone()[0]:
                raise RuntimeError("V4_HISTORY_EXACT_SOURCE_BARS_TABLE_MISSING:" + source)
            with pg.transaction():
                pg.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("V4_HISTORY_SINGLE_SCHEMA_R1:" + source,))
                versions = pg.execute(sql.SQL("""SELECT version,head_token,t0,source_digest,logical_digest,symbol_count,bar_count
                    FROM {}.history_versions ORDER BY version COLLATE \"C\"""").format(sql.Identifier(source))).fetchall()
                moved = 0
                for version, head, t0, source_digest, logical_digest, symbols, bars in versions:
                    old = pg.execute("""SELECT head_token,t0,source_digest,logical_digest,symbol_count,bar_count
                        FROM v4.history_versions_r1 WHERE version=%s""", (version,)).fetchone()
                    expected = (head,t0,source_digest,logical_digest,symbols,bars)
                    if old is not None and old != expected:
                        raise RuntimeError("V4_HISTORY_CENTRAL_VERSION_IDENTITY_CONFLICT")
                    source_count = pg.execute(sql.SQL("SELECT count(*) FROM {}.history WHERE version=%s").format(sql.Identifier(source)),(version,)).fetchone()[0]
                    if source_count != symbols:
                        raise RuntimeError("V4_HISTORY_SOURCE_SYMBOL_COUNT_MISMATCH")
                    source_bars = pg.execute(sql.SQL("SELECT coalesce(sum(jsonb_array_length(payload)),0) FROM {}.history WHERE version=%s").format(sql.Identifier(source)),(version,)).fetchone()[0]
                    if source_bars != bars:
                        raise RuntimeError("V4_HISTORY_SOURCE_BAR_COUNT_MISMATCH")
                    if old is None:
                        pg.execute("SET CONSTRAINTS ALL DEFERRED")
                        pg.execute(sql.SQL("""INSERT INTO v4.history_bars_r1(version,security,payload)
                            SELECT version,security,payload FROM {}.history WHERE version=%s""").format(sql.Identifier(source)),(version,))
                        pg.execute("""INSERT INTO v4.history_versions_r1(version,head_token,t0,source_digest,logical_digest,symbol_count,bar_count)
                            VALUES(%s,%s,%s,%s,%s,%s,%s)""",(version,head,t0,source_digest,logical_digest,symbols,bars))
                    target_count=pg.execute("SELECT count(*) FROM v4.history_bars_r1 WHERE version=%s",(version,)).fetchone()[0]
                    if target_count!=source_count:
                        raise RuntimeError("V4_HISTORY_TARGET_SYMBOL_COUNT_MISMATCH")
                    target_bars=pg.execute("SELECT coalesce(sum(jsonb_array_length(payload)),0) FROM v4.history_bars_r1 WHERE version=%s",(version,)).fetchone()[0]
                    if target_bars!=source_bars or target_bars!=bars:
                        raise RuntimeError("V4_HISTORY_TARGET_BAR_COUNT_MISMATCH")
                    proof=dict(status="VERIFIED",row_count=source_count,logical_digest=logical_digest,
                               source_identity=dict(head_token=head,T0=t0.isoformat(),source_digest=source_digest))
                    prior_map=pg.execute("""SELECT canonical_version,T0,head_token,source_digest,logical_digest,symbol_count,bar_count,verification
                        FROM v4.history_migration_map_r1 WHERE source_schema=%s AND source_version=%s""",(source,version)).fetchone()
                    if prior_map:
                        if prior_map[:7]!=(version,t0,head,source_digest,logical_digest,symbols,bars) or prior_map[7].get('status')!='VERIFIED':
                            raise RuntimeError("V4_HISTORY_EXISTING_MIGRATION_MAP_CONFLICT")
                    else:
                        mismatch=pg.execute(sql.SQL("""SELECT count(*) FROM {}.history s
                            FULL JOIN v4.history_bars_r1 t ON t.version=s.version AND t.security=s.security
                            WHERE (s.version=%s OR t.version=%s) AND
                              (s.version IS NULL OR t.version IS NULL OR s.payload IS DISTINCT FROM t.payload)""").format(sql.Identifier(source)),(version,version)).fetchone()[0]
                        if mismatch:
                            raise RuntimeError("V4_HISTORY_SOURCE_TARGET_ROW_PARITY_FAILED")
                    pg.execute("""INSERT INTO v4.history_migration_map_r1
                        (source_schema,source_version,canonical_version,T0,head_token,source_digest,logical_digest,symbol_count,bar_count,verification)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                        ON CONFLICT(source_schema,source_version) DO NOTHING""",
                        (source,version,version,t0,head,source_digest,logical_digest,symbols,bars,json.dumps(proof,separators=(",",":"))))
                    mapping=pg.execute("""SELECT canonical_version,T0,head_token,source_digest,logical_digest,symbol_count,bar_count,verification
                        FROM v4.history_migration_map_r1 WHERE source_schema=%s AND source_version=%s""",(source,version)).fetchone()
                    if mapping[:7]!=(version,t0,head,source_digest,logical_digest,symbols,bars) or mapping[7].get('status')!='VERIFIED':
                        raise RuntimeError("V4_HISTORY_MIGRATION_MAP_READBACK_MISMATCH")
                    moved+=source_count
                results.append(dict(source_schema=source,versions=len(versions),symbols=moved,status="VERIFIED"))
    return dict(status="MIGRATED_AND_VERIFIED",database=identity,target_schema="v4",results=results)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--apply",action="store_true")
    args=parser.parse_args()
    if not args.apply:raise SystemExit("Refusing database writes without --apply")
    sys.path.insert(0,"src")
    from workbench_db.v4_native import configured_dsn
    print(json.dumps(migrate(configured_dsn()),ensure_ascii=False,sort_keys=True,default=str))


if __name__=="__main__":main()
