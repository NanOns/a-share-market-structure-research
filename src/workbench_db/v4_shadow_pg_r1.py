"""Immutable Shadow readback exports; no publication heads or live writer."""
from contextlib import contextmanager
import hashlib
import json
import re

import psycopg
from psycopg import sql

from .v4_native import configured_dsn, connection, create_schema

CONTRACT = 'V4_PG_SHADOW_READBACK_R1'
FIELDS = {'contract_id', 'engine', 'schema', 'logical_digest'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def build_readback_r1(root, records, *, environment, evidence_origin):
    """Former per-export schema writer, disabled by the single-schema contract."""
    raise RuntimeError('V4_SINGLE_SCHEMA_SHADOW_EXPORT_MIGRATION_REQUIRED')
    if (environment, evidence_origin) not in [('REAL', 'PIT_OBSERVED'),
                                               ('ACTIVATION_SIMULATION', 'ACTIVATION_SIMULATION')]:
        raise ValueError('SHADOW_STORAGE_ORIGIN_INVALID')
    rows = sorted(records, key=lambda r: (r['kind'], r['id']))
    if len({(r['kind'], r['id']) for r in rows}) != len(rows):
        raise ValueError('SHADOW_DUPLICATE_FACT')
    for row in rows:
        payload = row['payload']
        if any(payload.get(k) != v for k, v in [('namespace', 'SHADOW_V4'),
                   ('execution_mode', 'SHADOW'), ('evidence_origin', evidence_origin)]):
            raise ValueError('SHADOW_FACT_IDENTITY_MISMATCH')
    digest = hashlib.sha256(canonical(dict(environment=environment, evidence_origin=evidence_origin,
                                           records=rows))).hexdigest()
    schema = 'v4_shadow_' + hashlib.sha256((str(root) + ':' + digest).encode()).hexdigest()[:32]
    descriptor = dict(contract_id=CONTRACT, engine='postgresql', schema=schema, logical_digest=digest)
    with psycopg.connect(configured_dsn(), connect_timeout=5) as pg:
        pg.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (schema,))
        exists = pg.execute('SELECT to_regnamespace(%s)', (schema,)).fetchone()[0]
        if exists is not None:
            pg.execute(sql.SQL('SET LOCAL search_path TO {},pg_catalog').format(sql.Identifier(schema)))
            if pg.execute('SELECT digest,contract_id FROM shadow_readback_identity').fetchall() != [(digest, CONTRACT)]:
                raise ValueError('SHADOW_EXPORT_IDENTITY_CONFLICT')
            return descriptor
        create_schema(pg, schema)
        pg.execute(sql.SQL('SET LOCAL search_path TO {},pg_catalog').format(sql.Identifier(schema)))
        pg.execute('CREATE TABLE storage_identity(singleton integer PRIMARY KEY CHECK(singleton=1),environment text NOT NULL,evidence_origin text NOT NULL)')
        pg.execute('INSERT INTO storage_identity VALUES(1,%s,%s)', (environment, evidence_origin))
        pg.execute('CREATE TABLE facts(kind text NOT NULL,id text NOT NULL,namespace text NOT NULL,execution_mode text NOT NULL,evidence_origin text NOT NULL,payload text NOT NULL,digest text NOT NULL,PRIMARY KEY(kind,id))')
        for row in rows:
            payload = canonical(row['payload'])
            pg.execute('INSERT INTO facts VALUES(%s,%s,%s,%s,%s,%s,%s)',
                       (row['kind'], row['id'], 'SHADOW_V4', 'SHADOW', evidence_origin,
                        payload.decode(), hashlib.sha256(payload).hexdigest()))
        pg.execute('CREATE TABLE shadow_readback_identity(digest text PRIMARY KEY,contract_id text NOT NULL)')
        pg.execute('INSERT INTO shadow_readback_identity VALUES(%s,%s)', (digest, CONTRACT))
        pg.execute("CREATE FUNCTION reject_shadow_readback_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'IMMUTABLE_SHADOW_READBACK'; END $$")
        for table in ('storage_identity', 'facts', 'shadow_readback_identity'):
            pg.execute(sql.SQL('CREATE TRIGGER immutable_shadow BEFORE INSERT OR UPDATE OR DELETE OR TRUNCATE ON {} FOR EACH STATEMENT EXECUTE FUNCTION reject_shadow_readback_mutation()').format(sql.Identifier(table)))
    return descriptor


class ReadTransaction:
    def __init__(self, pg):
        self.pg = pg

    def execute(self, query, params=()):
        return self.pg.execute(query.replace('?', '%s'), params)


def build_readback(root, records, *, environment, evidence_origin):
    from .v4_shadow_pg_r2 import build_readback as build_r2
    return build_r2(root, records, environment=environment, evidence_origin=evidence_origin)


@contextmanager
def read(descriptor):
    if descriptor.get('contract_id') == 'V4_PG_SHADOW_READBACK_R2':
        from .v4_shadow_pg_r2 import read as read_r2
        with read_r2(descriptor) as reader:
            yield reader
        return
    if set(descriptor) != FIELDS or descriptor.get('contract_id') != CONTRACT or descriptor.get('engine') != 'postgresql':
        raise ValueError('PG_SHADOW_BINDING_REQUIRED_NO_FALLBACK')
    if not re.fullmatch(r'[0-9a-f]{64}', descriptor['logical_digest']):
        raise ValueError('SHADOW_READBACK_DIGEST_INVALID')
    with connection(descriptor['schema'], read_only=True) as pg:
        pg.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        if pg.execute('SELECT digest,contract_id FROM shadow_readback_identity').fetchall() != [(descriptor['logical_digest'], CONTRACT)]:
            raise ValueError('SHADOW_READBACK_IDENTITY_MISMATCH')
        yield ReadTransaction(pg)
