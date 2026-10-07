import json
from .conftest import ROOT
def test_binding():
 x=json.loads((ROOT/"data/forward/observations/20260904/revision_3/OBSERVATION_IDENTITY.json").read_text(encoding="utf-8"));assert all(x[k] for k in ("v1_computation_identity","r3_integrated_shadow_identity","priority_shadow_identity","source_revision_id"))
