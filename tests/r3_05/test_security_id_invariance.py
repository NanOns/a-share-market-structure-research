import inspect
from shadow_v2.early_mover import classify
def test_no_id_input():assert "security_id" not in inspect.signature(classify).parameters
