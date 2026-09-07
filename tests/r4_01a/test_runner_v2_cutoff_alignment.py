from run_live_forward import run
from .conftest import FakeServices
def test_alignment(live_root):assert run(root=live_root,tdx=live_root/"tdx",services=FakeServices(bad_cutoff=True))[1]["error"]=="V2_CUTOFF_ALIGNMENT_BLOCKED"
