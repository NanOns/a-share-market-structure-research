"""Publication-layer transition quality; fixtures never represent market facts."""
from copy import deepcopy
import pytest
from src.v4 import confirmation_events_candidate_r3 as candidate


def state(**changes):
    value=dict(entity_id='QUALITY_ORACLE_ENTITY',state_freshness='FRESH',maturity='CONFIRMED',
        final_eligibility='TRUE',validity='VALID',scenario='LAUNCH_CONFIRM',scenario_status='KNOWN')
    value.update(changes)
    return value


def publish(monkeypatch,current,prior,primary_event='NEW_CONFIRMED',revision_of=None):
    # Isolate only the publication wrapper under test. The already frozen raw
    # runtime is exercised separately by the D2/event contract tests.
    raw=dict(entity_id=current['entity_id'],primary_event=primary_event,event_types=[primary_event],
        event_predicates={primary_event:True},prior_session_state_head_digest='FROZEN_PRIOR_ORACLE',
        permissions=dict(production=False,shadow=False,focus=False),revision_of=revision_of)
    calls=[]
    def runtime():
        def exact_predicates(publication,frozen,*,revision_of=None):
            calls.append(revision_of)
            return [deepcopy(raw)]
        return exact_predicates
    monkeypatch.setattr(candidate,'runtime',runtime)
    result=candidate.events(dict(rows=[current]),dict(rows=[] if prior is None else [prior]),revision_of=revision_of)[0]
    assert calls==[revision_of]
    for field in ('primary_event','event_types','event_predicates','prior_session_state_head_digest','revision_of'):
        assert result[field]==raw[field]
    assert result['accepted'] is False and result['AS_RECORDED'] is False
    assert result['permissions']==dict(production=False,shadow=False,focus=False,global_mandatory_adoption=False)
    return result


@pytest.mark.parametrize('change',[
    dict(state_freshness='STALE',maturity='NONE',validity='UNKNOWN',final_eligibility='UNKNOWN'),
    dict(final_eligibility='UNKNOWN'),dict(validity='UNKNOWN'),
])
def test_unknown_prior_never_becomes_known_new_confirmed(monkeypatch,change):
    result=publish(monkeypatch,state(),state(**change))
    assert result['primary_event']=='NEW_CONFIRMED'  # Exact raw diagnostic retained.
    assert result['effective_event']=='UNKNOWN'
    assert result['event_quality']=='UNKNOWN_PRIOR_D2_REQUIRED_FACTS'
    assert result['event_unknown_predicates']==['UNKNOWN_PRIOR_D2_REQUIRED_FACTS']


def test_fresh_known_unconfirmed_prior_allows_new_confirmed(monkeypatch):
    prior=state(maturity='NONE',final_eligibility='FALSE',scenario='NONE')
    result=publish(monkeypatch,state(),prior)
    assert result['effective_event']=='NEW_CONFIRMED'
    assert result['event_quality']=='KNOWN' and result['event_unknown_predicates']==[]


def test_new_entity_remains_first_observed_without_invented_prior(monkeypatch):
    result=publish(monkeypatch,state(),None,primary_event='FIRST_OBSERVED')
    assert result['effective_event']=='FIRST_OBSERVED'
    assert result['event_quality']=='KNOWN' and result['event_unknown_predicates']==[]


def test_missing_current_required_facts_still_fail_closed(monkeypatch):
    result=publish(monkeypatch,state(state_freshness='STALE',final_eligibility='UNKNOWN',validity='UNKNOWN'),state())
    assert result['effective_event']=='UNKNOWN'
    assert result['event_quality']=='UNKNOWN_CURRENT_D2_REQUIRED_FACTS'


def test_unknown_prior_scenario_cannot_publish_known_scenario_change(monkeypatch):
    result=publish(monkeypatch,state(),state(scenario_status='UNKNOWN'),primary_event='SCENARIO_CHANGED')
    assert result['effective_event']=='UNKNOWN'
    assert result['event_unknown_predicates']==['UNKNOWN_PRIOR_D2_SCENARIO']


def test_same_day_revision_does_not_replace_unknown_frozen_prior(monkeypatch):
    result=publish(monkeypatch,state(),state(state_freshness='STALE'),revision_of='CURRENT_REVISION_ORACLE')
    assert result['revision_of']=='CURRENT_REVISION_ORACLE'
    assert result['prior_session_state_head_digest']=='FROZEN_PRIOR_ORACLE'
    assert result['effective_event']=='UNKNOWN'
