from scripts.build_fp06_sector_v2 import width_facts

def test_width_adapter_rejects_missing_stale_or_unknown_basis_dependencies():
    day='2026-09-30'
    def row(close=10,ma=9,date=day,basis='accepted',quality='ACCEPTED'):
        return dict(trade_date=date,price_basis_id=basis,fields={
            'close':dict(value=close,quality=quality,max_source_date=date),
            'ma20':dict(value=ma,quality='ACCEPTED',max_source_date=date)})
    values={'positive':row(),'equal':row(ma=10),'negative':row(ma=11),'missing':row(ma=None),
        'stale':row(date='2026-09-29'),'basis':row(basis=None),'unknown':row(quality='UNKNOWN')}
    result=width_facts(values,day)
    assert [result[k]['fields']['close_minus_ma20']['value'] for k in ('positive','equal','negative')]==[1,0,-1]
    for key in ('missing','stale','basis','unknown'):
        assert result[key]['fields']['close_minus_ma20']['quality']=='UNKNOWN'
    assert all('close_minus_ma20' not in row['fields'] for row in values.values())
