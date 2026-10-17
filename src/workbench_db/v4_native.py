"""Native PG V4 candidate connections: explicit configuration, no fallback."""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import re
import psycopg
from psycopg import sql

CONTRACT = 'V4_NATIVE_POSTGRESQL_CONNECTION_R4'
_SCHEMA = re.compile(r'(?:v4|v4_[a-z0-9_]{1,56})')

def configured_dsn():
    # Writes must be explicit even when the same PostgreSQL instance is used.
    value=os.environ.get('V4_NATIVE_PG_DSN')
    if not value: raise RuntimeError('V4_NATIVE_PG_DSN_REQUIRED')
    return value

def configured_reader_dsn():
    """Reuse the project's existing DSN; no separate reader instance/DSN."""
    value=os.environ.get('WORKBENCH_PG_DSN')
    if not value: raise RuntimeError('WORKBENCH_PG_DSN_REQUIRED')
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
            "read": "SHARED_DATABASE_DSN_AND_READ_ONLY_TRANSACTION_REQUIRED",
            "write": "EXPLICIT_V4_NATIVE_PG_DSN_REQUIRED",
            "owner_mapping": "MUST_BE_AUTHORITY_BOUND",
        },
    }

def attest_read_role(pg, schema):
    """Attest that this transaction cannot write, irrespective of role grants."""
    mode = pg.execute('SHOW transaction_read_only').fetchone()
    if not mode or str(mode[0]).lower() != 'on':
        raise RuntimeError('PG_READER_TRANSACTION_NOT_READ_ONLY')
    return True

@contextmanager
def connection(schema, *, read_only=False, dsn=None, row_factory=None):
    if not _SCHEMA.fullmatch(schema): raise ValueError('INVALID_V4_PG_SCHEMA')
    with psycopg.connect(dsn or (configured_reader_dsn() if read_only else configured_dsn()),connect_timeout=5,row_factory=row_factory) as pg:
        if read_only: pg.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        pg.execute("SET LOCAL statement_timeout='30s'")
        pg.execute("SET LOCAL lock_timeout='5s'")
        pg.execute(sql.SQL('SET LOCAL search_path TO {}, pg_catalog').format(sql.Identifier(schema)))
        if read_only: attest_read_role(pg, schema)
        yield pg

def create_schema(pg,schema):
    if not _SCHEMA.fullmatch(schema): raise ValueError('INVALID_V4_PG_SCHEMA')
    pg.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(sql.Identifier(schema)))
