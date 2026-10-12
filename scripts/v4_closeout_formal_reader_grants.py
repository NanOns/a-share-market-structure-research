"""Explicit SELECT-only admission to schemas owned by the new formal producer."""
import json,os,sys
from pathlib import Path
SOURCE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(SOURCE),str(SOURCE/'src')]
ROOT=Path('G:/codex work/v4-production-20261012')
OUT=Path('G:/codex_tmp/v4_full_closeout_20261012/formal_reader_grants_r1')
def main():
    import psycopg
    from psycopg import sql
    from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
    credentials=load_credentials(ROOT/'config/native_pg_roles.dpapi')
    OUT.mkdir(parents=True,exist_ok=False)
    with psycopg.connect(credentials[ROLES[1]]) as pg:
        if pg.execute('SELECT current_user,current_database(),system_identifier::text FROM pg_control_system()').fetchone()!=(ROLES[1],'market_research','7688198230782699460'):raise ValueError('FORMAL_CLUSTER_ROLE_REQUIRED')
        schemas=[row[0] for row in pg.execute('SELECT nspname FROM pg_namespace WHERE nspowner=(SELECT oid FROM pg_roles WHERE rolname=current_user) ORDER BY nspname')]
        if not schemas or any(not name.startswith('v4_') for name in schemas):raise ValueError('FORMAL_PRODUCER_SCHEMA_SCOPE_REQUIRED')
        for schema in schemas:
            pg.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(schema),sql.Identifier(ROLES[0])))
            pg.execute(sql.SQL('GRANT SELECT ON ALL TABLES IN SCHEMA {} TO {}').format(sql.Identifier(schema),sql.Identifier(ROLES[0])))
    tables=[]
    with psycopg.connect(credentials[ROLES[0]]) as pg:
        pg.execute('SET TRANSACTION READ ONLY')
        if pg.execute('SELECT current_user,current_database(),system_identifier::text FROM pg_control_system()').fetchone()!=(ROLES[0],'market_research','7688198230782699460'):raise ValueError('FORMAL_READER_IDENTITY_REQUIRED')
        for schema in schemas:
            if pg.execute("SELECT has_schema_privilege(current_user,%s,'CREATE')",(schema,)).fetchone()[0]:raise ValueError('READER_SCHEMA_CREATE_NOT_ALLOWED')
            for table,oid in pg.execute("SELECT relname,oid FROM pg_class WHERE relnamespace=(SELECT oid FROM pg_namespace WHERE nspname=%s) AND relkind='r'",(schema,)):
                rights=pg.execute("SELECT has_table_privilege(current_user,%s,'SELECT'),has_table_privilege(current_user,%s,'INSERT,UPDATE,DELETE,TRUNCATE')",(oid,oid)).fetchone()
                if rights!=(True,False):raise ValueError('READER_SELECT_ONLY_REQUIRED')
                pg.execute(sql.SQL('SELECT 1 FROM {}.{} LIMIT 1').format(sql.Identifier(schema),sql.Identifier(table))).fetchall()
                tables.append(dict(schema=schema,table=table,select=True,mutation=False))
    result=dict(status='ACTUAL_FORMAL_READER_SELECT_ONLY_PASS',schemas=schemas,tables=tables,existing_production_schema_grants_changed=False,production_activated=False)
    (OUT/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(dict(status=result['status'],tables=len(tables))))
if __name__=='__main__':main()
