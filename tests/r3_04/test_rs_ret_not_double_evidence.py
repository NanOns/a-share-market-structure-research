import inspect
from shadow_v2.sector_leader import classify
def test_ret_rank_absent_from_classifier(): assert "ret" not in inspect.signature(classify).parameters
