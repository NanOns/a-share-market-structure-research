from run_live_forward import run
from .conftest import FakeServices
def test_full(live_root):
 c,r=run(root=live_root,tdx=live_root/"tdx",services=FakeServices());assert c==0 and r["observation_written"] and r["daily_receipt_written"]
