import pandas as pd
from shadow_v21.pullback import anchored_diagnostics,classify_row

def test_latest_equal_peak_is_shared_by_depth_duration_and_amount_segments():
    dates=pd.date_range("2026-01-01",periods=6)
    result=anchored_diagnostics(dates,[8,10,9,10,9,8],[80,100,90,200,50,40])
    assert result["peak_date_v21"]==dates[3]
    assert result["days_since_peak_v21"]==2
    assert result["advance_amount_mean_v21"]==(80+100+90+200)/4
    assert result["pullback_amount_mean_v21"]==45
    assert result["advance_bar_count_v21"]+result["pullback_bar_count_v21"]==6

def test_no_post_peak_bar_is_data_insufficient_not_zero():
    result=anchored_diagnostics(pd.date_range("2026-01-01",periods=3),[8,9,10],[80,90,100])
    assert pd.isna(result["pullback_amount_ratio_v21"])
    assert result["pullback_bar_count_v21"]==0
    assert classify_row(True,result)["v21_pullback_class"]=="DATA_INSUFFICIENT"
