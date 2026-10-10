"""G-only regression receipt; fixtures cannot grant historical or live authority."""
from immediate_r3_common import *
import time
D=OUT/'11_DEEPENING'
def main():
    tests=['tests/test_research_hypotheses_r3.py','tests/test_validation_cohort_read_contract_r3.py','tests/test_core_product_read_r1.py',
      'tests/test_forward_r2.py','tests/test_forward_final_path_boundary.py','tests/test_forward_p1_stock.py',
      'tests/test_forward_p1_sector.py','tests/test_forward_p1_isolation.py','tests/v4_a04_r3/test_amount_a_go_forward.py']
    os.environ['PYTHONPATH']=str(ROOT/'src');import sys
    command=[sys.executable,'-m','pytest',*tests,'-q','--basetemp','G:/codex_tmp/test_temp/r3_deepening_'+str(time.time_ns()),'-p','no:cacheprovider']
    start=time.monotonic();r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf8')
    receipt=dict(command=command,exit_code=r.returncode,elapsed_seconds=time.monotonic()-start,stdout=r.stdout,stderr=r.stderr,
      tests=[binding(t) for t in tests],implementation=[binding(p) for p in ['src/workbench_service/core_product_bff_r1.py','src/workbench_service/research_hypotheses_r3.py','src/workbench_analysis/validation_cohort_read_contract_r3.py']],evidence_class='FIXTURE_ENGINEERING_AND_REAL_LEDGER_GUARD_TESTS',
      historical_as_recorded_acceptance=False,FEP_production_permission=False)
    write(OUT/'05_P1_COHORT/P1_FORWARD_FREEZE_AND_MATURITY_TESTS.json',receipt)
    print(r.stdout[-1500:]);return r.returncode
if __name__=='__main__':raise SystemExit(main())
