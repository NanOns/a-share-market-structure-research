"""FEP_E1_ACCEPTANCE_RUNNER_V1. Explicit loopback isolated PostgreSQL only.

Start a dedicated PostgreSQL instance with data/logs on E: or F:, then set
FEP_E1_ADMIN_DSN to that instance's postgres database. No config/.env is read.
Fresh and upgrade runs require separate empty isolated instances because
historical V4 migration 024 creates a cluster role. No existing database is
deleted or replaced. Production/schema promotion is not an entry point.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from workbench_analysis.fep_e1.db import apply, validate_inventory
from workbench_analysis.fep_e1.contracts import atomic_json, digest

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT/'reports/fep_e1'
DATABASES = ('fep_e1_fresh', 'fep_e1_upgrade')


def inventory(pg):
    queries = dict(
        tables="select tablename from pg_tables where schemaname='fep' order by tablename",
        columns="select table_name,column_name,data_type,is_nullable from information_schema.columns where table_schema='fep' order by table_name,ordinal_position",
        constraints="select c.relname,k.conname,k.contype,pg_get_constraintdef(k.oid) from pg_constraint k join pg_class c on c.oid=k.conrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname='fep' order by c.relname,k.conname",
        triggers="select c.relname,t.tgname,pg_get_triggerdef(t.oid) from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname='fep' and not t.tgisinternal order by c.relname,t.tgname",
        functions="select p.proname,pg_get_function_identity_arguments(p.oid),pg_get_userbyid(p.proowner),p.prosecdef,p.proconfig,pg_get_functiondef(p.oid) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='fep' order by p.proname",
        grants="select grantee,table_name,privilege_type from information_schema.role_table_grants where table_schema='fep' order by grantee,table_name,privilege_type",
        roles="select rolname,rolsuper,rolinherit,rolcreaterole,rolcreatedb,rolcanlogin,rolbypassrls from pg_roles where rolname like 'fep_%' order by rolname",
    )
    return {k:dict(sql=q,rows=pg.execute(q).fetchall()) for k,q in queries.items()}


def tests(name, params):
    env=os.environ.copy()
    env['FEP_E1_TEST_DSN']=make_conninfo(**dict(params,dbname=name))
    env['PYTHONPATH']=str(ROOT)+os.pathsep+str(ROOT/'src')
    env['TMP']=env['TEMP']='E:/codex_tmp/test_temp'
    output=REPORT/(name+'.log')
    cmd=[sys.executable,'-B','-m','pytest','tests/fep','-q','-s',
         '--basetemp=E:/codex_tmp/test_temp/'+name,
         '--junitxml='+str(REPORT/(name+'.xml'))]
    with output.with_suffix('.log.tmp').open('wb') as stream:
        code=subprocess.call(cmd,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
    os.replace(output.with_suffix('.log.tmp'),output)
    cases=ET.parse(REPORT/(name+'.xml')).findall('.//testcase')
    return dict(command=cmd,exit_code=code,tests=len(cases),
                passed=sum(c.find('failure') is None and c.find('error') is None and c.find('skipped') is None for c in cases),
                skipped=sum(c.find('skipped') is not None for c in cases),
                failed_nodes=[c.attrib['classname']+'::'+c.attrib['name'] for c in cases if c.find('failure') is not None or c.find('error') is not None])


def run():
    params=conninfo_to_dict(os.environ['FEP_E1_ADMIN_DSN'])
    if params.get('host')!='127.0.0.1' or params.get('user')!='fep_e1_admin' or params.get('dbname')!='postgres':
        raise ValueError('FEP_EXPLICIT_LOOPBACK_ENGINEERING_ADMIN_REQUIRED')
    REPORT.mkdir(parents=True,exist_ok=True)
    with psycopg.connect(make_conninfo(**params),autocommit=True) as admin:
        directory=admin.execute('show data_directory').fetchone()[0]
        if not directory.replace('\\','/').lower().startswith(('e:/codex_tmp/fep_e1_', 'f:/codex_tmp/fep_e1_')):
            raise ValueError('FEP_ISOLATED_DATA_DIRECTORY_REQUIRED')
        env=dict(version=admin.execute('select version()').fetchone()[0],data_directory=directory,
                 port=admin.execute('show port').fetchone()[0],timezone=admin.execute('show timezone').fetchone()[0],
                 locale=admin.execute('show lc_messages').fetchone()[0],config_file=admin.execute('show config_file').fetchone()[0],
                 max_connections=admin.execute('show max_connections').fetchone()[0],shared_buffers=admin.execute('show shared_buffers').fetchone()[0],
                 instance='ISOLATED_ENGINEERING_FIXTURES_ONLY',credentials='NO_PRODUCTION_CREDENTIALS',database_names=DATABASES)
        atomic_json(REPORT/'POSTGRES_ENVIRONMENT.json',env)
        for name in DATABASES[:1]:
            admin.execute(sql.SQL('create database {}').format(sql.Identifier(name)))
    upgrade_params=conninfo_to_dict(os.environ['FEP_E1_UPGRADE_ADMIN_DSN'])
    if upgrade_params.get('host')!='127.0.0.1' or upgrade_params.get('user')!='fep_e1_admin' or upgrade_params.get('dbname')!='postgres':
        raise ValueError('FEP_EXPLICIT_UPGRADE_INSTANCE_REQUIRED')
    with psycopg.connect(make_conninfo(**upgrade_params),autocommit=True) as admin:
        directory=admin.execute('show data_directory').fetchone()[0]
        if not directory.replace('\\','/').lower().startswith(('e:/codex_tmp/fep_e1_', 'f:/codex_tmp/fep_e1_')):
            raise ValueError('FEP_UPGRADE_DATA_DIRECTORY_REQUIRED')
        if directory==env['data_directory']:
            raise ValueError('FEP_SEPARATE_CLUSTER_REQUIRED_FOR_UPSTREAM_GLOBAL_ROLES')
        atomic_json(REPORT/'POSTGRES_UPGRADE_ENVIRONMENT.json',dict(version=admin.execute('select version()').fetchone()[0],data_directory=directory,
            port=admin.execute('show port').fetchone()[0],timezone=admin.execute('show timezone').fetchone()[0],
            locale=admin.execute('show lc_messages').fetchone()[0],max_connections=admin.execute('show max_connections').fetchone()[0],
            shared_buffers=admin.execute('show shared_buffers').fetchone()[0],instance='ISOLATED_UPGRADE_ENGINEERING_FIXTURE'))
        admin.execute('create database fep_e1_upgrade')
    summaries={}; identities={}; migration_results={}
    for name in DATABASES:
        active_params=params if name=='fep_e1_fresh' else upgrade_params
        if name=='fep_e1_upgrade':
            # Close the baseline session before PostgreSQL template cloning.
            with psycopg.connect(make_conninfo(**dict(active_params,dbname=name))) as baseline_pg:
                paths=sorted((ROOT/'src/workbench_db/migrations/v4_postgres').glob('[0-9][0-9][0-9]_*.sql'))
                for path in paths:
                    if int(path.name[:3])<28:
                        baseline_pg.execute(path.read_text(encoding='utf8'))
            with psycopg.connect(make_conninfo(**active_params),autocommit=True) as admin:
                admin.execute('create database fep_e1_core_template template fep_e1_upgrade')
        with psycopg.connect(make_conninfo(**dict(active_params,dbname=name))) as pg:
            before=pg.execute("select table_schema,table_name from information_schema.tables where table_schema in ('v4','fep') order by 1,2").fetchall()
            result=apply(pg,ROOT,bootstrap=name=='fep_e1_fresh');pg.commit()
            repeated=apply(pg,ROOT,bootstrap=name=='fep_e1_fresh');pg.commit()
            validate_inventory(pg)
            inv=inventory(pg);identities[name]=dict(inventory=inv,schema_digest=digest(inv))
            migration_results[name]=dict(before_schema=before,migrations=result,replay=repeated,
                after_schema=pg.execute("select table_schema,table_name from information_schema.tables where table_schema in ('v4','fep') order by 1,2").fetchall())
        with psycopg.connect(make_conninfo(**active_params),autocommit=True) as admin:
            admin.execute(sql.SQL('create database fep_e1_template template {}').format(sql.Identifier(name)))
        print(name+': migrations applied; running real PostgreSQL tests',flush=True)
        summaries[name]=tests(name,active_params)
        print(name+': '+json.dumps(summaries[name]),flush=True)
    same=identities[DATABASES[0]]['schema_digest']==identities[DATABASES[1]]['schema_digest']
    atomic_json(REPORT/'SCHEMA_INVENTORY.json',dict(same_fresh_upgrade_schema=same,databases=identities))
    atomic_json(REPORT/'MIGRATION_EXECUTION.json',migration_results)
    atomic_json(REPORT/'TARGETED_TEST_SUMMARY.json',dict(databases=summaries,same_fresh_upgrade_schema=same))
    if not same or any(v['exit_code'] for v in summaries.values()):
        return 1
    return 0


if __name__=='__main__':
    argparse.ArgumentParser().parse_args()
    raise SystemExit(run())
