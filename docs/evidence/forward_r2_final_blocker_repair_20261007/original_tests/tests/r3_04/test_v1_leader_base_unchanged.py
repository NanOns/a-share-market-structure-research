from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
def test_v1_count():
 p=ROOT/"reports/releases/20260904/695c7ae5affd4abbb3d86eddb4b154e0/stocks.csv";x=pd.read_csv(p,usecols=["sector_leader"]);assert x.sector_leader.astype(str).str.lower().eq("true").sum()==505
