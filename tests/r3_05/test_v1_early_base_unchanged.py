from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
def test_count():
 import json
 p=Path(json.loads((ROOT/"reports/current/CURRENT_RELEASE.json").read_text("utf8"))["latest_release"]["release_path"])/"stocks.csv";x=pd.read_csv(p,usecols=["early_mover"]);assert x.early_mover.astype(str).str.lower().eq("true").sum()==86
