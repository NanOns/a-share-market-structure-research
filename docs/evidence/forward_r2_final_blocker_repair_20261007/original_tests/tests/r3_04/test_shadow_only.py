from pathlib import Path
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[2]
def test_flags():
 x=pq.read_table(ROOT/"reports/shadow/v2/20260904/sector_leader/SECTOR_LEADER_V2_SHADOW.parquet",columns=["shadow","production_eligible"]).to_pandas();assert x.shadow.all() and not x.production_eligible.any()
