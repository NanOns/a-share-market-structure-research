from pathlib import Path
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[2]
def test_unique():
 x=pq.read_table(ROOT/"reports/shadow/v2/20260904/priority/V2_UNIFIED_RESEARCH_BOARD.parquet",columns=["security_id"]).to_pandas();assert len(x)==1015 and x.security_id.is_unique
