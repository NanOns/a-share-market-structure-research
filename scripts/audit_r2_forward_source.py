"""Actual two-date source oracle, explicitly distinct from real cohort maturity."""
import json,math,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.production_v4 import ProductionV4ResearchReader
from focus_tracker.v4_daily_driver import path_inputs
from focus_tracker.v4_path_adapter import AcceptedPaths
from workbench_service.forward_daily import LocalForwardPriceSource
from workbench_service.current_v4_context import SourceInvalid
from workbench_analysis.v4_15_settlement_successor import price_path
OUT=ROOT/'docs/evidence/r2_forward_continuation_20261008'

def main():
    r=ProductionV4ResearchReader(ROOT);inputs=path_inputs(ROOT,r.manifest);paths=AcceptedPaths(ROOT,inputs)
    source=LocalForwardPriceSource(ROOT,inputs,'2026-09-29','2026-09-30',accepted_paths=paths)
    comparisons=[]
    with sqlite3.connect(paths.series.as_uri()+'?mode=ro',uri=True) as db:
        ids=[v[0] for v in db.execute("SELECT security FROM bars WHERE day IN ('2026-09-29','2026-09-30') GROUP BY security HAVING count(*)=2 ORDER BY security LIMIT 10")]
        for sid in ids:
            bars={day:json.loads(payload) for day,payload in db.execute('SELECT day,payload FROM bars WHERE security=? AND day>=? AND day<=?',(sid,'2026-09-29','2026-09-30'))}
            row=source.read(sid,'2026-09-30','2026-09-30','2026-09-30');raw0=float(bars['2026-09-29']['raw_ohlc'][3]);raw1=float(bars['2026-09-30']['raw_ohlc'][3])
            assert row['verified_identity'] and row['verified_adjustment']
            # These ten actual windows contain no corporate action, allowing a
            # RAW-only ratio oracle independent from the affine/Forward kernels.
            assert row['T0_transform_coefficients']==dict(alpha=1.,beta=0.)
            result=price_path(raw0,[row],'2026-09-30');expected=raw1/raw0-1
            assert math.isclose(result['R_N'],expected,abs_tol=1e-12)
            expected_mfe=max(raw0,float(bars['2026-09-30']['raw_ohlc'][1]))/raw0-1
            expected_mae=min(raw0,float(bars['2026-09-30']['raw_ohlc'][2]))/raw0-1
            assert math.isclose(result['MFE_N'],expected_mfe,abs_tol=1e-12) and math.isclose(result['MAE_N'],expected_mae,abs_tol=1e-12)
            assert math.isclose(result['PATH_MDD_CLOSE_N'],min(0,expected),abs_tol=1e-12)
            comparisons.append(dict(security_id=sid,R_N=result['R_N'],MFE_N=result['MFE_N'],MAE_N=result['MAE_N'],PATH_MDD_CLOSE_N=result['PATH_MDD_CLOSE_N']))
    rejected=[]
    for day,basis,cutoff in [('2026-10-09','2026-10-09','2026-09-30'),('2026-09-30','2026-10-09','2026-09-30'),('2026-09-30','2026-09-30','2026-10-09')]:
        try:source.read(ids[0],day,basis,cutoff)
        except SourceInvalid as e:rejected.append(str(e))
        else:raise AssertionError('future input allowed')
    write(OUT/'REAL_TWO_DATE_PRICE_ORACLE.json',dict(result='PASS',scope='ACTUAL_SOURCE_PATH_ONLY_NOT_COHORT_MATURITY',actual_windows=10,
        numeric_comparisons=40,comparisons=comparisons,future_reads_rejected=rejected,inputs=inputs,strict_pit=False,real_cohort_maturity_proven=False))
    print(json.dumps(dict(result='PASS',windows=len(comparisons))))

if __name__=='__main__':main()
