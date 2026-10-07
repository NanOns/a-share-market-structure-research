import json
from .conftest import ROOT
def test_frozen():assert json.loads((ROOT/"reports/shadow/v2/20260904/integrated/R3_INTEGRATED_SEAL_RECEIPT.json").read_text())["semantic_freeze_pass"]
