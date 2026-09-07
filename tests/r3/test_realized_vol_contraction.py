import numpy as np
from shadow_v2.diagnostics import nonoverlap_vol
def test_vol_contraction():
 c=np.cumprod([1]+[1.1,.9]*5+[1.01,.99]*5);assert nonoverlap_vol(c)[2]<1
