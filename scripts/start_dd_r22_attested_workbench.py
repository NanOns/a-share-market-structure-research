"""Human-invoked normal start only, after previous service exits normally.

Does not stop an existing process; refuses an occupied port. Imports current
data modules, records real __file__/SHA/PID, then uses the existing AUTO service.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib,json,os,socket,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]

def main():
    for key in ('TMP','TEMP','TMPDIR'):os.environ[key]='G:/codex_tmp'
    sys.dont_write_bytecode=True
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1',28765))==0:raise SystemExit('PORT_OCCUPIED: normal exit of previous service required; no process stopped')
    modules=[]
    for name in ['operational_daily_executor_v1','source_readiness_v2','operational_daily_ready_owner_v2','operational_daily_owner_v1','operational_daily_jobs_v1','operational_daily_periods_v1']:
        path=ROOT/'src/workbench_analysis'/f'{name}.py'
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        module=importlib.import_module('workbench_analysis.'+name)
        actual=Path(module.__file__).resolve()
        assert actual==path.resolve() and hashlib.sha256(actual.read_bytes()).hexdigest()==before,'IMPORT_SOURCE_CHANGED'
        modules.append(dict(module=module.__name__,runtime_module_path=str(actual),sha256=before))
    from workbench_analysis.operational_daily_storage_v1 import atomic_json
    from workbench_service.operational_daily_server_v1 import serve_v4
    receipt=dict(contract='DD_R22_STARTUP_MODULE_ATTESTATION_V1',pid=os.getpid(),python=sys.executable,working_directory=str(ROOT),attested_at=datetime.now(timezone.utc).isoformat(),git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),modules=modules,port=28765,scope='Normal startup imports, no new data produced by attestation')
    os.chdir(ROOT)
    atomic_json(ROOT,ROOT/'runtime/dynamic_daily/loaded_modules_r22.json',receipt)
    print(json.dumps(receipt),flush=True)
    try:serve_v4(ROOT,'127.0.0.1',28765)
    except KeyboardInterrupt:pass

if __name__=='__main__':main()
