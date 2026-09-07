import pandas as pd
from scanner.stock_scanner import market_percentiles
def test_average_market_rank():
 d=pd.DataFrame({'universe_status':['IN_NORMAL_UNIVERSE']*3,'RS5':[1,1,2],'RS20':[1,2,3],'RS60':[1,2,3],'VOLATILITY20':[1,2,3],'AMOUNT_RATIO_5_20':[1,2,3]});r=market_percentiles(d);assert list(r.stock_rs5_pct)==[.5,.5,1]
