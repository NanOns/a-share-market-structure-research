"""Native live Shadow ledger and queue; exact descriptors and explicit isolation."""
from pathlib import Path
import copy,hashlib,json,os,uuid
import psycopg
from psycopg import sql
from .v4_native import configured_dsn
from .v4_snapshot_pg_r1 import translate

CONTRACT='R4_R3_NATIVE_SHADOW_LIVE_STORAGE_V1'
MIGRATION='migrations/v4_shadow_live_pg_r3.sql'
ROOT=Path(__file__).resolve().parents[2]
INTEGRITY_TABLES=('integrity_calendar_v2','integrity_authority_v2','integrity_activation_v2','integrity_manifest_v2','integrity_slot_v2','integrity_publication_v2','integrity_event_v2','integrity_freeze_v2','integrity_enrollment_v2','integrity_admission_v2','integrity_due_v2','integrity_evaluation_source_v2','integrity_outcome_v2','integrity_state_v2')
TABLES=set(INTEGRITY_TABLES)|{'shadow_live_identity','storage_identity','facts','publication_heads','activation_head','settlement_queue_v2'}

def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def require(value,reason):
    if not value:raise ValueError(reason)
def digest(raw):return hashlib.sha256(raw).hexdigest()

class NativeConnection:
    """Existing bounded query protocol, executed exclusively by psycopg."""
    def __init__(self,pg):self.pg=pg
    def execute(self,query,params=()):
        require('sqlite_master' not in query.casefold() and not query.lstrip().upper().startswith(('PRAGMA','BEGIN IMMEDIATE')),'NATIVE_PG_QUERY_REQUIRED')
        return self.pg.execute(translate(query),params)
    def close(self):self.pg.close()

