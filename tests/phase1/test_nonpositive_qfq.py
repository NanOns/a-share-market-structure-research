from factors.engine import calculate

def test_nonpositive_blocks_only_corresponding_price_window(context):
    context.loc[80,'close']=-1
    r,_=calculate(context)
    assert r['RET60']!=r['RET60']
    assert r['RET5']==r['RET5']
    assert r['MA60']==r['MA60']
    assert 'NONPOSITIVE_QFQ' in r['RET60__quality_flag']
