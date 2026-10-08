"""Test receipt plus independent real-data invariants; does not accept release."""
import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.market_source_acquisition import write, digest
OUT=ROOT/'docs/evidence/source_acquisition_r4_20261009'


def main():
    result=subprocess.run([sys.executable,'-X','utf8','-B','-m','pytest',
        'tests/test_market_source_acquisition_r4.py','tests/test_v4_current_daily_refresh.py',
        'tests/v4_dm01/test_official_daily_sources_v2.py','-q',
        '--basetemp','E:/codex_tmp/test_temp/r4_release_verification'],cwd=ROOT,capture_output=True,text=True,encoding='utf8')
    oracle=json.loads((OUT/'03_FOUR_SESSION_QFQ_GAP_RECAPTURE_AND_ADJUSTMENT_ORACLE.json').read_bytes())
    matrix=list(csv.DictReader((OUT/'02_FOUR_SESSION_PER_SECURITY_SOURCE_MATRIX.csv').open(encoding='utf8')))
    entry=json.loads((OUT/'00_R4_ENTRY_HEAD_AND_EXISTING_SOURCE_CONTRACT.json').read_bytes())
    checks=dict(legacy_qfq_security_days=oracle['legacy_qfq_count']==528,
        preserved_suspension_baseline=sum(r['before']=='EXPECTED_NO_BAR' for r in oracle['legacy_rows'])==35,
        exact_four_dates=set(r['trade_date'] for r in matrix)==set(entry['dates']),
        no_sz399_index_as_stock=not any(r['source_security_key'].startswith('sz.399') for r in matrix),
        real_sample_minimum=len(oracle['oracle_comparisons'])>=20,
        protected_heads_and_old_contracts=all(digest((ROOT/p).read_bytes())==sha for p,sha in entry['preserved'].items()))
    write(OUT/'TEST_RESULTS.json',dict(pytest_exit=result.returncode,stdout=result.stdout,stderr=result.stderr,
        independent_real_receipt_invariants=checks,matrix_counts=dict(Counter(r['trade_date'] for r in matrix)),
        release_acceptance=False,stage_acceptance='NOT_COMPLETE'))
    print(json.dumps(dict(pytest_exit=result.returncode,checks=checks)))
    return 0 if result.returncode==0 and all(checks.values()) else 2


if __name__=='__main__':raise SystemExit(main())
