"""Normal product start after the previous service exits; never stops a process."""
from pathlib import Path
import hashlib, importlib, json, marshal, os, socket, subprocess, sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]

def configure_temp_root():
    from common.paths import resolve_ingest_temp_root
    temp_root=resolve_ingest_temp_root(ROOT)
    temp_root.mkdir(parents=True,exist_ok=True)
    for key in ('TMP','TEMP','TMPDIR'):os.environ[key]=str(temp_root)

def main():
    configure_temp_root()
    sys.dont_write_bytecode=True
    from workbench_desktop.storage import WorkspaceLease
    with WorkspaceLease(ROOT):return owned_main()

def owned_main():
    configure_temp_root()
    sys.dont_write_bytecode=True
    # The configured shared project identity may be privileged. Every startup
    # probe remains in a server-side READ ONLY transaction.
    os.environ['V4_NATIVE_ALLOW_PRIVILEGED_READ_ROLE']='1'
    from workbench_db.v4_publication_reader import PgPublicationReader,PublicationReadError
    try:pg_authority_before=PgPublicationReader.startup_head_tuple()
    except PublicationReadError as exc:raise SystemExit('V4_PG_STARTUP_AUTHORITY_UNAVAILABLE:'+exc.code) from exc
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1',28765))==0:
            raise SystemExit('PORT_OCCUPIED: previous service must exit normally; no process stopped')
    names=['workbench_service.core_product_server_r1','workbench_service.core_product_bff_r1',
           'workbench_service.research_hypotheses_r3','workbench_analysis.validation_cohort_read_contract_r3',
           'workbench_analysis.operational_daily_jobs_v1','workbench_analysis.operational_daily_executor_v1',
           'workbench_analysis.fep_e5.admission','workbench_analysis.fep_e5.trusted_authority',
           'workbench_analysis.cohort_capture_readiness_r1','workbench_analysis.cohort_first_capture_producer_r1',
           'sector.producer_entry_r1','sector.legacy_producer_candidate_r1']
    before={name:hashlib.sha256((ROOT/'src'/Path(*name.split('.')).with_suffix('.py')).read_bytes()).hexdigest() for name in names}
    modules=[]
    for name in names:
        module=importlib.import_module(name);path=Path(module.__file__).resolve()
        expected=(ROOT/'src'/Path(*name.split('.')).with_suffix('.py')).resolve()
        if path!=expected or hashlib.sha256(path.read_bytes()).hexdigest()!=before[name]:
            raise ValueError('STARTUP_IMPORT_SOURCE_CHANGED:'+name)
        functions={k:hashlib.sha256(marshal.dumps(v.__code__)).hexdigest() for k,v in vars(module).items()
                   if getattr(v,'__module__',None)==name and hasattr(v,'__code__')}
        modules.append(dict(module=name,runtime_module_path=str(path),source_sha256=before[name],loaded_function_bytecode_sha256=functions))
    from workbench_analysis.operational_daily_storage_v1 import atomic_json
    try:pg_authority_after=PgPublicationReader.startup_head_tuple()
    except PublicationReadError as exc:raise SystemExit('V4_PG_STARTUP_AUTHORITY_CHANGED_OR_UNAVAILABLE:'+exc.code) from exc
    if pg_authority_after!=pg_authority_before:raise SystemExit('V4_PG_STARTUP_AUTHORITY_MOVED_DURING_IMPORT')
    receipt=dict(contract_id='R4_PRODUCT_STARTUP_ATTESTATION_V1',pid=os.getpid(),startup_time=datetime.now(timezone.utc).isoformat(),
                 python_executable=sys.executable,repo_root=str(ROOT),exact_HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                 active_port=28765,modules=modules,pg_authority=pg_authority_before,
                 scope='Normal startup only; existing AUTO configuration preserved')
    atomic_json(ROOT,ROOT/'runtime/r4_product_loaded_modules.json',receipt)
    print(json.dumps(receipt),flush=True)
    import time
    from workbench_desktop.engine import EngineController
    engine=EngineController(ROOT,28765)
    try:
        engine.perform('start')
        while True:time.sleep(.5)
    except KeyboardInterrupt:pass
    finally:
        if engine.state!='STOPPED':engine.perform('stop')

if __name__=='__main__':main()
