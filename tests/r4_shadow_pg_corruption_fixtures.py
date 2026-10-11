"""G-only isolated PG corruption copies, never mutate the source ledger."""
import hashlib,json,os,uuid
from pathlib import Path
import psycopg
from psycopg import sql
from scripts.r4_shadow_pg_readonly import open_existing,Reader

def clone_for_corruption(source,target,root):
    source=Path(source).resolve();target=Path(target).with_suffix('.pg.json').resolve()
    if not target.is_relative_to(Path('G:/codex_tmp').resolve()) or target.exists():raise ValueError('NEW_G_ONLY_CORRUPTION_FIXTURE_REQUIRED')
    identity=json.loads(source.read_bytes());old_schema=identity['schema']
    schema='v4_shadow_live_'+uuid.uuid4().hex
    oracle=open_existing(source,root)
    try:dsn=oracle.pg.info.dsn
    finally:oracle.close()
    pg=psycopg.connect(dsn,autocommit=True)
    try:
        with pg.transaction():
            pg.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
            pg.execute(sql.SQL('SET LOCAL search_path TO {},pg_catalog').format(sql.Identifier(schema)))
            pg.execute((Path(root)/'migrations/v4_shadow_live_pg_r3.sql').read_text(encoding='utf8'))
            tables=[r[0] for r in pg.execute('SELECT tablename FROM pg_tables WHERE schemaname=%s ORDER BY tablename',(schema,))]
            pg.execute("SET LOCAL session_replication_role='replica'")
            for table in tables:
                if table=='shadow_live_identity':continue
                query=sql.SQL('INSERT INTO {}.{} OVERRIDING SYSTEM VALUE SELECT * FROM {}.{}').format(sql.Identifier(schema),sql.Identifier(table),sql.Identifier(old_schema),sql.Identifier(table))
                pg.execute(query)
            identity=dict(identity,schema=schema)
            pg.execute('INSERT INTO shadow_live_identity VALUES(1,%s,%s,%s,%s)',(identity['contract_id'],schema,identity['root_digest'],identity['migration_sha256']))
        pg.execute(sql.SQL('SET search_path TO {},pg_catalog').format(sql.Identifier(schema)))
        # Only this newly created adversarial fixture may permit fact mutation.
        pg.execute('ALTER TABLE facts DISABLE TRIGGER immutable_facts')
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x',encoding='utf8') as f:json.dump(identity,f)
        return target,Reader(pg)
    except BaseException:pg.close();raise

def restore_mutation_guard(conn):conn.execute('ALTER TABLE facts ENABLE TRIGGER immutable_facts')
