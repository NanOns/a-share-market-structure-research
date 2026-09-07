import pandas as pd
def test_exact_join_resolves():
 c=pd.DataFrame({'primary_leader_sector':['THEME:1']});s=pd.DataFrame({'primary_leader_sector':['THEME:1'],'name':['x'],'type':['THEME'],'pattern':['CURRENT_STRENGTH']});assert c.merge(s,on='primary_leader_sector').iloc[0]['name']=='x'
