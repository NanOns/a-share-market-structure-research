from run_live_forward import run
from .conftest import FakeServices
def test_noop(live_root):
 c,r=run(root=live_root,tdx=live_root/"tdx",services=FakeServices("noop"));assert c==0 and r["status"]=="VERIFIED_NO_NEW_FORWARD_OBSERVATION" and not r["observation_written"]
