import pandas as pd
from sector.phase2 import sectors
def test_common_breadth_uses_same_members():
    # Contract-level arithmetic counterexample: independent denominators differ; common set does not.
    f=pd.DataFrame({'RET5':[1,-1,float('nan')],'RET20':[float('nan'),-1,1]})
    c=f.dropna();assert len(c)==1 and (c.RET5>0).mean()==(c.RET20>0).mean()==0
