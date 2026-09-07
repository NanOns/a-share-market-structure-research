import sys
from .conftest import ROOT
sys.path.insert(0,str(ROOT/"src"));from shadow_v2.research_priority import research_band
def test_fixture():assert research_band(["CORE",None])=="CORE_RESEARCH"
