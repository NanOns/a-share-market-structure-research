import json
from .conftest import ROOT
def test_identity():
 x=json.loads((ROOT/"reports/shadow/v2/20260904/integrated/R3_INTEGRATED_SEAL_RECEIPT.json").read_text())
 identity=ROOT/"reports/shadow/v2/20260904/integrated/R3_INTEGRATED_SHADOW_IDENTITY.json"
 if x["final_status"]=="PASS":
  value=json.loads(identity.read_text());assert len(value["receipt_chain"])==7 and len(value["sha256"])==64
 else:
  assert x["final_status"]=="BLOCKED" and not identity.exists()
