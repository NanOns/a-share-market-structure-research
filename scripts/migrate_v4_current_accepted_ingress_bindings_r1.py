"""Migrate only the exact source ingress bindings in the approved current V4 contract."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

SOURCE_SCHEMA = "v4_forward_213e535c50ad7135"
NAMESPACE = "v4w_799b175957211459a670773167f8fcc7:forward"
CONTRACT_ID = "V4_CURRENT_ACCEPTED_READ_CONTRACT_V1"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(value).hexdigest()


def collect_refs(value, found):
    if isinstance(value, dict):
        if (isinstance(value.get("path"), str) and isinstance(value.get("sha256"), str)
                and type(value.get("bytes")) is int):
            found[(value["path"], value["sha256"], value["bytes"])] = value
        for child in value.values():
            collect_refs(child, found)
    elif isinstance(value, list):
        for child in value:
            collect_refs(child, found)


def run(dsn):
    sys.path.insert(0, "src")
    from workbench_analysis.contract_registry_pg_v1 import load_unique_current_approved_contract
    from workbench_db.v4_historical_source_ingress_pg_r1 import CONTRACT as INGRESS_CONTRACT, source_id_for_path
    from workbench_db.v4_native import configured_reader_dsn
    from workbench_db.v4_publication_reader import PgPublicationReader

    with psycopg.connect(configured_reader_dsn(), connect_timeout=5) as reader:
        reader.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        identity = PgPublicationReader._read_database_identity(reader)
        registered = load_unique_current_approved_contract(
            reader, CONTRACT_ID, "1.0.0", expected_database_identity=identity)
        contract = registered.parsed_json
        contract_sha = registered.raw_sha256
        if (registered.namespace != "V4_CURRENT_ACCEPTED" or not contract
                or registered.approval_source_sha256 != contract_sha
                or contract.get("source_discovery") is not False
                or contract.get("fallback") != "NONE"):
            raise RuntimeError("CURRENT_ACCEPTED_CONTRACT_NOT_EXACTLY_APPROVED")
        refs = {}
        collect_refs(contract, refs)
        keys = []
        for path, sha, byte_count in sorted(refs):
            source_id = source_id_for_path(path)
            key = digest(canonical({"contract_id": INGRESS_CONTRACT,
                                   "source_id": source_id, "source_sha256": sha}))
            keys.append((path, sha, byte_count, key))
        if len(keys) != 390 or len({row[3] for row in keys}) != len(keys):
            raise RuntimeError("CURRENT_ACCEPTED_CONTRACT_BINDING_SET_CHANGED")

    source_digest = hashlib.sha256()
    total_source_bytes = 0
    with psycopg.connect(dsn, connect_timeout=5) as pg:
        ident = pg.execute("SELECT current_database(),inet_server_addr()::text,inet_server_port() FROM pg_stat_activity WHERE pid=pg_backend_pid()").fetchone()
        if ident[0] != "market_research" or ident[1] not in ("127.0.0.1", "127.0.0.1/32") or ident[2] != 5432:
            raise RuntimeError("CURRENT_ACCEPTED_INGRESS_DATABASE_IDENTITY_MISMATCH")
        pg.execute("SET LOCAL statement_timeout='120s'")
        pg.execute("SET LOCAL lock_timeout='5s'")
        alias = pg.execute("SELECT logical_workspace_id,purpose,status FROM v4.workspace_namespace_aliases_r1 WHERE physical_schema=%s",
                           (SOURCE_SCHEMA,)).fetchall()
        if alias != [(NAMESPACE.removesuffix(":forward"), "forward", "ACTIVE")]:
            raise RuntimeError("CURRENT_ACCEPTED_INGRESS_ALIAS_IDENTITY_MISMATCH")
        with pg.transaction():
            pg.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",
                       ("V4_CURRENT_ACCEPTED_INGRESS_R1:" + SOURCE_SCHEMA,))
            for path, expected_sha, expected_bytes, key in keys:
                source = pg.execute(
                    sql.SQL("SELECT payload,payload_sha256,source_sha256 FROM {}.forward_facts WHERE kind=%s AND fact_key=%s").format(
                        sql.Identifier(SOURCE_SCHEMA)),
                    ("historical_source_ingress", key)).fetchone()
                if not source:
                    raise RuntimeError("CURRENT_ACCEPTED_INGRESS_EXACT_FACT_MISSING:" + path)
                payload, payload_sha, source_sha = source
                if digest(payload.encode("utf-8")) != payload_sha.strip():
                    raise RuntimeError("CURRENT_ACCEPTED_INGRESS_SOURCE_DIGEST_MISMATCH:" + path)
                record = json.loads(payload)
                if (record.get("contract_id") != INGRESS_CONTRACT
                        or record.get("source_path") != path
                        or record.get("source_sha256") != expected_sha
                        or record.get("source_bytes") != expected_bytes):
                    raise RuntimeError("CURRENT_ACCEPTED_INGRESS_EXACT_BINDING_MISMATCH:" + path)
                target = pg.execute("""SELECT payload,payload_sha256,source_sha256
                    FROM v4.forward_facts WHERE workspace_namespace=%s AND kind=%s AND fact_key=%s""",
                    (NAMESPACE, "historical_source_ingress", key)).fetchone()
                if target is None:
                    pg.execute("""INSERT INTO v4.forward_facts
                        (workspace_namespace,kind,fact_key,payload,payload_sha256,source_sha256)
                        VALUES(%s,%s,%s,%s,%s,%s)""",
                        (NAMESPACE, "historical_source_ingress", key, payload, payload_sha.strip(), source_sha))
                    target = (payload, payload_sha.strip(), source_sha)
                if target != (payload, payload_sha.strip(), source_sha):
                    raise RuntimeError("CURRENT_ACCEPTED_INGRESS_TARGET_CONFLICT:" + path)
                proof = {"status": "VERIFIED", "contract_id": CONTRACT_ID,
                         "contract_sha256": contract_sha, "exact_path": path,
                         "exact_source_sha256": expected_sha, "exact_source_bytes": expected_bytes,
                         "source_payload_sha256": payload_sha.strip(),
                         "target_payload_sha256": target[1]}
                prior = pg.execute("""SELECT workspace_namespace,payload_sha256,target_sha256,verification
                    FROM v4.forward_schema_migration_map_r1
                    WHERE source_schema=%s AND kind=%s AND fact_key=%s""",
                    (SOURCE_SCHEMA, "historical_source_ingress", key)).fetchone()
                if prior:
                    if (prior[0] != NAMESPACE or prior[1].strip() != payload_sha.strip()
                            or prior[2].strip() != payload_sha.strip()
                            or prior[3].get("status") != "VERIFIED"):
                        raise RuntimeError("CURRENT_ACCEPTED_INGRESS_RECEIPT_CONFLICT:" + path)
                else:
                    pg.execute("""INSERT INTO v4.forward_schema_migration_map_r1
                        (source_schema,workspace_namespace,kind,fact_key,payload_sha256,source_sha256,target_sha256,verification)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (SOURCE_SCHEMA, NAMESPACE, "historical_source_ingress", key,
                         payload_sha.strip(), source_sha, payload_sha.strip(), Jsonb(proof)))
                receipt_line = canonical([path, expected_sha, expected_bytes, key, payload_sha.strip()])
                source_digest.update(len(receipt_line).to_bytes(8, "big")); source_digest.update(receipt_line)
                total_source_bytes += expected_bytes
    return {"status": "MIGRATED_AND_VERIFIED", "database": ident,
            "source_schema": SOURCE_SCHEMA, "target_schema": "v4", "namespace": NAMESPACE,
            "approved_contract_sha256": contract_sha, "exact_binding_count": len(keys),
            "source_bytes": total_source_bytes, "receipt_set_sha256": source_digest.hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        raise SystemExit("Refusing database writes without --apply")
    sys.path.insert(0, "src")
    from workbench_db.v4_native import configured_dsn
    print(json.dumps(run(configured_dsn()), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
