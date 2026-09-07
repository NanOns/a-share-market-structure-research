from pathlib import Path
def test_readonly():
 x=(Path(__file__).parents[2]/"run_live_forward.py").read_text();assert "tdx.write" not in x and "os.replace(tdx" not in x
