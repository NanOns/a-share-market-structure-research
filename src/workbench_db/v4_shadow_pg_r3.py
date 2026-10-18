"""Fixed-v4 immutable Shadow readback exports.

Exports are keyed by their complete logical digest in versioned relations under
the sole business schema. Readers pin the current database and verify every
fact before exposing a read transaction.
"""
from contextlib import contextmanager
import json

from .v4_native import connection
from .v4_snapshot_pg_r2 import database_identity, digest, canonical
from .v4_shadow_pg_r1 import ReadTransaction
from psycopg.types.json import Jsonb

CONTRACT = 'V4_PG_SHADOW_READBACK_R3'
FIELDS = {'contract_id', 'engine', 'schema', 'logical_digest',
          'database_identity', 'content_digest'}


def _records(records, evidence_origin):
    rows = sorted(records, key=lambda r: (r['kind'], r['id']))
    if len({(r['kind'], r['id']) for r in rows}) != len(rows):
        raise ValueError('SHADOW_DUPLICATE_FACT')
    for row in rows:
        payload = row['payload']
        if not isinstance(payload, dict) or any(
                payload.get(k) != v for k, v in (
                    ('namespace', 'SHADOW_V4'), ('execution_mode', 'SHADOW'),
                    ('evidence_origin', evidence_origin))):
            raise ValueError('SHADOW_FACT_IDENTITY_MISMATCH')
    return rows


def content_digest(pg, logical_digest):
    identity = pg.execute(
        'SELECT environment,evidence_origin FROM v4.shadow_readback_identity_r1 '
        'WHERE logical_digest=%s', (logical_digest,)).fetchone()
    if identity is None:
        raise ValueError('SHADOW_READBACK_IDENTITY_MISSING')
    environment, evidence_origin = identity
    rows = []
    for kind, ident, namespace, mode, origin, payload, checksum in pg.execute(
            'SELECT kind,id,namespace,execution_mode,evidence_origin,payload,digest '
            'FROM v4.shadow_readback_facts_r1 WHERE logical_digest=%s '
            'ORDER BY kind COLLATE "C",id COLLATE "C"', (logical_digest,)):
        value = json.loads(payload)
        if digest(value) != checksum:
            raise ValueError('SHADOW_FACT_CONTENT_MISMATCH')
        expected = ('SHADOW_V4', 'SHADOW', evidence_origin)
        if (namespace, mode, origin) != expected or any(
                value.get(k) != v for k, v in zip(
                    ('namespace', 'execution_mode', 'evidence_origin'), expected)):
            raise ValueError('SHADOW_FACT_IDENTITY_MISMATCH')
        rows.append(dict(kind=kind, id=ident, payload=value))
    return digest(dict(environment=environment, evidence_origin=evidence_origin,
                       records=rows))


def verify(pg, descriptor):
    if (set(descriptor) != FIELDS or descriptor.get('contract_id') != CONTRACT
            or descriptor.get('engine') != 'postgresql' or descriptor.get('schema') != 'v4'):
        raise ValueError('PG_SHADOW_R3_FIXED_V4_BINDING_REQUIRED')
    if digest({k: v for k, v in descriptor.items() if k != 'logical_digest'}) != descriptor['logical_digest']:
        raise ValueError('SHADOW_DESCRIPTOR_IDENTITY_MISMATCH')
    if database_identity(pg) != descriptor['database_identity']:
        raise ValueError('SHADOW_DATABASE_IDENTITY_MISMATCH')
    row = pg.execute(
        'SELECT content_digest,database_identity,contract_id '
        'FROM v4.shadow_readback_identity_r1 WHERE logical_digest=%s',
        (descriptor['logical_digest'],)).fetchone()
    if row != (descriptor['content_digest'], descriptor['database_identity'], CONTRACT):
        raise ValueError('SHADOW_READBACK_IDENTITY_MISMATCH')
    if content_digest(pg, descriptor['logical_digest']) != descriptor['content_digest']:
        raise ValueError('SHADOW_EXPORT_CONTENT_MISMATCH')


def build_readback(root, records, *, environment, evidence_origin):
    del root  # Root remains part of the API for compatibility, never a storage locator.
    if (environment, evidence_origin) not in (
            ('REAL', 'PIT_OBSERVED'),
            ('ACTIVATION_SIMULATION', 'ACTIVATION_SIMULATION')):
        raise ValueError('SHADOW_STORAGE_ORIGIN_INVALID')
    rows = _records(records, evidence_origin)
    checksum = digest(dict(environment=environment, evidence_origin=evidence_origin,
                           records=rows))
    with connection('v4') as pg:
        db_identity = database_identity(pg)
        descriptor = dict(contract_id=CONTRACT, engine='postgresql', schema='v4',
                          content_digest=checksum, database_identity=db_identity)
        descriptor['logical_digest'] = digest(descriptor)
        existing = pg.execute(
            'SELECT content_digest,database_identity,contract_id '
            'FROM v4.shadow_readback_identity_r1 WHERE logical_digest=%s',
            (descriptor['logical_digest'],)).fetchone()
        if existing is not None:
            verify(pg, descriptor)
            return descriptor
        pg.execute(
            'INSERT INTO v4.shadow_readback_identity_r1 '
            '(logical_digest,contract_id,content_digest,database_identity,environment,evidence_origin) '
            'VALUES (%s,%s,%s,%s,%s,%s)',
            (descriptor['logical_digest'], CONTRACT, checksum, Jsonb(db_identity),
             environment, evidence_origin))
        for row in rows:
            payload = row['payload']
            pg.execute(
                'INSERT INTO v4.shadow_readback_facts_r1 '
                '(logical_digest,kind,id,namespace,execution_mode,evidence_origin,payload,digest) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                (descriptor['logical_digest'], row['kind'], row['id'], 'SHADOW_V4',
                 'SHADOW', evidence_origin, canonical(payload).decode(), digest(payload)))
        verify(pg, descriptor)
    return descriptor


@contextmanager
def read(descriptor):
    if descriptor.get('contract_id') != CONTRACT or descriptor.get('schema') != 'v4':
        raise ValueError('PG_SHADOW_R3_FIXED_V4_BINDING_REQUIRED')
    with connection('v4', read_only=True) as pg:
        pg.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        verify(pg, descriptor)
        yield ReadTransaction(pg)
