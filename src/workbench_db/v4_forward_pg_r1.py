"""PG authoritative append-only Forward facts; JSON is migration evidence only."""
from pathlib import Path
import hashlib
import json
import re
from psycopg import sql
from psycopg.types.json import Jsonb
from .v4_native import (connection, configured_dsn,
                        configured_reader_dsn, workspace_logical_id)

CONTRACT = 'V4_FORWARD_PG_FACT_STORE_R1'

def _require_fixed_forward_storage(pg):
    expected = {
        'forward_facts': 'v4.forward_facts',
        'forward_migration_r1': 'v4.forward_migration_r1',
        'forward_schema_migration_map_r1': 'v4.forward_schema_migration_map_r1',
    }
    actual = dict(pg.execute(
        "SELECT c.relname, n.nspname || '.' || c.relname "
        "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname='v4' AND c.relname = ANY(%s)",
        (list(expected),),
    ).fetchall())
    if actual != expected:
        raise RuntimeError('V4_FORWARD_FIXED_STORAGE_MIGRATION_REQUIRED')
    guard = pg.execute("""
        SELECT t.tgname,p.proname FROM pg_trigger t
        JOIN pg_proc p ON p.oid=t.tgfoid
        WHERE t.tgrelid='v4.forward_facts'::regclass
          AND NOT t.tgisinternal AND t.tgenabled='O'
    """).fetchall()
    if ('forward_append_only_r1', 'reject_forward_fact_mutation_r1') not in guard:
        raise RuntimeError('V4_FORWARD_APPEND_ONLY_MIGRATION_REQUIRED')

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()

def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def is_legacy_forward_schema_locator(source_schema):
    """Recognize only frozen legacy locator shapes; storage remains in v4."""
    return (isinstance(source_schema, str)
            and re.fullmatch(r'v4_(?:forward|r8_forward)_[a-f0-9]{16}', source_schema) is not None)