class NativeShadowDatabase:
    engine='postgresql'
    artifact_prefix='pg-shadow:'
    def __init__(self,controller,path):
        # This former writer targeted a separately provisioned PostgreSQL
        # instance and a path-derived schema.  V4 storage is now confined to
        # market_research.v4; never create the legacy shadow namespace.
        raise RuntimeError('V4_SINGLE_SCHEMA_SHADOW_STORAGE_MIGRATION_REQUIRED')
        controller.guard();self.controller=controller
        root=Path(controller.root).resolve();self.path=Path(path).resolve()
        require(os.environ.get('R4_NATIVE_ISOLATION')=='1','EXPLICIT_NATIVE_SHADOW_ISOLATION_REQUIRED')
        temporary_root=os.environ.get('TMPDIR') or os.environ.get('TEMP') or os.environ.get('TMP')
        require(root==ROOT or (temporary_root and root.is_relative_to(Path(temporary_root).resolve())),'NATIVE_SHADOW_APPROVED_ENGINEERING_ROOT_REQUIRED')
        allowed=(root/controller.storage['simulation_root' if controller.simulation else 'real_root']).resolve()
        require(allowed.is_relative_to(root) and self.path.is_relative_to(allowed) and self.path.name.endswith('.pg.json'),'STORAGE_IDENTITY_NOT_ACCEPTED')
        require(self.path==(root/controller.grant['storage_identity']['database_path']).resolve(),'EXACT_STORAGE_IDENTITY_REQUIRED')
        require(controller.storage.get('engine')=='postgresql' and controller.storage.get('contract_id')==CONTRACT,'NATIVE_SHADOW_STORAGE_CONTRACT_REQUIRED_NO_FALLBACK')
        ref=controller.deps['migration'];require(ref['path']==MIGRATION,'NATIVE_SHADOW_MIGRATION_REQUIRED')
        migration=(root/MIGRATION).read_bytes();require(digest(migration)==ref['sha256'] and len(migration)==ref['bytes'],'NATIVE_SHADOW_MIGRATION_DIGEST_MISMATCH')
        self.schema='v4_shadow_live_'+digest(str(self.path).casefold().encode())[:24]
        self.identity=dict(contract_id=CONTRACT,engine='postgresql',schema=self.schema,root_digest=digest(str(root).casefold().encode()),migration_sha256=digest(migration))
        if self.path.exists():require(json.loads(self.path.read_bytes())==self.identity,'NATIVE_SHADOW_DESCRIPTOR_IDENTITY_MISMATCH')
        dsn=configured_dsn();settings=psycopg.conninfo.conninfo_to_dict(dsn)
        require(settings.get('host') in ('127.0.0.1','localhost') and settings.get('port')=='55791' and settings.get('dbname')=='postgres' and settings.get('user')=='r4_isolated_admin','NATIVE_SHADOW_UNAPPROVED_DATABASE')
        self.pg=psycopg.connect(dsn,connect_timeout=5,autocommit=True)
        try:
            # The engineering writer cannot interpret an arbitrary deployment DSN.
            require(self.pg.info.host in ('127.0.0.1','localhost') and self.pg.info.port==55791 and self.pg.info.dbname=='postgres' and self.pg.info.user=='r4_isolated_admin','NATIVE_SHADOW_UNAPPROVED_DATABASE')
            data_directory=self.pg.execute('SHOW data_directory').fetchone()[0]
            approved_data_directory=os.environ.get('R4_NATIVE_SHADOW_DATA_DIRECTORY')
            require(approved_data_directory and Path(data_directory).resolve()==Path(approved_data_directory).resolve(),'NATIVE_SHADOW_UNAPPROVED_DATA_DIRECTORY')
            require(str(self.pg.execute('SELECT system_identifier FROM pg_control_system()').fetchone()[0])=='7695278778933357404','NATIVE_SHADOW_CLUSTER_IDENTITY_MISMATCH')
            self.pg.execute(sql.SQL('SET search_path TO {},pg_catalog').format(sql.Identifier(self.schema)))
            self.pg.execute("SET statement_timeout='30s'");self.pg.execute("SET lock_timeout='5s'")
            with self.pg.transaction():
                self.pg.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',(self.schema,))
                exists=self.pg.execute('SELECT 1 FROM pg_namespace WHERE nspname=%s',(self.schema,)).fetchone()
                if not exists:
                    require(not getattr(controller,'settlement_only',False),'EXISTING_ACCEPTED_OBLIGATION_DATABASE_REQUIRED')
                    self.pg.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(self.schema)))
                    self.pg.execute(migration.decode('utf8'))
                    self.pg.execute('INSERT INTO shadow_live_identity VALUES(1,%s,%s,%s,%s)',(CONTRACT,self.schema,self.identity['root_digest'],self.identity['migration_sha256']))
                tables={row[0] for row in self.pg.execute('SELECT tablename FROM pg_tables WHERE schemaname=%s',(self.schema,))}
                require(tables==TABLES,'NATIVE_SHADOW_SCHEMA_TABLE_SET_MISMATCH')
                expected=(CONTRACT,self.schema,self.identity['root_digest'],self.identity['migration_sha256'])
                require(self.pg.execute('SELECT contract_id,schema_name,root_digest,migration_sha256 FROM shadow_live_identity WHERE singleton=1').fetchall()==[expected],'NATIVE_SHADOW_SCHEMA_IDENTITY_MISMATCH')
                env=controller.activation['environment_class']
                self.pg.execute('INSERT INTO storage_identity VALUES(1,%s,%s) ON CONFLICT DO NOTHING',(env,controller.origin))
                require(self.pg.execute('SELECT environment,evidence_origin FROM storage_identity').fetchall()==[(env,controller.origin)],'STORAGE_IDENTITY_MISMATCH')
                for index,day in enumerate(controller.authority.sessions):
                    self.pg.execute('INSERT INTO integrity_calendar_v2 VALUES(%s,%s) ON CONFLICT DO NOTHING',(index,day))
                    require(self.pg.execute('SELECT trade_date FROM integrity_calendar_v2 WHERE session_no=%s',(index,)).fetchone()==(day,),'CALENDAR_IDENTITY_DRIFT')
                activation_ref=controller.accepted_activation_binding if getattr(controller,'settlement_only',False) else controller.deps['activation']
                self.pg.execute('INSERT INTO integrity_authority_v2 VALUES(%s,%s::jsonb) ON CONFLICT DO NOTHING',(controller.activation['authority_id'],canonical(activation_ref)))
                require(self.pg.execute('SELECT authority_binding FROM integrity_authority_v2 WHERE authority_id=%s',(controller.activation['authority_id'],)).fetchone()==(activation_ref,),'ACTIVATION_BINDING_DRIFT')
            self.conn=NativeConnection(self.pg)
            if not self.path.exists():
                self.path.parent.mkdir(parents=True,exist_ok=True)
                temporary=self.path.with_name(self.path.name+'.'+uuid.uuid4().hex+'.staging')
                try:
                    with temporary.open('x',encoding='utf8') as stream:stream.write(canonical(self.identity)+'\n');stream.flush();os.fsync(stream.fileno())
                    try:os.link(temporary,self.path)
                    except FileExistsError:require(json.loads(self.path.read_bytes())==self.identity,'NATIVE_SHADOW_DESCRIPTOR_IDENTITY_MISMATCH')
                finally:temporary.unlink(missing_ok=True)
        except BaseException:self.pg.close();raise

    def append(self,kind,key,value):
        p=copy.deepcopy(value)
        p.update(namespace='SHADOW_V4',execution_mode='SHADOW',evidence_origin=self.controller.origin,evidence_class='NOT_REAL_EVIDENCE' if self.controller.simulation else 'PIT_OBSERVED_REAL')
        raw=canonical(p);sha=digest(raw.encode())
        old=self.pg.execute('SELECT digest FROM facts WHERE kind=%s AND id=%s',(kind,key)).fetchone()
        if old:require(old[0]==sha,'APPEND_ONLY_IDENTITY_CONFLICT')
        else:self.pg.execute('INSERT INTO facts(kind,id,namespace,execution_mode,evidence_origin,payload,digest) VALUES(%s,%s,%s,%s,%s,%s,%s)',(kind,key,'SHADOW_V4','SHADOW',self.controller.origin,raw,sha))
        return p

    def register_evaluation_source(self,binding,rows=None):
        raw=(Path(self.controller.root)/binding['path']).read_bytes()
        require(len(raw)==binding['bytes'] and digest(raw)==binding['sha256'],'EVALUATION_SOURCE_EXACT_BYTES_REQUIRED')
        if rows is not None:require(json.loads(raw)['rows']==rows,'EVALUATION_SOURCE_ROWS_DIFFER_FROM_EXACT_BYTES')
        self.pg.execute('INSERT INTO integrity_evaluation_source_v2 VALUES(%s,%s::jsonb) ON CONFLICT DO NOTHING',(binding['sha256'],canonical(binding)))
        require(self.pg.execute('SELECT source_binding FROM integrity_evaluation_source_v2 WHERE digest=%s',(binding['sha256'],)).fetchone()==(binding,),'EVALUATION_SOURCE_BINDING_CONFLICT')

    def independent_connection(self):
        # A separate real PostgreSQL session for restart/readback/CAS checks.
        pg=psycopg.connect(self.pg.info.dsn,autocommit=True,connect_timeout=5)
        pg.execute(sql.SQL('SET search_path TO {},pg_catalog').format(sql.Identifier(self.schema)))
        return NativeConnection(pg)

    def rows(self,kind):return [json.loads(row[0]) for row in self.pg.execute('SELECT payload FROM facts WHERE kind=%s ORDER BY ordinal',(kind,))]
    def get(self,kind,key):
        row=self.pg.execute('SELECT payload FROM facts WHERE kind=%s AND id=%s',(kind,key)).fetchone();require(row is not None,'MISSING_DURABLE_RECORD');return json.loads(row[0])
    def transaction(self,fn):
        with self.pg.transaction():
            self.pg.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',(self.schema,))
            return fn()
    def close(self):self.pg.close()

def native_mode():return 'V4_NATIVE_PG_DSN' in os.environ or os.environ.get('R4_NATIVE_ISOLATION')=='1'

def qualify_simulation_dependencies(root,deps,ref):
    """Only explicit simulation fixtures may qualify current native source bytes."""
    require(native_mode() and os.environ.get('R4_NATIVE_ISOLATION')=='1','EXPLICIT_NATIVE_SHADOW_SIMULATION_REQUIRED')
    require(Path(root).resolve()==ROOT,'EXACT_ISOLATED_SHADOW_SIMULATION_ROOT_REQUIRED')
    old_storage,old_migration=deps['storage'],deps['migration']
    deps['storage']=ref('config/v4_shadow_live_pg_storage_r3.json');deps['migration']=ref(MIGRATION)
    deps['bindings']=[deps['storage'] if row==old_storage else deps['migration'] if row==old_migration else ref(row['path']) for row in deps['bindings']]
    deps['bindings'].append(ref('src/workbench_db/v4_shadow_live_pg_r3.py'))
    deps['native_engineering_storage_qualification']=dict(contract=CONTRACT,external_acceptance='NOT_GRANTED',production=False,real_maturity=False)
