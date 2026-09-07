import numpy as np
from shadow_v2.diagnostics import nonoverlap_ranges
def test_windows_are_prior_then_recent_ten():
 close=np.full(20,10.);high=np.r_[np.full(10,12.),np.full(10,11.)];low=np.r_[np.full(10,8.),np.full(10,9.)]
 recent,prior,ratio=nonoverlap_ranges(close,high,low)
 assert (recent,prior,ratio)==(.2,.4,.5)
