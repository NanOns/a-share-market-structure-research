"""Clone native engineering FEP data for exact 032->033 migration negatives."""
from pathlib import Path
import hashlib,json
import psycopg
from psycopg import sql
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/audits/r4_r3_scope_20261011'
receipt=OUT/'FEP_SIGNAL_BASELINE32_FIXTURE_RECEIPT_R1.json'
if receipt.exists():raise ValueError('RETAIN_EXISTING_SIGNAL_FIXTURE_RECEIPT')
dsn='host=127.0.0.1 port=55793 user=r4_isolated_admin dbname='
source_name='fep_e5b_upgrade'
names=['fep_signal_baseline32_fresh','fep_signal_baseline32_upgrade']
expected=Path('G:/codex_tmp/r4_r3_fep_fixtures/upgrade_data').resolve()
def snapshot():
    with psycopg.connect(dsn+source_name) as pg:
        pg.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        actual=pg.execute("SELECT current_setting('data_directory')").fetchone()[0]
        if Path(actual).resolve()!=expected:raise ValueError('EXACT_ISOLATED_FIXTURE_CLUSTER_REQUIRED')
        tables=[r[0] for r in pg.execute("SELECT relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='fep' AND c.relkind='r' ORDER BY relname COLLATE \"C\"")]
        rows=[]
        for table in tables:
            values=[r[0] for r in pg.execute(sql.SQL('SELECT to_jsonb(t)::text FROM fep.{} t ORDER BY to_jsonb(t)::text COLLATE "C"').format(sql.Identifier(table)))]
            rows.append(dict(table=table,count=len(values),full_content_sha256=hashlib.sha256('\n'.join(values).encode()).hexdigest()))
        return rows
before=snapshot()
with psycopg.connect(dsn+'postgres',autocommit=True) as admin:
    if Path(admin.execute("SELECT current_setting('data_directory')").fetchone()[0]).resolve()!=expected:raise ValueError('FIXTURE_ADMIN_CLUSTER_MISMATCH')
    for name in names:
        if admin.execute('SELECT 1 FROM pg_database WHERE datname=%s',(name,)).fetchone():raise ValueError('EXISTING_DISPOSABLE_DATABASE_MUST_NOT_BE_OVERWRITTEN')
        admin.execute(sql.SQL('CREATE DATABASE {} TEMPLATE {}').format(sql.Identifier(name),sql.Identifier(source_name)))
for name in names:
    with psycopg.connect(dsn+name) as pg:
        if pg.execute('SELECT current_database()').fetchone()[0]!=name:raise ValueError('EXACT_NEW_DISPOSABLE_DATABASE_REQUIRED')
        pg.execute('ALTER TABLE fep.observations DROP CONSTRAINT observation_signal_contract_fk')
        pg.execute('DROP TABLE fep.signal_contract_registry CASCADE')
        for function in ('signal_registry_guard','observation_signal_guard','signal_registry_immutable'):
            pg.execute(sql.SQL('DROP FUNCTION fep.{}() CASCADE').format(sql.Identifier(function)))
        if pg.execute("SELECT count(*) FROM fep.observations WHERE scope_id='FEP_STOCK_ENTRY_CORE'").fetchone()[0]==0:
            raise ValueError('ACTUAL_ENGINEERING_OBSERVATION_INPUT_REQUIRED')
after=snapshot()
if before!=after:raise ValueError('SOURCE_CANONICAL_DATABASE_CHANGED')
base=json.loads((OUT/'R3_EXTRA_PG_FIXTURES.json').read_bytes())
extended=dict(base,contract_id='R4_R3_EXPLICIT_ENGINEERING_PG_FIXTURES_R2',
    predecessor_sha256=hashlib.sha256((OUT/'R3_EXTRA_PG_FIXTURES.json').read_bytes()).hexdigest())
extended['databases']=[*base['databases'],*[dict(database=name,port='55793',data_directory=str(expected)) for name in names]]
manifest=OUT/'R3_EXTRA_PG_FIXTURES_R2.json'
if manifest.exists():raise ValueError('RETAIN_PREVIOUS_EXTENDED_FIXTURE_MANIFEST')
manifest.write_text(json.dumps(extended,indent=2)+'\n',encoding='utf8')
result=dict(contract='R4_R3_SIGNAL_BASELINE32_DISPOSABLE_NATIVE_FIXTURES_R1',source_database=source_name,
    source_all_fep_table_content_before=before,source_all_fep_table_content_after=after,source_unchanged=True,
    new_databases=names,cluster_directory=str(expected),extra_capability_manifest=str(manifest.relative_to(ROOT)),
    schema_scope='Native cloned engineering seed; only 033 objects removed in new disposable databases for original 032->033 negative matrix',
    admission='ENGINEERING_ONLY_NOT_REAL_MATURITY_OR_PRODUCTION_ACCEPTANCE',production_changed=False)
receipt.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(new_databases=names,source_unchanged=True,source_table_denominator=len(before))))
