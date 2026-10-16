"""Native PG V4 candidate connections: explicit configuration, no fallback."""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import re
import psycopg
from psycopg import sql

CONTRACT = 'V4_NATIVE_POSTGRESQL_CONNECTION_R3'

def configured_dsn():
    value=os.environ.get('V4_NATIVE_PG_DSN')
    if not value: raise RuntimeError('V4_NATIVE_PG_DSN_REQUIRED_NO_FALLBACK')
    return value

def configured_reader_dsn():
    """Return a read connection string without ever falling back to the writer."""
    value = os.environ.get('V4_NATIVE_PG_READER_DSN') or os.environ.get('WORKBENCH_PG_DSN')
    if not value:
        raise RuntimeError('V4_NATIVE_PG_READER_DSN_REQUIRED_NO_WRITER_FALLBACK')
    return value

def workspace_schema(root, purpose):
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,24}',purpose): raise ValueError('INVALID_PG_PURPOSE')
    return 'v4_'+purpose+'_'+hashlib.sha256(str(Path(root).resolve()).casefold().encode()).hexdigest()[:16]

def workspace_namespace_identity(root, purpose):
    """Return a non-path-leaking, root-bound namespace/capability identity."""
    canonical_root = str(Path(root).resolve()).casefold()
    return {
        "contract_id": "V4_PG_WORKSPACE_NAMESPACE_ID_R1",
        "root_identity_sha256": hashlib.sha256(canonical_root.encode()).hexdigest(),
        "schema": workspace_schema(root, purpose),
        "purpose": purpose,
        "capabilities": {
            "read": "READER_DSN_AND_READ_ONLY_TRANSACTION_REQUIRED",
            "write": "EXPLICIT_V4_NATIVE_PG_DSN_REQUIRED",
            "owner_mapping": "MUST_BE_AUTHORITY_BOUND",
        },
    }

def attest_read_role(pg, schema):
    """Reject privileged or namespace-writing roles for every native read."""
    row = pg.execute(
        """SELECT r.rolsuper, r.rolcreaterole, r.rolcreatedb, r.rolreplication,
                  r.rolbypassrls,
                  n.oid IS NOT NULL,
                  COALESCE(has_schema_privilege(current_user, n.oid, 'CREATE'), false),
                  COALESCE(EXISTS (
                      SELECT 1 FROM pg_class c
                       WHERE c.relnamespace=n.oid AND c.relkind IN ('r','p','v','m','f')
                         AND (has_table_privilege(current_user, c.oid, 'INSERT')
                           OR has_table_privilege(current_user, c.oid, 'UPDATE')
                           OR has_table_privilege(current_user, c.oid, 'DELETE')
                           OR has_table_privilege(current_user, c.oid, 'TRUNCATE')
                           OR has_table_privilege(current_user, c.oid, 'TRIGGER'))
                  ), false),
                  COALESCE(EXISTS (
                      SELECT 1 FROM pg_class c
                       WHERE c.relnamespace=n.oid AND c.relkind='S'
                         AND (has_sequence_privilege(current_user, c.oid, 'USAGE')
                           OR has_sequence_privilege(current_user, c.oid, 'UPDATE'))
                  ), false)
             FROM pg_roles r
             LEFT JOIN pg_namespace n ON n.nspname=%s
            WHERE r.rolname=current_user""", (schema,)
    ).fetchone()
    if row is None:
        raise RuntimeError('PG_READER_ROLE_UNVERIFIABLE')
    if not row[5]:
        raise RuntimeError('PG_READER_SCHEMA_MISSING')
    if any(bool(value) for value in row[:5]) or bool(row[6]) or bool(row[7]) or bool(row[8]):
        raise RuntimeError('PG_READER_ROLE_HAS_WRITE_PRIVILEGES')
    return True

@contextmanager
def connection(schema, *, read_only=False, dsn=None, row_factory=None):
    if not re.fullmatch(r'v4_[a-z0-9_]{1,56}',schema): raise ValueError('INVALID_V4_PG_SCHEMA')
    with psycopg.connect(dsn or (configured_reader_dsn() if read_only else configured_dsn()),connect_timeout=5,row_factory=row_factory) as pg:
        if read_only: pg.execute('SET TRANSACTION READ ONLY')
        pg.execute("SET LOCAL statement_timeout='30s'")
        pg.execute("SET LOCAL lock_timeout='5s'")
        pg.execute(sql.SQL('SET LOCAL search_path TO {}, pg_catalog').format(sql.Identifier(schema)))
        if read_only: attest_read_role(pg, schema)
        yield pg

def create_schema(pg,schema):
    if not re.fullmatch(r'v4_[a-z0-9_]{1,56}',schema): raise ValueError('INVALID_V4_PG_SCHEMA')
    pg.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(sql.Identifier(schema)))
    reader=os.environ.get('V4_NATIVE_PG_READER_DSN')
    if reader:
        from psycopg.conninfo import conninfo_to_dict
        role=conninfo_to_dict(reader).get('user')
        if not role or pg.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(role,)).fetchone() is None:
            raise ValueError('CONFIGURED_READER_ROLE_REQUIRED')
        # Producer-owned candidate schemas expose SELECT to the configured
        # reader. Business writes continue to require the producer role.
        pg.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(schema),sql.Identifier(role)))
        pg.execute(sql.SQL('ALTER DEFAULT PRIVILEGES IN SCHEMA {} GRANT SELECT ON TABLES TO {}').format(sql.Identifier(schema),sql.Identifier(role)))
