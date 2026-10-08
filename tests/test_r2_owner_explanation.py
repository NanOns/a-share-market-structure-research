from workbench_service.stock_views import explanation

class Reader:
    def envelope(self,**kwargs):return kwargs

def test_fallback_remains_evidence_not_invented_waiting_condition(monkeypatch):
    monkeypatch.setattr("workbench_service.stock_views.membership_relations",lambda reader,item: {})
    item={'fields':{'transition_reasons':{'value':['REQUIRED_FACTS_UNKNOWN_PRESERVE'],'quality':'KNOWN'},'unknown_predicates':{'value':['SEED'],'quality':'KNOWN'}}}
    result=explanation(Reader(),item)
    assert result['owner_explanations']['why_now']['source_field']=='transition_reasons'
    assert result['owner_explanations']['waiting_for']['basis']=='MISSING_PREDICATE_EVIDENCE_ONLY'
    assert result['invalid_if'] is None and result['H']==[]
    assert {d['field'] for d in result['owner_specific_debt']}=={'why_now','waiting_for','invalid_if','hypothesis'}

def test_explicit_owner_fields_override_fallback_and_remove_debt(monkeypatch):
    monkeypatch.setattr("workbench_service.stock_views.membership_relations",lambda reader,item: {})
    item={'fields':{'why_now':{'value':['OWNER_REASON'],'quality':'KNOWN'},'waiting_for':{'value':['OWNER_WAIT'],'quality':'KNOWN'},'unknown_predicates':{'value':['SEED'],'quality':'KNOWN'}}}
    result=explanation(Reader(),item)
    assert result['owner_explanations']['waiting_for']['value']==['OWNER_WAIT']
    assert result['owner_explanations']['why_now']['basis']=='EXPLICIT_OWNER_FIELD'
    assert {d['field'] for d in result['owner_specific_debt']}=={'invalid_if','hypothesis'}
