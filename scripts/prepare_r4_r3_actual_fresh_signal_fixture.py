"""Retain prior replicas and add a clone of the actually bootstrapped fresh source."""
from pathlib import Path
import hashlib,json
import psycopg
from psycopg import sql
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/audits/r4_r3_scope_20261011'
source='fep_e5b_fresh';target='fep_signal_baseline32_actual_fresh'
base='host=127.0.0.1 port=55794 user=r4_isolated_admin dbname='
directory=Path('G:/codex_tmp/r4_r3_fep_fixtures/fresh_data').resolve()
receipt=OUT/'FEP_SIGNAL_ACTUAL_FRESH_BASELINE32_RECEIPT_R1.json'
if receipt.exists():raise ValueError('RETAIN_EXISTING_ACTUAL_FRESH_RECEIPT')
def snapshot():
    with psycopg.connect(base+source) as pg:
        pg.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        if Path(pg.execute("SELECT current_setting('data_directory')").fetchone()[0]).resolve()!=directory:raise ValueError('ACTUAL_FRESH_CLUSTER_REQUIRED')
        names=[r[0] for r in pg.execute("SELECT relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='fep' AND c.relkind='r' ORDER BY relname COLLATE \"C\"")]
        result=[]
        for name in names:
            rows=[r[0] for r in pg.execute(sql.SQL('SELECT to_jsonb(t)::text FROM fep.{} t ORDER BY to_jsonb(t)::text COLLATE "C"').format(sql.Identifier(name)))]
            result.append(dict(table=name,count=len(rows),content_sha256=hashlib.sha256('\n'.join(rows).encode()).hexdigest()))
        return result
before=snapshot()
with psycopg.connect(base+'postgres',autocommit=True) as pg:
    if pg.execute('SELECT 1 FROM pg_database WHERE datname=%s',(target,)).fetchone():raise ValueError('EXISTING_DATABASE_MUST_BE_PRESERVED')
    pg.execute(sql.SQL('CREATE DATABASE {} TEMPLATE {}').format(sql.Identifier(target),sql.Identifier(source)))
with psycopg.connect(base+target) as pg:
    if pg.execute('SELECT current_database()').fetchone()[0]!=target or Path(pg.execute("SELECT current_setting('data_directory')").fetchone()[0]).resolve()!=directory:raise ValueError('EXACT_NEW_FRESH_BASELINE_DATABASE_REQUIRED')
    pg.execute('ALTER TABLE fep.observations DROP CONSTRAINT observation_signal_contract_fk')
    pg.execute('DROP TABLE fep.signal_contract_registry CASCADE')
    for name in ('signal_registry_guard','observation_signal_guard','signal_registry_immutable'):
        pg.execute(sql.SQL('DROP FUNCTION fep.{}() CASCADE').format(sql.Identifier(name)))
after=snapshot()
if before!=after:raise ValueError('ACCEPTED_FRESH_SOURCE_CHANGED')
receipt.write_text(json.dumps(dict(contract='R4_R3_FEP_SIGNAL_ACTUAL_FRESH_BASELINE32_R1',
    source_database=source,new_database=target,source_all_table_contents_before=before,source_all_table_contents_after=after,
    source_unchanged=True,scope='Clone of the actually fresh-bootstrapped canonical fixture; 033 reverted only in new disposable database',
    previous_upgrade_source_replicas_preserved=True,production_changed=False),indent=2)+'\n',encoding='utf8')
with psycopg.connect(base+target) as pg:
    pg.execute('CREATE TABLE r4_evidence.signal_baseline_fixture(contract text PRIMARY KEY,source_receipt_sha256 text NOT NULL,admission text NOT NULL)')
    pg.execute('INSERT INTO r4_evidence.signal_baseline_fixture VALUES(%s,%s,%s)',
        ('R4_R3_FEP_SIGNAL_BASELINE32_ENGINEERING_R1',hashlib.sha256(receipt.read_bytes()).hexdigest(),'NOT_REAL_MATURITY_OR_PRODUCTION_ACCEPTANCE'))
manifest=json.loads((OUT/'R3_EXTRA_PG_FIXTURES_R2.json').read_bytes())
manifest['databases'].append(dict(database=target,port='55794',data_directory=str(directory)))
path=OUT/'R3_EXTRA_PG_FIXTURES_R3.json'
with path.open('x',encoding='utf8') as stream:stream.write(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(actual_fresh_source=source,new_database=target,source_unchanged=True,table_denominator=len(before))))
