import pytest,pandas as pd
from forward.live import publish_observation
def test_conflict(live_root):
 frame=pd.DataFrame([{"security_id":"x","candidate_state":"NEW","shadow_research_band":"CORE"}]);receipt={"outcomes":{}}
 publish_observation(live_root,"20260907",1,frame,{"observation_id":"a"},receipt)
 with pytest.raises(RuntimeError,match="CONFLICT"):publish_observation(live_root,"20260907",1,frame,{"observation_id":"b"},receipt)
