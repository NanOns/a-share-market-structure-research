"""R2 content-addressed snapshots. R1 descriptors remain historical bindings.

Every read verifies the four tables in one repeatable-read transaction. Restores
to another database require a new descriptor and independent admission.
"""
from contextlib import contextmanager
import hashlib
import json
import uuid
from decimal import Decimal
from fractions import Fraction

from psycopg import sql

from .v4_native import connection
from .v4_snapshot_pg_r1 import Builder as LegacyBuilder, ReadTransaction

CONTRACT = 'V4_PG_RESEARCH_SNAPSHOT_R2'
DIGEST_CONTRACT = 'V4_PG_CANONICAL_FOUR_TABLES_R1'
TABLES = {
    'objects': ('domain', 'id', 'name', 'symbol', 'state', 'payload'),
    'aliases': ('alias', 'id'),
    'members': ('sector', 'security'),
    'metadata': ('key', 'value'),
}
ORDER = {'objects': ('domain', 'id'), 'aliases': ('alias', 'id'),
         'members': ('sector', 'security'), 'metadata': ('key',),
         'bars': ('security', 'day'), 'days': ('day',), 'day_inputs': ('day',)}
FIELDS = {'contract_id', 'engine', 'schema', 'logical_digest', 'release_id', 'T0',
          'content_manifest', 'database_identity'}
EXTRA_TABLES = {
    'snapshot': {},
    'series': {'bars': (('security', 'text'), ('day', 'date'), ('payload', 'text'))},
    'journal': {'days': (('day', 'text'), ('source_digest', 'text'), ('payload', 'text')),
                'day_inputs': (('day', 'text'), ('payload', 'text'))},
}
EXTRA_FIELDS = {
    'snapshot': set(),
    'series': {'series_contract_id', 'source_digest', 'bar_count', 'symbol_count'},
    'journal': {'journal_contract', 'head', 'registry_schema', 'registry_key'},
}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def canonical_json_payload(raw):
    """Typed JSON tree: exact decimal numbers, no duplicate-key ambiguity."""
    def pairs(items):
        value={}
        for key,item in items:
            if key in value:raise ValueError('PG_SNAPSHOT_DUPLICATE_JSON_KEY')
            value[key]=item
        return value
    def invalid(value):raise ValueError('PG_SNAPSHOT_NONFINITE_JSON_NUMBER')
    parsed=json.loads(raw,parse_float=Decimal,object_pairs_hook=pairs,parse_constant=invalid)
    def typed(value):
        if value is None:return ['null']
        if type(value) is bool:return ['boolean',value]
        if isinstance(value,str):return ['string',value]
        if isinstance(value,(int,Decimal)):
            if isinstance(value,Decimal) and abs(value.as_tuple().exponent)>1000:
                raise ValueError('PG_SNAPSHOT_JSON_NUMBER_BOUND')
            number=Fraction(value)
            if max(number.numerator.bit_length(),number.denominator.bit_length())>4096:
                raise ValueError('PG_SNAPSHOT_JSON_NUMBER_BOUND')
            return ['number',str(number.numerator),str(number.denominator)]
        if isinstance(value,list):return ['array',[typed(x) for x in value]]
        return ['object',[[k,typed(value[k])] for k in sorted(value)]]
    return typed(parsed)


def database_identity(pg):
    # No DSN/password/physical path is persisted. pg_control_system requires
    # explicit EXECUTE for a non-superuser verifier; denial is fail-closed.
    system, name, oid = pg.execute(
        'SELECT system_identifier::text,current_database(),'
        '(SELECT oid::text FROM pg_database WHERE datname=current_database()) '
        'FROM pg_control_system()').fetchone()
    return dict(system_identifier=system, database=name, database_oid=oid)


def grant_verifier(pg, schema, role, tables=(*TABLES, 'snapshot_identity')):
    """Explicit candidate grant, only to a role with no elevated membership.

    Caller owns provisioning; this never creates/changes a production role.
    The identity function exposes only cluster identity. No DML/DDL is granted.
    """
    allowed = pg.execute(
        'SELECT NOT (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls) '
        'FROM pg_roles WHERE rolname=%s', (role,)).fetchone()
    elevated = pg.execute(
        'SELECT rolname FROM pg_roles WHERE rolname<>%s '
        'AND pg_has_role(%s,oid,\'MEMBER\')', (role,role)).fetchall() if allowed else []
    if allowed != (True,) or elevated:
        raise ValueError('PG_VERIFIER_LEAST_PRIVILEGE_REQUIRED')
    pg.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(schema), sql.Identifier(role)))
    for table in tables:
        pg.execute(sql.SQL('GRANT SELECT ON {}.{} TO {}').format(sql.Identifier(schema), sql.Identifier(table), sql.Identifier(role)))
    pg.execute(sql.SQL('GRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO {}').format(sql.Identifier(role)))


