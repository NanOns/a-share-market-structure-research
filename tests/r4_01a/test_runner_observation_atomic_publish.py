from run_live_forward import run
from .conftest import FakeServices
def test_atomic(live_root):
 c,r=run(root=live_root,tdx=live_root/"tdx",services=FakeServices(),fail_before_commit=True);assert c and not (live_root/"data/forward/observations/20260907").exists()
