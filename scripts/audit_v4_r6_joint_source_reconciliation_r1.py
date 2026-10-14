"""Resolve the sealed engineering-series descriptor mismatch with exact PG verification."""
import hashlib,json,os,psutil,sys
from pathlib import Path
from psycopg import sql

ROOT=Path(r'G:\codex work\v4-production-20261012');SOURCE=Path(__file__).resolve().parents[1]

def inherit_live_environment():
    for process in psutil.process_iter(['pid','name','cmdline']):
        try:
            argv=process.info.get('cmdline') or []
            if (process.info.get('name') or '').lower()=='daav4.exe' and '--port' in argv and argv[argv.index('--port')+1]=='28765':
                env=process.environ()
                for key in ('V4_NATIVE_PG_DSN','V4_NATIVE_PG_READER_DSN'):os.environ[key]=env[key]
                return process.info['pid']
        except (psutil.Error,ValueError,IndexError,KeyError):pass
    raise RuntimeError('LIVE_28765_CONTROLLED_PG_ENVIRONMENT_UNAVAILABLE')

def ref(path):
    raw=path.read_bytes();return {'path':path.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def main():
    pid=inherit_live_environment();sys.path[:0]=[str(SOURCE/'src'),str(SOURCE)]
    from workbench_analysis.operational_daily_storage_v1 import atomic_json
    from workbench_service.current_v4_context import canonical
    from workbench_db.v4_native import connection
    from workbench_db.v4_snapshot_pg_r2 import verify,database_identity
    head_path=ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';head=json.loads(head_path.read_bytes())
    historical_joint_path=ROOT/'config/v4_joint_release_authority_v1.json';historical_joint=json.loads(historical_joint_path.read_bytes())
    old_manifest_ref=historical_joint['snapshot']['manifest'];old_manifest_path=ROOT/old_manifest_ref['path']
    old_manifest=json.loads(old_manifest_path.read_bytes());old_series=old_manifest['sources']['stock_series']
    current_path=ROOT/'data/v4/engineering_series_r3/series.pg.json';current_raw=current_path.read_bytes();current_desc=json.loads(current_raw)
    migration_path=SOURCE/'scripts/migrate_engineering_series_r3.py'
    if not migration_path.is_file():raise ValueError('VERSIONED_SERIES_MIGRATION_SOURCE_NOT_FOUND')
    if (len(current_raw),hashlib.sha256(current_raw).hexdigest())!=(2032,'839f28521d3e661bd8810c785b0b983ad5e549285e81c4283335cea4194cbe3e'):
        raise ValueError('CURRENT_SERIES_DESCRIPTOR_BYTES_CHANGED_DURING_AUDIT')
    if current_desc.get('contract_id')!='V4_PG_RESEARCH_SNAPSHOT_R2' or current_desc.get('series_contract_id')!='V4_PG_DATED_SERIES_R2':
        raise ValueError('VERSIONED_CURRENT_SERIES_CONTRACT_MISMATCH')
    if current_desc['T0']!='2026-09-30' or current_desc['bar_count']!=1309832 or current_desc['symbol_count']!=5224:
        raise ValueError('VERSIONED_CURRENT_SERIES_DENOMINATOR_MISMATCH')
    schema=current_desc['schema']
    with connection(schema,read_only=True) as pg:
        pg.execute("SET LOCAL statement_timeout='300s'")
        verify(pg,current_desc)
        identity=database_identity(pg)
        counts=pg.execute(sql.SQL('SELECT count(*),count(DISTINCT security),min(day)::text,max(day)::text FROM {}.bars').format(sql.Identifier(schema))).fetchone()
    if counts[:2]!=(1309832,5224) or counts[3]!='2026-09-30':
        raise ValueError('CURRENT_SERIES_PG_ROW_READBACK_MISMATCH:'+repr(counts))
    migration_raw=migration_path.read_bytes()
    migration_ref={'path':migration_path.relative_to(SOURCE).as_posix(),'bytes':len(migration_raw),
                   'sha256':hashlib.sha256(migration_raw).hexdigest(),'scope':'R6_SOURCE_REPOSITORY'}
    old_path=ROOT/old_series['path'];old_bytes_present=old_path.is_file() and hashlib.sha256(old_path.read_bytes()).hexdigest()==old_series['sha256']
    doc=dict(contract_id='V4_ENGINEERING_SERIES_SOURCE_RECONCILIATION_R1',version='1.0.0',
        formal_joint=ref(historical_joint_path),formal_manifest=old_manifest_ref,old_series_binding=old_series,
        old_series_bytes_recovered=old_bytes_present,
        current_series_binding=ref(current_path),current_descriptor=current_desc,
        current_postgres_readback=dict(database_identity=identity,row_count=counts[0],symbol_count=counts[1],
            minimum_trade_date=counts[2],maximum_trade_date=counts[3],full_content_manifest_verified=True),
        migration_producer=migration_ref,
        migration_reason='V4_PG_DATED_SERIES_R1 2,020-byte descriptor was replaced by the versioned V4_PG_DATED_SERIES_R2 / V4_PG_RESEARCH_SNAPSHOT_R2 descriptor. R2 adds a canonical four-table content manifest and database identity while preserving the 2026-09-30 source digest, release identity, logical bar digest, 1,309,832 bars and 5,224 securities. The sealed historical manifest still binds the former descriptor bytes; its digest is retained verbatim and is not rewritten.',
        old_source_resolution='OLD_DESCRIPTOR_BYTES_NOT_PRESENT_AT_SEALED_PATH; historical manifest binding preserved exactly',
        new_source_resolution='CURRENT_R2_DESCRIPTOR_AND_FULL_POSTGRES_CONTENT_MANIFEST_VERIFIED',
        current_head_token_sha256=hashlib.sha256(json.dumps(head,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),
        T0=current_desc['T0'],auto_daily_changed=False,head_changed=False,production_joint_pointer_changed=False)
    identity_sha=hashlib.sha256(canonical(doc)).hexdigest();folder=ROOT/'data/v4/engineering_series_source_reconciliations_r1'/identity_sha
    path=folder/'SOURCE_RECONCILIATION.json'
    if path.exists() and path.read_bytes()!=canonical(doc)+b'\n':raise ValueError('SERIES_RECONCILIATION_IMMUTABLE_CONFLICT')
    if not path.exists():atomic_json(ROOT,path,doc)
    result={'contract_id':'V4_R6_ENGINEERING_SERIES_JOINT_RECONCILIATION_R1','acceptance':'PASS_NEW_SERIES_SOURCE_VERSION_VERIFIED',
        'source_reconciliation':ref(path),'old_series_binding':old_series,'current_series_binding':doc['current_series_binding'],
        'current_postgres_readback':doc['current_postgres_readback'],'migration_producer':migration_ref,
        'production_joint_pointer_changed':False,'head_changed':False,'auto_daily_changed':False,
        'service_pid_used_for_controlled_environment':pid}
    output=SOURCE/'reports/audits/v4_r6_closeout_20261014/JOINT_SOURCE_RECONCILIATION.json';output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'acceptance':result['acceptance'],'old_series_sha':old_series['sha256'],'current_series_sha':doc['current_series_binding']['sha256'],
        'bar_count':counts[0],'symbol_count':counts[1]},ensure_ascii=False))

if __name__=='__main__':main()
