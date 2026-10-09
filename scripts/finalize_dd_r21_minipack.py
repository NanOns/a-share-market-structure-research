"""Atomic compact packaging and isolated offline acceptance; no cloud transfer."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.tdx_official_daily_source import _atomic_write
OUT=ROOT/'docs/evidence/dynamic_daily_r2_20261009';PACK=OUT/'minipack'

def write(path,data):_atomic_write(path,data,tdx_root=Path('D:/new_tdx'))
def bind(p):return dict(name=p.name,path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())

def main():
    for name in ['R2_02_SOURCE_RECEIPT_REPLAY.json','R2_04_TEST_RECEIPT.json','R2_04_AFTER_SERVICE_RELOAD.json','STAGE_LEDGER.json']:
        write(PACK/'receipts'/name,(OUT/name).read_bytes())
    for name in ['test_dynamic_daily_r21_repair.py','test_dd_r21_process_races.py','test_operational_successor_release_v1.py','test_operational_daily_periods_v1.py']:
        write(PACK/'tests'/name,(ROOT/'tests'/name).read_bytes())
    delta=subprocess.check_output(['git','diff','851770b1932d95836ce76bb44fd292117958bf04','HEAD','--','src/workbench_analysis/operational_daily_jobs_v1.py','src/workbench_analysis/operational_daily_executor_v1.py','src/workbench_analysis/source_readiness_v2.py','src/workbench_service/operational_daily_server_v1.py','src/workbench_service/operational_successor_bff_v1.py'],cwd=ROOT)
    write(PACK/'code/REPAIR.diff',delta)
    readme='''# R2.1 offline replay

Python 3.11+ standard library only. No network, account, provider login, database,
or repository is required for the numerical oracle.

```text
python oracle/independent_recompute.py --input . --output <separate_output_directory>
```

The script first verifies every SHA256SUMS entry. ZIP CRC must also be checked
with Python zipfile.ZipFile(...).testzip(). All sampling names were frozen
before reading factor values. Numerical inputs are bounded excerpts from frozen
normalized Owner history, not independent copies of raw official ZIP bytes.
Core rolling formulas, full-cohort RPS ranks/ties, selected-sector medians and
breadth, and period OHLCV/amount are reproducible. Event-to-affine provenance,
all-cohort antecedent returns, full Native/LOO/Market and period calendar/status
closure are NOT_VERIFIABLE. Full market/Owner independent acceptance is NOT_GRANTED.

The repository tests need pytest and repository src; they are included for
review, separately from the standalone offline numerical oracle. Their source
and publication admission are explicitly ISOLATED_INJECTION; the real service
readback receipt is REAL_LOCAL; frozen-source gate replay is SOURCE_RECEIPT_REPLAY.
Windows machine reboot/pre-login was NOT_TESTED.
'''
    write(PACK/'EXTERNAL_REPLAY_README.md',readme.encode())
    def sums():
        files=[p for p in PACK.rglob('*') if p.is_file() and p!=PACK/'checksums/SHA256SUMS.txt']
        write(PACK/'checksums/SHA256SUMS.txt',''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(PACK).as_posix()+'\n' for p in sorted(files)).encode())
    sums()
    result=subprocess.run([sys.executable,str(PACK/'oracle/independent_recompute.py'),'--input',str(PACK),'--output','E:/codex_tmp/dd_r21_oracle_final'],capture_output=True,text=True)
    if result.returncode:raise ValueError(result.stdout+result.stderr)
    write(PACK/'oracle/ORACLE_OUTPUT.json',Path('E:/codex_tmp/dd_r21_oracle_final/ORACLE_OUTPUT.json').read_bytes())
    write(PACK/'oracle/ORACLE_RUN.txt',(result.stdout+'exit_code=0\n').encode());sums()
    zip_path=OUT/'DD_R2_1_AUDIT_MINIPACK.zip';tmp=zip_path.with_suffix('.tmp')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(PACK.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(PACK).as_posix())
    if tmp.stat().st_size>10*1024*1024:raise ValueError('UPLOAD_BLOCKED_OVERSIZE')
    os.replace(tmp,zip_path)
    isolated=Path('E:/codex_tmp')/('dd_r21_offline_'+hashlib.sha256(zip_path.read_bytes()).hexdigest()[:16])
    with zipfile.ZipFile(zip_path) as z:
        if z.testzip() is not None:raise ValueError('ZIP_CRC_FAILED')
        for name in z.namelist():
            p=(isolated/name).resolve()
            if not p.is_relative_to(isolated.resolve()):raise ValueError('ZIP_PATH_ESCAPE')
        z.extractall(isolated)
    run=subprocess.run([sys.executable,str(isolated/'oracle/independent_recompute.py'),'--input',str(isolated),'--output',str(isolated.parent/(isolated.name+'_result'))],capture_output=True,text=True)
    if run.returncode:raise ValueError(run.stdout+run.stderr)
    result=json.loads((isolated.parent/(isolated.name+'_result')/'ORACLE_OUTPUT.json').read_bytes())
    atomic_json(ROOT,OUT/'R2_06_OFFLINE_ACCEPTANCE.json',dict(zip=bind(zip_path),crc='PASS',all_payload_sha='PASS',isolated_directory=str(isolated),oracle_exit=run.returncode,oracle_stdout=run.stdout,checks=result['checks'],period_checks=result['period_checks'],errors=len(result['errors']),external_acceptance='NOT_GRANTED'))
    print(json.dumps(dict(zip=bind(zip_path),stdout=run.stdout)))

if __name__=='__main__':main()
