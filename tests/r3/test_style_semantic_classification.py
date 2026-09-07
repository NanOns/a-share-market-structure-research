from shadow_v2.diagnostics import classify_style
def test_conservative_style():
 assert classify_style('昨日涨停')=='PRICE_BEHAVIOR' and classify_style('不可确认名称')=='UNKNOWN'
