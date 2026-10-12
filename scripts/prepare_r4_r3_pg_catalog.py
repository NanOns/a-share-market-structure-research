"""Project verified isolated SQL apply receipts into the native version catalog."""
import hashlib
import json
from pathlib import Path
import psycopg
from scripts.apply_v4_phase0_schema import VERSIONS

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/audits/r4_r3_scope_20261011'

def prepare():
    dsn='host=127.0.0.1 port=55792 user=r4_isolated_admin dbname=fep_e1_fresh connect_timeout=5'
    rows=[]
    with psycopg.connect(dsn) as pg:
        actual=Path(pg.execute('show data_directory').fetchone()[0]).resolve()
        if actual != Path('G:/codex_tmp/full_system_r4_fbd23a6b/fep_e1_data').resolve():
            raise ValueError('ISOLATED_CLUSTER_IDENTITY_REQUIRED')
        receipts={r[0]:(r[1],r[2]) for r in pg.execute('select path,sha256,applied_at from r4_evidence.migrations')}
        if len(receipts)!=33:raise ValueError('33_ACTUAL_SQL_APPLY_RECEIPTS_REQUIRED')
        for filename,version in VERSIONS.items():
            path=ROOT/'src/workbench_db/migrations/v4_postgres'/filename
            checksum=hashlib.sha256(path.read_text('utf8').encode()).hexdigest()
            if receipts[filename][0]!=checksum:raise ValueError('ACTUAL_MIGRATION_BYTES_DIFFER:'+filename)
            before=pg.execute('select checksum_sha256 from v4_meta.schema_migrations where version=%s',(version,)).fetchone()
            if before and before[0].strip()!=checksum:raise ValueError('CATALOG_CHECKSUM_CONFLICT')
            pg.execute('insert into v4_meta.schema_migrations(version,checksum_sha256,applied_at,contract_id) values(%s,%s,%s,%s) on conflict(version) do nothing',(version,checksum,receipts[filename][1],version))
            rows.append(dict(path=filename,version=version,actual_applied_sha256=checksum,status='PRESENT' if before else 'VERIFIED_RECEIPT_PROJECTED'))
        readback=pg.execute('select version,checksum_sha256 from v4_meta.schema_migrations order by version').fetchall()
    value=dict(contract_id='R4_R3_NATIVE_SQL_CATALOG_RECONCILIATION_R1',isolated_data_directory=str(actual),
        rows=rows,readback=readback,production_changed=False,
        meaning='Native version catalog projected from actual 33 SQL apply receipts; no table/schema or source/PIT modification')
    path=OUT/'PG_NATIVE_VERSION_CATALOG_R1.json'
    if path.exists():return value
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf8')
    return value

if __name__=='__main__':print(json.dumps(prepare(),default=str))
