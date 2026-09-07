from run_live_forward import run
from .conftest import FakeServices
def test_revision(live_root):
 c,r=run(root=live_root,tdx=live_root/"tdx",services=FakeServices("revision"));assert c==0 and r["revision_created"] and (live_root/"data/forward/observations/20260904/revision_2").exists()
