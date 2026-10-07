import json
import pyarrow.parquet as pq
from .conftest import ROOT
def test_unique():
 board=pq.read_table(ROOT/"reports/shadow/v2/20260904/priority/V2_UNIFIED_RESEARCH_BOARD.parquet").to_pandas()
 assert len(board)==board.security_id.nunique()==1015
