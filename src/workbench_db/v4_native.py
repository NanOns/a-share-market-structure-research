"""Native PG V4 candidate connections: explicit configuration, no fallback."""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import re
import psycopg
from psycopg import sql

CONTRACT = 'V4_NATIVE_POSTGRESQL_CONNECTION_R4'

def configured_dsn():
    # Default to the project's existing database identity for both reads and
    # writes; a V4-specific DSN remains an optional explicit override.
    value=os.environ.get('V4_NATIVE_PG_DSN') or os.environ.get('WORKBENCH_PG_DSN')
    if not value: raise RuntimeError('WORKBENCH_PG_DSN_REQUIRED')
    return value

def configured_reader_dsn():
    """Read from the existing project DB identity; connection() makes it read-only."""
    return configured_dsn()

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
    """Attest the transaction boundary, not a separate database identity."""
    exists = pg.execute(
        "SELECT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname=%s)", (schema,)
    ).fetchone()
    if not exists or not exists[0]:
        raise RuntimeError('PG_READER_SCHEMA_MISSING')
    mode = pg.execute('SHOW transaction_read_only').fetchone()
    if not mode or str(mode[0]).lower() != 'on':
        raise RuntimeError('PG_READER_TRANSACTION_NOT_READ_ONLY')
    return True

@contextmanager
def connection(schema, *, read_only=False, dsn=None, row_factory=None):
    if not re.fullmatch(r'v4_[a-z0-9_]{1,56}',schema): raise ValueError('INVALID_V4_PG_SCHEMA')
    with psycopg.connect(dsn or (configured_reader_dsn() if read_only else configured_dsn()),connect_timeout=5,row_factory=row_factory) as pg:
        if read_only: pg.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
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
