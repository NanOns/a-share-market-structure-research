"""Pin the provenance and exact baseline state of new disposable signal fixtures."""
from pathlib import Path
import hashlib,json
import psycopg
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/audits/r4_r3_scope_20261011'
source=OUT/'FEP_SIGNAL_BASELINE32_FIXTURE_RECEIPT_R1.json'
document=json.loads(source.read_bytes());source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
for name in document['new_databases']:
    with psycopg.connect('host=127.0.0.1 port=55793 user=r4_isolated_admin dbname='+name) as pg:
        if pg.execute('SELECT current_database()').fetchone()[0] not in ('fep_signal_baseline32_fresh','fep_signal_baseline32_upgrade'):
            raise ValueError('EXACT_DISPOSABLE_SIGNAL_DATABASE_REQUIRED')
        if Path(pg.execute("SELECT current_setting('data_directory')").fetchone()[0]).resolve()!=Path(document['cluster_directory']).resolve():
            raise ValueError('EXACT_SIGNAL_FIXTURE_CLUSTER_REQUIRED')
        if pg.execute("SELECT to_regclass('fep.signal_contract_registry')").fetchone()[0] is not None:
            raise ValueError('SIGNAL_BASELINE_SCHEMA_032_REQUIRED')
        pg.execute('CREATE TABLE r4_evidence.signal_baseline_fixture(contract text PRIMARY KEY,source_receipt_sha256 text NOT NULL,admission text NOT NULL)')
        pg.execute('INSERT INTO r4_evidence.signal_baseline_fixture VALUES(%s,%s,%s)',
            ('R4_R3_FEP_SIGNAL_BASELINE32_ENGINEERING_R1',source_sha,'NOT_REAL_MATURITY_OR_PRODUCTION_ACCEPTANCE'))
output=OUT/'FEP_SIGNAL_BASELINE32_MARKER_RECEIPT_R1.json'
if output.exists():raise ValueError('RETAIN_EXISTING_SIGNAL_MARKER_RECEIPT')
output.write_text(json.dumps(dict(contract='R4_R3_FEP_SIGNAL_BASELINE32_ENGINEERING_R1',source_receipt_sha256=source_sha,
    databases=document['new_databases'],state='EXPLICIT_NATIVE_ENGINEERING_032_BASELINE',production_changed=False),indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(marked_databases=document['new_databases'],production_changed=False)))
