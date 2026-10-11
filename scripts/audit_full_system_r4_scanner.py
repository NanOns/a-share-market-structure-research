"""Real V4 files, frozen full-receipt scanner comparison and bounded timings."""
import json,subprocess,sys,time,types,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.audit_full_system_r4_scope import write,sha
from scripts import scan_no_symbol_specific_runtime_logic as current

def main():
    source=subprocess.check_output(['git','show','fbd23a6b:scripts/scan_no_symbol_specific_runtime_logic.py'],cwd=ROOT)
    frozen=types.ModuleType('r4_frozen_scanner');exec(compile(source,'frozen_scanner','exec'),frozen.__dict__)
    origin=Path('G:/codex work/大A交易');paths=[ROOT/'src/workbench_service/core_product_bff_r1.py',ROOT/'src/workbench_analysis/operational_daily_jobs_pg_r1.py',ROOT/'src/workbench_db/migrations/v4_postgres/033_fep_e5_pipeline_typed_signal_authority_v1.sql',origin/'reports/fep_e1_r2_final/OWNER_ROW_PROJECTION.json']
    # Choose the real declared 033 filename without guessing its suffix.
    paths[2]=next((ROOT/'src/workbench_db/migrations/v4_postgres').glob('033_*.sql'))
    rows=[]
    for path in paths:
        root=ROOT if path.is_relative_to(ROOT) else origin;start=time.perf_counter();old=frozen.scan_file(path,root=root,category='EVIDENCE');old_time=time.perf_counter()-start
        start=time.perf_counter();new=current.scan_file(path,root=root,category='EVIDENCE');new_time=time.perf_counter()-start
        if new!=old:raise ValueError('REAL_FILE_SCANNER_RECEIPT_DIFF:'+str(path))
        rows.append(dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size,frozen_seconds=old_time,indexed_seconds=new_time,receipt_sha256=hashlib.sha256(json.dumps(new,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),identical=True))
    write('R4_09_REAL_FILE_SCANNER_RESULT.json',dict(contract_id=current.LINE_INDEX_CONTRACT,denominator=len(rows),files=rows,current_status='SCOPED_REAL_FILE_FULL_RECEIPT_EQUIVALENCE_PASS',limitations=['Single-process bounded timings; not a full governance scan or homepage capacity acceptance','Category policy and hard gate are unchanged; no new performance threshold invented'],next_conditions=['Complete supported V4 scan and separately authorized homepage capacity threshold']))
    print(json.dumps(dict(real_files=len(rows),full_receipt_differences=0)))
if __name__=='__main__':main()
