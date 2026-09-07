from pathlib import Path
import json
from common.identity import computation_identity
ROOT=Path(__file__).resolve().parents[2]
def test_v1_computation_identity_is_frozen():
    x=json.loads((ROOT/"reports/current/CURRENT_RELEASE.json").read_text("utf8"))
    assert x["latest_release"]["computation_identity"]["sha256"] == computation_identity(ROOT)["sha256"]