def migrate_exact_legacy_fact(source_schema, kind, key, expected_sha256=None):
    """Move one exact legacy fact into the fixed table and record its locator."""
    if (not is_legacy_forward_schema_locator(source_schema)
            or not isinstance(kind,str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,60}',kind)
            or not isinstance(key,str)):
        raise ValueError('FORWARD_LEGACY_EXACT_LOCATOR_INVALID')
    if expected_sha256 is not None and not re.fullmatch(r'[0-9a-f]{64}',str(expected_sha256)):
        raise ValueError('FORWARD_LEGACY_EXPECTED_DIGEST_INVALID')
    with connection('v4',dsn=configured_dsn()) as pg:
        pg.execute("SELECT set_config('statement_timeout','120s',true)")
        prior=pg.execute('''SELECT workspace_namespace,payload_sha256,verification
            FROM forward_schema_migration_map_r1 WHERE source_schema=%s AND kind=%s AND fact_key=%s''',
            (source_schema,kind,key)).fetchone()
        if prior:
            namespace,stored_sha,proof=prior
            if proof.get('status')!='VERIFIED' or (expected_sha256 and stored_sha.strip()!=expected_sha256):
                raise ValueError('FORWARD_LEGACY_MIGRATION_RECEIPT_CONFLICT')
            return namespace
        aliases=pg.execute('''SELECT logical_workspace_id FROM workspace_namespace_alias_history_r1
            WHERE physical_schema=%s AND purpose='forward' AND status='ACTIVE' ''',
            (source_schema,)).fetchall()
        if aliases:
            if len(aliases)!=1:raise ValueError('FORWARD_LEGACY_NAMESPACE_ALIAS_NOT_UNIQUE')
            namespace=str(aliases[0][0])+':forward'
        else:
            namespace='legacy:'+source_schema
        source=sql.SQL('{}.forward_facts').format(sql.Identifier(source_schema))
        row=pg.execute(sql.SQL('SELECT payload,payload_sha256,source_sha256 FROM {} WHERE kind=%s AND fact_key=%s').format(source),(kind,key)).fetchone()
        if row is None:raise ValueError('FORWARD_LEGACY_EXACT_FACT_NOT_FOUND')
        payload,payload_sha,source_sha=row
        if digest(payload.encode('utf-8'))!=payload_sha or (expected_sha256 and payload_sha!=expected_sha256):
            raise ValueError('FORWARD_LEGACY_EXACT_FACT_DIGEST_MISMATCH')
        pg.execute('''INSERT INTO forward_facts(workspace_namespace,kind,fact_key,payload,payload_sha256,source_sha256)
            VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
            (namespace,kind,key,payload,payload_sha,source_sha))
        target=pg.execute('''SELECT payload,payload_sha256,source_sha256 FROM forward_facts
            WHERE workspace_namespace=%s AND kind=%s AND fact_key=%s''',(namespace,kind,key)).fetchone()
        if target!=(payload,payload_sha,source_sha):raise ValueError('FORWARD_LEGACY_TARGET_IDENTITY_CONFLICT')
        proof=Jsonb(dict(status='VERIFIED',row_count=1,source_digest=payload_sha,target_digest=payload_sha,exact_locator=True))
        pg.execute('''INSERT INTO forward_schema_migration_map_r1
            (source_schema,workspace_namespace,kind,fact_key,payload_sha256,source_sha256,target_sha256,verification)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s)''',
            (source_schema,namespace,kind,key,payload_sha,source_sha,payload_sha,proof))
        return namespace


def resolve_migrated_legacy_fact(source_schema, kind, key, expected_sha256=None):
    """Resolve an already migrated locator using the read-only v4 receipt."""
    if (not is_legacy_forward_schema_locator(source_schema)
            or not isinstance(kind,str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,60}',kind)
            or not isinstance(key,str)):
        raise ValueError('FORWARD_LEGACY_EXACT_LOCATOR_INVALID')
    if expected_sha256 is not None and not re.fullmatch(r'[0-9a-f]{64}',str(expected_sha256)):
        raise ValueError('FORWARD_LEGACY_EXPECTED_DIGEST_INVALID')
    with connection('v4',dsn=configured_reader_dsn(),read_only=True) as pg:
        row=pg.execute('''SELECT workspace_namespace,payload_sha256,target_sha256,verification
            FROM forward_schema_migration_map_r1 WHERE source_schema=%s AND kind=%s AND fact_key=%s''',
            (source_schema,kind,key)).fetchone()
        if (not row or row[3].get('status')!='VERIFIED'
                or str(row[1]).strip()!=str(row[2]).strip()
                or (expected_sha256 is not None and str(row[1]).strip()!=expected_sha256)):
            raise ValueError('FORWARD_LEGACY_FACT_NOT_MIGRATED')
        target=pg.execute('''SELECT payload_sha256 FROM forward_facts
            WHERE workspace_namespace=%s AND kind=%s AND fact_key=%s''',(row[0],kind,key)).fetchone()
        if not target or target[0].strip()!=str(row[1]).strip():
            raise ValueError('FORWARD_LEGACY_MIGRATION_TARGET_MISMATCH')
        return row[0]

class ForwardFactStore:
    def __init__(self, root, folder, *, workspace_namespace=None):
        self.root = Path(root).resolve()
        self.folder = (self.root / folder).resolve()
        if self.root.drive.upper() != 'G:' or not self.folder.is_relative_to(self.root):
            raise ValueError('FORWARD_G_ONLY_ROOT_REQUIRED')
        self.dsn = configured_dsn()
        self.schema = 'v4'
        if workspace_namespace is not None and (
                not isinstance(workspace_namespace, str)
                or not re.fullmatch(r'[A-Za-z0-9:_-]{1,160}', workspace_namespace)):
            raise ValueError('FORWARD_STABLE_NAMESPACE_INVALID')
        self.workspace_namespace = workspace_namespace or self.namespace_for(self.folder)
        with connection('v4', dsn=self.dsn) as pg:
            _require_fixed_forward_storage(pg)
            self.database_identity = self._database_identity(pg)
            if workspace_namespace is None:
                pg.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', (self.schema,))
                marker = pg.execute('SELECT receipt FROM forward_migration_r1 WHERE workspace_namespace=%s',
                                    (self.workspace_namespace,)).fetchone()
            else:
                # 固定业务命名空间不根据本地目录迁入或生成身份。
                marker = True
            if marker is None:
                # One transaction imports original raw bytes and records SHA.
                originals = []
                for path in sorted(self.folder.glob('*/*.json')):
                    if path.name.endswith('.pg.json'):
                        continue
                    raw = path.read_bytes()
                    json.loads(raw)
                    kind, key = path.parent.name, path.stem
                    pg.execute('INSERT INTO forward_facts(workspace_namespace,kind,fact_key,payload,payload_sha256,source_sha256) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING', (self.workspace_namespace,kind, key, raw.decode('utf8'), digest(raw), digest(raw)))
                    row = pg.execute('SELECT payload_sha256,payload FROM forward_facts WHERE workspace_namespace=%s AND kind=%s AND fact_key=%s', (self.workspace_namespace,kind, key)).fetchone()
                    if row != (digest(raw), raw.decode('utf8')):
                        raise ValueError('FORWARD_MIGRATION_IDENTITY_CONFLICT')
                    originals.append(dict(path=path.relative_to(self.root).as_posix(), sha256=digest(raw), bytes=len(raw), kind=kind, key=key))
                from psycopg.types.json import Jsonb
                pg.execute('INSERT INTO forward_migration_r1 VALUES(%s,%s)', (self.workspace_namespace,Jsonb(dict(contract_id=CONTRACT, workspace_namespace=self.workspace_namespace, originals=originals, original_files_unchanged=True)),))

    def _binding(self, kind, key, payload_digest):
        if not re.fullmatch('[a-z][a-z0-9_]{0,60}', kind):
            raise ValueError('FORWARD_FACT_KIND_INVALID')
        descriptor = dict(contract_id=CONTRACT, engine='postgresql', database_identity=self.database_identity, schema='v4', workspace_namespace=self.workspace_namespace, kind=kind, fact_key=key, payload_sha256=payload_digest)
        path = self.folder / kind / (digest(str(key).encode()) + '.pg.json')
        raw = canonical(descriptor)
        # The locator is descriptive only. The exact PG descriptor travels
        # inline with its Head-bound binding; no local descriptor file is
        # created or consulted by a consumer.
        return dict(path=path.relative_to(self.root).as_posix(), sha256=digest(raw),
                    bytes=len(raw), pg_descriptor=descriptor)

    @staticmethod
    def namespace_for(folder):
        path=Path(folder).resolve()
        return workspace_logical_id(path)+':forward'

    def append(self, kind, key, value, *, migration_timeout_seconds=30):
        if type(migration_timeout_seconds) is not int or not 30<=migration_timeout_seconds<=120:
            raise ValueError('FORWARD_BOUNDED_MIGRATION_TIMEOUT_REQUIRED')
        if not re.fullmatch('[a-z][a-z0-9_]{0,60}', kind):
            raise ValueError('FORWARD_FACT_KIND_INVALID')
        raw = canonical(value)
        with connection(self.schema, dsn=self.dsn) as pg:
            pg.execute("SELECT set_config('statement_timeout',%s,true)",(str(migration_timeout_seconds)+'s',))
            pg.execute('INSERT INTO forward_facts(workspace_namespace,kind,fact_key,payload,payload_sha256) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING', (self.workspace_namespace,kind, key, raw.decode(), digest(raw)))
            existing = pg.execute('SELECT payload,payload_sha256 FROM forward_facts WHERE workspace_namespace=%s AND kind=%s AND fact_key=%s', (self.workspace_namespace,kind, key)).fetchone()
            if json.loads(existing[0]) != value or digest(existing[0].encode()) != existing[1]:
                raise ValueError('FORWARD_APPEND_IDENTITY_CONFLICT')
        return self._binding(kind, key, existing[1])

    def refs(self, kind):
        with connection(self.schema, dsn=configured_reader_dsn(), read_only=True) as pg:
            rows = pg.execute('SELECT fact_key,payload_sha256 FROM forward_facts WHERE workspace_namespace=%s AND kind=%s ORDER BY fact_key COLLATE "C"', (self.workspace_namespace,kind,)).fetchall()
        return [self._binding(kind, key, sha) for key, sha in rows]

    def binding(self, kind, key):
        if not re.fullmatch('[a-z][a-z0-9_]{0,60}',kind):
            raise ValueError('FORWARD_FACT_KIND_INVALID')
        with connection(self.schema, dsn=configured_reader_dsn(), read_only=True) as pg:
            row=pg.execute('SELECT payload_sha256 FROM forward_facts WHERE workspace_namespace=%s AND kind=%s AND fact_key=%s',
                           (self.workspace_namespace,kind,key)).fetchone()
        if row is None:raise ValueError('FORWARD_PG_FACT_NOT_FOUND')
        return self._binding(kind,key,row[0])

    def read(self, binding):
        path = (self.root / binding['path']).resolve()
        if not path.is_relative_to(self.folder):
            # External historical/source bytes are resolved from the shared
            # PG ingress store after their one-time exact-source admission.
            from .v4_historical_source_ingress_pg_r1 import read_bound
            source = read_bound(self.root, binding['path'], binding['sha256'])
            if len(source['raw']) != binding.get('bytes', len(source['raw'])):
                raise ValueError('FORWARD_SOURCE_INGRESS_SIZE_MISMATCH')
            return json.loads(source['raw'])
        if path.name.endswith('.pg.json'):
            descriptor = binding.get('pg_descriptor')
            namespace=self.workspace_namespace
            if descriptor is None:
                # Legacy Head bindings may omit the inline locator. Resolve
                # their exact descriptor from PG rows, never from disk.
                kind = path.parent.name
                with connection(self.schema, dsn=configured_reader_dsn(), read_only=True) as pg:
                    rows = pg.execute('SELECT fact_key,payload_sha256 FROM forward_facts WHERE workspace_namespace=%s AND kind=%s',
                                      (self.workspace_namespace,kind)).fetchall()
                matches = []
                for fact_key, payload_sha in rows:
                    candidate = dict(contract_id=CONTRACT, engine='postgresql',
                        database_identity=self.database_identity, schema='v4',workspace_namespace=self.workspace_namespace,
                        kind=kind, fact_key=fact_key, payload_sha256=payload_sha)
                    raw_candidate = canonical(candidate)
                    candidate_path = self.folder / kind / (digest(str(fact_key).encode()) + '.pg.json')
                    if (candidate_path == path and digest(raw_candidate) == binding.get('sha256')
                            and len(raw_candidate) == binding.get('bytes')):
                        matches.append(candidate)
                if len(matches) != 1:
                    raise ValueError('FORWARD_INLINE_DESCRIPTOR_REQUIRED_NO_FILE_FALLBACK')
                descriptor = matches[0]
            raw = canonical(descriptor)
            if digest(raw) != binding.get('sha256') or len(raw) != binding.get('bytes'):
                raise ValueError('FORWARD_DESCRIPTOR_DIGEST_MISMATCH')
            if (descriptor.get('contract_id') != CONTRACT or descriptor.get('engine') != 'postgresql'
                    or descriptor.get('database_identity') != self.database_identity):
                raise ValueError('FORWARD_DESCRIPTOR_IDENTITY_MISMATCH')
            kind, key, expected = descriptor['kind'], descriptor['fact_key'], descriptor['payload_sha256']
            if (not isinstance(kind,str) or not isinstance(key,str)
                    or not re.fullmatch('[a-z][a-z0-9_]{0,60}',kind)
                    or path != (self.folder/kind/(digest(key.encode())+'.pg.json')).resolve()):
                raise ValueError('FORWARD_DESCRIPTOR_PATH_MISMATCH')
            source_schema=descriptor.get('schema')
            if source_schema=='v4':
                namespace=descriptor.get('workspace_namespace')
                if namespace!=self.workspace_namespace:raise ValueError('FORWARD_WORKSPACE_NAMESPACE_MISMATCH')
            else:
                namespace=resolve_migrated_legacy_fact(source_schema,kind,key,expected)
        else:
            kind, key, expected = path.parent.name, path.stem, binding['sha256']
        with connection('v4', dsn=configured_reader_dsn(), read_only=True) as pg:
            if self._database_identity(pg) != self.database_identity:
                raise ValueError('FORWARD_DATABASE_IDENTITY_MISMATCH')
            row = pg.execute('SELECT payload,payload_sha256 FROM forward_facts WHERE workspace_namespace=%s AND kind=%s AND fact_key=%s', (namespace,kind, key)).fetchone()
        if row is None or row[1] != expected or digest(row[0].encode()) != expected:
            raise ValueError('FORWARD_PG_FACT_DIGEST_MISMATCH')
        return json.loads(row[0])

    @staticmethod
    def _database_identity(pg):
        database,oid,host,port = pg.execute("SELECT current_database(),(SELECT oid FROM pg_database WHERE datname=current_database()),inet_server_addr()::text,inet_server_port()").fetchone()
        return dict(database=database,database_oid=oid,host=host,port=port)
