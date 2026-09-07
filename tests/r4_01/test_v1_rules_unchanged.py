import json
from common.identity import computation_identity
from pathlib import Path
ROOT=Path(__file__).parents[2]
def test_v1_identity():assert json.loads((ROOT/"reports/current/CURRENT_RELEASE.json").read_text("utf8"))["latest_release"]["computation_identity"]["sha256"]==computation_identity(ROOT)["sha256"]
