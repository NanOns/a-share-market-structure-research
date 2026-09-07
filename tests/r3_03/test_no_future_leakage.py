import numpy as np
from shadow_v2.diagnostics import nonoverlap_ranges
def test_future_high_excluded_by_cutoff_slice():
 c=np.full(21,10.);h=np.r_[np.full(10,12.),np.full(10,11.),99.];l=np.r_[np.full(10,8.),np.full(10,9.),9.]
 assert nonoverlap_ranges(c[:20],h[:20],l[:20])==(.2,.4,.5)
