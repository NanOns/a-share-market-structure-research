"""Immutable PG Owner for dated, descriptive three-family risk changes."""
import hashlib,json
from pathlib import Path
from psycopg import sql
from psycopg.types.json import Jsonb
from .v4_native import connection,create_schema,workspace_schema
from .v4_forward_pg_r1 import ForwardFactStore

CONTRACT='V4_OPERATIONAL_RISK_PG_OWNER_R1'
RISK_INPUT_CONTRACTS=('V4_OPERATIONAL_RISK_CHANGE_R1','V4_OPERATIONAL_RISK_CHANGE_R2')

def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def digest(v):return hashlib.sha256(v if isinstance(v,bytes) else canonical(v)).hexdigest()

def schema_for_revision(root,owner_digest):
    if not isinstance(owner_digest,str) or len(owner_digest)!=64 or any(c not in '0123456789abcdef' for c in owner_digest):
        raise ValueError('OPERATIONAL_RISK_OWNER_DIGEST_INVALID')
    return 'v4'

def _install(pg,schema,family):
    if family not in ('risk_r1','priority_r1'):raise ValueError('V4_OWNER_FAMILY_INVALID')
    create_schema(pg,schema)
    versions='owner_versions_'+family;payloads='owner_payloads_'+family
    guard='owner_guard_'+family;no_truncate='owner_no_truncate_'+family
    pg.execute(f"""CREATE TABLE IF NOT EXISTS v4.{versions}(
        token text NOT NULL,T0 text NOT NULL,contract text NOT NULL,digest text NOT NULL,
        row_count integer NOT NULL,database_identity jsonb NOT NULL,sealed boolean NOT NULL DEFAULT false,
        PRIMARY KEY(token,T0))""")
    pg.execute(f"""CREATE TABLE IF NOT EXISTS v4.{payloads}(
        token text NOT NULL,T0 text NOT NULL,payload jsonb NOT NULL,payload_sha256 text NOT NULL,
        PRIMARY KEY(token,T0),FOREIGN KEY(token,T0) REFERENCES v4.{versions}(token,T0))""")
    pg.execute(f"""CREATE OR REPLACE FUNCTION v4.{guard}() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
        IF TG_TABLE_NAME='{versions}' THEN
          IF TG_OP='INSERT' AND NOT NEW.sealed THEN RETURN NEW; END IF;
          IF TG_OP='UPDATE' AND NOT OLD.sealed AND NEW.sealed AND
             (OLD.token,OLD.T0,OLD.contract,OLD.digest,OLD.row_count,OLD.database_identity)=
             (NEW.token,NEW.T0,NEW.contract,NEW.digest,NEW.row_count,NEW.database_identity) THEN RETURN NEW; END IF;
        ELSE
          IF TG_OP='INSERT' AND NOT EXISTS(
             SELECT 1 FROM v4.{versions} WHERE token=NEW.token AND T0=NEW.T0 AND sealed) THEN RETURN NEW; END IF;
        END IF;
        RAISE EXCEPTION 'OPERATIONAL_RISK_OWNER_IMMUTABLE';
      END $$""")
    pg.execute(f"""CREATE OR REPLACE FUNCTION v4.{no_truncate}() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN RAISE EXCEPTION 'OPERATIONAL_RISK_OWNER_IMMUTABLE'; END $$""")
    for table in (versions,payloads):
        pg.execute(f'DROP TRIGGER IF EXISTS {family}_immutable_guard ON v4.{table}')
        pg.execute(f'DROP TRIGGER IF EXISTS {family}_no_truncate_guard ON v4.{table}')
        pg.execute(f'CREATE TRIGGER {family}_immutable_guard BEFORE INSERT OR UPDATE OR DELETE ON v4.{table} FOR EACH ROW EXECUTE FUNCTION v4.{guard}()')
        pg.execute(f'CREATE TRIGGER {family}_no_truncate_guard BEFORE TRUNCATE ON v4.{table} FOR EACH STATEMENT EXECUTE FUNCTION v4.{no_truncate}()')

