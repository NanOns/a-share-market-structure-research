"""Normal product start after the previous service exits; never stops a process."""
from pathlib import Path
import hashlib, importlib, json, marshal, os, socket, subprocess, sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]

def main():
    for key in ('TMP','TEMP','TMPDIR'):os.environ[key]='G:/codex_tmp'
    sys.dont_write_bytecode=True
    authority=ROOT/'config/v4_production_runtime_authority_v1.json'
    if not authority.is_file():raise SystemExit('V4_RUNTIME_AUTHORITY_MISSING: fail closed')
    json.loads(authority.read_bytes())  # Same explicit --v4-default entry as the existing launcher.
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1',28765))==0:
            raise SystemExit('PORT_OCCUPIED: previous service must exit normally; no process stopped')
    names=['workbench_service.core_product_server_r1','workbench_service.core_product_bff_r1',
           'workbench_service.research_hypotheses_r3','workbench_analysis.validation_cohort_read_contract_r3',
           'workbench_analysis.operational_daily_jobs_v1','workbench_analysis.operational_daily_executor_v1']
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
    protected={name:hashlib.sha256((ROOT/'data/v4'/name).read_bytes()).hexdigest()
               for name in ('V4_OPERATIONAL_RESEARCH_HEAD.json','V4_DATA_ACCEPTED_HEAD.json')}
    receipt=dict(contract_id='R4_PRODUCT_STARTUP_ATTESTATION_V1',pid=os.getpid(),startup_time=datetime.now(timezone.utc).isoformat(),
                 python_executable=sys.executable,repo_root=str(ROOT),exact_HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                 active_port=28765,modules=modules,protected_heads=protected,scope='Normal startup only; existing AUTO configuration preserved')
    atomic_json(ROOT,ROOT/'runtime/r4_product_loaded_modules.json',receipt)
    print(json.dumps(receipt),flush=True)
    try:sys.modules[names[0]].serve_v4(ROOT,'127.0.0.1',28765)
    except KeyboardInterrupt:pass

if __name__=='__main__':main()
