"""Read-only runtime/role discovery. Never print or persist credentials."""
import json
import os
from pathlib import Path
import psycopg
from psycopg.conninfo import conninfo_to_dict
import psutil

SOURCE=Path('G:/codex work/大A交易')
OUT=Path('G:/codex_tmp/v4_full_closeout_20261012/production_identity')

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    records=[];candidates={}
    for key in ('V4_NATIVE_PG_DSN','WORKBENCH_PG_DSN'):
        if os.environ.get(key):candidates['agent_environment:'+key]=os.environ[key]
    processes=[]
    for process in psutil.process_iter(['pid','name','cmdline']):
        argv=process.info.get('cmdline') or []
        if any('run_workbench_service.py' in arg and str(SOURCE).casefold() in arg.casefold() for arg in argv):
            record=dict(pid=process.pid,argv=argv)
            try:
                record.update(username=process.username(),cwd=process.cwd(),exe=process.exe())
                env=process.environ()
                record['pg_environment_keys']=[key for key in ('V4_NATIVE_PG_DSN','WORKBENCH_PG_DSN') if env.get(key)]
                for key in record['pg_environment_keys']:candidates['production_process:'+str(process.pid)+':'+key]=env[key]
            except (psutil.Error,OSError) as exc:record['inspection_error']=type(exc).__name__
            processes.append(record)
    envfile=SOURCE/'config/.env'
    if envfile.is_file():
        for line in envfile.read_text(encoding='utf-8-sig').splitlines():
            key,sep,value=line.partition('=')
            if sep and key.strip() in ('V4_NATIVE_PG_DSN','WORKBENCH_PG_DSN'):
                candidates['original_config:'+key.strip()]=value.strip().strip('\"').strip("'")
    for origin,dsn in candidates.items():
        parsed=conninfo_to_dict(dsn)
        row=dict(origin=origin,identity={k:parsed.get(k) for k in ('host','port','dbname','user')},read_only=True)
        try:
            with psycopg.connect(dsn,connect_timeout=5) as pg:
                pg.execute('SET TRANSACTION READ ONLY')
                value=pg.execute("SELECT current_user,current_database(),inet_server_addr()::text,inet_server_port(),(SELECT oid FROM pg_database WHERE datname=current_database()),has_database_privilege(current_user,current_database(),'CREATE'),has_schema_privilege(current_user,'public','USAGE'),has_schema_privilege(current_user,'public','CREATE')").fetchone()
                row['observed']=dict(zip(('role','database','host','port','database_oid','database_create','public_usage','public_create'),value))
                row['schemas']=[r[0] for r in pg.execute("SELECT nspname FROM pg_namespace WHERE nspname LIKE 'v4_%' ORDER BY nspname")]
            for query,name in [('SHOW data_directory','data_directory'),('SELECT system_identifier::text FROM pg_control_system()','system_identifier')]:
                try:
                    with psycopg.connect(dsn,connect_timeout=5) as pg:
                        pg.execute('SET TRANSACTION READ ONLY');row[name]=pg.execute(query).fetchone()[0]
                except psycopg.Error as exc:row[name+'_error']=dict(sqlstate=exc.sqlstate,error_type=type(exc).__name__)
            row['status']='READ_ONLY_IDENTITY_OBSERVED_NOT_WRITE_ACCEPTANCE'
        except psycopg.Error as exc:
            row['status']='CONNECTION_FAILED';row['error']=dict(sqlstate=exc.sqlstate,error_type=type(exc).__name__)
        records.append(row)
    result=dict(contract_id='V4_PRODUCTION_READ_ONLY_IDENTITY_V1',processes=processes,pg_candidates=records,
                production_changed=False,credentials_persisted=False,no_candidate_is_automatically_formal=True)
    (OUT/'RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(processes=len(processes),dsn_candidates=len(records),observed=sum(r['status'].startswith('READ_ONLY') for r in records))))

if __name__=='__main__':main()
