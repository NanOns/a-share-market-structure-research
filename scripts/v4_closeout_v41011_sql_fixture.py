"""G-only independent full SQL fixture; never modifies existing databases."""
import hashlib,json,os,subprocess,argparse
from pathlib import Path
import psycopg
from psycopg import sql
from scripts.apply_v4_phase0_schema import VERSIONS

ROOT=Path(__file__).resolve().parents[1]
DATABASE='v4_v41011_clean_20261013_r1'
CONTRACT='V4_CLOSEOUT_V41011_FULL_SQL_ENGINEERING_R1'
RECEIPT=ROOT/'docs/audits/v4_full_closeout_20261012/continuation_20261013/V41011_FULL_SQL_FIXTURE_R1.json'
DIRECTORY=Path('G:/codex_tmp/v4_v41011_sql_fixture_20261013/pg_data').resolve()
PORT=55795

def connection(database):
    return dict(host='127.0.0.1',port=PORT,user='r4_isolated_admin',dbname=database)

def identity(pg):
    if Path(pg.execute('show data_directory').fetchone()[0]).resolve()!=DIRECTORY:
        raise ValueError('V41011_ISOLATED_CLUSTER_REQUIRED')

def verify(pg,receipt):
    identity(pg)
    if str(pg.execute('select system_identifier from pg_control_system()').fetchone()[0])!=receipt['system_identifier']:
        raise ValueError('V41011_CLUSTER_SYSTEM_IDENTITY_CHANGED')
    if receipt.get('contract_id')!=CONTRACT or receipt.get('database')!=DATABASE or receipt.get('production_authorized') is not False:
        raise ValueError('V41011_ENGINEERING_FIXTURE_CONTRACT_REQUIRED')
    if pg.execute('select contract,admission from r4_evidence.v41011_fixture').fetchall()!=[(CONTRACT,'ENGINEERING_ONLY_NO_PRODUCTION_AUTHORITY')]:
        raise ValueError('V41011_ENGINEERING_MARKER_REQUIRED')
    rows=dict(pg.execute('select version,checksum_sha256 from v4_meta.schema_migrations').fetchall())
    paths=sorted((ROOT/'src/workbench_db/migrations/v4_postgres').glob('*.sql'))
    if len(receipt['migrations'])!=len(paths) or len(rows)!=len(paths):raise ValueError('V41011_FULL_SQL_REQUIRED')
    for item,path in zip(receipt['migrations'],paths):
        raw=path.read_bytes()
        if item['path']!=path.relative_to(ROOT).as_posix() or hashlib.sha256(raw).hexdigest()!=item['source_sha256'] or rows.get(item['version'],'').strip()!=item['sql_checksum_sha256']:
            raise ValueError('V41011_EXECUTED_SQL_SOURCE_REQUIRED')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--resume-empty-cluster',action='store_true');args=parser.parse_args()
    if RECEIPT.exists():raise ValueError('PRESERVE_EXISTING_FIXTURE_RECEIPT')
    if DIRECTORY.exists() and not args.resume_empty_cluster:raise ValueError('PRESERVE_EXISTING_CLUSTER')
    DIRECTORY.parent.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp')
    if not args.resume_empty_cluster:
        subprocess.run(['E:/Postgres/bin/initdb.exe','-D',str(DIRECTORY),'-U','r4_isolated_admin','-A','trust','--encoding=UTF8','--locale=C'],env=env,check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
        # A persistent Windows server can inherit pipe handles. File-backed
        # launcher output avoids waiting for the server to close those handles.
        with (DIRECTORY.parent/'launcher.log').open('x') as launcher:
            subprocess.run(['E:/Postgres/bin/pg_ctl.exe','-D',str(DIRECTORY),'-l',str(DIRECTORY.parent/'server.log'),'-o','-h 127.0.0.1 -p '+str(PORT),'-w','start'],env=env,check=True,stdout=launcher,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    with psycopg.connect(**connection('postgres'),autocommit=True) as admin:
        identity(admin)
        if admin.execute('select 1 from pg_database where datname=%s',(DATABASE,)).fetchone():raise ValueError('PRESERVE_EXISTING_DATABASE')
        admin.execute(sql.SQL('create database {} template template0 encoding {}').format(sql.Identifier(DATABASE),sql.Literal('UTF8')))
    rows=[]
    with psycopg.connect(**connection(DATABASE)) as pg:
        identity(pg)
        for path in sorted((ROOT/'src/workbench_db/migrations/v4_postgres').glob('*.sql')):
            raw=path.read_bytes();text=raw.decode('utf8');checksum=hashlib.sha256(text.encode()).hexdigest()
            version=VERSIONS.get(path.name,'V4_STAGE_'+path.stem.upper())
            with pg.transaction():
                pg.execute(text)
                pg.execute('insert into v4_meta.schema_migrations(version,checksum_sha256,applied_at,contract_id) values (%s,%s,now(),%s)',(version,checksum,version))
            rows.append(dict(path=path.relative_to(ROOT).as_posix(),version=version,source_sha256=hashlib.sha256(raw).hexdigest(),sql_checksum_sha256=checksum))
        pg.execute('create schema r4_evidence')
        pg.execute('create table r4_evidence.v41011_fixture(contract text primary key,admission text not null)')
        pg.execute('insert into r4_evidence.v41011_fixture values (%s,%s)',(CONTRACT,'ENGINEERING_ONLY_NO_PRODUCTION_AUTHORITY'))
    with psycopg.connect(**connection(DATABASE)) as pg:
        system=str(pg.execute('select system_identifier from pg_control_system()').fetchone()[0])
    receipt=dict(contract_id=CONTRACT,database=DATABASE,port=PORT,data_directory=str(DIRECTORY),system_identifier=system,production_authorized=False,existing_databases_unchanged=True,migrations=rows)
    with psycopg.connect(**connection(DATABASE)) as pg:verify(pg,receipt)
    temp=RECEIPT.with_suffix('.tmp');temp.write_text(json.dumps(receipt,indent=2),encoding='utf8');os.replace(temp,RECEIPT)
    print(json.dumps(dict(status='GENUINE_FULL_SQL_FIXTURE_READY',migration_count=len(rows))))

if __name__=='__main__':main()
