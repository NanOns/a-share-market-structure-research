"""Independent legacy scanner and stock ratio formula oracles, no acceptance claim."""
from copy import deepcopy
from datetime import date,timedelta
import ast
from scripts.v4_11_candidate_inputs_r2 import projection,positive_values,seal
from src.v4.confirmation import package,exact,bound,detect_confirmation
from scripts.next_round_bundle_r2 import bind

def verify():
    c,m,p,a,scanner=package();ns={}
    exec(compile(exact(m['legacy_source']).read_text(encoding='utf8'),m['legacy_source']['path'],'exec'),ns)
    source_oracle=ns['scan_today_research'];results=[]
    probes=[('launch','clv',.60,.5999),('pullback','pullback_episode_confirmed',True,False),
        ('recovery_turn','clv',.55,.5499),('trend_continue','rps20',.70,.6999)]
    for branch,field,boundary,negative in probes:
        for label,value,expected in [('positive',positive_values()[field],True),('negative',negative,False),('boundary',boundary,True),('UNKNOWN',None,None)]:
            v=positive_values();v[field]=value;got=source_oracle(v)
            assert got[branch]['eligible'] is expected and got==scanner(v)
            results.append(dict(branch=branch,probe=label,expected=expected,actual=got[branch]['eligible']))
    for branch,key,values in [('launch','AMR20_GTE_120',[(1.2,True),(1.1999,False),(None,None)]),
        ('recovery_turn','AMR20_GTE_105',[(1.05,True),(1.0499,False),(None,None)]),
        ('trend_continue','AMR20_IN_080_250',[(.8,True),(2.5,True),(.7999,False),(2.5001,False),(None,None)])]:
        for value,expected in values:
            v=positive_values();v['amr20_mean_prior']=value
            assert source_oracle(v)[branch]['checks'][key] is expected
            row=detect_confirmation(projection(v))['rows'][0]
            canonical=m['scenario_mapping'][{'launch':'LAUNCH','pullback':'PULLBACK'}.get(branch,branch.upper())]
            assert row['raw_predicates'][canonical][key] is expected
            assert not any('AUD-AMOUNT-A-06' in reason for reason in row['unknown_predicates'])
            results.append(dict(branch=branch,probe='STOCK_AMR20',value=value,expected=expected))
    erratum=bound(c['semantic_erratum']);factor_ns={}
    source=exact(erratum['source']).read_text(encoding='utf8')
    funcs={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
    assert funcs==erratum['exact_function_AST']
    exec(compile(source,erratum['source']['path'],'exec'),factor_ns)
    bars=[];target=(date(2026,8,1)+timedelta(days=20)).isoformat()
    for i in range(21):
        bars.append(dict(date=(date(2026,8,1)+timedelta(days=i)).isoformat(),session_index=i,anchor_cutoff=target,
            has_actual_bar=True,is_synthetic_fill=False,price_basis=factor_ns['PRICE_BASIS'],open=10.,high=11.,low=9.,close=10.,
            raw_open=10.,raw_close=10.,volume=100.,amount=100. if i<20 else 250.))
    ratio=factor_ns['calculate_today_facts'](bars)['amr20_mean_prior']
    assert ratio==250./(sum(r['amount'] for r in bars[:-1])/20)==2.5
    assert ratio!=250./(sum(r['amount'] for r in bars[-20:])/20)
    for mutation in ('missing','suspended','zero','gap','anchor'):
        x=deepcopy(bars)
        if mutation=='missing':x[0]['amount']=None
        if mutation=='suspended':x[0]['has_actual_bar']=False
        if mutation=='zero':x[0]['amount']=0.
        if mutation=='gap':x[0]['session_index']=-2
        if mutation=='anchor':x[0]['anchor_cutoff']='2099-01-01'
        try:
            value=factor_ns['calculate_today_facts'](x)['amr20_mean_prior'];assert mutation not in ('gap','anchor') and value is None
        except ValueError:assert mutation in ('gap','anchor')
    fixed=projection(positive_values());expected=detect_confirmation(fixed)
    # A04 has no input slot or lookup in the stock detector. Opening/closing arbitrary
    # sector authority cannot alter the same sealed stock publication.
    for state in ('OPEN','CLOSED','UNKNOWN'):
        from unittest.mock import patch
        with patch('workbench_analysis.amount_a_authority_r2.evaluate_amount_a',create=True,side_effect=AssertionError('SECTOR_LOOKUP_FORBIDDEN')):
            assert detect_confirmation(fixed)==expected
    return dict(status='PASS_ENGINEERING',source=bind(m['legacy_source']['path']),factor_source=erratum['source'],
        probes=results,stock_formula_ratio=ratio,prior_window_excludes_target=True,missing_window_propagates_UNKNOWN=True,
        sector_amount_A_status_irrelevant=True,retired_golden='AMOUNT_A_DISABLED',
        active_golden={'AMR20_KNOWN_TRUE':'PASS','AMR20_KNOWN_FALSE':'PASS','AMR20_UNKNOWN':'PASS','SECTOR_AMOUNT_A_STATUS_IRRELEVANT':'PASS'},
        threshold_changes=False,external_acceptance=False)

if __name__=='__main__':
    import json
    print(json.dumps(verify(),ensure_ascii=False))