def prepare(root,token,day,payload):
    root=Path(root).resolve()
    if payload.get('contract_id') not in RISK_INPUT_CONTRACTS or payload.get('T0')!=day:raise ValueError('OPERATIONAL_RISK_PAYLOAD_CONTEXT_INVALID')
    expected={'STOCK_STRUCTURE_RISK','SECTOR_ECOLOGY_RISK','MARKET_PRESSURE_RISK'}
    if set(payload.get('families',{}))!=expected:raise ValueError('OPERATIONAL_RISK_FAMILY_SET_INVALID')
    if any(item.get('T0')!=day for item in payload['families'].values()):raise ValueError('OPERATIONAL_RISK_FAMILY_DATE_INVALID')
    owner_digest=digest(dict(contract_id=CONTRACT,token=token,T0=day,payload=payload));schema=schema_for_revision(root,owner_digest)
    with connection(schema) as pg:
        _install(pg,schema,'risk_r1');pg.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',(''.join((schema,token,day)),))
        identity=ForwardFactStore._database_identity(pg)
        old=pg.execute(sql.SQL('SELECT digest,sealed FROM {}.owner_versions_risk_r1 WHERE token=%s AND T0=%s').format(sql.Identifier(schema)),(token,day)).fetchone()
        if old and (old[0]!=owner_digest or old[1] is not True):raise ValueError('OPERATIONAL_RISK_OWNER_IMMUTABLE_CONFLICT')
        if old is None:
            pg.execute(sql.SQL('INSERT INTO {}.owner_versions_risk_r1 VALUES(%s,%s,%s,%s,%s,%s,false)').format(sql.Identifier(schema)),
                (token,day,CONTRACT,owner_digest,3,Jsonb(identity)))
            pg.execute(sql.SQL('INSERT INTO {}.owner_payloads_risk_r1 VALUES(%s,%s,%s,%s)').format(sql.Identifier(schema)),
                (token,day,Jsonb(payload),digest(payload)))
            pg.execute(sql.SQL('UPDATE {}.owner_versions_risk_r1 SET sealed=true WHERE token=%s AND T0=%s').format(sql.Identifier(schema)),(token,day))
        row=pg.execute(sql.SQL('SELECT payload,payload_sha256 FROM {}.owner_payloads_risk_r1 WHERE token=%s AND T0=%s').format(sql.Identifier(schema)),(token,day)).fetchone()
        if row is None or row[1]!=digest(row[0]) or row[0]!=payload:raise ValueError('OPERATIONAL_RISK_OWNER_READBACK_MISMATCH')
    binding=dict(contract_id=CONTRACT,engine='postgresql',schema=schema,token=token,T0=day,digest=owner_digest,
        payload_sha256=digest(payload),row_count=3,database_identity=identity)
    from .v4_pg_binding_registry_r1 import put
    put(root,'risk_owner',token,day,binding)
    return binding,payload

def load(root,token,day):
    root=Path(root).resolve()
    from .v4_pg_binding_registry_r1 import get
    binding=get(root,'risk_owner',token,day)
    if binding is None:raise ValueError('OPERATIONAL_RISK_AUTHORITY_BINDING_MISSING')
    if binding.get('contract_id')!=CONTRACT or binding.get('engine')!='postgresql' or binding.get('token')!=token or binding.get('T0')!=day:raise ValueError('OPERATIONAL_RISK_BINDING_CONTEXT_INVALID')
    schema=binding.get('schema')
    # The physical locator is fixed at v4; the version identity is the
    # token/T0/digest tuple, never the PostgreSQL schema name.
    if binding.get('schema')!=schema_for_revision(root,binding['digest']):raise ValueError('OPERATIONAL_RISK_SCHEMA_MISMATCH')
    with connection(schema,read_only=True) as pg:
        if ForwardFactStore._database_identity(pg)!=binding.get('database_identity'):raise ValueError('OPERATIONAL_RISK_DATABASE_IDENTITY_MISMATCH')
        row=pg.execute(sql.SQL('SELECT payload,payload_sha256 FROM {}.owner_payloads_risk_r1 WHERE token=%s AND T0=%s').format(sql.Identifier(schema)),(token,day)).fetchone()
    if row is None or row[1]!=binding.get('payload_sha256') or digest(row[0])!=row[1]:raise ValueError('OPERATIONAL_RISK_PAYLOAD_DIGEST_MISMATCH')
    return binding,row[0]

def _priority_schema(root,owner_digest):
    if not isinstance(owner_digest,str) or len(owner_digest)!=64 or any(c not in '0123456789abcdef' for c in owner_digest):
        raise ValueError('RESEARCH_PRIORITY_OWNER_DIGEST_INVALID')
    return 'v4'

