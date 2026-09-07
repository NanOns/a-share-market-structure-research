from pathlib import Path
def test_no_write_api():
 text=(Path(__file__).parents[2]/"run_live_forward.py").read_text("utf8");assert "TDX/" not in text or ".write_" not in text
