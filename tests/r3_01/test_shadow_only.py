from pathlib import Path
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[2]
def test_all_rows_shadow_only():
    x=pq.read_table(ROOT/"reports/shadow/v2/20260904/steady_trend/STEADY_TREND_V2_SHADOW.parquet",columns=["shadow","production_eligible"]).to_pandas()
    assert x.shadow.all() and not x.production_eligible.any()

