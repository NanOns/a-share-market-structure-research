from pathlib import Path
from .conftest import ROOT
def test_artifacts():
 data=ROOT/"data/forward/observations/20260904/revision_3";report=ROOT/"reports/forward/20260904/revision_3"
 assert {"FORWARD_OBSERVATION.parquet","OBSERVATION_IDENTITY.json","OUTCOME_BATCH.json"}<={p.name for p in data.iterdir()}
 assert {"DAILY_FORWARD_CAPTURE_RECEIPT.json","manifest.json","STATE_TRANSITION_AUDIT.json","DUE_OUTCOME_AUDIT.json"}<={p.name for p in report.iterdir()}
