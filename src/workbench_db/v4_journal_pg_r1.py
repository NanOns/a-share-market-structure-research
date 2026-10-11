"""Copy-on-write native PG Focus journal; immutable descriptors carry identity."""
import json
from pathlib import Path
import uuid
from psycopg import sql
from .v4_snapshot_pg_r1 import Builder,read
from .v4_native import workspace_schema,create_schema,connection
from workbench_service.v4_daily_refresh import atomic_bytes
from workbench_service.current_v4_context import canonical

class JournalConnection(Builder):
    def __init__(self,path,root,contract):
        self.path=Path(path);self.contract=contract
        self.release_id=uuid.uuid4().hex
        if self.path.suffix!='.json':raise ValueError('PG_JOURNAL_DESCRIPTOR_REQUIRED_NO_FALLBACK')
        super().__init__(root,self.release_id)
        try:self._initialize(root)
        except BaseException:
            self.pg.rollback();self.pg.close();raise

    def _initialize(self,root):
        self.registry_schema=workspace_schema(root,'journal_registry')
        self.registry_key=str(self.path.resolve()).casefold()
        # Lock the journal identity, not the new version identity. Hold this lock
        # through the CAS and PG commit; competing constructors see the new head.
        self.pg.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(self.registry_key,))
        create_schema(self.pg,self.registry_schema)
        self.pg.execute(sql.SQL('CREATE TABLE IF NOT EXISTS {}.journal_heads(key text PRIMARY KEY,contract text NOT NULL,descriptor jsonb NOT NULL)').format(sql.Identifier(self.registry_schema)))
        current=self.pg.execute(sql.SQL('SELECT contract,descriptor FROM {}.journal_heads WHERE key=%s').format(sql.Identifier(self.registry_schema)),(self.registry_key,)).fetchone()
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
                tables={table:old.execute('SELECT * FROM '+table).fetchall() for table in ('days','metadata','day_inputs')}
        else:tables=None
        self.executescript('CREATE TABLE objects(domain text,id text,payload text);CREATE TABLE aliases(alias text,id text);CREATE TABLE members(sector text,security text);CREATE TABLE days(day text PRIMARY KEY,source_digest text NOT NULL,payload text NOT NULL);CREATE TABLE metadata(key text PRIMARY KEY,value text);CREATE TABLE day_inputs(day text PRIMARY KEY,payload text NOT NULL);')
        if tables:
            for name,rows in tables.items():
                cols=3 if name=='days' else 2
                self.executemany('INSERT INTO '+name+' VALUES('+','.join('?' for _ in range(cols))+')',rows)
    def execute(self,query,params=()):
        if query=='BEGIN IMMEDIATE':return self.pg.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(self.registry_key,))
        if query.startswith('INSERT OR REPLACE INTO metadata '):
            query=query.replace('INSERT OR REPLACE','INSERT',1)+' ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value'
        return super().execute(query,params)
    def rollback(self):self.pg.rollback()
    def commit(self):
        head=self.execute("SELECT value FROM metadata WHERE key='head'").fetchone()[0]
        day=self.execute('SELECT max(day) FROM days').fetchone()[0]
        descriptor=self.seal(dict(release_id=self.release_id,context=dict(accepted_trade_date=day),head=head,journal_contract=self.contract))
        for table in ('days','day_inputs'):
            self.pg.execute(sql.SQL('CREATE TRIGGER immutable_snapshot BEFORE INSERT OR UPDATE OR DELETE OR TRUNCATE ON {} FOR EACH STATEMENT EXECUTE FUNCTION reject_snapshot_mutation()').format(sql.Identifier(table)))
        descriptor.update(journal_contract=self.contract,head=head,registry_schema=self.registry_schema,registry_key=self.registry_key)
        from psycopg.types.json import Jsonb
        self.pg.execute(sql.SQL('INSERT INTO {}.journal_heads VALUES(%s,%s,%s) ON CONFLICT(key) DO UPDATE SET descriptor=EXCLUDED.descriptor').format(sql.Identifier(self.registry_schema)),(self.registry_key,self.contract,Jsonb(descriptor)))
        super().commit()
        self.path.parent.mkdir(parents=True,exist_ok=True);atomic_bytes(self.path,canonical(descriptor))

def open_read(path):
    p=Path(path)
    if p.suffix!='.json':raise ValueError('PG_JOURNAL_DESCRIPTOR_REQUIRED_NO_FALLBACK')
    descriptor=json.loads(p.read_bytes())
    if descriptor['registry_key']!=str(p.resolve()).casefold():
        return read(descriptor)
    with connection(descriptor['registry_schema'],read_only=True) as pg:
        current=pg.execute('SELECT contract,descriptor FROM journal_heads WHERE key=%s',(descriptor['registry_key'],)).fetchone()
        if not current or current[0]!=descriptor['journal_contract']:raise ValueError('PG_JOURNAL_REGISTRY_IDENTITY_MISMATCH')
    return read(current[1])
