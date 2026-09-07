from forward.live import target_for_horizon
def test_trading_days():assert target_for_horizon(["20260904","20260907","20260908"],"20260904",1)=="20260907"
