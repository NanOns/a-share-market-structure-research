from copy import deepcopy
import pytest
from src.v4.confirmation_events_candidate_r4 import event_unknown_reasons

def state(**changes):
    r=dict(state_freshness='FRESH',validity='VALID',final_eligibility='TRUE',maturity='CONFIRMED',scenario_status='KNOWN')
    r.update(changes);return r

@pytest.mark.parametrize('changes',[{'state_freshness':'STALE'},{'validity':'UNKNOWN'},{'final_eligibility':'UNKNOWN'},{'maturity':'UNKNOWN'}])
def test_unknown_prior_cannot_be_false(changes):
    assert 'UNKNOWN_PRIOR_D2_REQUIRED_FACTS' in event_unknown_reasons(state(),state(**changes))

@pytest.mark.parametrize('changes',[{'state_freshness':'STALE'},{'validity':'UNKNOWN'},{'final_eligibility':'UNKNOWN'}])
def test_unknown_current_not_deterministic(changes):
    assert 'UNKNOWN_CURRENT_D2_REQUIRED_FACTS' in event_unknown_reasons(state(**changes),state())

def test_unknown_prior_scenario_with_active_endpoints():
    assert event_unknown_reasons(state(),state(scenario_status='UNKNOWN'))==['UNKNOWN_PRIOR_D2_SCENARIO']

def test_true_prior_false_current_is_known_transition():
    assert event_unknown_reasons(state(final_eligibility='FALSE',maturity='NONE'),state())==[]
