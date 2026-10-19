"""Migrate the inventoried immutable Owner versions into fixed v4 relations."""
from __future__ import annotations

import argparse
import json
import sys

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

SOURCES = (
    ("research_priority", "v4_010ec70a0aec548ac90822657ab528c146dac69d2dba00efb2f65d4d"),
    ("research_priority", "v4_1d03238596d40b243bbe20251652a31daabf07f175664007bdde0dee"),
    ("research_priority", "v4_912533e33e54174e4d3b636c08236964ca679e2dc71050508f001860"),
    ("operational_risk", "v4_1d314c5c198c87e14096534bc6ec5b592ce101da01d4f62eab2a2496"),
    ("operational_risk", "v4_cd017ab98f5b3a4cbdfeaab0a98babd96f9565aad5cf7a0c6a0bc1c6"),
    ("operational_risk", "v4_d42d3617395cd804459ee5940b31590c74a69817a94daea159bbef4a"),
    ("sector_lifecycle", "v4_f8a7432ae9ae29f4a9fe737e204e8a5d0598f365d42a23f1379a665c"),
)
CONTRACTS = {
    "research_priority": "V4_RESEARCH_PRIORITY_PG_OWNER_R1",
    "operational_risk": "V4_OPERATIONAL_RISK_PG_OWNER_R1",
    "sector_lifecycle": "V4_SECTOR_LIFECYCLE_PG_OWNER_R1",
}
TARGETS = {
    "research_priority": ("owner_versions_priority_r1", "owner_payloads_priority_r1"),
    "operational_risk": ("owner_versions_risk_r1", "owner_payloads_risk_r1"),
    "sector_lifecycle": ("sector_lifecycle_owner_versions_r1", "sector_lifecycle_owner_rows_r1"),
}


def _install(pg, family):
    if family == "sector_lifecycle":
        from workbench_db.v4_sector_lifecycle_pg_r1 import _install_schema
        _install_schema(pg, "v4")
    else:
        from workbench_db.v4_operational_risk_pg_r1 import _install
        _install(pg, "v4", "priority_r1" if family == "research_priority" else "risk_r1")


