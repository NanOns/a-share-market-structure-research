"""Real isolated PG corruption/rollback vectors; no production acceptance."""
from copy import deepcopy
import json

import psycopg
from psycopg import sql
import pytest

from workbench_db.v4_native import connection
from workbench_db.v4_snapshot_pg_r2 import Builder, read, digest, grant_verifier, verify
from workbench_db.v4_snapshot_pg_r1 import read as dispatch_read


def build(root, *, fail=False):
    db = Builder(root, 'identity-vector')
    try:
        db.executescript('CREATE TABLE objects(domain text,id text,name text,symbol text,state text,payload text,PRIMARY KEY(domain,id));CREATE TABLE aliases(alias text,id text,PRIMARY KEY(alias,id));CREATE TABLE members(sector text,security text,PRIMARY KEY(sector,security));CREATE TABLE metadata(key text PRIMARY KEY,value text);')
        db.execute('INSERT INTO objects VALUES(?,?,?,?,?,?)',
                   ('stocks', 'one', '中文', None, 'UNKNOWN', '{"amount":{"value":1,"unit":"CNY"},"quality":null}'))
        db.execute('INSERT INTO aliases VALUES(?,?)', ('SH.600000', 'one'))
        db.execute('INSERT INTO members VALUES(?,?)', ('sector', 'one'))
        db.execute('INSERT INTO metadata VALUES(?,?)', ('snapshot', '{"source":"frozen"}'))
        descriptor = db.seal(dict(release_id='identity-vector', context=dict(accepted_trade_date='2026-10-09')),
                             source_binding=dict(kind='FROZEN_ORACLE', sha256='a' * 64))
        if fail:
            raise ValueError('INJECTED_AFTER_SEAL_BEFORE_COMMIT')
        db.commit()
        return descriptor
    finally:
        db.close()


def test_read_dispatch_and_repeatable_read(tmp_path):
    descriptor = build(tmp_path)
    with dispatch_read(descriptor) as reader:
        assert reader.execute('SHOW transaction_isolation').fetchone() == ('repeatable read',)
        assert reader.execute('SHOW transaction_read_only').fetchone() == ('on',)
        assert reader.execute('SELECT count(*) FROM objects').fetchone() == (1,)
    assert all(table['rows'] == 1 for table in descriptor['content_manifest']['tables'].values())
    with pytest.raises(psycopg.Error, match='IMMUTABLE'):
        with connection(descriptor['schema']) as pg:
            pg.execute('UPDATE objects SET name=%s', ('changed',))


@pytest.mark.parametrize('table,mutation', [
    ('objects', "UPDATE objects SET payload='{\"amount\":{\"value\":1,\"unit\":\"shares\"},\"quality\":null}'"),
    ('objects', "UPDATE objects SET symbol=''"),
    ('objects', "UPDATE objects SET payload='{\"amount\":{\"value\":1.00000000000000000001,\"unit\":\"CNY\"},\"quality\":null}'"),
    ('aliases', "UPDATE aliases SET alias='other'"),
    ('members', "DELETE FROM members"),
    ('metadata', "UPDATE metadata SET value='changed'"),
])
def test_admin_bypass_dml_cannot_preserve_identity(tmp_path, table, mutation):
    descriptor = build(tmp_path)
    # Explicit corruption of disposable test schema only, bypassing trigger.
    with connection(descriptor['schema']) as pg:
        pg.execute(sql.SQL('ALTER TABLE {} DISABLE TRIGGER immutable_snapshot').format(sql.Identifier(table)))
        pg.execute(mutation)
    with pytest.raises(ValueError, match='CONTENT_IDENTITY_MISMATCH'):
        with read(descriptor):
            pass


@pytest.mark.parametrize('table', ['objects', 'aliases', 'members', 'metadata'])
def test_partial_restore_missing_table_fails_closed(tmp_path, table):
    descriptor = build(tmp_path)
    with connection(descriptor['schema']) as pg:
        pg.execute(sql.SQL('DROP TABLE {}').format(sql.Identifier(table)))
    with pytest.raises(ValueError, match='TABLE_SCHEMA_MISMATCH'):
        with read(descriptor):
            pass


@pytest.mark.parametrize('field', ['database_identity', 'schema', 'content_manifest'])
def test_descriptor_tamper_rejected(tmp_path, field):
    descriptor = build(tmp_path)
    bad = deepcopy(descriptor)
    if field == 'database_identity': bad[field]['system_identifier'] = '0'
    elif field == 'schema': bad[field] = 'v4_other_schema'
    else: bad[field]['tables']['objects']['rows'] = 0
    with pytest.raises((ValueError, psycopg.Error)):
        with read(bad):
            pass


def test_resigned_wrong_instance_rejected_before_content(tmp_path):
    descriptor = build(tmp_path)
    bad = deepcopy(descriptor)
    bad['database_identity']['database_oid'] = '0'
    bad['logical_digest'] = digest({k: v for k, v in bad.items() if k != 'logical_digest'})
    with pytest.raises(ValueError, match='DATABASE_IDENTITY_MISMATCH'):
        with read(bad):
            pass


def test_schema_type_change_rejected(tmp_path):
    descriptor = build(tmp_path)
    with connection(descriptor['schema']) as pg:
        pg.execute('ALTER TABLE objects ALTER COLUMN symbol TYPE varchar')
    with pytest.raises(ValueError, match='TABLE_SCHEMA_MISMATCH'):
        with read(descriptor):
            pass


def test_seal_failure_rolls_back_all_tables(tmp_path):
    with pytest.raises(ValueError, match='INJECTED'):
        build(tmp_path, fail=True)
    # Same namespace can be created after rolled-back schema+identity+triggers.
    descriptor = build(tmp_path)
    with read(descriptor) as reader:
        assert reader.execute('SELECT count(*) FROM snapshot_identity').fetchone() == (1,)


def test_wrong_schema_with_valid_content_rejected(tmp_path):
    first = build(tmp_path / 'first'); second = build(tmp_path / 'second')
    assert first['content_manifest'] == second['content_manifest']
    bad = dict(first, schema=second['schema'])
    with pytest.raises(ValueError, match='IDENTITY_MISMATCH'):
        with read(bad):
            pass


def test_least_privileged_reader_and_write_denial(tmp_path):
    import uuid
    descriptor = build(tmp_path)
    role = 'r4_verify_' + uuid.uuid4().hex[:16]
    with connection(descriptor['schema']) as pg:
        pg.execute(sql.SQL('CREATE ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS').format(sql.Identifier(role)))
        grant_verifier(pg, descriptor['schema'], role)
    with connection(descriptor['schema'], read_only=True) as pg:
        pg.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(role)))
        verify(pg, descriptor)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with connection(descriptor['schema']) as pg:
            pg.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(role)))
            pg.execute('UPDATE objects SET name=%s', ('forbidden',))
    with pytest.raises(ValueError, match='LEAST_PRIVILEGE'):
        with connection(descriptor['schema']) as pg:
            grant_verifier(pg, descriptor['schema'], pg.info.user)


def test_duplicate_payload_keys_rejected_even_with_same_last_value(tmp_path):
    descriptor=build(tmp_path)
    with connection(descriptor['schema']) as pg:
        pg.execute('ALTER TABLE objects DISABLE TRIGGER immutable_snapshot')
        pg.execute("UPDATE objects SET payload='{\"quality\":1,\"amount\":{\"value\":1,\"unit\":\"CNY\"},\"quality\":null}'")
    with pytest.raises(ValueError,match='DUPLICATE_JSON_KEY'):
        with read(descriptor):pass
