from run_live_forward import run,ORCHESTRATION_ORDER
from .conftest import FakeServices
def test_nine(live_root):assert run(root=live_root,tdx=live_root/"tdx",services=FakeServices())[1]["steps_completed"]==list(ORCHESTRATION_ORDER)
