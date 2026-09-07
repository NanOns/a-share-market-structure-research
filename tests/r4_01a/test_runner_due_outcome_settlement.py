from run_live_forward import run
from .conftest import FakeServices
def test_due(live_root):
 x={"signal_observation_id":"old","horizon":1,"target_revision":1,"outcome_status":"OBSERVED"};r=run(root=live_root,tdx=live_root/"tdx",services=FakeServices(outcomes=[x]))[1];assert r["outcomes"]["observed"]==1
