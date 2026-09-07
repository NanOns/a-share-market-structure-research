import json
import pyarrow.parquet as pq
from pathlib import Path
ROOT=Path(__file__).parents[2]
def test_v2_identity():
 x=json.loads((ROOT/"reports/shadow/v2/20260904/priority/V2_PRIORITY_SHADOW_IDENTITY.json").read_text())
 board=pq.read_table(ROOT/"reports/shadow/v2/20260904/priority/V2_UNIFIED_RESEARCH_BOARD.parquet").to_pandas()
 assert len(x["sha256"])==64 and len(board)==1015 and board.security_id.is_unique
