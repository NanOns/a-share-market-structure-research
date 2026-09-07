from factors.engine import calculate

def test_suspension_not_removed_from_window(context):
    context.loc[118,['close','amount','synthetic','state']]=[context.close.iloc[117],0,True,'SUSPENDED']
    context.loc[118,['high','low']]=float('nan')
    r,_=calculate(context)
    assert r['MA5__valid_sample_count']==5
    assert r['POS20']!=r['POS20']
    assert r['AMOUNT_MA5']==context.amount.tail(5).mean()
