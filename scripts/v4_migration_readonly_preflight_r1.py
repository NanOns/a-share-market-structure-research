"""Read-only V4 migration/catalog preflight. This script never applies SQL."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_DIR = ROOT / "src/workbench_db/migrations/v4_postgres"
MUTATION = re.compile(r"\b(ALTER|CREATE|DROP|TRUNCATE|INSERT|UPDATE|DELETE|GRANT|REVOKE|COMMENT)\b", re.I)
RISK = {
    "drop": re.compile(r"\bDROP\b", re.I),
    "not_valid": re.compile(r"\bNOT\s+VALID\b", re.I),
    "role_or_grant": re.compile(r"\b(CREATE\s+ROLE|ALTER\s+ROLE|GRANT|REVOKE)\b", re.I),
    "trigger": re.compile(r"\b(TRIGGER|FUNCTION)\b", re.I),
    "data_write": re.compile(r"\b(INSERT|UPDATE|DELETE|TRUNCATE)\b", re.I),
    "dynamic_sql": re.compile(r"\bEXECUTE\b", re.I),
    "index_build": re.compile(r"\bCREATE\s+(UNIQUE\s+)?INDEX\b", re.I),
    "table_rewrite_or_validation": re.compile(r"\b(NOT\s+NULL|VALIDATE\s+CONSTRAINT|ADD\s+CONSTRAINT)\b", re.I),
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _migration_inventory() -> list[dict]:
    paths = sorted(MIGRATION_DIR.glob("*.sql"), key=lambda p: p.name.lower())
    result = []
    for path in paths:
        raw = path.read_bytes()
        sql_text = raw.decode("utf-8")
        actions = sorted({m.group(1).upper() for m in MUTATION.finditer(sql_text)})
        risks = sorted(name for name, pattern in RISK.items() if pattern.search(sql_text))
        numbered = re.match(r"^(\d+)_", path.name)
        result.append({
            "filename": path.name,
            "sequence_number": int(numbered.group(1)) if numbered else None,
            "raw_bytes": len(raw),
            "raw_sha256": _sha(raw),
            "utf8_text_sha256": _sha(sql_text.encode("utf-8")),
            "sql_actions": actions,
            "static_risk_tags": risks,
            "contains_sql_mutation": bool(actions),
            "contract_dependency_source": "R6_CONTRACT_DERIVED_NOT_SELF_DESCRIBED",
        })
    return result


def _configured_reader_dsn() -> str:
    value = os.environ.get("V4_NATIVE_PG_READER_DSN") or os.environ.get("WORKBENCH_PG_DSN")
    if value:
        return value
    # The existing project security file may own the read DSN. Only this
    # explicitly read-only variable is recognized; the writer key is never
    # read as fallback and no value is emitted to stdout or evidence files.
    env_file = ROOT / "config/.env"
    if env_file.is_file():
        for raw in env_file.read_text("utf-8-sig").splitlines():
            key, sep, val = raw.partition("=")
            if sep and key.strip() == "WORKBENCH_PG_DSN":
                value = val.strip().strip('"').strip("'")
                if value:
                    return value
    raise RuntimeError("V4_NATIVE_PG_READER_DSN_REQUIRED_NO_WRITER_FALLBACK")


def _read_catalog() -> dict:
    """Read one repeatable-read snapshot; no DSN or sensitive value is emitted."""
    import psycopg

    with psycopg.connect(_configured_reader_dsn(), connect_timeout=5) as pg:
        pg.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
        pg.execute("SET LOCAL statement_timeout='30s'")
        pg.execute("SET LOCAL lock_timeout='5s'")
        read_only = pg.execute("SHOW transaction_read_only").fetchone()[0]
        if read_only != "on":
            raise RuntimeError("PREFLIGHT_TRANSACTION_NOT_READ_ONLY")
        identity = pg.execute(
            """SELECT current_database(),inet_server_addr()::text,inet_server_port(),d.oid,
                      pg_get_userbyid(d.datdba),pg_encoding_to_char(d.encoding),d.datcollate,d.datctype,
                      current_user,
                      r.rolsuper,r.rolcreaterole,r.rolcreatedb,r.rolreplication,r.rolbypassrls
                 FROM pg_database d JOIN pg_roles r ON r.rolname=current_user
                WHERE d.datname=current_database()"""
        ).fetchone()
        if identity is None:
            raise RuntimeError("PREFLIGHT_DATABASE_IDENTITY_UNAVAILABLE")
        ledgers = []
        if pg.execute("SELECT to_regclass('v4_meta.schema_migrations')").fetchone()[0]:
            columns = {r[0] for r in pg.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema='v4_meta' AND table_name='schema_migrations'"
            ).fetchall()}
            if {"version", "checksum_sha256"}.issubset(columns):
                ledgers = [dict(version=r[0], checksum_sha256=str(r[1]).strip()) for r in pg.execute(
                    "SELECT version,checksum_sha256 FROM v4_meta.schema_migrations ORDER BY version"
                ).fetchall()]
            else:
                ledgers = [{"status": "LEDGER_COLUMNS_UNRECOGNIZED", "columns": sorted(columns)}]
        relations = pg.execute(
            """SELECT n.nspname,c.relname,c.relkind,c.reltuples::bigint,
                      pg_total_relation_size(c.oid),c.oid
                 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname IN ('v4','v4_meta') AND c.relkind IN ('r','p','v','m','S')
                ORDER BY n.nspname,c.relname"""
        ).fetchall()
        relation_rows = []
        for schema, name, kind, estimated_rows, total_bytes, oid in relations:
            columns = pg.execute(
                """SELECT a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,
                          pg_get_expr(d.adbin,d.adrelid)
                     FROM pg_attribute a LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
                    WHERE a.attrelid=%s AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum""", (oid,)
            ).fetchall()
            constraints = pg.execute(
                "SELECT conname,contype,convalidated,pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid=%s ORDER BY conname", (oid,)
            ).fetchall()
            indexes = pg.execute("SELECT indexname,indexdef FROM pg_indexes WHERE schemaname=%s AND tablename=%s ORDER BY indexname", (schema,name)).fetchall()
            triggers = pg.execute(
                """SELECT tgname,pg_get_triggerdef(oid),tgenabled FROM pg_trigger
                    WHERE tgrelid=%s AND NOT tgisinternal ORDER BY tgname""", (oid,)
            ).fetchall()
            relation_rows.append({
                "schema": schema, "name": name, "kind": kind, "estimated_rows": estimated_rows,
                "total_bytes": total_bytes,
                "columns": [dict(name=r[0], type=r[1], not_null=r[2], default=r[3]) for r in columns],
                "constraints": [dict(name=r[0], kind=r[1], validated=r[2], definition=r[3]) for r in constraints],
                "indexes": [dict(name=r[0], definition=r[1]) for r in indexes],
                "triggers": [dict(name=r[0], definition=r[1], enabled=r[2]) for r in triggers],
            })
        role_grants = pg.execute(
            """SELECT table_schema,table_name,privilege_type
                 FROM information_schema.role_table_grants WHERE grantee=current_user
                   AND table_schema IN ('v4','v4_meta') ORDER BY table_schema,table_name,privilege_type"""
        ).fetchall()
        functions = pg.execute(
            """SELECT n.nspname,p.proname,pg_get_function_identity_arguments(p.oid),
                      pg_get_functiondef(p.oid),r.rolname,p.prosecdef
                 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_roles r ON r.oid=p.proowner
                WHERE n.nspname IN ('v4','v4_meta') ORDER BY n.nspname,p.proname"""
        ).fetchall()
        pg.execute("COMMIT")
    superuser, createrole, createdb, replication, bypassrls = map(bool, identity[9:14])
    write_grants = {"INSERT", "UPDATE", "DELETE", "TRUNCATE", "TRIGGER", "REFERENCES"}
    has_write_grant = any(r[2].upper() in write_grants for r in role_grants)
    return {
        "transaction_read_only": True,
        "database": {"name": identity[0], "address": identity[1], "port": identity[2], "oid": identity[3],
                     "owner": identity[4], "encoding": identity[5], "collation": identity[6], "ctype": identity[7]},
        "reader_role": {"name": identity[8],
                        "superuser": superuser, "create_role": createrole, "create_db": createdb,
                        "replication": replication, "bypass_rls": bypassrls,
                        "table_write_grant": has_write_grant,
                        "status": "BLOCKED_PRIVILEGED_READER" if any((superuser,createrole,createdb,replication,bypassrls,has_write_grant)) else "READ_ROLE_PRIVILEGE_PASS"},
        "migration_ledger": ledgers, "relations": relation_rows,
        "grants": [dict(schema=r[0],table=r[1],privilege=r[2]) for r in role_grants],
        "functions": [dict(schema=r[0],name=r[1],arguments=r[2],definition=r[3],owner=r[4],security_definer=r[5]) for r in functions],
    }


def _atomic_write(out_dir: Path, document: dict) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "V4_R12_PG_MIGRATION_READONLY_PREFLIGHT_R1.json"
    fd, temporary = tempfile.mkstemp(prefix=".v4-r12-preflight-", suffix=".tmp", dir=out_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(document, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return target


def run(out_dir: str | Path, *, read_catalog: bool = True) -> dict:
    output = Path(out_dir).resolve()
    allowed_root = Path(tempfile.gettempdir()).resolve()
    if not output.is_relative_to(allowed_root):
        raise ValueError("PREFLIGHT_OUTPUT_MUST_BE_UNDER_TEMP_ROOT")
    migrations = _migration_inventory()
    sequence_counts = {}
    for item in migrations:
        sequence_counts[item["sequence_number"]] = sequence_counts.get(item["sequence_number"], 0) + 1
    duplicate_numbers = sorted(k for k,v in sequence_counts.items() if v > 1)
    try:
        catalog = _read_catalog() if read_catalog else {"status": "NOT_REQUESTED"}
    except Exception as exc:
        catalog = {"status": "BLOCKED_READ_ONLY_CATALOG_UNAVAILABLE",
                   "error_type": type(exc).__name__,
                   "reason": "No connection string or SQL detail is recorded in evidence."}
    document = {
        "contract_id": "V4_R12_PG_MIGRATION_READONLY_PREFLIGHT_R1",
        "status": "READ_ONLY_PREFLIGHT_ONLY_NO_DDL_DML_NO_HEAD",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository_head": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                                           check=True, capture_output=True, text=True).stdout.strip(),
        "migration_count": len(migrations), "duplicate_sequence_numbers": duplicate_numbers,
        "migration_files": migrations,
        "expected_order_note": "001-040 plus duplicated 010 filenames; publication chain 010 source-manifest, 034–040 is contract-derived and not encoded as a complete SQL dependency graph.",
        "database_catalog": catalog,
    }
    document["migration_ledger_reconcile"] = {
        "catalog_connection_status": document["database_catalog"].get("reader_role", {}).get("status", "NOT_READ"),
        "known_required_chain": ["010_source_manifest_contract_r1.sql", "034_source_package_revision_authority_r2.sql",
                                 "035_source_manifest_contract_r2.sql", "036_source_package_fact_provenance_r6.sql",
                                 "037_daily_core_result_binding_r6.sql", "038_publication_module_results_r4.sql",
                                 "039_tdx_package_row_count_authority_r1.sql",
                                 "040_source_manifest_r3_fact_proof.sql"],
        "automatic_apply_decision": "BLOCKED_UNTIL_CATALOG_LEDGER_RECONCILIATION_AND_APPROVED_MIGRATION_ROLE",
        "ddl_executed": False, "dml_executed": False, "head_changed": False,
    }
    document["evidence_path"] = str(output / "V4_R12_PG_MIGRATION_READONLY_PREFLIGHT_R1.json")
    _atomic_write(output, document)
    return document


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--static-only", action="store_true")
    args = parser.parse_args()
    result = run(args.out_dir, read_catalog=not args.static_only)
    print(json.dumps({k: result[k] for k in ("status", "migration_count", "duplicate_sequence_numbers", "evidence_path", "migration_ledger_reconcile")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