def _migrate_one(pg, family, schema):
    versions_table, payload_table = TARGETS[family]
    version_rows = sql.Identifier(schema, "owner_versions")
    versions = pg.execute(sql.SQL("SELECT * FROM {} ORDER BY token,T0").format(version_rows)).fetchall()
    if not versions:
        return dict(source_schema=schema, family=family, versions=0, rows=0, status="EMPTY")
    _install(pg, family)
    migrated_rows = 0
    for source in versions:
        if family == "sector_lifecycle":
            token, day, contract, digest, producer, parameter, inputs, row_count, identity, sealed = source
        else:
            token, day, contract, digest, row_count, identity, sealed = source
        if contract != CONTRACTS[family] or sealed is not True:
            raise RuntimeError(f"OWNER_SOURCE_VERSION_INVALID:{schema}:{family}:{token}:{day}")
        if family == "sector_lifecycle":
            source_rows = pg.execute(sql.SQL("SELECT sector_id,payload,payload_sha256 FROM {} WHERE token=%s AND T0=%s ORDER BY sector_id COLLATE \"C\"").format(sql.Identifier(schema, "owner_rows")), (token, day)).fetchall()
        else:
            source_rows = pg.execute(sql.SQL("SELECT payload,payload_sha256 FROM {} WHERE token=%s AND T0=%s").format(sql.Identifier(schema, "owner_payloads")), (token, day)).fetchall()
        if len(source_rows) != (1 if family != "sector_lifecycle" else row_count):
            raise RuntimeError(f"OWNER_SOURCE_ROW_COUNT_MISMATCH:{schema}:{token}:{day}")
        target_version = pg.execute(sql.SQL("SELECT digest,contract,sealed,row_count FROM v4.{} WHERE token=%s AND T0=%s").format(sql.Identifier(versions_table)), (token, day)).fetchone()
        if target_version and target_version != (digest, contract, True, row_count):
            raise RuntimeError(f"OWNER_TARGET_VERSION_CONFLICT:{schema}:{token}:{day}")
        if target_version is None:
            if family == "sector_lifecycle":
                pg.execute("INSERT INTO v4.sector_lifecycle_owner_versions_r1(token,T0,contract,digest,producer_sha256,parameter_digest,input_digest,row_count,database_identity,sealed) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,false)", (token, day, contract, digest, producer, parameter, inputs, row_count, Jsonb(identity)))
                with pg.cursor() as cur:
                    cur.executemany("INSERT INTO v4.sector_lifecycle_owner_rows_r1(token,T0,sector_id,payload,payload_sha256) VALUES(%s,%s,%s,%s,%s)", [(token, day, sid, Jsonb(payload), sha) for sid, payload, sha in source_rows])
                pg.execute("UPDATE v4.sector_lifecycle_owner_versions_r1 SET sealed=true WHERE token=%s AND T0=%s", (token, day))
            else:
                pg.execute(sql.SQL("INSERT INTO v4.{}(token,T0,contract,digest,row_count,database_identity,sealed) VALUES(%s,%s,%s,%s,%s,%s,false)").format(sql.Identifier(versions_table)), (token, day, contract, digest, row_count, Jsonb(identity)))
                pg.execute(sql.SQL("INSERT INTO v4.{}(token,T0,payload,payload_sha256) VALUES(%s,%s,%s,%s)").format(sql.Identifier(payload_table)), (token, day, Jsonb(source_rows[0][0]), source_rows[0][1]))
                pg.execute(sql.SQL("UPDATE v4.{} SET sealed=true WHERE token=%s AND T0=%s").format(sql.Identifier(versions_table)), (token, day))
        if family == "sector_lifecycle":
            target_rows = pg.execute("SELECT sector_id,payload,payload_sha256 FROM v4.sector_lifecycle_owner_rows_r1 WHERE token=%s AND T0=%s ORDER BY sector_id COLLATE \"C\"", (token, day)).fetchall()
        else:
            target_rows = pg.execute(sql.SQL("SELECT payload,payload_sha256 FROM v4.{} WHERE token=%s AND T0=%s").format(sql.Identifier(payload_table)), (token, day)).fetchall()
        if target_rows != source_rows:
            raise RuntimeError(f"OWNER_SOURCE_TARGET_ROW_PARITY_FAILED:{schema}:{token}:{day}")
        proof = dict(status="VERIFIED", source_rows=len(source_rows), target_rows=len(target_rows), row_parity=True,
                     source_digest=digest, database_identity=identity)
        pg.execute("""INSERT INTO v4.owner_schema_migration_map_r1
          (family,source_schema,token,T0,digest,contract,row_count,verification)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING""",
          (family, schema, token, day, digest, contract, row_count, json.dumps(proof, separators=(",", ":"))))
        mapped = pg.execute("SELECT digest,contract,row_count,verification FROM v4.owner_schema_migration_map_r1 WHERE family=%s AND source_schema=%s AND token=%s AND T0=%s", (family, schema, token, day)).fetchone()
        if not mapped or mapped[:3] != (digest, contract, row_count) or mapped[3].get("status") != "VERIFIED":
            raise RuntimeError(f"OWNER_MIGRATION_MAP_READBACK_FAILED:{schema}:{token}:{day}")
        migrated_rows += len(source_rows)
    return dict(source_schema=schema, family=family, versions=len(versions), rows=migrated_rows, status="VERIFIED")


def migrate(dsn):
    results = []
    with psycopg.connect(dsn, connect_timeout=5) as pg:
        identity = pg.execute("SELECT current_database(),inet_server_addr()::text,inet_server_port() FROM pg_stat_activity WHERE pid=pg_backend_pid()").fetchone()
        if identity[0] != "market_research" or identity[1] not in ("127.0.0.1", "127.0.0.1/32") or identity[2] != 5432:
            raise RuntimeError("V4_OWNER_DATABASE_IDENTITY_MISMATCH")
        pg.execute("SET statement_timeout='120s'"); pg.execute("SET lock_timeout='5s'")
        for family, schema in SOURCES:
            with pg.transaction():
                pg.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("V4_OWNER_SINGLE_SCHEMA_R1:" + schema,))
                results.append(_migrate_one(pg, family, schema))
    return dict(status="MIGRATED_AND_VERIFIED", database=identity, target_schema="v4", results=results)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--apply", action="store_true"); args = parser.parse_args()
    if not args.apply: raise SystemExit("Refusing database writes without --apply")
    sys.path.insert(0, "src")
    from workbench_db.v4_native import configured_dsn
    print(json.dumps(migrate(configured_dsn()), ensure_ascii=False, sort_keys=True, default=str))


if __name__ == "__main__": main()
