import json
from common.identity import computation_identity
from .conftest import ROOT
def test_v1():assert json.loads((ROOT/"reports/current/CURRENT_RELEASE.json").read_text("utf8"))["latest_release"]["computation_identity"]["sha256"]==computation_identity(ROOT)["sha256"]
