import json
import pyarrow.parquet as pq
from .conftest import ROOT
def test_absent():
 x=json.loads((ROOT/"reports/shadow/v2/20260904/integrated/R3_INTEGRATED_SEAL_RECEIPT.json").read_text())
 board=pq.read_table(ROOT/"reports/shadow/v2/20260904/priority/V2_UNIFIED_RESEARCH_BOARD.parquet").to_pandas()
 assert x["no_global_weighted_score_pass"] and x["no_v2_abcd_rating_pass"]
 assert not any(c.lower() in {"v2_rating","v2_a","v2_b","v2_c"} for c in board.columns)
