from common.identity import computation_identity
from common.v2_identity import v2_execution_identity

def test_v2_runtime_files_are_not_v1_computation_files():
    v1=set(computation_identity(".")["files"]);v2=set(v2_execution_identity(".")["files"])
    assert "src/common/identity.py" in v1
    assert "src/common/v2_identity.py" not in v1
    assert {"src/common/v2_identity.py","run_live_forward.py","src/forward/evaluation.py"}<=v2
