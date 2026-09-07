from pathlib import Path
from production.daily import run_daily
def test_historical_rejected():assert run_daily(Path('.'),Path('D:/new_tdx'),'20200101')[0]==2
