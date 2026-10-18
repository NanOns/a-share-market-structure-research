"""Shadow R2 pins database provenance and verifies the complete export."""
import hashlib
from contextlib import contextmanager
import json

import psycopg
from psycopg import sql

from .v4_native import configured_dsn, connection, create_schema
from .v4_snapshot_pg_r2 import database_identity, digest, canonical
from .v4_shadow_pg_r1 import ReadTransaction

CONTRACT = 'V4_PG_SHADOW_READBACK_R2'
FIELDS = {'contract_id', 'engine', 'schema', 'logical_digest', 'database_identity', 'content_digest'}


def content_digest(pg):
    origin = pg.execute('SELECT environment,evidence_origin FROM storage_identity ORDER BY singleton').fetchall()
    if len(origin) != 1:
        raise ValueError('SHADOW_STORAGE_IDENTITY_MISMATCH')
    records = []
    for kind, ident, namespace, mode, evidence_origin, payload, checksum in pg.execute(
            'SELECT kind,id,namespace,execution_mode,evidence_origin,payload,digest '
            'FROM facts ORDER BY kind COLLATE "C",id COLLATE "C"'):
        value = json.loads(payload)
        if digest(value) != checksum:
            raise ValueError('SHADOW_FACT_CONTENT_MISMATCH')
        expected = ('SHADOW_V4', 'SHADOW', origin[0][1])
        if (namespace, mode, evidence_origin) != expected or any(
                value.get(k) != v for k, v in zip(('namespace', 'execution_mode', 'evidence_origin'), expected)):
            raise ValueError('SHADOW_FACT_IDENTITY_MISMATCH')
        records.append(dict(kind=kind, id=ident, payload=value))
    return digest(dict(environment=origin[0][0], evidence_origin=origin[0][1], records=records))


def verify(pg, descriptor):
    if set(descriptor) != FIELDS or descriptor.get('contract_id') != CONTRACT or descriptor.get('engine') != 'postgresql':
        raise ValueError('PG_SHADOW_R2_BINDING_REQUIRED_NO_FALLBACK')
    if digest({k: v for k, v in descriptor.items() if k != 'logical_digest'}) != descriptor['logical_digest']:
        raise ValueError('SHADOW_DESCRIPTOR_IDENTITY_MISMATCH')
    if database_identity(pg) != descriptor['database_identity']:
        raise ValueError('SHADOW_DATABASE_IDENTITY_MISMATCH')
    if pg.execute('SELECT digest,contract_id FROM shadow_readback_identity').fetchall() != [(descriptor['logical_digest'], CONTRACT)]:
        raise ValueError('SHADOW_READBACK_IDENTITY_MISMATCH')
    if content_digest(pg) != descriptor['content_digest']:
        raise ValueError('SHADOW_EXPORT_CONTENT_MISMATCH')


def build_readback(root, records, *, environment, evidence_origin):
    raise RuntimeError('V4_SINGLE_SCHEMA_SHADOW_EXPORT_MIGRATION_REQUIRED')
    if (environment, evidence_origin) not in [('REAL', 'PIT_OBSERVED'),
                                              ('ACTIVATION_SIMULATION', 'ACTIVATION_SIMULATION')]:
        raise ValueError('SHADOW_STORAGE_ORIGIN_INVALID')
    rows = sorted(records, key=lambda r: (r['kind'], r['id']))
    if len({(r['kind'], r['id']) for r in rows}) != len(rows):
        raise ValueError('SHADOW_DUPLICATE_FACT')
    for row in rows:
        if any(row['payload'].get(k) != v for k, v in [('namespace', 'SHADOW_V4'),
                     ('execution_mode', 'SHADOW'), ('evidence_origin', evidence_origin)]):
            raise ValueError('SHADOW_FACT_IDENTITY_MISMATCH')
    checksum = digest(dict(environment=environment, evidence_origin=evidence_origin, records=rows))
    schema = 'v4_shadow_r2_' + hashlib.sha256((str(root) + ':' + checksum).encode()).hexdigest()[:32]
    with psycopg.connect(configured_dsn(), connect_timeout=5) as pg:
        descriptor = dict(contract_id=CONTRACT, engine='postgresql', schema=schema,
                          content_digest=checksum, database_identity=database_identity(pg))
        descriptor['logical_digest'] = digest(descriptor)
        pg.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (schema,))
        if pg.execute('SELECT to_regnamespace(%s)', (schema,)).fetchone()[0] is not None:
            pg.execute(sql.SQL('SET LOCAL search_path TO {},pg_catalog').format(sql.Identifier(schema)))
            verify(pg, descriptor)
            return descriptor
        create_schema(pg, schema)
        pg.execute(sql.SQL('SET LOCAL search_path TO {},pg_catalog').format(sql.Identifier(schema)))
        pg.execute('CREATE TABLE storage_identity(singleton integer PRIMARY KEY CHECK(singleton=1),environment text NOT NULL,evidence_origin text NOT NULL)')
        pg.execute('INSERT INTO storage_identity VALUES(1,%s,%s)', (environment, evidence_origin))
        pg.execute('CREATE TABLE facts(kind text NOT NULL,id text NOT NULL,namespace text NOT NULL,execution_mode text NOT NULL,evidence_origin text NOT NULL,payload text NOT NULL,digest text NOT NULL,PRIMARY KEY(kind,id))')
        for row in rows:
            payload = row['payload']
            pg.execute('INSERT INTO facts VALUES(%s,%s,%s,%s,%s,%s,%s)',
                       (row['kind'], row['id'], 'SHADOW_V4', 'SHADOW', evidence_origin, canonical(payload).decode(), digest(payload)))
        pg.execute('CREATE TABLE shadow_readback_identity(digest text PRIMARY KEY,contract_id text NOT NULL)')
        pg.execute('INSERT INTO shadow_readback_identity VALUES(%s,%s)', (descriptor['logical_digest'], CONTRACT))
        pg.execute("CREATE FUNCTION reject_shadow_readback_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'IMMUTABLE_SHADOW_READBACK'; END $$")
        for table in ('storage_identity', 'facts', 'shadow_readback_identity'):
            pg.execute(sql.SQL('CREATE TRIGGER immutable_shadow BEFORE INSERT OR UPDATE OR DELETE OR TRUNCATE ON {} FOR EACH STATEMENT EXECUTE FUNCTION reject_shadow_readback_mutation()').format(sql.Identifier(table)))
        verify(pg, descriptor)
    return descriptor


@contextmanager
def read(descriptor):
    if descriptor.get('contract_id') != CONTRACT:
        raise ValueError('PG_SHADOW_R2_BINDING_REQUIRED_NO_FALLBACK')
    with connection(descriptor['schema'], read_only=True) as pg:
        pg.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        verify(pg, descriptor)
        yield ReadTransaction(pg)
