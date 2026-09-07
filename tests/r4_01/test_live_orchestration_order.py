from forward.live import ORCHESTRATION_ORDER
def test_order():assert len(ORCHESTRATION_ORDER)==9 and ORCHESTRATION_ORDER[0].startswith("RESOLVE") and ORCHESTRATION_ORDER[-1].startswith("PUBLISH")
