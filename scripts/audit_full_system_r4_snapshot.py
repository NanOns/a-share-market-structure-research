"""Real frozen research projection, staged only; full source-row oracle."""
import hashlib,json,os,subprocess,sys,time,traceback
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.audit_full_system_r4_scope import write,sha
from workbench_db.v4_native import connection
from workbench_service.current_v4_context import canonical

def main():
    from workbench_service.production_v4 import build_snapshot,ProductionV4ResearchReader,numeric_sort_expressions
    from tests import v4_native_isolation_plugin_r4 as guard
    name='R4_04_REAL_SNAPSHOT';candidate=Path('G:/codex_tmp/full_system_r4_fbd23a6b/snapshot_candidate');candidate.mkdir(parents=True,exist_ok=True)
    pointer=ROOT/'config/v4_research_snapshot_authority_v1.json';before=pointer.read_bytes()
    authority=json.loads(before);manifest=json.loads((ROOT/authority['manifest']['path']).read_bytes())
    original=manifest['database'];source=ROOT/original['path']
    if sha(source)!=original['sha256']:raise ValueError('ORIGINAL_SNAPSHOT_IDENTITY_INVALID')
    oracle=candidate/'sqlite_oracle.json'
    subprocess.run([sys.executable,'-B',str(ROOT/'scripts/r4_sqlite_readonly_oracle.py'),'--source',str(source),'--output',str(oracle),'--kind','snapshot'],check=True)
    os.environ['R4_PG_DATA_DIRECTORY']='G:/codex_tmp/full_system_r4_fbd23a6b/pg_data'
    os.environ['R4_CONNECTION_LEDGER']=str(ROOT/'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b'/f'{name}_CONNECTIONS.jsonl')
    config=SimpleNamespace();guard.pytest_configure(config);guard.ACTIVE='REAL_ACCEPTED_STAGED_SNAPSHOT'
    start=time.time();result={};code=1
    try:
        staged=build_snapshot(ROOT,publish=False)
        reader=ProductionV4ResearchReader(ROOT,snapshot_authority=staged['pointer'])
        descriptor=reader.pg_descriptor;frozen=json.loads(oracle.read_bytes())['data'];actual={}
        with connection(descriptor['schema'],read_only=True) as pg:
            for table,order in [('objects','domain,id'),('aliases','alias,id'),('members','sector,security')]:
                digest=hashlib.sha256();count=0
                with pg.cursor(name='r4_snapshot_'+table) as cur:
                    cur.execute('SELECT * FROM '+table+' ORDER BY '+order)
                    for row in cur:
                        values=list(row)
                        if table=='objects':values[-1]=json.loads(values[-1])
                        digest.update(canonical(values)+b'\n');count+=1
                actual[table]=dict(rows=count,digest=digest.hexdigest())
            sorts={direction:[r[0] for r in pg.execute("SELECT id FROM objects WHERE domain='stocks' ORDER BY "+','.join(numeric_sort_expressions('close',direction=='DESC'))+',id ASC')] for direction in ('ASC','DESC')}
        differences=[table for table in actual if actual[table]!=frozen[table]]
        sort_differences=[direction for direction in sorts if sorts[direction]!=frozen['numeric_sort'][direction]]
        result=dict(staged=staged,pg_binding=descriptor,original_binding=original,whole_table_oracle=actual,oracle_expected={k:v for k,v in frozen.items() if k!='numeric_sort'},differences=differences,numeric_sort_differences=sort_differences,denominator=dict(objects=actual['objects']['rows'],aliases=actual['aliases']['rows'],members=actual['members']['rows']))
        if differences or sort_differences:raise ValueError('REAL_SNAPSHOT_ORACLE_DIFFERENCE_REQUIRES_REVIEW')
        # Run actual reader SQL, rather than only testing standalone PG queries.
        for domain in reader.manifest['counts']:
            page=reader.query(domain,dict(limit='2',offset='0'))
            if page['total']!=reader.manifest['counts'][domain]:raise ValueError('READER_DOMAIN_COUNT_MISMATCH')
        reader.query('stocks',dict(sort='-close',limit='2'))
        code=0
    except BaseException as error:
        result.update(error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc())
    finally:
        guard.pytest_sessionfinish(None,code);guard.pytest_unconfigure(config)
        result.update(protected_pointer_unchanged=pointer.read_bytes()==before,original_sqlite_unchanged=sha(source)==original['sha256'])
        if not all((result['protected_pointer_unchanged'],result['original_sqlite_unchanged'])):code=1
        write(name+'_RESULT.json',dict(**result,current_status='SCOPED_REAL_SNAPSHOT_EQUIVALENCE_PASS' if code==0 else 'SCOPED_REAL_SNAPSHOT_FAIL',seconds=time.time()-start,evidence_links=[str(oracle),name+'_CONNECTIONS.jsonl'],limitations=['Frozen 2026-09-30 snapshot only; joint CAS and dated HTTP/browser gate open; production not switched'],next_conditions=['Historical dated snapshots, all numeric sorts and joint-release/rollback semantics']))
    print(json.dumps(dict(status='PASS' if code==0 else 'FAIL',seconds=time.time()-start,error=result.get('error'),differences=result.get('differences'))))
    return code
if __name__=='__main__':raise SystemExit(main())
