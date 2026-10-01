"""R2 semantic-repair and scoped-formalization clean verification in disposable DB."""
from datetime import datetime,timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,os,subprocess,sys,time,xml.etree.ElementTree as ET
import psycopg
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.next_round_bundle_r2 import verify_protected,bind,write,atomic_bytes,P,read,exact
from scripts.verify_dm01_data_head_promotion_clean_r1 import FAMILIES,DESELECT
from scripts.run_v4_08_r3_isolated_verification import disposable_cluster,apply_migrations
from scripts.scan_no_symbol_specific_runtime_logic import run as scan
from scripts.verify_v4_08_r5_1 import compact_scan
from workbench_analysis.dm01_accepted_chain_v1 import validate_head_v2,validate_historical_incremental_registry
from workbench_analysis.parallel_scoped_acceptance_r1 import (
    read_accepted_history,DISPOSITIONS,record_path,validate_record,
    OWNER_PATH,READER_PATH,validate_accepted_owner_metadata,validate_reader_manifest)
from scripts.verify_next_round_bundle_clean_r1 import EXTRA as PREVIOUS_EXTRA
EXTRA=['tests/v4_a10','tests/v4_a10_r2','tests/v4_a11','tests/v4_a12','tests/v4_a12_r2','tests/v4_a08','tests/v4_a09','tests/v4_registry_r3','tests/v4_registry_r4',
 'tests/v4_dm01_r2','tests/v4_a10_a12_r3','tests/v4_a13','tests/v4_dm01_r3','tests/v4_dm01_promotion',
 'tests/v4_11','tests/v4_a02_r2','tests/v4_a03_a04_a07_r2','tests/v4_a05_r2','tests/v4_a06_r2','tests/v4_owner_bootstrap_r1','tests/v4_publication_reader_di_r1',
 'tests/v4_parallel_scoped_formalization_r1','tests/v4_a04_r3']

