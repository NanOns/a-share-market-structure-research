"""PG authoritative append-only Forward facts; JSON is migration evidence only."""
from pathlib import Path
import hashlib
import json
import re
from .v4_native import connection, create_schema, configured_dsn, configured_reader_dsn, workspace_schema

CONTRACT = 'V4_FORWARD_PG_FACT_STORE_R1'
DDL = '''
CREATE TABLE IF NOT EXISTS forward_facts(
 kind text NOT NULL, fact_key text NOT NULL, payload text NOT NULL,
 payload_sha256 text NOT NULL, source_sha256 text,
 ordinal bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
 PRIMARY KEY(kind,fact_key));
CREATE TABLE IF NOT EXISTS forward_migration(singleton integer PRIMARY KEY CHECK(singleton=1),receipt jsonb NOT NULL);
CREATE OR REPLACE FUNCTION reject_forward_fact_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'FORWARD_FACTS_APPEND_ONLY'; END $$;
DO $$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM pg_trigger WHERE tgrelid='forward_facts'::regclass AND tgname='forward_append_only') THEN
 CREATE TRIGGER forward_append_only BEFORE UPDATE OR DELETE OR TRUNCATE ON forward_facts FOR EACH STATEMENT EXECUTE FUNCTION reject_forward_fact_mutation();
 END IF;
END $$;
'''

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

