from pathlib import Path
import json
from common.identity import computation_identity
ROOT=Path(__file__).resolve().parents[2]
def test_identity(): assert json.loads((ROOT/"reports/current/CURRENT_RELEASE.json").read_text("utf8"))["latest_release"]["computation_identity"]["sha256"]==computation_identity(ROOT)["sha256"]
