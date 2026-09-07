import json
from .conftest import ROOT
def test_zero():
 rows=[]
 for p in (ROOT/"data/forward/observations").rglob("OUTCOME_BATCH.json"):rows.extend(json.loads(p.read_text("utf8")).get("rows",[]))
 assert rows==[]
