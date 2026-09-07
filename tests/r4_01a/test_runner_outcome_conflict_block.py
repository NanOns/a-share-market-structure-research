import pytest
from forward.live import append_outcomes
def test_conflict(live_root):
 x={"signal_observation_id":"s","horizon":1,"target_revision":1,"v":1};append_outcomes(live_root,[x])
 with pytest.raises(RuntimeError):append_outcomes(live_root,[{**x,"v":2}])
