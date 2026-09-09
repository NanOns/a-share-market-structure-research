import json
from .conftest import ROOT
def test_no_future_outcomes_are_generated():
    rows=[]
    observation_root=ROOT/"data/forward/observations"
    sealed_dates=sorted(p.name for p in observation_root.iterdir() if p.is_dir())
    for p in observation_root.rglob("OUTCOME_BATCH.json"):
        rows.extend(json.loads(p.read_text("utf8")).get("rows",[]))
    assert all(row.get("signal_date") in sealed_dates for row in rows)
    assert all(row.get("target_trading_date") in sealed_dates for row in rows)
    assert all(str(row.get("target_trading_date")) > str(row.get("signal_date")) for row in rows)
    assert all(int(row.get("target_revision",0)) >= 1 for row in rows)
