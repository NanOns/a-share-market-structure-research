"""Native PG V4 candidate connections: explicit configuration, no fallback."""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import re
import psycopg
from psycopg import sql

CONTRACT = 'V4_NATIVE_POSTGRESQL_CONNECTION_R1'

def configured_dsn():
    value=os.environ.get('V4_NATIVE_PG_DSN')
    if not value: raise RuntimeError('V4_NATIVE_PG_DSN_REQUIRED_NO_FALLBACK')
    return value

def workspace_schema(root, purpose):
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,24}',purpose): raise ValueError('INVALID_PG_PURPOSE')
    return 'v4_'+purpose+'_'+hashlib.sha256(str(Path(root).resolve()).casefold().encode()).hexdigest()[:16]

@contextmanager
def connection(schema, *, read_only=False, dsn=None, row_factory=None):
    if not re.fullmatch(r'v4_[a-z0-9_]{1,56}',schema): raise ValueError('INVALID_V4_PG_SCHEMA')
    with psycopg.connect(dsn or configured_dsn(),connect_timeout=5,row_factory=row_factory) as pg:
        pg.execute("SET LOCAL statement_timeout='30s'")
        pg.execute("SET LOCAL lock_timeout='5s'")
        pg.execute(sql.SQL('SET LOCAL search_path TO {}, pg_catalog').format(sql.Identifier(schema)))
        if read_only: pg.execute('SET TRANSACTION READ ONLY')
        yield pg

def create_schema(pg,schema):
    if not re.fullmatch(r'v4_[a-z0-9_]{1,56}',schema): raise ValueError('INVALID_V4_PG_SCHEMA')
    pg.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(sql.Identifier(schema)))
