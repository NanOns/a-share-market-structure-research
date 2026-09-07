import json
from pathlib import Path
import pandas as pd
def test_published_fields_exist():
 current=json.loads(Path('reports/current/CURRENT_RELEASE.json').read_text('utf8'))
 x=pd.read_csv(Path(current['latest_release']['release_path'])/'candidates.csv',nrows=1)
 assert {'primary_leader_sector_id','primary_leader_sector_name','primary_leader_sector_type','primary_leader_pattern','best_sector_name'}<=set(x.columns)
