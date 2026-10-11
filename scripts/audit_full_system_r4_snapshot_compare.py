"""Compare native candidate with the same-source frozen pre-R4 producer."""
import hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from types import SimpleNamespace
from scripts.audit_full_system_r4_scope import write
from workbench_db.v4_native import connection
from workbench_service.current_v4_context import canonical

def main():
    from workbench_service.production_v4 import ProductionV4ResearchReader,numeric_sort_expressions
    from tests import v4_native_isolation_plugin_r4 as guard
    evidence=ROOT/'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b'
    prior=json.loads((evidence/'R4_04_REAL_SNAPSHOT_RESULT.json').read_bytes())
    oracle_root=Path('G:/codex_tmp/full_system_r4_fbd23a6b/snapshot_candidate')
    oracle=json.loads((oracle_root/'frozen_producer_oracle.json').read_bytes())['data']
    frozen=json.loads((oracle_root/'frozen_producer_receipt.json').read_bytes())
    os.environ['R4_PG_DATA_DIRECTORY']='G:/codex_tmp/full_system_r4_fbd23a6b/pg_data';os.environ['R4_CONNECTION_LEDGER']=str(evidence/'R4_04_SAME_SOURCE_CONNECTIONS.jsonl')
    config=SimpleNamespace();guard.pytest_configure(config);guard.ACTIVE='REAL_SNAPSHOT_SAME_SOURCE_READBACK'
    actual={};sorts={};code=1
    try:
        reader=ProductionV4ResearchReader(ROOT,snapshot_authority=prior['staged']['pointer'])
        with connection(reader.pg_descriptor['schema'],read_only=True) as pg:
            for table,order in [('objects','domain,id'),('aliases','alias,id'),('members','sector,security')]:
                count=0;digest=hashlib.sha256()
                with pg.cursor(name='r4_frozen_compare_'+table) as cur:
                    cur.execute('SELECT * FROM '+table+' ORDER BY '+order)
                    for row in cur:
                        values=list(row)
                        if table=='objects':values[-1]=json.loads(values[-1])
                        digest.update(canonical(values)+b'\n');count+=1
                actual[table]=dict(rows=count,digest=digest.hexdigest())
            for direction in ('ASC','DESC'):
                sorts[direction]=[r[0] for r in pg.execute("SELECT id FROM objects WHERE domain='stocks' ORDER BY "+','.join(numeric_sort_expressions('close',direction=='DESC'))+',id ASC')]
        differences=[table for table in actual if actual[table]!=oracle[table]]
        sort_differences=[direction for direction in sorts if sorts[direction]!=oracle['numeric_sort'][direction]]
        pages={domain:reader.query(domain,dict(limit='2'))['total'] for domain in reader.manifest['counts']}
        if pages!=reader.manifest['counts']:raise ValueError('DOMAIN_READER_COUNT_MISMATCH')
        reader.query('stocks',dict(sort='-close',limit='2'))
        code=int(bool(differences or sort_differences))
        write('R4_04_SAME_SOURCE_ORACLE_RESULT.json',dict(current_status='SCOPED_REAL_SAME_SOURCE_EQUIVALENCE_PASS' if code==0 else 'SCOPED_SAME_SOURCE_DIFF_OPEN',denominator=dict(objects=actual['objects']['rows'],aliases=actual['aliases']['rows'],members=actual['members']['rows']),whole_table_oracle=actual,differences=differences,numeric_sort_differences=sort_differences,actual_reader_domain_counts=pages,frozen_source_SHA=frozen['source_SHA'],original_published_comparison='R4_04_REAL_SNAPSHOT_RESULT.json',pg_binding=reader.pg_descriptor,frozen_producer_receipt=frozen,evidence_links=['R4_04_SAME_SOURCE_CONNECTIONS.jsonl',str(oracle_root/'frozen_producer_oracle.json')],limitations=['Original accepted snapshot predates current unit projection bindings: original comparison remains a difference; Amount A cross-cutting acceptance is independent','No joint publication, rollback or production switch'],next_conditions=['Unit/provenance source-delta review and joint-release acceptance']))
        print(json.dumps(dict(status='PASS' if code==0 else 'FAIL',differences=differences,numeric_sort_differences=sort_differences)))
    finally:guard.pytest_sessionfinish(None,code);guard.pytest_unconfigure(config)
    return code
if __name__=='__main__':raise SystemExit(main())
