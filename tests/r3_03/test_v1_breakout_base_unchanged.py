from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
def test_v1_count_304():
 import json
 p=Path(json.loads((ROOT/"reports/current/CURRENT_RELEASE.json").read_text("utf8"))["latest_release"]["release_path"])/"stocks.csv";x=pd.read_csv(p,usecols=["breakout_prep"])
 assert x.breakout_prep.astype(str).str.lower().eq("true").sum()==304
