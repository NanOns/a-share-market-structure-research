import pyarrow.parquet as pq
from .conftest import ROOT
def test_seed():
 x=pq.read_table(ROOT/"data/forward/observations/20260904/revision_1/FORWARD_OBSERVATION.parquet",columns=["candidate_state"]).to_pandas();assert len(x)==1015 and x.candidate_state.eq("BASELINE").all()
