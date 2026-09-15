import pytest
from workbench_analysis.bundle_reporting_dimensions_v3_3 import enrich

def test_enrich_binds_same_day_market_and_volatility():
 rows=[{"security_id":"SH.1"}];market=[{"date":"2026-09-14","market_ret20_median":-.02}];factors=[{"security_id":"SH.1","date":"2026-09-14","VOLATILITY20":.03}]
 result=enrich(rows,market,factors,"2026-09-14")[0]
 assert result["market_strength"]==-.02 and result["volatility"]==.03
 assert result["market_strength_contract"] and result["volatility_contract"]

def test_missing_or_cross_day_dimensions_fail_closed():
 with pytest.raises(ValueError,match="MARKET_STRENGTH_UNAVAILABLE"):enrich([{"security_id":"SH.1"}],[],[],"2026-09-14")
 with pytest.raises(ValueError,match="VOLATILITY20_UNAVAILABLE"):enrich([{"security_id":"SH.1"}],[{"date":"2026-09-14","market_ret20_median":0}],[],"2026-09-14")
