import json
from .conftest import ROOT
def test_chain():
 x=json.loads((ROOT/"reports/shadow/v2/20260904/integrated/R3_INTEGRATED_SEAL_RECEIPT.json").read_text())
 if x["final_status"]=="PASS":
  assert json.loads((ROOT/"reports/shadow/v2/20260904/integrated/R3_RECEIPT_CHAIN_AUDIT.json").read_text())["pass"]
 else:
  assert x["final_status"]=="BLOCKED" and x["blocking_reasons"]
