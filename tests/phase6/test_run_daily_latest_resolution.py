from pathlib import Path
from production.daily import latest_resolution
def test_latest_is_local_and_calendar():
 r=latest_resolution(Path('.'),Path('D:/new_tdx'))
 assert r['cutoff_status'] in {'NO_NEW_DATA','NORMAL_NEW_TRADING_DAY','WEEKEND_NO_NEW_DATA','HOLIDAY_NO_NEW_DATA','PARTIAL_UPDATE','INVALID_FUTURE_OUTLIER','INPUT_NOT_READY'}
 if r['cutoff_status']=='NORMAL_NEW_TRADING_DAY':assert r['resolved_cutoff_date']==r['local_tdx_latest_session']
 else:assert r['resolved_cutoff_date']==r['master_calendar_latest_session']
