import pandas as pd
def test_same_date_replacement_has_one_key():
 x=pd.DataFrame({'date':[1,1],'id':['a','a']});new=x.iloc[-1:];combined=pd.concat([x[x.date<1],new]);assert len(combined)==1
