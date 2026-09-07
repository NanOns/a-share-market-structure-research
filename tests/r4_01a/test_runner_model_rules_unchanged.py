from pathlib import Path
def test_no_rules():assert "shadow_v2/" not in (Path(__file__).parents[2]/"run_live_forward.py").read_text().replace('reports/shadow_v2/','')
