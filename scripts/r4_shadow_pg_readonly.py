"""Independent native ledger reader. No runtime, writer or grant creation."""
import hashlib,json,os,re,uuid
from pathlib import Path
import psycopg
from psycopg import sql

def check(ok,reason):
    if not ok:raise ValueError(reason)

class Reader:
    def __init__(self,pg):self.pg=pg
    def execute(self,query,params=()):return self.pg.execute(query.replace('?', '%s'),params)
    def close(self):self.pg.close()

def open_existing(path,root):
    root=Path(root).resolve();path=Path(path).resolve()
    check(os.environ.get('R4_NATIVE_ISOLATION')=='1','EXPLICIT_NATIVE_SHADOW_ISOLATION_REQUIRED')
    check(path.is_relative_to(root) or path.is_relative_to(Path('G:/codex_tmp').resolve()),'NATIVE_SHADOW_APPROVED_READER_PATH_REQUIRED')
    identity=json.loads(path.read_bytes())
    schema=identity['schema']
    check(identity.get('engine')=='postgresql' and identity.get('contract_id')=='R4_R3_NATIVE_SHADOW_LIVE_STORAGE_V1' and schema.startswith('v4_shadow_live_') and schema.replace('_','').isalnum(),'NATIVE_SHADOW_DESCRIPTOR_IDENTITY_MISMATCH')
    dsn=os.environ.get('V4_NATIVE_PG_DSN','');settings=psycopg.conninfo.conninfo_to_dict(dsn)
    check(settings.get('host') in ('127.0.0.1','localhost') and settings.get('port')=='55791' and settings.get('dbname')=='postgres' and settings.get('user')=='r4_isolated_admin','NATIVE_SHADOW_UNAPPROVED_DATABASE')
    pg=psycopg.connect(dsn,autocommit=True,connect_timeout=5)
    try:
        check(pg.execute('SHOW data_directory').fetchone()[0].replace('\\','/').casefold()=='g:/codex_tmp/full_system_r4_fbd23a6b/pg_data','NATIVE_SHADOW_UNAPPROVED_DATA_DIRECTORY')
        check(str(pg.execute('SELECT system_identifier FROM pg_control_system()').fetchone()[0])=='7695278778933357404','NATIVE_SHADOW_CLUSTER_IDENTITY_MISMATCH')
        pg.execute(sql.SQL('SET search_path TO {},pg_catalog').format(sql.Identifier(schema)))
        pg.execute('SET default_transaction_read_only=on')
        pg.execute('SET default_transaction_isolation=\'repeatable read\'')
        check(pg.execute('SELECT contract_id,schema_name,root_digest,migration_sha256 FROM shadow_live_identity WHERE singleton=1').fetchall()==[(identity['contract_id'],schema,identity['root_digest'],identity['migration_sha256'])],'NATIVE_SHADOW_SCHEMA_IDENTITY_MISMATCH')
        check(identity['migration_sha256']==hashlib.sha256((root/'migrations/v4_shadow_live_pg_r3.sql').read_bytes()).hexdigest(),'NATIVE_SHADOW_MIGRATION_DIGEST_MISMATCH')
        return Reader(pg)
    except BaseException:pg.close();raise

def schema_signature(pg,schema):
    queries=[
        ('column',"SELECT c.relname,a.attname,a.atttypid::regtype::text,a.attnotnull,a.attidentity,pg_get_expr(d.adbin,d.adrelid) FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum WHERE n.nspname=%s AND c.relkind='r' AND a.attnum>0 AND NOT a.attisdropped ORDER BY c.relname,a.attnum"),
        ('constraint',"SELECT c.relname,k.conname,k.condeferrable,k.condeferred,pg_get_constraintdef(k.oid) FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s ORDER BY c.relname,k.conname"),
        ('index',"SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname=%s ORDER BY tablename,indexname"),
        ('trigger',"SELECT c.relname,t.tgname,t.tgenabled,pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s AND NOT t.tgisinternal ORDER BY c.relname,t.tgname"),
        ('function',"SELECT p.proname,pg_get_functiondef(p.oid) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname=%s ORDER BY p.proname")]
    return [(kind,tuple(re.sub(r'\s+',' ',str(v).replace(schema,'SCHEMA')).strip() for v in row)) for kind,q in queries for row in pg.execute(q,(schema,))]

def validate_schema(reader,root,deps):
    migration=(Path(root)/deps['migration']['path']).read_bytes()
    check(len(migration)==deps['migration']['bytes'] and hashlib.sha256(migration).hexdigest()==deps['migration']['sha256'],'NATIVE_SHADOW_MIGRATION_DIGEST_MISMATCH')
    schema=reader.pg.execute('SELECT current_schema()').fetchone()[0]
    actual=schema_signature(reader.pg,schema)
    expected_schema='v4_shadow_live_oracle_'+uuid.uuid4().hex
    expected=None
    class RollbackExpected(Exception):pass
    with psycopg.connect(reader.pg.info.dsn,autocommit=True) as pg:
        try:
            with pg.transaction():
                pg.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(expected_schema)))
                pg.execute(sql.SQL('SET LOCAL search_path TO {},pg_catalog').format(sql.Identifier(expected_schema)))
                pg.execute(migration.decode('utf8'))
                expected=schema_signature(pg,expected_schema)
                raise RollbackExpected()
        except RollbackExpected:pass
        check(pg.execute('SELECT count(*) FROM pg_namespace WHERE nspname=%s',(expected_schema,)).fetchone()[0]==0,'ORACLE_EXPECTED_SCHEMA_NOT_ROLLED_BACK')
    check(actual==expected,'STORAGE_SCHEMA_SEMANTICS')
