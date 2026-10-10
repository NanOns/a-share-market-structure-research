from copy import deepcopy
import pytest
from workbench_analysis.fep_e5.admission import evaluate, frozen_equal, REASONS, current_gate
from pathlib import Path

def test_current_historical_models_do_not_promote():
    gate=current_gate(Path(__file__).resolve().parents[2])
    assert gate['historical_engineering_model_count']==3
    assert 'MODEL_NOT_ACCEPTED' in gate['reasons']
    assert 'MODEL_NOT_FOUND' not in gate['reasons']
    assert not gate['production_authorized']
    assert all(v['value'] is None for v in gate['fields'].values())

@pytest.mark.parametrize('key',list(REASONS))
def test_explicit_closed_reasons(key):
    absent=evaluate()
    engineering=evaluate({'production_role':'NONE'})
    assert key in set(absent['reasons'])|set(engineering['reasons'])
    assert REASONS[key]

@pytest.mark.parametrize('field',['accepted_at','revision','model_id','input_digest','axes'])
def test_frozen_prediction_all_fields_immutable(field):
    old=dict(accepted_at='2026-10-06T00:00:00Z',revision=1,model_id='A',input_digest='a',axes={})
    changed=deepcopy(old);changed[field]='changed'
    with pytest.raises(ValueError,match='FROZEN_PREDICTION_MUTATION'):frozen_equal(old,changed)
    assert frozen_equal(old,deepcopy(old))==old

def test_engineering_shadow_grant_cannot_authorize_current_production():
    request=dict(scope_id='S',target_id='T',horizon='T1',feature_contract_id='F',model_set_id='M',model_revision=1,capability='MODEL_DISPLAY')
    grant=dict(request,capability='SHADOW_INFERENCE',formal_approval=True,active=True)
    gate=evaluate({'production_role':'ACCEPTED_PRODUCTION'},accepted=True,request=request,grant=grant,input_asof=True,mature=True,scoring=True)
    assert gate['reasons']==['GRANT_MISSING']

def test_actual_ledger_put_rejects_frozen_clock_change():
    from workbench_analysis.fep_e5.ledger import Ledger
    class ExistingOnlyLedger(Ledger):
        def fixture_guard(self):pass
        def get(self,table,key):return dict(revision=1,accepted_at='2026-10-06T00:00:00Z')
    ledger=ExistingOnlyLedger(None,historical_fixture=True)
    with pytest.raises(ValueError,match='FROZEN_PREDICTION_MUTATION'):
        ledger.put('predictions','same',dict(revision=1,accepted_at='2026-10-07T00:00:00Z'))
