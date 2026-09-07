import pandas as pd
def test_old_new_equivalent_on_shared_rank():
    p=pd.Series([.1,.3,.8,.9,1.]);old=(p>=.8)&((p>=.7)|False);new=p>=.8;assert old.equals(new)