class ForwardFactStore:
    def __init__(self, root, folder):
        self.root = Path(root).resolve()
        self.folder = (self.root / folder).resolve()
        if self.root.drive.upper() != 'G:' or not self.folder.is_relative_to(self.root):
            raise ValueError('FORWARD_G_ONLY_ROOT_REQUIRED')
        self.dsn = configured_dsn()
        self.schema = workspace_schema(self.folder, 'forward')
        with connection(self.schema, dsn=self.dsn) as pg:
            create_schema(pg, self.schema)
        with connection(self.schema, dsn=self.dsn) as pg:
            pg.execute(DDL)
            self.database_identity = self._database_identity(pg)
            pg.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', (self.schema,))
            marker = pg.execute('SELECT receipt FROM forward_migration WHERE singleton=1').fetchone()
            if marker is None:
                # One transaction imports original raw bytes and records SHA.
                originals = []
                for path in sorted(self.folder.glob('*/*.json')):
                    if path.name.endswith('.pg.json'):
                        continue
                    raw = path.read_bytes()
                    json.loads(raw)
                    kind, key = path.parent.name, path.stem
                    pg.execute('INSERT INTO forward_facts(kind,fact_key,payload,payload_sha256,source_sha256) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING', (kind, key, raw.decode('utf8'), digest(raw), digest(raw)))
                    row = pg.execute('SELECT payload_sha256,payload FROM forward_facts WHERE kind=%s AND fact_key=%s', (kind, key)).fetchone()
                    if row != (digest(raw), raw.decode('utf8')):
                        raise ValueError('FORWARD_MIGRATION_IDENTITY_CONFLICT')
                    originals.append(dict(path=path.relative_to(self.root).as_posix(), sha256=digest(raw), bytes=len(raw), kind=kind, key=key))
                from psycopg.types.json import Jsonb
                pg.execute('INSERT INTO forward_migration VALUES(1,%s)', (Jsonb(dict(contract_id=CONTRACT, originals=originals, original_files_unchanged=True)),))

    def _binding(self, kind, key, payload_digest):
        if not re.fullmatch('[a-z][a-z0-9_]{0,60}', kind):
            raise ValueError('FORWARD_FACT_KIND_INVALID')
        descriptor = dict(contract_id=CONTRACT, engine='postgresql', database_identity=self.database_identity, schema=self.schema, kind=kind, fact_key=key, payload_sha256=payload_digest)
        path = self.folder / kind / (digest(str(key).encode()) + '.pg.json')
        raw = canonical(descriptor)
        # The locator is descriptive only. The exact PG descriptor travels
        # inline with its Head-bound binding; no local descriptor file is
        # created or consulted by a consumer.
        return dict(path=path.relative_to(self.root).as_posix(), sha256=digest(raw),
                    bytes=len(raw), pg_descriptor=descriptor)

    def append(self, kind, key, value, *, migration_timeout_seconds=30):
        if type(migration_timeout_seconds) is not int or not 30<=migration_timeout_seconds<=120:
            raise ValueError('FORWARD_BOUNDED_MIGRATION_TIMEOUT_REQUIRED')
        if not re.fullmatch('[a-z][a-z0-9_]{0,60}', kind):
            raise ValueError('FORWARD_FACT_KIND_INVALID')
        raw = canonical(value)
        with connection(self.schema, dsn=self.dsn) as pg:
            pg.execute("SELECT set_config('statement_timeout',%s,true)",(str(migration_timeout_seconds)+'s',))
            pg.execute('INSERT INTO forward_facts(kind,fact_key,payload,payload_sha256) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING', (kind, key, raw.decode(), digest(raw)))
            existing = pg.execute('SELECT payload,payload_sha256 FROM forward_facts WHERE kind=%s AND fact_key=%s', (kind, key)).fetchone()
            if json.loads(existing[0]) != value or digest(existing[0].encode()) != existing[1]:
                raise ValueError('FORWARD_APPEND_IDENTITY_CONFLICT')
        return self._binding(kind, key, existing[1])

    def refs(self, kind):
        with connection(self.schema, dsn=configured_reader_dsn(), read_only=True) as pg:
            rows = pg.execute('SELECT fact_key,payload_sha256 FROM forward_facts WHERE kind=%s ORDER BY fact_key COLLATE "C"', (kind,)).fetchall()
        return [self._binding(kind, key, sha) for key, sha in rows]

    def binding(self, kind, key):
        if not re.fullmatch('[a-z][a-z0-9_]{0,60}',kind):
            raise ValueError('FORWARD_FACT_KIND_INVALID')
        with connection(self.schema, dsn=configured_reader_dsn(), read_only=True) as pg:
            row=pg.execute('SELECT payload_sha256 FROM forward_facts WHERE kind=%s AND fact_key=%s',
                           (kind,key)).fetchone()
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
            if descriptor is None:
                # Legacy Head bindings may omit the inline locator. Resolve
                # their exact descriptor from PG rows, never from disk.
                kind = path.parent.name
                with connection(self.schema, dsn=configured_reader_dsn(), read_only=True) as pg:
                    rows = pg.execute('SELECT fact_key,payload_sha256 FROM forward_facts WHERE kind=%s',
                                      (kind,)).fetchall()
                matches = []
                for fact_key, payload_sha in rows:
                    candidate = dict(contract_id=CONTRACT, engine='postgresql',
                        database_identity=self.database_identity, schema=self.schema,
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
            if descriptor.get('contract_id') != CONTRACT or descriptor.get('schema') != self.schema or descriptor.get('engine') != 'postgresql' or descriptor.get('database_identity') != self.database_identity:
                raise ValueError('FORWARD_DESCRIPTOR_IDENTITY_MISMATCH')
            kind, key, expected = descriptor['kind'], descriptor['fact_key'], descriptor['payload_sha256']
            if (not isinstance(kind,str) or not isinstance(key,str)
                    or not re.fullmatch('[a-z][a-z0-9_]{0,60}',kind)
                    or path != (self.folder/kind/(digest(key.encode())+'.pg.json')).resolve()):
                raise ValueError('FORWARD_DESCRIPTOR_PATH_MISMATCH')
        else:
            kind, key, expected = path.parent.name, path.stem, binding['sha256']
        with connection(self.schema, dsn=configured_reader_dsn(), read_only=True) as pg:
            if self._database_identity(pg) != self.database_identity:
                raise ValueError('FORWARD_DATABASE_IDENTITY_MISMATCH')
            row = pg.execute('SELECT payload,payload_sha256 FROM forward_facts WHERE kind=%s AND fact_key=%s', (kind, key)).fetchone()
        if row is None or row[1] != expected or digest(row[0].encode()) != expected:
            raise ValueError('FORWARD_PG_FACT_DIGEST_MISMATCH')
        return json.loads(row[0])

    @staticmethod
    def _database_identity(pg):
        database,oid,host,port = pg.execute("SELECT current_database(),(SELECT oid FROM pg_database WHERE datname=current_database()),inet_server_addr()::text,inet_server_port()").fetchone()
        return dict(database=database,database_oid=oid,host=host,port=port)
