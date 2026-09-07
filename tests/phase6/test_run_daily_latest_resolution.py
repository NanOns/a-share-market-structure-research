from pathlib import Path
from production.daily import latest_resolution
def test_latest_is_local_and_calendar():
 r=latest_resolution(Path('.'),Path('D:/new_tdx'));assert r['resolved_cutoff_date']==r['master_calendar_latest_session']==r['local_tdx_latest_session']
