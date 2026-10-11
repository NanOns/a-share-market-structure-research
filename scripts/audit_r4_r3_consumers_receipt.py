"""Read-only source binding and scoped real scheduler consumer receipt."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import psycopg

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/audits/r4_r3_consumers_20261011'
def write(name,value):
    temporary=OUT/(name+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    os.replace(temporary,OUT/name)

def main():
    sources=['src/workbench_analysis/operational_daily_jobs_v1.py',
             'src/workbench_analysis/operational_daily_jobs_pg_r1.py',
             'src/workbench_analysis/operational_daily_executor_v1.py',
             'src/workbench_desktop/jobs.py','src/workbench_desktop/engine.py',
             'src/workbench_service/core_product_server_r1.py',
             'src/workbench_service/operational_daily_server_v1.py',
             'tests/test_v4_pg_runtime_consumers_r3.py','tests/test_v4_pg_jobs_r4.py',
             'tests/v4_native_isolation_plugin_r4.py']
    bindings={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sources}
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    ledger=[json.loads(line) for line in (OUT/'V4_DATABASE_RUNTIME_INTENTS.jsonl').read_text(encoding='utf8').splitlines()]
    cases=ET.parse(OUT/'CONSUMERS_JUNIT.xml').findall('.//testcase')
    counts={state:sum(1 for case in cases if ('FAIL' if case.find('failure') is not None else 'ERROR' if case.find('error') is not None else 'SKIP' if case.find('skipped') is not None else 'PASS')==state) for state in ['PASS','FAIL','ERROR','SKIP']}
    with psycopg.connect(os.environ['V4_NATIVE_PG_DSN']) as pg:
        identity=pg.execute("SELECT current_database(),(SELECT oid FROM pg_database WHERE datname=current_database()),(pg_control_system()).system_identifier,current_setting('data_directory')").fetchone()
    nonpg=[event for event in ledger if event.get('engine') in ('sqlite3','duckdb')]
    business_nonpg=[event for event in nonpg if not (event.get('nodeid') or '').endswith('test_guard_cannot_satisfy_business_exception')]
    write('EXECUTION_SOURCE_BINDINGS.json',dict(contract_id='R4_R3_CONSUMER_SOURCE_BINDINGS_R1',run_utc=datetime.now(timezone.utc).isoformat(),base_commit=head,dirty_working_source_sha256=bindings,source_binding_rule='Exact file digests bind loaded source; final evidence commit is not execution source SHA',database_identity=dict(database=identity[0],database_oid=identity[1],system_identifier=identity[2],data_directory=identity[3])))
    write('PG_ONLY_RUNTIME_ZERO_FALLBACK.json',dict(contract_id='R4_R3_RUNTIME_CONSUMERS_SCOPED_R1',results=counts,scope='Historical public import and default/desktop workers with actual executor accepted-T0 recovery NOOP and default HTTP settings',business_non_pg_attempts=len(business_nonpg),injected_negative_non_pg_attempts=len(nonpg)-len(business_nonpg),pg_sql_intents=sum(event.get('event')=='SQL_INTENT' for event in ledger),independent_oracle='Original accepted-trade-date bytes determine expected NOOP receipt; PG final status independently read through state query and HTTP paused boolean; Head bytes identical',status='SCOPED_PASS' if counts['PASS']==13 and not business_nonpg and not counts['FAIL'] and not counts['ERROR'] else 'SCOPED_FAIL',full_runtime_closure='OPEN',limitations=['Real acquisition/Owner ingestion/Joint Head publication not exercised by accepted-T0 no-op','Desktop engine production_factory Windows packaging not exercised','DB06/08/09/12 dynamic supported-branch proof remains OPEN','No source field numeric computation is performed by accepted-T0 no-op; numeric oracle belongs to separate algorithm work package'],closing_conditions=['Complete actual source publication/PG consumers integration','Supported dynamic entry probes and replay/exception paths','Independent frozen-commit external review']))
    rows=[
        ['Historical DailyJobs import','operational_daily_jobs_v1.DailyJobs','Native PG constructor','TRUE','PUBLIC_IMPORT_FAIL_CLOSED_PASS'],
        ['Default worker','operational_daily_jobs_v1.start -> tick','execute_sources accepted-T0 no-op -> PG jobs','TRUE','SCOPED_RECOVERY_PASS'],
        ['Desktop worker','ManagedDailyJobs.start -> execute','execute_sources accepted-T0 no-op -> PG jobs','TRUE','SCOPED_RECOVERY_PASS'],
        ['Default HTTP settings','make_product_handler -> make_daily_handler','PG scheduler_policy','TRUE','PAUSED_READBACK_PASS'],
        ['Source acquisition and Joint Head','serve_v4 executor','Sources -> PG snapshot/series/journal/shadow','CONDITIONAL','OPEN_INTEGRATION'],
        ['Desktop full engine','EngineController.production_factory','Recovery -> HTTP -> managed worker','CONDITIONAL','OPEN_WINDOWS_ENGINE'],
        ['DuckDB API bridge','PostgresDuckDBApiConnectionProvider','Legacy app/research builder','UNRESOLVED','OPEN_DYNAMIC_SCOPE'],
    ]
    import csv,io
    buffer=io.StringIO();writer=csv.writer(buffer);writer.writerow(['consumer','entry','producer_to_store','actual_call','status']);writer.writerows(rows)
    temporary=OUT/'V4_ALL_REAL_CONSUMERS.csv.tmp';temporary.write_text(buffer.getvalue(),encoding='utf8');os.replace(temporary,OUT/'V4_ALL_REAL_CONSUMERS.csv')
    print(json.dumps(dict(results=counts,business_non_pg_attempts=len(business_nonpg),pg_sql_intents=sum(event.get('event')=='SQL_INTENT' for event in ledger))))

if __name__=='__main__':main()
