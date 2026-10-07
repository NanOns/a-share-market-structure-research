from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
ROOT = Path(__file__).resolve().parents[2]
def test_concentration_is_exact_reuse():
    d = pq.read_table(ROOT/"reports/shadow/v2/20260904/V2_DIAGNOSTIC_FACTORS.parquet", columns=["security_id","RETURN_CONCENTRATION_20"]).to_pandas()
    s = pq.read_table(ROOT/"reports/shadow/v2/20260904/steady_trend/STEADY_TREND_V2_SHADOW.parquet", columns=["security_id","return_concentration_20"]).to_pandas()
    x=d.merge(s,on="security_id",validate="one_to_one")
    pd.testing.assert_series_equal(x.RETURN_CONCENTRATION_20, x.return_concentration_20, check_names=False)

