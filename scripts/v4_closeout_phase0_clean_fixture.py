"""G-local clean Phase 0 fixture, with genuine SQL and migration receipts."""
import hashlib,json,os
from pathlib import Path
import psycopg
from psycopg import sql
from scripts.apply_v4_phase0_schema import VERSIONS,MIGRATIONS

ROOT=Path(__file__).resolve().parents[1]
DATABASE='v4_phase0_clean_20261013'
DIRECTORY=Path('G:/codex_tmp/full_system_r4_fbd23a6b/pg_data').resolve()
SYSTEM='7695278778933357404'
CONTRACT='V4_CLOSEOUT_PHASE0_CLEAN_SQL_FIXTURE_R1'
RECEIPT=ROOT/'docs/audits/v4_full_closeout_20261012/continuation_20261013/PHASE0_CLEAN_SQL_FIXTURE_R1.json'

def connection(database):
    return dict(host='127.0.0.1',port=55791,user='r4_isolated_admin',dbname=database)

def identity(pg):
    if Path(pg.execute('show data_directory').fetchone()[0]).resolve()!=DIRECTORY:
        raise ValueError('PHASE0_DISPOSABLE_DIRECTORY_REQUIRED')
    if str(pg.execute('select system_identifier from pg_control_system()').fetchone()[0])!=SYSTEM:
        raise ValueError('PHASE0_DISPOSABLE_SYSTEM_REQUIRED')

def prepare():
    if RECEIPT.exists():raise ValueError('PRESERVE_EXISTING_FIXTURE_RECEIPT')
    with psycopg.connect(**connection('postgres'),autocommit=True) as admin:
        identity(admin)
        if admin.execute('select 1 from pg_database where datname=%s',(DATABASE,)).fetchone():
            raise ValueError('PRESERVE_EXISTING_DATABASE')
        admin.execute(sql.SQL('create database {} template template0 encoding {}').format(sql.Identifier(DATABASE),sql.Literal('UTF8')))
    rows=[]
    with psycopg.connect(**connection(DATABASE)) as pg:
        identity(pg)
        for name,version in sorted(VERSIONS.items()):
            path=MIGRATIONS/name;raw=path.read_bytes();text=raw.decode('utf8')
            checksum=hashlib.sha256(text.encode()).hexdigest()
            with pg.transaction():
                pg.execute(text)
                pg.execute('insert into v4_meta.schema_migrations(version,checksum_sha256,applied_at,contract_id) values (%s,%s,now(),%s)',(version,checksum,version))
            rows.append(dict(path=path.relative_to(ROOT).as_posix(),source_sha256=hashlib.sha256(raw).hexdigest(),sql_checksum_sha256=checksum,version=version))
        pg.execute('create schema r4_evidence')
        pg.execute('create table r4_evidence.phase0_clean_fixture(contract text primary key,admission text not null)')
        pg.execute('insert into r4_evidence.phase0_clean_fixture values (%s,%s)',(CONTRACT,'ENGINEERING_ONLY_NO_PRODUCTION_AUTHORITY'))
    value=dict(contract=CONTRACT,database=DATABASE,port='55791',system_identifier=SYSTEM,data_directory=str(DIRECTORY),migrations=rows,production_authorized=False,existing_databases_unchanged=True)
    temp=RECEIPT.with_suffix('.json.tmp');temp.write_text(json.dumps(value,indent=2),encoding='utf8');os.replace(temp,RECEIPT)
    print(json.dumps(dict(status='CREATED',migration_count=len(rows),database=DATABASE)))

if __name__=='__main__':prepare()
