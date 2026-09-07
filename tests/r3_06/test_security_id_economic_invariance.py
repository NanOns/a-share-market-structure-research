import inspect
from shadow_v2.research_priority import research_band
def test_no_id():assert "security_id" not in inspect.signature(research_band).parameters
