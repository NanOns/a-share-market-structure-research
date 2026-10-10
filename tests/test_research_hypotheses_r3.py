from workbench_service.research_hypotheses_r3 import competing_explanations

def cells():
    return {k:dict(value=v,quality='OBSERVED',source={'sha256':'fixture'},adjustment_basis='QFQ_T0')
            for k,v in [('close',12),('ma20',10),('ret5',.1),('rps20',80)]}

def test_competing_explanations_preserve_actual_evidence_and_no_probability():
    f=cells();r=competing_explanations(f)
    assert r['status']=='READY' and len(r['items'])==2
    assert r['evidence']==f and r['probability'] is None
    assert r['items'][0]['current_support'] and not r['items'][1]['current_support']
    f['close']['value']=9
    r=competing_explanations(f)
    assert not r['items'][0]['current_support'] and r['items'][1]['current_support']

def test_unknown_or_unbound_facts_do_not_generate_specific_explanations():
    f=cells();f['ret5']['quality']='UNKNOWN'
    assert competing_explanations(f)['items']==[]
    f=cells();f['close']['source']=None
    assert competing_explanations(f)['status']=='SOURCE_INCOMPLETE'

def test_nonfinite_fact_is_not_evidence():
    f=cells();f['ma20']['value']=float('nan')
    assert competing_explanations(f)['missing_fields']==['ma20']

def test_raw_price_cannot_be_compared_to_adjusted_ma():
    f=cells();f['close']['adjustment_basis']='RAW'
    assert competing_explanations(f)['missing_fields']==['CONSISTENT_PRICE_BASIS']