def required_families():
    # Every already-required old family is retained. New independently owned
    # A02/A05 test directories can land later without omission from this batch.
    additions=[p.relative_to(ROOT).as_posix() for pattern in ('v4_a02*','v4_a05*')
        for p in sorted((ROOT/'tests').glob(pattern)) if p.is_dir()]
    families=list(dict.fromkeys(FAMILIES+PREVIOUS_EXTRA+EXTRA+additions))
    missing=[p for p in families if not (ROOT/p).exists()]
    if missing:raise ValueError('REQUIRED_REGRESSION_FAMILY_MISSING:'+','.join(missing))
    return families

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True,encoding='utf8').strip()
def main():
    started=time.monotonic();before=git('status','--porcelain=v1');head=git('rev-parse','HEAD')
    if before or (ROOT/'config/.env').exists():raise ValueError('CLEAN_CHECKOUT_WITHOUT_CONFIG_ENV_REQUIRED')
    entry=verify_protected();protected={r['path']:hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest() for r in entry['protected_baseline']}
    manifest=read(P+'BATCH_CANDIDATE_ARTIFACT_MANIFEST_R1.json')
    for ref in manifest['artifacts']:exact(ref)
    source_readback=validate_head_v2(ROOT,read('data/v4/V4_DATA_ACCEPTED_HEAD.json'),source_readback=True)
    registry=validate_historical_incremental_registry(ROOT)
    scoped_records={p:validate_record(ROOT,read(record_path(p)),p) for p in DISPOSITIONS}
    scoped_owner=validate_accepted_owner_metadata(ROOT,read(OWNER_PATH))
    scoped_reader=validate_reader_manifest(ROOT,read(READER_PATH))
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(read_accepted_history,ROOT,'V4-09'),pool.submit(read_accepted_history,ROOT,'V4-10'),pool.submit(__import__('scripts.validate_v4_10_promotion_r1',fromlist=['validate']).validate)]
        historical_v9,historical_v10,current_v10=[f.result() for f in futures]
    if historical_v9['status']!='PASS' or historical_v10['status']!='PASS' or current_v10['checks']['P19_protected']!='FAIL':
        raise ValueError('HISTORY_OR_CURRENT_AUTHORITY_BOUNDARY_CHANGED')
    cmd=[sys.executable,'scripts/verify_a02_a05_formal_amendment_readback_r1.py']
    ar=subprocess.run(cmd,cwd=ROOT,check=True,capture_output=True,text=True,encoding='utf8',timeout=180)
    a02a05=json.loads(ar.stdout)
    if a02a05.get('status')!='PASS':raise ValueError('A02_A05_FORMAL_AMENDMENT_READBACK_FAILED')
    with disposable_cluster(Path('E:/Postgres/bin')) as (dsn,temp):
        with psycopg.connect(dsn) as pg:
            migrations=apply_migrations(pg);identity=pg.execute('SELECT current_database(),current_user,inet_server_addr()::text,inet_server_port()').fetchone()
        nums=[int(Path(m['path']).name[:3]) for m in migrations]
        if nums!=list(range(1,28)):raise ValueError('UNIFIED_MIGRATION_ALLOCATION_INVALID')
        guard=temp/'guard';guard.mkdir()
        (guard/'sitecustomize.py').write_text("import sys,os\ndef forbid(event,args):\n if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):\n  path=os.fsdecode(args[0]).replace('\\\\','/').lower()\n  if path.endswith('/config/.env'):raise RuntimeError('CONFIG_ENV_READ_FORBIDDEN')\nsys.addaudithook(forbid)\n",encoding='utf8')
        env=os.environ.copy();env.update(WORKBENCH_PG_DSN=dsn,V4_10_DISPOSABLE_TEST_DSN=dsn,PYTHONPATH=str(guard)+os.pathsep+str(ROOT)+os.pathsep+str(ROOT/'src'),PYTHONIOENCODING='utf-8')
        for k in ('PGPASSWORD','PGSERVICE','PGSERVICEFILE'):env.pop(k,None)
        families=required_families();junit=temp/'tests.xml'
        command=[sys.executable,'-m','pytest','-q',*families,'--deselect='+DESELECT,'--junitxml='+str(junit)]
        proc=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=1500)
        suites=list(ET.parse(junit).getroot().iter('testsuite')) if junit.exists() else []
        summary={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')};summary['passed']=summary['tests']-summary['failures']-summary['errors']-summary['skipped']
        xml=junit.read_bytes() if junit.exists() else b''
    no_symbol=scan(ROOT);after=git('status','--porcelain=v1');verify_protected()
    unchanged=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==s for p,s in protected.items())
    ok=bool(suites) and proc.returncode==0 and unchanged and not after and no_symbol['status']=='PASS' and registry['status'].startswith('PASS')
    attempt=1
    while (ROOT/(P+f'BATCH_CLEAN_ATTEMPT_R{attempt}.json')).exists():attempt+=1
    prefix=P+f'BATCH_CLEAN_ATTEMPT_R{attempt}'
    atomic_bytes(prefix+'.xml',xml);atomic_bytes(prefix+'.log',(proc.stdout+'\n'+proc.stderr).encode('utf8'))
    receipt=dict(contract_id='V4_NEXT_ROUND_CLEAN_CHECKOUT_V2',status='PASS_ENGINEERING_REGRESSION' if ok else 'FAIL',tested_commit=head,
        summary=summary,required_families=families,pytest_return_code=proc.returncode,authorized_deselects=[DESELECT],new_deselects=[],
        junit=bind(prefix+'.xml'),log=bind(prefix+'.log'),no_symbol=compact_scan(no_symbol),git_status_before=before,git_status_after=after,
        protected_heads_before=protected,protected_heads_unchanged=unchanged,stage_head_action='KEEP',data_head_action='KEEP',
        source_readback=source_readback,incremental_registry=registry,A02_A05_independent_source_readback=a02a05,
        scoped_external_acceptance_records=scoped_records,inactive_accepted_owner_metadata=scoped_owner,accepted_history_only_v2_reader=scoped_reader,
        historical_publications=dict(V4_09=historical_v9,V4_10=historical_v10),current_v4_10_protected_gate=current_v10['checks']['P19_protected'],
        migrations=migrations,database_identity=dict(zip(('database','owner','address','port'),identity)),
        database_scope='DISPOSABLE_ISOLATED_CLUSTER_ONLY',temporary_cluster_cleaned_up=True,config_dot_env_read=False,config_dot_env_present=False,
        configured_or_production_database_used=False,password_persisted=False,candidate_artifact_manifest=bind(P+'BATCH_CANDIDATE_ARTIFACT_MANIFEST_R1.json'),
        permissions=entry['permissions'],external_acceptance=False,new_implementation_external_acceptance=False,next_stage='STOP_WAIT_FOR_INDEPENDENT_EXTERNAL_REAUDIT',
        completed_at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=round(time.monotonic()-started,3))
    write(prefix+'.json',receipt)
    if ok:write(P+'BATCH_CLEAN_CHECKOUT_R1.json',receipt)
    print(json.dumps(dict(status=receipt['status'],tested_commit=head,summary=summary,no_symbol=no_symbol['status'],elapsed_seconds=receipt['elapsed_seconds'])))
    return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
