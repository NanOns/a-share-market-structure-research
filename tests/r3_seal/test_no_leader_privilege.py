import sys
from .conftest import ROOT
sys.path.insert(0,str(ROOT/"src"));from shadow_v2.research_priority import research_band
def test_equal():assert research_band(["CORE",None])==research_band([None,"CORE"])
