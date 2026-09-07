import inspect
from shadow_v2.sector_leader import classify
def test_membership_absent(): assert "count" not in inspect.signature(classify).parameters
