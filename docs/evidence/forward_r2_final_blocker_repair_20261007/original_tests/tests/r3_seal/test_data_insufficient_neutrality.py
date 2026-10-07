import json
from .conftest import ROOT
def test_neutral():
 x=json.loads((ROOT/"reports/shadow/v2/20260904/integrated/R3_INTEGRATED_SEAL_RECEIPT.json").read_text())
 assert x["data_insufficient_neutral_pass"]
