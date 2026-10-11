import pandas as pd
import pytest
from workbench_analysis.full_loo_v3_3 import recompute_full_current_loo,FullLooV33Error
from tests.upgrade_v3.test_p12_12_full_loo import config,frames

def singleton():
    row=dict(sector_id='A',sector_name='A',sector_type='INDUSTRY',sector_role='INDUSTRY',security_id='S',trade_date='2026-09-15',ret1=.01)
    return pd.DataFrame([row]),pd.DataFrame([row,dict(row,security_id='OUTSIDE',ret1=-.1)])

def test_singleton_empty_sector_is_unknown_not_exception():
    members,market=singleton()
    row=recompute_full_current_loo(['S'],members,market,config())['S']
    assert row['support'] is None and row['unknown_relations']==1
    assert row['relations'][0]['reason']=='SECTOR_EMPTY_AFTER_EXCLUSION'

def test_no_members_and_no_related_sector_are_known_false():
    members,market=singleton()
    for source in (members,members.iloc[:0]):
        row=recompute_full_current_loo(['OUTSIDE2'],source,market,config())['OUTSIDE2']
        assert row['support'] is False and row['tested_relations']==0

@pytest.mark.parametrize('market_case',['initial_empty','target_only'])
def test_market_empty_has_unique_controlled_rejection(market_case):
    members,market=singleton()
    market=market.iloc[:0] if market_case=='initial_empty' else market.iloc[:1]
    with pytest.raises(FullLooV33Error,match='^FULL_LOO_MARKET_EMPTY_AFTER_EXCLUSION$'):
        recompute_full_current_loo(['S'],members,market,config())

def test_other_sector_does_not_change_empty_related_classification():
    members,market=singleton()
    members=pd.concat([members,pd.DataFrame([dict(members.iloc[0],sector_id='OTHER',security_id='OUTSIDE')])],ignore_index=True)
    assert recompute_full_current_loo(['S'],members,market,config())['S']['relations'][0]['reason']=='SECTOR_EMPTY_AFTER_EXCLUSION'

def test_empty_shortcut_does_not_hide_invalid_dates():
    members,market=singleton();market.loc[1,'trade_date']='2026-09-16'
    with pytest.raises(FullLooV33Error,match='FULL_LOO_REQUIRES_ONE_TRADE_DATE'):
        recompute_full_current_loo(['S'],members,market,config())

@pytest.mark.parametrize('count',[2,6])
def test_remaining_medians_and_counts_independently(count):
    members,market=singleton()
    members=pd.DataFrame([dict(members.iloc[0],security_id=f'S{i}',ret1=.01*(i+1)) for i in range(count)])
    market=pd.concat([members[['security_id','trade_date','ret1']],market.iloc[1:][['security_id','trade_date','ret1']]],ignore_index=True)
    row=recompute_full_current_loo(['S0'],members,market,config())['S0']['relations'][0]
    import statistics
    assert row['member_count']==count-1
    assert row['m1']==statistics.median([.01*(i+1) for i in range(1,count)])
    assert row['market_m1']==statistics.median([.01*(i+1) for i in range(1,count)]+[-.1])
