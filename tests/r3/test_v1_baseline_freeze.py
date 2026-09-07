import json
from pathlib import Path
def test_current_release_is_bound():
 x=json.load(open('reports/current/CURRENT_RELEASE.json',encoding='utf8'))['latest_release'];assert Path(x['release_path']).is_dir() and (Path(x['release_path'])/'manifest.json').is_file()
