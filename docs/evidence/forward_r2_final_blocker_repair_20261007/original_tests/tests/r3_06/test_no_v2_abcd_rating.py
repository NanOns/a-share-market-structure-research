from pathlib import Path
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[2]
def test_no_rating():assert not any("rating" in c.lower() or "score" in c.lower() for c in pq.read_table(ROOT/"reports/shadow/v2/20260904/priority/V2_UNIFIED_RESEARCH_BOARD.parquet").column_names)
