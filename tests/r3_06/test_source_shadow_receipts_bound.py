from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
def test_bound():
 x=json.loads((ROOT/"reports/shadow/v2/20260904/priority/V2_PRIORITY_SHADOW_IDENTITY.json").read_text("utf8"));assert set(x["source_artifacts"])=={"R3-01","R3-02","R3-03","R3-04","R3-05"} and all(v["sha256"] for v in x["source_artifacts"].values())
