from pathlib import Path
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[2]
def test_output_is_never_production_eligible():
 x=pq.read_table(ROOT/"reports/shadow/v2/20260904/strong_pullback/STRONG_PULLBACK_V2_SHADOW.parquet",columns=["shadow","production_eligible"]).to_pandas()
 assert x.shadow.all() and not x.production_eligible.any()
