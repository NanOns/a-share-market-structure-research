from workbench_analysis.today_research_rank_loo_v3_3 import current_loo,change_loo,support_audit,rank,simple_shadow,score_category
def members(vals):return [{'security_id':f'S{i}','ret1':v,'actual_bar':True} for i,v in enumerate(vals)]
def test_six_stock_loo_passes_after_target_removed():
 x=current_loo('S0',members([.5,.01,.02,.03,.04,.05,.06]),True);assert x['valid_members']==6 and x['support'] is True
def test_five_member_sector_cannot_pass_after_target_removed():
 x=current_loo('S0',members([.5,.01,.02,.03,.04]),True);assert x['support'] is None and x['reason']=='SAMPLE_INSUFFICIENT'
def test_track_false_is_known_failure_when_sample_complete():assert current_loo('X',members([.01]*6),False)['support'] is False
def test_missing_historic_membership_keeps_change_unknown():assert change_loo('S0',None,members([.1]*6),potential=True,metric='ret1')['support'] is None
def test_support_dedup_and_industry_theme_audit():
 x=support_audit([{'sector_id':'A','sector_type':'INDUSTRY','support':True},{'sector_id':'A','sector_type':'INDUSTRY','support':True},{'sector_id':'B','sector_type':'THEME','support':None}]);assert x['sector_relations_tested']==2 and x['support'] is True and x['unknown_relations_count']==1
def test_rank_keeps_unscored_and_primary_is_fixed_not_highest_score():
 rows=[{'security_id':'A','matched_categories':['RECOVERY_TURN','LAUNCH_CONFIRM'],'selection_mode':'INDEPENDENT','break_margin_close20':.02,'clv':.7,'amr20_mean_prior':1.5,'rps5_delta3':None,'freshness':.2,'liq20_amount':3e7},{'security_id':'B','matched_categories':['LAUNCH_CONFIRM'],'selection_mode':'INDEPENDENT','break_margin_close20':.02,'clv':.8,'amr20_mean_prior':1.8,'rps5_delta3':.1,'freshness':1,'liq20_amount':2e7}]
 out=rank(rows);assert out[0]['primary_category']=='LAUNCH_CONFIRM' and out[0]['rank_status']=='QUALIFIED_UNRANKED' and out[0]['category_rank'] is None;assert out[1]['category_rank']==1;assert {x['security_id'] for x in simple_shadow(out)}=={'A','B'}
def test_continue_score_is_bounded_and_missing_required_field_is_null():
 row={'slope20':.015,'r2_20':.8,'clv':.9,'amr20_mean_prior':1.2,'rps20':.95,'bias20':.04,'freshness':1}
 assert score_category('TREND_CONTINUE',row)==100
 row['rps20']=None;assert score_category('TREND_CONTINUE',row) is None
