"""Immutable PostgreSQL Owner for reconstructed Sector maturity/health."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from psycopg import sql
from psycopg.types.json import Jsonb

from .v4_native import connection,create_schema,workspace_schema
from .v4_forward_pg_r1 import ForwardFactStore

CONTRACT='V4_SECTOR_LIFECYCLE_PG_OWNER_R1'


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')


def digest(value):
    return hashlib.sha256(value if isinstance(value,bytes) else canonical(value)).hexdigest()


def schema_for_revision(root,owner_digest):
    if not isinstance(owner_digest,str) or len(owner_digest)!=64 or any(c not in '0123456789abcdef' for c in owner_digest):
        raise ValueError('SECTOR_LIFECYCLE_OWNER_DIGEST_INVALID')
    return 'v4'


def _install_schema(pg,schema):
    create_schema(pg,schema)
    pg.execute(sql.SQL('''CREATE TABLE IF NOT EXISTS {}.sector_lifecycle_owner_versions_r1(
        token text NOT NULL,T0 text NOT NULL,contract text NOT NULL,digest text NOT NULL,
        producer_sha256 text NOT NULL,parameter_digest text NOT NULL,input_digest text NOT NULL,
        row_count integer NOT NULL,database_identity jsonb NOT NULL,sealed boolean NOT NULL DEFAULT false,
        PRIMARY KEY(token,T0))''').format(sql.Identifier(schema)))
    pg.execute(sql.SQL('''CREATE TABLE IF NOT EXISTS {}.sector_lifecycle_owner_rows_r1(
        token text NOT NULL,T0 text NOT NULL,sector_id text NOT NULL,payload jsonb NOT NULL,
        payload_sha256 text NOT NULL,PRIMARY KEY(token,T0,sector_id),
        FOREIGN KEY(token,T0) REFERENCES {}.sector_lifecycle_owner_versions_r1(token,T0))''').format(sql.Identifier(schema),sql.Identifier(schema)))
    pg.execute(sql.SQL('''CREATE OR REPLACE FUNCTION {}.sector_lifecycle_owner_immutable_r1() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
        IF TG_TABLE_NAME='sector_lifecycle_owner_versions_r1' THEN
          IF TG_OP='INSERT' AND NOT NEW.sealed THEN RETURN NEW; END IF;
          IF TG_OP='UPDATE' AND NOT OLD.sealed AND NEW.sealed AND
             (OLD.token,OLD.T0,OLD.contract,OLD.digest,OLD.producer_sha256,OLD.parameter_digest,OLD.input_digest,OLD.row_count,OLD.database_identity)=
             (NEW.token,NEW.T0,NEW.contract,NEW.digest,NEW.producer_sha256,NEW.parameter_digest,NEW.input_digest,NEW.row_count,NEW.database_identity) THEN RETURN NEW; END IF;
          RAISE EXCEPTION 'SECTOR_LIFECYCLE_OWNER_IMMUTABLE';
        END IF;
        IF TG_OP<>'INSERT' OR EXISTS(SELECT 1 FROM {}.sector_lifecycle_owner_versions_r1 WHERE token=NEW.token AND T0=NEW.T0 AND sealed) THEN
          RAISE EXCEPTION 'SECTOR_LIFECYCLE_OWNER_IMMUTABLE';
        END IF;
        RETURN NEW;
      END $$''').format(sql.Identifier(schema),sql.Identifier(schema)))
    pg.execute(sql.SQL('''CREATE OR REPLACE FUNCTION {}.owner_sector_lifecycle_no_truncate_r1() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN RAISE EXCEPTION 'SECTOR_LIFECYCLE_OWNER_IMMUTABLE'; END $$''').format(sql.Identifier(schema)))
    for table in ('sector_lifecycle_owner_versions_r1','sector_lifecycle_owner_rows_r1'):
        pg.execute(sql.SQL('DROP TRIGGER IF EXISTS sector_lifecycle_owner_immutable_r1_guard ON {}.{}').format(sql.Identifier(schema),sql.Identifier(table)))
        pg.execute(sql.SQL('CREATE TRIGGER sector_lifecycle_owner_immutable_r1_guard BEFORE INSERT OR UPDATE OR DELETE ON {}.{} FOR EACH ROW EXECUTE FUNCTION {}.sector_lifecycle_owner_immutable_r1()').format(sql.Identifier(schema),sql.Identifier(table),sql.Identifier(schema)))
        pg.execute(sql.SQL('DROP TRIGGER IF EXISTS owner_sector_lifecycle_no_truncate_r1_guard ON {}.{}').format(sql.Identifier(schema),sql.Identifier(table)))
        pg.execute(sql.SQL("CREATE TRIGGER owner_sector_lifecycle_no_truncate_r1_guard BEFORE TRUNCATE ON {}.{} FOR EACH STATEMENT EXECUTE FUNCTION {}.owner_sector_lifecycle_no_truncate_r1()").format(sql.Identifier(schema),sql.Identifier(table),sql.Identifier(schema)))


def prepare(root,token,day,rows,*,producer_sha256,parameter_digest,input_digest):
    """Append/readback an immutable owner; never updates the accepted Head."""
    root=Path(root).resolve();rows=sorted(rows,key=lambda row:row['sector_id'])
    if not rows or len({row['sector_id'] for row in rows})!=len(rows):raise ValueError('SECTOR_LIFECYCLE_OWNER_DENOMINATOR_INVALID')
    if any(row.get('T0')!=day or row.get('contract_id')!='SECTOR_LIFECYCLE_RECONSTRUCTED_V1' for row in rows):
        raise ValueError('SECTOR_LIFECYCLE_OWNER_DATE_OR_CONTRACT_MISMATCH')
    material=dict(owner_contract=CONTRACT,token=token,T0=day,producer_sha256=producer_sha256,
        parameter_digest=parameter_digest,input_digest=input_digest,rows=rows)
    owner_digest=digest(material);schema=schema_for_revision(root,owner_digest)
    with connection(schema) as pg:
        _install_schema(pg,schema)
        pg.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',(''.join((schema,token,day)),))
        identity=ForwardFactStore._database_identity(pg)
        old=pg.execute(sql.SQL('SELECT digest,sealed FROM {}.sector_lifecycle_owner_versions_r1 WHERE token=%s AND T0=%s').format(sql.Identifier(schema)),(token,day)).fetchone()
        if old and (old[0]!=owner_digest or old[1] is not True):raise ValueError('SECTOR_LIFECYCLE_OWNER_IMMUTABLE_VERSION_CONFLICT')
        if old is None:
            pg.execute(sql.SQL('INSERT INTO {}.sector_lifecycle_owner_versions_r1 VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,false)').format(sql.Identifier(schema)),
                (token,day,CONTRACT,owner_digest,producer_sha256,parameter_digest,input_digest,len(rows),Jsonb(identity)))
            pg.cursor().executemany(sql.SQL('INSERT INTO {}.sector_lifecycle_owner_rows_r1 VALUES(%s,%s,%s,%s,%s)').format(sql.Identifier(schema)),
                [(token,day,row['sector_id'],Jsonb(row),digest(row)) for row in rows])
            pg.execute(sql.SQL('UPDATE {}.sector_lifecycle_owner_versions_r1 SET sealed=true WHERE token=%s AND T0=%s').format(sql.Identifier(schema)),(token,day))
        readback=pg.execute(sql.SQL('SELECT sector_id,payload,payload_sha256 FROM {}.sector_lifecycle_owner_rows_r1 WHERE token=%s AND T0=%s ORDER BY sector_id COLLATE "C"').format(sql.Identifier(schema)),(token,day)).fetchall()
        if len(readback)!=len(rows) or [r[0] for r in readback]!=[r['sector_id'] for r in rows]:raise ValueError('SECTOR_LIFECYCLE_OWNER_READBACK_COUNT_MISMATCH')
        for (_,payload,sha),expected in zip(readback,rows):
            if payload!=expected or digest(payload)!=sha:raise ValueError('SECTOR_LIFECYCLE_OWNER_READBACK_DIGEST_MISMATCH')
    binding=dict(contract_id=CONTRACT,engine='postgresql',schema=schema,token=token,T0=day,
        digest=owner_digest,producer_sha256=producer_sha256,parameter_digest=parameter_digest,
        input_digest=input_digest,row_count=len(rows),database_identity=identity)
    from .v4_pg_binding_registry_r1 import put
    registry=put(root,'sector_lifecycle',token,day,binding)
    return dict(binding=binding,registry=registry,head_changed=False)


def load(root,token,day):
    root=Path(root).resolve()
    from .v4_pg_binding_registry_r1 import get
    binding=get(root,'sector_lifecycle',token,day)
    if (binding.get('contract_id')!=CONTRACT or binding.get('engine')!='postgresql'
            or binding.get('sealed',True) is not True):
        raise ValueError('SECTOR_LIFECYCLE_OWNER_BINDING_INVALID')
    if binding.get('schema')!=schema_for_revision(root,binding.get('digest')):raise ValueError('SECTOR_LIFECYCLE_OWNER_SCHEMA_MISMATCH')
    with connection(binding['schema'],read_only=True) as pg:
        identity=ForwardFactStore._database_identity(pg)
        if identity!=binding['database_identity']:raise ValueError('SECTOR_LIFECYCLE_OWNER_DATABASE_MISMATCH')
        version=pg.execute(sql.SQL('SELECT digest,contract,sealed,row_count FROM {}.sector_lifecycle_owner_versions_r1 WHERE token=%s AND T0=%s').format(sql.Identifier(binding['schema'])),(token,day)).fetchone()
        if not version or version[0]!=binding['digest'] or version[1]!=CONTRACT or version[2] is not True or version[3]!=binding['row_count']:
            raise ValueError('SECTOR_LIFECYCLE_OWNER_VERSION_ATTESTATION_FAILED')
        rows=pg.execute(sql.SQL('SELECT sector_id,payload,payload_sha256 FROM {}.sector_lifecycle_owner_rows_r1 WHERE token=%s AND T0=%s ORDER BY sector_id COLLATE "C"').format(sql.Identifier(binding['schema'])),(token,day)).fetchall()
    if len(rows)!=binding['row_count'] or any(digest(payload)!=sha for _,payload,sha in rows):raise ValueError('SECTOR_LIFECYCLE_OWNER_ROW_DIGEST_FAILED')
    return binding,{sector_id:payload for sector_id,payload,_ in rows}
