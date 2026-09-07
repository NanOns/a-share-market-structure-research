from run_live_forward import run
from .conftest import FakeServices
def test_identity(live_root):assert run(root=live_root,tdx=live_root/"tdx",services=FakeServices(bad_model=True))[1]["error"]=="MODEL_VERSION_CHANGED"
