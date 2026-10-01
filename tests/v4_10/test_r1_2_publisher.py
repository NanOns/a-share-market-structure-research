import pytest
from src.v4.research_state_persistence import persist,publish_state
from scripts.v4_10_r1_2_fixtures import synthetic_input,publisher_scope

def test_output_rows_are_not_a_controlled_publisher_input(pg):
    with pytest.raises(ValueError,match='CONTROLLED_REDUCER_PUBLISH_PATH_REQUIRED'):persist(pg,[{'maturity':'CONFIRMED'}],'FORGED_OUTPUT')
    with publisher_scope(pg):
        with pytest.raises(ValueError,match='MISSING_STATE_INPUT_FIELDS'):publish_state(pg,[{'maturity':'CONFIRMED'}],'FORGED_OUTPUT')

def test_owner_connection_does_not_implicitly_become_reducer_publisher(pg):
    with pytest.raises(ValueError,match='AUTHORIZED_REDUCER_PUBLISHER_ROLE_REQUIRED'):publish_state(pg,[synthetic_input()],'OWNER_IMPLICIT_PUBLISH')
