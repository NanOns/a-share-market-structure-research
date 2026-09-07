from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
def test_v1_count():
 import json
 p=Path(json.loads((ROOT/"reports/current/CURRENT_RELEASE.json").read_text("utf8"))["latest_release"]["release_path"])/"stocks.csv";x=pd.read_csv(p,usecols=["sector_leader"]);assert x.sector_leader.astype(str).str.lower().eq("true").sum()==505
