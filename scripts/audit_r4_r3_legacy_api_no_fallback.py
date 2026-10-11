"""Actual provider entry negatives, without pytest or replaced driver functions."""
from pathlib import Path
import os,sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from workbench_db import api_connection as api

output=ROOT/'docs/audits/r4_r3_scope_20261011/LEGACY_API_INDEPENDENT_R2.json'
if output.exists():raise ValueError('PRESERVE_EXISTING_PROVIDER_EVIDENCE')
storage=Path('G:/codex_tmp/test_temp/legacy_api_independent_r2')
storage.mkdir(exist_ok=False)
attempts=[]
def audit(event,args):
    if event=='socket.connect':attempts.append(dict(event=event,address=str(args[1])))
sys.addaudithook(audit)
os.environ['R4_NATIVE_ISOLATION']='1'
results=[]
for config in ('configured','empty','missing'):
    if config=='missing':os.environ.pop('V4_NATIVE_PG_DSN',None)
    else:os.environ['V4_NATIVE_PG_DSN']='host=127.0.0.1 port=1 dbname=forbidden' if config=='configured' else ''
    for name in ('DuckDBApiConnectionProvider','PostgresDuckDBApiConnectionProvider'):
        provider=getattr(api,name)(storage/'legacy.duckdb' if name.startswith('DuckDB') else 'host=127.0.0.1 port=1 dbname=forbidden')
        for entry in ('connect','memory'):
            try:
                with getattr(provider,entry)():raise AssertionError('UNEXPECTED_DATABASE_ENTRY')
            except RuntimeError as error:
                assert str(error)=='V4_LEGACY_API_DATABASE_FORBIDDEN_NO_FALLBACK'
                results.append(dict(configuration=config,provider=name,entry=entry,status='EXPECTED_REJECTION',reason=str(error)))
assert len(results)==12 and not attempts and not list(storage.rglob('*'))
record=dict(contract='R4_R3_ACTUAL_API_NO_FALLBACK_NEGATIVES_R2',driver_functions_replaced=False,pytest_plugin_loaded=False,
    attempted_socket_connections=attempts,created_database_files=[],results=results,
    actual_source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ('src/workbench_db/api_connection.py','scripts/audit_r4_r3_legacy_api_no_fallback.py')},
    full_native_api_migration='OPEN_REACHABLE_BUSINESS_REPLACEMENTS_REQUIRED',production_changed=False)
output.write_text(json.dumps(record,indent=2)+'\n',encoding='utf8');print(json.dumps(record))
