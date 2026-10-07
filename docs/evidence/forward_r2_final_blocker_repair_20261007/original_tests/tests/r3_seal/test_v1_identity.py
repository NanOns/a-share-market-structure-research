import json
from .conftest import ROOT
def test_v1():
 pointer=json.loads((ROOT/"reports/current/CURRENT_RELEASE.json").read_text(encoding="utf-8"))
 seal=json.loads((ROOT/"reports/shadow/v2/20260904/integrated/R3_INTEGRATED_SEAL_RECEIPT.json").read_text())
 assert pointer["production_ready"] and seal["v1_baseline_run_id"]=="695c7ae5affd4abbb3d86eddb4b154e0"
