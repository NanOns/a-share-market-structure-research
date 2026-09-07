import pandas as pd
from run_live_forward import run
from .conftest import FakeServices
def test_source_revised(live_root):
 run(root=live_root,tdx=live_root/"tdx",services=FakeServices("revision"));x=pd.read_parquet(live_root/"data/forward/observations/20260904/revision_2/FORWARD_OBSERVATION.parquet");assert set(x.candidate_state)=={"SOURCE_REVISED"}