def table_manifest(pg, schema, storage_kind='snapshot'):
    if storage_kind not in EXTRA_TABLES:
        raise ValueError('PG_SNAPSHOT_STORAGE_CONTRACT_REQUIRED')
    result = {}
    definitions = {t: tuple((c, 'text') for c in columns) for t, columns in TABLES.items()}
    definitions.update(EXTRA_TABLES[storage_kind])
    for table, definition in definitions.items():
        columns = tuple(c for c, _ in definition)
        actual = pg.execute(
            'SELECT column_name,data_type FROM information_schema.columns '
            'WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position',
            (schema, table)).fetchall()
        if actual != list(definition):
            raise ValueError('PG_SNAPSHOT_TABLE_SCHEMA_MISMATCH:' + table)
        query = sql.SQL('SELECT {} FROM {}.{} ORDER BY {}').format(
            sql.SQL(',').join(map(sql.Identifier, columns)),
            sql.Identifier(schema), sql.Identifier(table),
            sql.SQL(',').join(sql.SQL('{} COLLATE "C" NULLS FIRST' if dict(definition)[column]=='text' else '{} NULLS FIRST').format(
                sql.Identifier(column)) for column in ORDER.get(table, (columns[0],))))
        h = hashlib.sha256(); count = 0
        with pg.cursor(name='snapshot_verify_' + uuid.uuid4().hex) as cursor:
            cursor.execute(query)
            for row in cursor:
                values = [value.isoformat() if kind == 'date' and value is not None else value
                          for value, (_, kind) in zip(row, definition)]
                # JSON values are parsed while NULL, text, number, empty string
                # and UNKNOWN remain distinct. units in payload are included.
                if table == 'objects' and values[-1] is not None:
                    values[-1] = canonical_json_payload(values[-1])
                h.update(canonical(values) + b'\n'); count += 1
        result[table] = dict(columns=list(columns), types=[kind for _, kind in definition],
                             rows=count, digest=h.hexdigest())
    return result


class Builder(LegacyBuilder):
    def __init__(self, root, release_id, *, storage_kind='snapshot'):
        # A versioned namespace never upgrades an existing R1 schema in place.
        if storage_kind not in EXTRA_TABLES:raise ValueError('PG_SNAPSHOT_STORAGE_CONTRACT_REQUIRED')
        self.storage_kind=storage_kind
        super().__init__(root, CONTRACT + ':' + storage_kind + ':' + release_id)

    def seal(self, meta, *, source_binding=None, consumer_binding=None):
        source_binding = source_binding or dict(kind='MANIFEST_BOUND_SOURCES',
                                                manifest_sha256=digest(meta))
        consumer_binding=consumer_binding or {}
        if set(consumer_binding)!=EXTRA_FIELDS[self.storage_kind]:
            raise ValueError('PG_SNAPSHOT_CONSUMER_BINDING_REQUIRED')
        manifest = dict(contract_id=DIGEST_CONTRACT, storage_kind=self.storage_kind, metadata=meta,
                        metadata_sha256=digest(meta), source_binding=source_binding,
                        tables=table_manifest(self.pg, self.schema, self.storage_kind))
        identity = database_identity(self.pg)
        descriptor = dict(contract_id=CONTRACT, engine='postgresql', schema=self.schema,
                          release_id=meta['release_id'], T0=meta['context']['accepted_trade_date'],
                          content_manifest=manifest, database_identity=identity)
        descriptor.update(consumer_binding)
        descriptor['logical_digest'] = digest(descriptor)
        self.pg.execute('CREATE TABLE snapshot_identity(digest text PRIMARY KEY,contract_id text NOT NULL,descriptor text NOT NULL)')
        self.pg.execute('INSERT INTO snapshot_identity VALUES(%s,%s,%s)',
                        (descriptor['logical_digest'], CONTRACT, canonical(descriptor).decode()))
        self.pg.execute("CREATE FUNCTION reject_snapshot_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'IMMUTABLE_RESEARCH_SNAPSHOT'; END $$")
        for table in (*TABLES, *EXTRA_TABLES[self.storage_kind], 'snapshot_identity'):
            self.pg.execute(sql.SQL('CREATE TRIGGER immutable_snapshot BEFORE INSERT OR UPDATE OR DELETE OR TRUNCATE ON {} FOR EACH STATEMENT EXECUTE FUNCTION reject_snapshot_mutation()').format(sql.Identifier(table)))
        verify(self.pg, descriptor)  # independent rescan before commit
        return descriptor


def verify(pg, descriptor):
    storage_kind=descriptor.get('content_manifest',{}).get('storage_kind','snapshot')
    if storage_kind not in EXTRA_FIELDS or set(descriptor) != FIELDS | EXTRA_FIELDS[storage_kind] or descriptor.get('contract_id') != CONTRACT or descriptor.get('engine') != 'postgresql':
        raise ValueError('PG_SNAPSHOT_R2_BINDING_REQUIRED_NO_FALLBACK')
    if digest({k: v for k, v in descriptor.items() if k != 'logical_digest'}) != descriptor['logical_digest']:
        raise ValueError('PG_SNAPSHOT_DESCRIPTOR_IDENTITY_MISMATCH')
    if database_identity(pg) != descriptor['database_identity']:
        raise ValueError('PG_SNAPSHOT_DATABASE_IDENTITY_MISMATCH')
    rows = pg.execute('SELECT digest,contract_id,descriptor FROM snapshot_identity').fetchall()
    expected = [(descriptor['logical_digest'], CONTRACT, canonical(descriptor).decode())]
    if rows != expected:
        raise ValueError('PG_SNAPSHOT_IDENTITY_MISMATCH')
    manifest = descriptor['content_manifest']
    if manifest['contract_id'] != DIGEST_CONTRACT or digest(manifest['metadata']) != manifest['metadata_sha256']:
        raise ValueError('PG_SNAPSHOT_MANIFEST_IDENTITY_MISMATCH')
    if table_manifest(pg, descriptor['schema'], storage_kind) != manifest['tables']:
        raise ValueError('PG_SNAPSHOT_CONTENT_IDENTITY_MISMATCH')


@contextmanager
def read(descriptor):
    if descriptor.get('contract_id') != CONTRACT:
        raise ValueError('PG_SNAPSHOT_R2_BINDING_REQUIRED_NO_FALLBACK')
    with connection(descriptor['schema'], read_only=True) as pg:
        pg.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        verify(pg, descriptor)
        yield ReadTransaction(pg)
