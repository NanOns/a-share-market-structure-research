"""Native PG ingestion and independent row oracle for frozen migration bytes."""
import hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
TARGET=Path('G:/codex_tmp/r4_r3_pg_publication')
OUT=ROOT/'docs/audits/r4_r3_consumers_20261011'
from workbench_db.v4_series_pg_r1 import build
from workbench_db.v4_snapshot_pg_r2 import read
from workbench_service.production_v4 import reference
from workbench_service.v4_daily_refresh import atomic_bytes
from workbench_service.current_v4_context import canonical
from types import SimpleNamespace
from tests import v4_native_isolation_plugin_r4 as guard
os.environ['R4_PG_DATA_DIRECTORY']='G:/codex_tmp/full_system_r4_fbd23a6b/pg_data'
os.environ['R4_CONNECTION_LEDGER']=str(OUT/'ENGINEERING_SERIES_PG_INTENTS.jsonl')
cfg=SimpleNamespace();guard.pytest_configure(cfg);guard.ACTIVE='TRUE_PG_SERIES_INGEST_AND_READBACK'
ledger=Path(os.environ['R4_CONNECTION_LEDGER']).open('w',encoding='utf8')
class StreamedIntents:
    def append(self,event):
        ledger.write(json.dumps(event,ensure_ascii=False)+'\n')
guard.EVENTS=StreamedIntents()
try:
    authority=json.loads((TARGET/'config/v4_stock_operational_authority_v1.json').read_bytes())
    source=authority['series'];oracle=TARGET/'series_oracle_r3.jsonl';receipt=json.loads(oracle.with_suffix('.receipt.json').read_bytes())
    if receipt['source_sha256']!=source['sha256']:raise ValueError('SERIES_SOURCE_IDENTITY_MISMATCH')
    path=TARGET/'data/v4/engineering_series_r3/series.pg.json'
    def rows():
        with oracle.open(encoding='utf8') as stream:
            for line in stream:
                sid,day,value=json.loads(line);yield sid,day,value
    if not path.exists():descriptor=build(TARGET,path,rows(),t0=authority['trade_date'],source_digest=source['sha256'])
    else:descriptor=json.loads(path.read_bytes())
    from workbench_db.v4_native import connection
    with connection(descriptor['schema']) as pg:
        # Explicit bounded engineering index maintenance only. Runtime content
        # reads below retain the unchanged 30s per-statement safety limit.
        pg.execute("SET LOCAL statement_timeout='300s'")
        pg.execute('CREATE INDEX IF NOT EXISTS bars_digest_order ON bars(security COLLATE "C" ASC NULLS FIRST,day ASC NULLS FIRST)')
    independent=hashlib.sha256();count=0
    with read(descriptor) as pg:
        with pg.pg.cursor(name='full_series_independent_oracle') as cur:
            cur.execute('SELECT security,day::text,payload FROM bars ORDER BY security,day')
            for sid,day,payload in cur:
                independent.update(canonical([sid,day,json.loads(payload)])+b'\n');count+=1
    if independent.hexdigest()!=receipt['logical_sha256'] or count!=receipt['rows']:raise ValueError('FULL_SERIES_INDEPENDENT_ORACLE_MISMATCH')
    binding=reference(TARGET,path);authority['series']=binding
    atomic_bytes(TARGET/'config/v4_stock_operational_authority_v1.json',canonical(authority))
    joint_path=TARGET/'config/v4_joint_release_authority_v1.json';joint=json.loads(joint_path.read_bytes());joint['daily_owner_authorities']['stocks']['series']=binding
    atomic_bytes(joint_path,canonical(joint))
    result=dict(contract_id='R4_R3_FULL_SERIES_ENGINEERING_MIGRATION',status='SCOPED_FULL_BARS_ORACLE_PASS',rows=count,expected_digest=receipt['logical_sha256'],actual_digest=independent.hexdigest(),source=source,pg=binding,source_changed=False,production_changed=False)
    atomic_bytes(OUT/'ENGINEERING_SERIES_RESULT.json',canonical(result))
    print(json.dumps(dict(status=result['status'],rows=count)),flush=True)
finally:
    ledger.close();guard.pytest_unconfigure(cfg)