def prepare_priority(root,token,day,payload):
    root=Path(root).resolve()
    if (payload.get('contract_id')!='V4_DAILY_RESEARCH_PRIORITY_R1'
            or payload.get('T0')!=day or payload.get('context_token')!=token):
        raise ValueError('RESEARCH_PRIORITY_PAYLOAD_CONTEXT_INVALID')
    if set(payload.get('source_bindings',{}))!={'stock','sector'} or not payload.get('parameter_digest'):
        raise ValueError('RESEARCH_PRIORITY_BINDINGS_REQUIRED')
    owner_digest=digest(dict(contract_id='V4_RESEARCH_PRIORITY_PG_OWNER_R1',token=token,T0=day,payload=payload));schema=_priority_schema(root,owner_digest)
    with connection(schema) as pg:
        _install(pg,schema,'priority_r1');pg.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',(''.join((schema,token,day)),));identity=ForwardFactStore._database_identity(pg)
        old=pg.execute(sql.SQL('SELECT digest,sealed FROM {}.owner_versions_priority_r1 WHERE token=%s AND T0=%s').format(sql.Identifier(schema)),(token,day)).fetchone()
        if old and (old[0]!=owner_digest or old[1] is not True):raise ValueError('RESEARCH_PRIORITY_OWNER_IMMUTABLE_CONFLICT')
        if old is None:
            rows=sum(len(payload[k].get('all_items',[]))+len(payload[k].get('not_rankable_rows',[])) for k in ('stocks','sectors'))
            pg.execute(sql.SQL('INSERT INTO {}.owner_versions_priority_r1 VALUES(%s,%s,%s,%s,%s,%s,false)').format(sql.Identifier(schema)),
                (token,day,'V4_RESEARCH_PRIORITY_PG_OWNER_R1',owner_digest,rows,Jsonb(identity)))
            pg.execute(sql.SQL('INSERT INTO {}.owner_payloads_priority_r1 VALUES(%s,%s,%s,%s)').format(sql.Identifier(schema)),(token,day,Jsonb(payload),digest(payload)))
            pg.execute(sql.SQL('UPDATE {}.owner_versions_priority_r1 SET sealed=true WHERE token=%s AND T0=%s').format(sql.Identifier(schema)),(token,day))
        row=pg.execute(sql.SQL('SELECT payload,payload_sha256 FROM {}.owner_payloads_priority_r1 WHERE token=%s AND T0=%s').format(sql.Identifier(schema)),(token,day)).fetchone()
        if row is None or row[0]!=payload or row[1]!=digest(row[0]):raise ValueError('RESEARCH_PRIORITY_PG_READBACK_MISMATCH')
    binding=dict(contract_id='V4_RESEARCH_PRIORITY_PG_OWNER_R1',engine='postgresql',schema=schema,token=token,T0=day,
        digest=owner_digest,payload_sha256=digest(payload),database_identity=identity)
    from .v4_pg_binding_registry_r1 import put
    put(root,'research_priority',token,day,binding)
    return binding,payload

def load_priority(root,token,day):
    root=Path(root).resolve()
    from .v4_pg_binding_registry_r1 import get
    binding=get(root,'research_priority',token,day)
    if binding is None:raise ValueError('RESEARCH_PRIORITY_BINDING_MISSING')
    if binding.get('contract_id')!='V4_RESEARCH_PRIORITY_PG_OWNER_R1' or binding.get('token')!=token or binding.get('T0')!=day:raise ValueError('RESEARCH_PRIORITY_BINDING_CONTEXT_INVALID')
    schema=binding.get('schema')
    if schema!=_priority_schema(root,binding['digest']):raise ValueError('RESEARCH_PRIORITY_SCHEMA_MISMATCH')
    with connection(schema,read_only=True) as pg:
        if ForwardFactStore._database_identity(pg)!=binding.get('database_identity'):raise ValueError('RESEARCH_PRIORITY_DATABASE_IDENTITY_MISMATCH')
        row=pg.execute(sql.SQL('SELECT payload,payload_sha256 FROM {}.owner_payloads_priority_r1 WHERE token=%s AND T0=%s').format(sql.Identifier(schema)),(token,day)).fetchone()
    if row is None or row[1]!=binding.get('payload_sha256') or digest(row[0])!=row[1]:raise ValueError('RESEARCH_PRIORITY_PAYLOAD_DIGEST_MISMATCH')
    return binding,row[0]
