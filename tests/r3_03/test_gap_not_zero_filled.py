import math
import numpy as np
from shadow_v2.diagnostics import nonoverlap_ranges,nonoverlap_vol
def test_insufficient_valid_observations_remain_missing():
 c=np.arange(20,dtype=float)+10;c[5]=np.nan
 assert all(math.isnan(x) for x in nonoverlap_ranges(c,c+1,c-1))
 assert all(math.isnan(x) for x in nonoverlap_vol(c))
