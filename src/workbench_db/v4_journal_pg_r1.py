"""Copy-on-write native PG Focus journal; immutable descriptors carry identity."""
import json
from pathlib import Path
import uuid
from .v4_snapshot_pg_r1 import read
from .v4_snapshot_pg_r2 import Builder
from .v4_native import connection,workspace_logical_id
from workbench_service.v4_daily_refresh import atomic_bytes
from workbench_service.current_v4_context import canonical,digest

_JOURNAL_TABLE_SELECTS = {
    'days': 'SELECT * FROM days',
    'metadata': 'SELECT * FROM metadata',
    'day_inputs': 'SELECT * FROM day_inputs',
}
_JOURNAL_TABLE_INSERTS = {
    'days': 'INSERT INTO days VALUES(?,?,?)',
    'metadata': 'INSERT INTO metadata VALUES(?,?)',
    'day_inputs': 'INSERT INTO day_inputs VALUES(?,?)',
}

def _require_fixed_journal_registry(pg):
    expected = {
        'journal_heads': 'v4.journal_heads',
        'journal_registry_migration_map_r1': 'v4.journal_registry_migration_map_r1',
    }
    actual = dict(pg.execute(
        "SELECT c.relname, n.nspname || '.' || c.relname "
        "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname='v4' AND c.relname = ANY(%s)",
        (list(expected),),
    ).fetchall())
    if actual != expected:
        raise RuntimeError('V4_JOURNAL_REGISTRY_MIGRATION_REQUIRED')

class JournalConnection(Builder):
    def __init__(self,path,root,contract):
        self.path=Path(path);self.contract=contract
        self.release_id=uuid.uuid4().hex
        if self.path.suffix!='.json':raise ValueError('PG_JOURNAL_DESCRIPTOR_REQUIRED_NO_FALLBACK')
        super().__init__(root,self.release_id,storage_kind='journal')
        try:self._initialize(root)
        except BaseException:
            self.pg.rollback();self.pg.close();raise

    def _initialize(self,root):
        self.registry_schema='v4'
        try:relative=self.path.resolve().relative_to(Path(root).resolve()).as_posix().casefold()
        except ValueError as exc:raise ValueError('PG_JOURNAL_PATH_OUTSIDE_WORKSPACE') from exc
        self.registry_key=workspace_logical_id(root)+':journal:'+relative
        # Lock the journal identity, not the new version identity. Hold this lock
        # through the CAS and PG commit; competing constructors see the new head.
        self.pg.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(self.registry_key,))
        _require_fixed_journal_registry(self.pg)
        current=self.pg.execute('SELECT contract,descriptor FROM v4.journal_heads WHERE key=%s',(self.registry_key,)).fetchone()
        if current and current[0]!=self.contract:raise ValueError('PG_JOURNAL_CONTRACT_CONFLICT')
        previous=current[1] if current else None
        if not previous and self.path.exists():
            # A copied descriptor starts a new journal namespace from an exact
            # immutable version; it must never follow the source's moving head.
            previous=json.loads(self.path.read_bytes())
            if previous.get('journal_contract')!=self.contract:raise ValueError('PG_JOURNAL_FORK_CONTRACT_MISMATCH')
            if previous.get('registry_key')==self.registry_key:raise ValueError('PG_JOURNAL_REGISTRY_MISSING_NO_FALLBACK')
        if previous:
            with read(previous) as old:
                tables={table:old.execute(_JOURNAL_TABLE_SELECTS[table]).fetchall() for table in _JOURNAL_TABLE_SELECTS}
        else:tables=None
        self.executescript('CREATE TABLE objects(domain text,id text,name text,symbol text,state text,payload text,PRIMARY KEY(domain,id));CREATE TABLE aliases(alias text,id text,PRIMARY KEY(alias,id));CREATE TABLE members(sector text,security text,PRIMARY KEY(sector,security));CREATE TABLE days(day text PRIMARY KEY,source_digest text NOT NULL,payload text NOT NULL);CREATE TABLE metadata(key text PRIMARY KEY,value text);CREATE TABLE day_inputs(day text PRIMARY KEY,payload text NOT NULL);')
        if tables:
            for name,rows in tables.items():
                self.executemany(_JOURNAL_TABLE_INSERTS[name],rows)
    def execute(self,query,params=()):
        if query=='BEGIN IMMEDIATE':return self.pg.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(self.registry_key,))
        if query.startswith('INSERT OR REPLACE INTO metadata '):
            query=query.replace('INSERT OR REPLACE','INSERT',1)+' ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value'
        return super().execute(query,params)
    def rollback(self):self.pg.rollback()
    def commit(self):
        head=self.execute("SELECT value FROM metadata WHERE key='head'").fetchone()[0]
        day=self.execute('SELECT max(day) FROM days').fetchone()[0]
        descriptor=self.seal(dict(release_id=self.release_id,context=dict(accepted_trade_date=day),head=head,journal_contract=self.contract),consumer_binding=dict(journal_contract=self.contract,head=head,registry_schema=self.registry_schema,registry_key=self.registry_key))
        from psycopg.types.json import Jsonb
        self.pg.execute('INSERT INTO v4.journal_heads(key,contract,descriptor) VALUES(%s,%s,%s) ON CONFLICT(key) DO UPDATE SET descriptor=EXCLUDED.descriptor,updated_at=clock_timestamp()',(self.registry_key,self.contract,Jsonb(descriptor)))
        super().commit()
        self.path.parent.mkdir(parents=True,exist_ok=True);atomic_bytes(self.path,canonical(descriptor))

def open_read(path):
    p=Path(path)
    if p.suffix!='.json':raise ValueError('PG_JOURNAL_DESCRIPTOR_REQUIRED_NO_FALLBACK')
    descriptor=json.loads(p.read_bytes())
    registry_schema=descriptor.get('registry_schema');registry_key=descriptor.get('registry_key')
    if not isinstance(registry_key,str) or not isinstance(registry_schema,str):raise ValueError('PG_JOURNAL_REGISTRY_IDENTITY_MISMATCH')
    with connection('v4',read_only=True) as pg:
        if registry_schema=='v4':
            current=pg.execute('SELECT contract,descriptor FROM v4.journal_heads WHERE key=%s',(registry_key,)).fetchone()
            if not current:raise ValueError('PG_JOURNAL_REGISTRY_IDENTITY_MISMATCH')
        else:
            migrated=pg.execute('''SELECT canonical_release_id,canonical_descriptor_sha256,canonical_descriptor
                FROM v4.journal_registry_migration_map_r1
                WHERE source_schema=%s AND registry_key=%s AND legacy_release_id=%s''',
                (registry_schema,registry_key,descriptor.get('release_id'))).fetchone()
            if not migrated:raise ValueError('PG_JOURNAL_LEGACY_REGISTRY_NOT_MIGRATED')
            current=(descriptor.get('journal_contract'),migrated[2])
            if migrated[0]!=descriptor.get('release_id') or digest(canonical(current[1]))!=str(migrated[1]).strip():
                raise ValueError('PG_JOURNAL_LEGACY_REGISTRY_DESCRIPTOR_MISMATCH')
        if current[0]!=descriptor['journal_contract']:raise ValueError('PG_JOURNAL_REGISTRY_IDENTITY_MISMATCH')
    return read(current[1])
