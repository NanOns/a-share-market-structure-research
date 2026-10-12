"""Targeted module replay after exact missing-input recovery; no baseline replacement."""
import csv,json,os,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/audits/r4_r3_scope_20261011'
ledger=OUT/'V4_BASELINE_FULL_GUARDED_20261011T120132_INDEPENDENT_NODES.csv'
modules=set()
for row in csv.DictReader(ledger.open(encoding='utf8')):
    if row['category']!='FROZEN_FIXTURE_ABSENT':continue
    module=row['nodeid'].split('::')[0].replace('.','/')+'.py'
    if not (ROOT/module).is_file():raise ValueError('FAILURE_MODULE_IDENTITY_UNRESOLVED:'+module)
    modules.add(module)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S');name='RECOVERED_INPUT_MODULES_'+stamp
dsn='host=127.0.0.1 port=55792 user=r4_isolated_admin dbname=fep_e1_fresh'
env=dict(os.environ,TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join([str(ROOT/'src'),str(ROOT),'G:/codex_tmp/r4_r3_python_deps']),V4_NATIVE_PG_DSN='host=127.0.0.1 port=55791 user=r4_isolated_admin dbname=postgres',R4_NATIVE_ISOLATION='1',R4_PG_DATA_DIRECTORY='G:/codex_tmp/full_system_r4_fbd23a6b/pg_data',R4_CONNECTION_LEDGER=str(OUT/(name+'_INTENTS.jsonl')),FEP_E1_TEST_DSN=dsn,FEP_E5_TEST_DSN=dsn,WORKBENCH_PG_DSN=dsn,V4_10_DISPOSABLE_TEST_DSN=dsn,R4_PG_TEST_CAPABILITIES=str(ROOT/'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b/R4_PG_TEST_CAPABILITIES.json'),R4_R3_EXTRA_PG_FIXTURES=str(OUT/'R3_EXTRA_PG_FIXTURES.json'),FEP_E5_CANONICAL_TEST_ENABLE='1',FEP_AUTHORITY_TEST_DSN='host=127.0.0.1 port=55793 user=r4_isolated_admin dbname=fep_authority_isolated')
command=[sys.executable,'-B','-m','pytest','-p','tests.v4_native_isolation_plugin_r4','-q',*sorted(modules),'--basetemp=G:/codex_tmp/test_temp/'+name,'-o','cache_dir=G:/codex_tmp/pytest_cache_failure_fixtures','--junitxml='+str(OUT/(name+'.xml'))]
(OUT/(name+'_ADMISSION.json')).write_text(json.dumps(dict(source_ledger=str(ledger.relative_to(ROOT)),modules=sorted(modules),scope='Targeted recovery diagnostic; all historical outcomes preserved; not final legal denominator'),indent=2),encoding='utf8')
with (OUT/(name+'_RAW.log')).open('x',encoding='utf8') as log:
    result=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
print(json.dumps(dict(evidence=name,exit_code=result.returncode)))
